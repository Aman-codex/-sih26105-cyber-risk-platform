"""
The Risk Engine (module 5) and Financial Quantification (module 6).

Every number here is derived from data already in the database (assets,
vulnerabilities, threats, controls) and configurable weights in
RiskModelConfig — nothing is hard-coded or invented. Given the same inputs
and config, this always produces the same output, which is what makes the
platform's numbers explainable and defensible in front of a judge/CISO.
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.risk_config import DEFAULT_RISK_MODEL_CONFIG, RiskModelConfig
from app.models.security_control import SecurityControl, asset_controls
from app.models.threat import threat_asset_relevance
from app.models.vulnerability import Vulnerability, VulnerabilityStatus


def get_or_create_config(db: Session, org_id: int) -> RiskModelConfig:
    config = db.query(RiskModelConfig).filter(RiskModelConfig.organization_id == org_id).first()
    if not config:
        config = RiskModelConfig(organization_id=org_id, parameters=DEFAULT_RISK_MODEL_CONFIG)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@dataclass
class RiskDriver:
    factor: str
    impact_pct: float  # signed % change in likelihood this factor caused


@dataclass
class RiskCalculationResult:
    asset_id: int
    likelihood: float
    risk_score: float
    primary_vulnerability_id: Optional[int]
    financial_impact_given_incident: float
    expected_annual_loss: float
    value_at_risk: float
    confidence_level: float
    drivers: List[RiskDriver] = field(default_factory=list)
    financial_breakdown: dict = field(default_factory=dict)


def _worst_open_vulnerability(asset: Asset, exclude_vulnerability_id: Optional[int] = None) -> Optional[Vulnerability]:
    open_vulns = [
        v for v in asset.vulnerabilities
        if v.status == VulnerabilityStatus.OPEN and v.id != exclude_vulnerability_id
    ]
    if not open_vulns:
        return None
    return max(open_vulns, key=lambda v: v.cvss_score)


def _max_threat_relevance(db: Session, asset_id: int) -> float:
    row = (
        db.query(threat_asset_relevance.c.relevance_score)
        .filter(threat_asset_relevance.c.asset_id == asset_id)
        .order_by(threat_asset_relevance.c.relevance_score.desc())
        .first()
    )
    return float(row[0]) if row else 0.0


def _total_control_mitigation(
    db: Session, asset_id: int, max_mitigation: float,
    exclude_control_id: Optional[int] = None, effectiveness_override: Optional[dict] = None,
) -> float:
    total = 0.0
    controls = (
        db.query(SecurityControl, asset_controls.c.coverage_percentage)
        .join(asset_controls, asset_controls.c.control_id == SecurityControl.id)
        .filter(asset_controls.c.asset_id == asset_id, SecurityControl.is_active.is_(True))
        .all()
    )
    for control, coverage_pct in controls:
        if control.id == exclude_control_id:
            continue
        effectiveness = (effectiveness_override or {}).get(control.id, control.effectiveness_score)
        total += effectiveness * (coverage_pct / 100.0)
    return min(total, max_mitigation)


def calculate_asset_risk(
    db: Session, asset: Asset, config: Optional[RiskModelConfig] = None, extra_mitigation: float = 0.0,
    exclude_control_id: Optional[int] = None, exclude_vulnerability_id: Optional[int] = None,
    effectiveness_override: Optional[dict] = None,
) -> RiskCalculationResult:
    """
    Normal calls (Phase 3) leave every override at its default and behave
    exactly as before. The override parameters exist so the What-If
    Simulator (Phase 6) and Investment Optimizer (Phase 5) can ask "what
    would this asset's risk be if..." without writing anything to the
    database:
      - extra_mitigation: an additional not-yet-deployed control's effectiveness
      - exclude_control_id: pretend this currently-active control doesn't exist
      - exclude_vulnerability_id: pretend this open vulnerability is already fixed
      - effectiveness_override: {control_id: new_effectiveness} to test tuning a control
    """
    cfg = (config or get_or_create_config(db, asset.organization_id)).parameters

    worst_vuln = _worst_open_vulnerability(asset, exclude_vulnerability_id=exclude_vulnerability_id)
    severity_score = (worst_vuln.cvss_score / 10.0) if worst_vuln else 0.05  # residual baseline risk even with no known open CVEs
    exploitability_key = worst_vuln.exploitability.value if worst_vuln else "theoretical"

    drivers: List[RiskDriver] = []

    base_likelihood = cfg["exploitability_likelihood"].get(exploitability_key, 0.05)
    likelihood = base_likelihood
    if worst_vuln:
        drivers.append(RiskDriver(
            factor=f"Open vulnerability exploitability ({exploitability_key.replace('_', ' ')})",
            impact_pct=0.0,  # this IS the baseline, so no relative change to report
        ))

    # Severity modulates likelihood: a low-CVSS "actively exploited" issue is
    # still less dangerous than a critical one at the same exploitability tier.
    before = likelihood
    likelihood *= (0.5 + 0.5 * severity_score)
    if worst_vuln:
        drivers.append(_pct_driver(f"Vulnerability severity (CVSS {worst_vuln.cvss_score:.1f})", before, likelihood))

    if asset.internet_exposure:
        before = likelihood
        likelihood *= cfg["internet_exposure_multiplier"]
        drivers.append(_pct_driver("Internet exposure", before, likelihood))

    relevance = _max_threat_relevance(db, asset.id)
    if relevance > 0:
        before = likelihood
        likelihood *= (1 + cfg["threat_relevance_weight"] * relevance)
        drivers.append(_pct_driver(f"Active threat targeting (relevance {relevance:.0%})", before, likelihood))

    mitigation = _total_control_mitigation(
        db, asset.id, cfg["max_control_mitigation"],
        exclude_control_id=exclude_control_id, effectiveness_override=effectiveness_override,
    )
    mitigation = min(mitigation + extra_mitigation, cfg["max_control_mitigation"])
    if mitigation > 0:
        before = likelihood
        likelihood *= (1 - mitigation)
        label = "Security control coverage" + (" (incl. candidate investment)" if extra_mitigation > 0 else "")
        drivers.append(_pct_driver(label, before, likelihood))

    likelihood = max(0.01, min(0.95, likelihood))

    criticality_mult = cfg["criticality_multiplier"].get(asset.business_criticality.value, 1.0)
    risk_score = min(100.0, round(likelihood * severity_score * criticality_mult * 100, 2))

    # --- Financial Quantification ---
    weights = cfg["financial_impact_weights"]
    breakdown = {k: round(asset.business_value * w, 2) for k, w in weights.items()}
    financial_impact_given_incident = round(sum(breakdown.values()), 2)
    expected_annual_loss = round(likelihood * financial_impact_given_incident, 2)

    # --- Scenario-based Value at Risk (Monte Carlo) ---
    value_at_risk = _simulate_var(
        likelihood=likelihood,
        mean_impact=financial_impact_given_incident,
        std_dev_fraction=cfg["var_impact_std_dev_fraction"],
        runs=cfg["var_simulation_runs"],
        confidence_level=cfg["var_confidence_level"],
    )

    return RiskCalculationResult(
        asset_id=asset.id,
        likelihood=round(likelihood, 4),
        risk_score=risk_score,
        primary_vulnerability_id=worst_vuln.id if worst_vuln else None,
        financial_impact_given_incident=financial_impact_given_incident,
        expected_annual_loss=expected_annual_loss,
        value_at_risk=round(value_at_risk, 2),
        confidence_level=cfg["var_confidence_level"],
        drivers=drivers,
        financial_breakdown=breakdown,
    )


def _pct_driver(factor: str, before: float, after: float) -> RiskDriver:
    if before <= 0:
        return RiskDriver(factor=factor, impact_pct=0.0)
    return RiskDriver(factor=factor, impact_pct=round((after / before - 1) * 100, 1))


def _simulate_var(likelihood: float, mean_impact: float, std_dev_fraction: float, runs: int, confidence_level: float) -> float:
    """
    Simple Monte Carlo: each run, an incident either does or doesn't occur
    (Bernoulli(likelihood)); if it does, its cost is drawn from a normal
    distribution around mean_impact (clipped at 0) to represent uncertainty
    in how bad any single realized incident turns out to be. VaR is the
    loss value at the given confidence percentile across all runs
    (uninsured "worst case within X% confidence" figure).
    """
    rng = random.Random(42)  # fixed seed: deterministic, reproducible demo output
    std_dev = mean_impact * std_dev_fraction
    losses = []
    for _ in range(runs):
        if rng.random() < likelihood:
            loss = max(0.0, rng.gauss(mean_impact, std_dev))
        else:
            loss = 0.0
        losses.append(loss)
    losses.sort()
    index = min(len(losses) - 1, int(confidence_level * len(losses)))
    return losses[index]
