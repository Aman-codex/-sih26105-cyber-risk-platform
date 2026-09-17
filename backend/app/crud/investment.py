from typing import List

from sqlalchemy.orm import Session, joinedload

from app.models.investment import Investment, Recommendation
from app.services.investment_optimizer import InvestmentCandidate, OptimizationResult


def upsert_investments(db: Session, org_id: int, candidates: List[InvestmentCandidate]) -> dict:
    """Upserts by control_id, returns {control_id: Investment} for easy lookup when building a Recommendation."""
    result = {}
    for c in candidates:
        inv = db.query(Investment).filter(Investment.organization_id == org_id, Investment.control_id == c.control_id).first()
        if not inv:
            inv = Investment(organization_id=org_id, control_id=c.control_id)
            db.add(inv)
        inv.estimated_annual_cost = c.annual_cost
        inv.estimated_risk_reduction = c.estimated_risk_reduction
        db.commit()
        db.refresh(inv)
        result[c.control_id] = inv
    return result


def list_investments(db: Session, org_id: int) -> List[Investment]:
    return (
        db.query(Investment)
        .options(joinedload(Investment.control))
        .filter(Investment.organization_id == org_id)
        .order_by(Investment.estimated_risk_reduction.desc())
        .all()
    )


def create_recommendation(
    db: Session, org_id: int, result: OptimizationResult, investment_by_control_id: dict
) -> Recommendation:
    selected_ids = [investment_by_control_id[c.control_id].id for c in result.selected]
    rec = Recommendation(
        organization_id=org_id,
        budget=result.budget,
        baseline_total_eal=result.baseline_total_eal,
        total_investment=result.total_investment,
        total_risk_reduction=result.total_risk_reduction,
        remaining_risk=result.remaining_risk,
        rosi_percent=result.rosi_percent,
        selected_investment_ids=selected_ids,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_recommendations(db: Session, org_id: int) -> List[Recommendation]:
    return (
        db.query(Recommendation)
        .filter(Recommendation.organization_id == org_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )


def get_selected_investments(db: Session, recommendation: Recommendation) -> List[Investment]:
    if not recommendation.selected_investment_ids:
        return []
    return (
        db.query(Investment)
        .options(joinedload(Investment.control))
        .filter(Investment.id.in_(recommendation.selected_investment_ids))
        .all()
    )
