"""
The What-If Simulator (module 10).

Every scenario here is computed by calling the exact same Risk Engine
(Phase 3) and Investment Optimizer (Phase 5) used everywhere else in the
platform — nothing is a separate, parallel calculation. Nothing in this
module writes to the database; every function returns a before/after
comparison for the caller to display, and the underlying data is
untouched, so a user can explore "what if" freely without any risk of
accidentally changing real records.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.security_control import SecurityControl, asset_controls
from app.models.vulnerability import Vulnerability
from app.services.investment_optimizer import estimate_investment_candidates, optimize_budget_allocation
from app.services.risk_engine import calculate_asset_risk, get_or_create_config


@dataclass
class AssetSnapshot:
    asset_id: int
    asset_name: str
    risk_score: float
    likelihood: float
    expected_annual_loss: float


@dataclass
class WhatIfResult:
    scenario_type: str
    description: str
    before: List[AssetSnapshot] = field(default_factory=list)
    after: List[AssetSnapshot] = field(default_factory=list)
    total_eal_before: float = 0.0
    total_eal_after: float = 0.0
    eal_change: float = 0.0  # negative = improvement (risk went down)
    investment_change: float = 0.0  # positive = additional annual spend, negative = savings
    rosi_percent: Optional[float] = None
    affected_asset_ids: List[int] = field(default_factory=list)


def _snapshot(asset: Asset, result) -> AssetSnapshot:
    return AssetSnapshot(
        asset_id=asset.id, asset_name=asset.name, risk_score=result.risk_score,
        likelihood=result.likelihood, expected_annual_loss=result.expected_annual_loss,
    )


def _finalize(scenario_type: str, description: str, before: List[AssetSnapshot], after: List[AssetSnapshot],
              investment_change: float, affected_asset_ids: List[int]) -> WhatIfResult:
    total_before = round(sum(s.expected_annual_loss for s in before), 2)
    total_after = round(sum(s.expected_annual_loss for s in after), 2)
    eal_change = round(total_after - total_before, 2)
    reduction = -eal_change  # positive when EAL went down
    rosi = round((reduction / investment_change) * 100, 1) if investment_change > 0 else None

    return WhatIfResult(
        scenario_type=scenario_type, description=description, before=before, after=after,
        total_eal_before=total_before, total_eal_after=total_after, eal_change=eal_change,
        investment_change=round(investment_change, 2), rosi_percent=rosi, affected_asset_ids=affected_asset_ids,
    )


def _get_org_assets(db: Session, org_id: int, asset_ids: Optional[List[int]] = None) -> List[Asset]:
    query = db.query(Asset).filter(Asset.organization_id == org_id)
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))
    return query.all()


def simulate_add_control(db: Session, org_id: int, control_id: int, asset_ids: Optional[List[int]] = None) -> WhatIfResult:
    control = db.query(SecurityControl).filter(SecurityControl.id == control_id, SecurityControl.organization_id == org_id).first()
    if not control:
        raise ValueError("Control not found")

    config = get_or_create_config(db, org_id)
    assets = _get_org_assets(db, org_id, asset_ids)

    before, after = [], []
    for asset in assets:
        before.append(_snapshot(asset, calculate_asset_risk(db, asset, config)))
        after.append(_snapshot(asset, calculate_asset_risk(db, asset, config, extra_mitigation=control.effectiveness_score)))

    investment_change = 0.0 if control.is_active else control.annual_cost
    scope = "all assets" if not asset_ids else f"{len(assets)} selected asset(s)"
    return _finalize(
        "add_control",
        f"Deploy '{control.name}' across {scope}",
        before, after, investment_change, [a.id for a in assets],
    )


def simulate_remove_control(db: Session, org_id: int, control_id: int) -> WhatIfResult:
    control = db.query(SecurityControl).filter(SecurityControl.id == control_id, SecurityControl.organization_id == org_id).first()
    if not control:
        raise ValueError("Control not found")
    if not control.is_active:
        raise ValueError("Control is not currently active — nothing to remove")

    config = get_or_create_config(db, org_id)
    protected_asset_ids = [a.id for a in control.protected_assets]
    assets = _get_org_assets(db, org_id, protected_asset_ids) if protected_asset_ids else []

    if not assets:
        raise ValueError("This control doesn't currently protect any assets")

    before, after = [], []
    for asset in assets:
        before.append(_snapshot(asset, calculate_asset_risk(db, asset, config)))
        after.append(_snapshot(asset, calculate_asset_risk(db, asset, config, exclude_control_id=control.id)))

    return _finalize(
        "remove_control",
        f"Remove '{control.name}' from the {len(assets)} asset(s) it currently protects",
        before, after, investment_change=-control.annual_cost, affected_asset_ids=[a.id for a in assets],
    )


def simulate_fix_vulnerability(db: Session, org_id: int, vulnerability_id: int) -> WhatIfResult:
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id, Vulnerability.organization_id == org_id).first()
    if not vuln:
        raise ValueError("Vulnerability not found")

    affected_asset_ids = [a.id for a in vuln.affected_assets]
    if not affected_asset_ids:
        raise ValueError("This vulnerability isn't linked to any asset")

    config = get_or_create_config(db, org_id)
    assets = _get_org_assets(db, org_id, affected_asset_ids)

    before, after = [], []
    for asset in assets:
        before.append(_snapshot(asset, calculate_asset_risk(db, asset, config)))
        after.append(_snapshot(asset, calculate_asset_risk(db, asset, config, exclude_vulnerability_id=vuln.id)))

    label = vuln.cve_id or vuln.title
    return _finalize(
        "fix_vulnerability",
        f"Remediate '{label}' on the {len(assets)} affected asset(s)",
        before, after, investment_change=0.0, affected_asset_ids=[a.id for a in assets],
    )


def simulate_control_effectiveness_change(db: Session, org_id: int, control_id: int, new_effectiveness: float) -> WhatIfResult:
    control = db.query(SecurityControl).filter(SecurityControl.id == control_id, SecurityControl.organization_id == org_id).first()
    if not control:
        raise ValueError("Control not found")
    if not 0.0 <= new_effectiveness <= 1.0:
        raise ValueError("Effectiveness must be between 0.0 and 1.0")

    protected_asset_ids = [a.id for a in control.protected_assets]
    if not protected_asset_ids:
        raise ValueError("This control doesn't currently protect any assets")

    config = get_or_create_config(db, org_id)
    assets = _get_org_assets(db, org_id, protected_asset_ids)

    before, after = [], []
    for asset in assets:
        before.append(_snapshot(asset, calculate_asset_risk(db, asset, config)))
        after.append(_snapshot(asset, calculate_asset_risk(db, asset, config, effectiveness_override={control.id: new_effectiveness})))

    direction = "Improve" if new_effectiveness > control.effectiveness_score else "Reduce"
    return _finalize(
        "improve_control_effectiveness",
        f"{direction} '{control.name}' effectiveness from {control.effectiveness_score:.0%} to {new_effectiveness:.0%}",
        before, after, investment_change=0.0, affected_asset_ids=[a.id for a in assets],
    )


@dataclass
class BudgetWhatIfResult:
    """
    A different shape from WhatIfResult because this scenario compares two
    Investment Optimizer runs (Phase 5), not two per-asset risk states —
    it answers "what would we be able to afford, and how much more risk
    could we reduce, with a different budget?"
    """
    scenario_type: str = "increase_budget"
    description: str = ""
    old_budget: float = 0.0
    new_budget: float = 0.0
    old_total_investment: float = 0.0
    new_total_investment: float = 0.0
    old_risk_reduction: float = 0.0
    new_risk_reduction: float = 0.0
    additional_risk_reduction: float = 0.0
    newly_affordable_controls: List[str] = field(default_factory=list)


def simulate_budget_change(db: Session, org_id: int, new_budget: float, old_budget: Optional[float] = None) -> BudgetWhatIfResult:
    """
    Re-runs the Phase 5 Investment Optimizer at the current budget and at
    a hypothetical new budget, using the exact same candidate estimates
    for both so the comparison is apples-to-apples. Does not persist a
    Recommendation row for either run — purely exploratory.
    """
    from app.models.organization import Organization

    org = db.query(Organization).filter(Organization.id == org_id).first()
    effective_old_budget = old_budget if old_budget is not None else (org.annual_cyber_budget or 0.0)

    candidates = estimate_investment_candidates(db, org_id)
    if not candidates:
        raise ValueError("No candidate investments available to compare budgets against")

    config = get_or_create_config(db, org_id)
    assets = db.query(Asset).filter(Asset.organization_id == org_id).all()
    from app.services.investment_optimizer import _total_eal
    baseline_total_eal = _total_eal(db, assets, config, {})

    old_result = optimize_budget_allocation(db, org_id, candidates, effective_old_budget, baseline_total_eal)
    new_result = optimize_budget_allocation(db, org_id, candidates, new_budget, baseline_total_eal)

    old_names = {c.name for c in old_result.selected}
    new_names = {c.name for c in new_result.selected}
    newly_affordable = sorted(new_names - old_names)

    direction = "Increase" if new_budget > effective_old_budget else "Decrease"
    return BudgetWhatIfResult(
        description=f"{direction} cybersecurity budget from ${effective_old_budget:,.0f} to ${new_budget:,.0f}",
        old_budget=effective_old_budget, new_budget=new_budget,
        old_total_investment=old_result.total_investment, new_total_investment=new_result.total_investment,
        old_risk_reduction=old_result.total_risk_reduction, new_risk_reduction=new_result.total_risk_reduction,
        additional_risk_reduction=round(new_result.total_risk_reduction - old_result.total_risk_reduction, 2),
        newly_affordable_controls=newly_affordable,
    )
