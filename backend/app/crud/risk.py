from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset
from app.models.risk import FinancialImpact, Risk, RiskScenario
from app.services.risk_engine import RiskCalculationResult, calculate_asset_risk, get_or_create_config


def _risk_query(db: Session):
    return db.query(Risk).options(
        joinedload(Risk.financial_impact),
        joinedload(Risk.scenarios),
    )


def get_risk_for_asset(db: Session, org_id: int, asset_id: int) -> Optional[Risk]:
    return _risk_query(db).filter(Risk.organization_id == org_id, Risk.asset_id == asset_id).first()


def list_risks(db: Session, org_id: int) -> List[Risk]:
    return _risk_query(db).filter(Risk.organization_id == org_id).order_by(Risk.risk_score.desc()).all()


def _persist_result(db: Session, org_id: int, result: RiskCalculationResult) -> Risk:
    risk = db.query(Risk).filter(Risk.asset_id == result.asset_id).first()
    if not risk:
        risk = Risk(organization_id=org_id, asset_id=result.asset_id)
        db.add(risk)

    risk.likelihood = result.likelihood
    risk.risk_score = result.risk_score
    risk.primary_vulnerability_id = result.primary_vulnerability_id
    risk.expected_annual_loss = result.expected_annual_loss
    risk.financial_impact_given_incident = result.financial_impact_given_incident
    risk.risk_drivers = [{"factor": d.factor, "impact_pct": d.impact_pct} for d in result.drivers]
    db.commit()
    db.refresh(risk)

    fi = db.query(FinancialImpact).filter(FinancialImpact.risk_id == risk.id).first()
    if not fi:
        fi = FinancialImpact(risk_id=risk.id)
        db.add(fi)
    b = result.financial_breakdown
    fi.business_interruption = b.get("business_interruption", 0.0)
    fi.data_loss = b.get("data_loss", 0.0)
    fi.recovery_cost = b.get("recovery_cost", 0.0)
    fi.incident_response = b.get("incident_response", 0.0)
    fi.legal_regulatory = b.get("legal_regulatory", 0.0)
    fi.revenue_impact = b.get("revenue_impact", 0.0)
    fi.other_cost = b.get("other", 0.0)
    fi.total_impact = result.financial_impact_given_incident
    db.commit()

    scenario = db.query(RiskScenario).filter(RiskScenario.risk_id == risk.id, RiskScenario.name == "current").first()
    if not scenario:
        scenario = RiskScenario(risk_id=risk.id, name="current")
        db.add(scenario)
    scenario.likelihood = result.likelihood
    scenario.expected_annual_loss = result.expected_annual_loss
    scenario.value_at_risk = result.value_at_risk
    scenario.confidence_level = result.confidence_level
    db.commit()
    db.refresh(risk)

    return risk


def recalculate_asset_risk(db: Session, org_id: int, asset: Asset) -> Risk:
    config = get_or_create_config(db, org_id)
    result = calculate_asset_risk(db, asset, config)
    return _persist_result(db, org_id, result)


def recalculate_all_risks(db: Session, org_id: int) -> List[Risk]:
    config = get_or_create_config(db, org_id)
    assets = db.query(Asset).filter(Asset.organization_id == org_id).all()
    risks = []
    for asset in assets:
        result = calculate_asset_risk(db, asset, config)
        risks.append(_persist_result(db, org_id, result))
    return risks


# Risk score bands used purely for dashboard bucketing/coloring — not part
# of the underlying calculation, so changing these thresholds never changes
# an asset's actual risk_score or EAL.
RISK_SCORE_BANDS = {"critical": 75.0, "high": 50.0, "medium": 25.0}


def band_for_score(score: float) -> str:
    if score >= RISK_SCORE_BANDS["critical"]:
        return "critical"
    if score >= RISK_SCORE_BANDS["high"]:
        return "high"
    if score >= RISK_SCORE_BANDS["medium"]:
        return "medium"
    return "low"


def get_risk_summary(db: Session, org_id: int, top_n: int = 5) -> dict:
    risks = list_risks(db, org_id)
    bands = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_eal = 0.0
    total_var = 0.0
    total_exposure = 0.0

    for r in risks:
        bands[band_for_score(r.risk_score)] += 1
        total_eal += r.expected_annual_loss
        total_exposure += r.financial_impact_given_incident
        current_scenario = next((s for s in r.scenarios if s.name == "current"), None)
        if current_scenario:
            total_var += current_scenario.value_at_risk

    return {
        "total_expected_annual_loss": round(total_eal, 2),
        "total_value_at_risk": round(total_var, 2),
        "total_financial_exposure": round(total_exposure, 2),
        "asset_count": len(risks),
        "critical_risk_count": bands["critical"],
        "high_risk_count": bands["high"],
        "medium_risk_count": bands["medium"],
        "low_risk_count": bands["low"],
        "top_risks": risks[:top_n],
    }
