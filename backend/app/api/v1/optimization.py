from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import investment as investment_crud
from app.db.session import get_db
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.investment import InvestmentRead, OptimizeRequest, RecommendationRead
from app.services.investment_optimizer import _total_eal, estimate_investment_candidates, optimize_budget_allocation
from app.services.risk_engine import get_or_create_config

router = APIRouter(prefix="/optimization", tags=["optimization"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


def _to_recommendation_read(db: Session, recommendation) -> RecommendationRead:
    selected = investment_crud.get_selected_investments(db, recommendation)
    read = RecommendationRead.model_validate(recommendation)
    read.selected_investments = [InvestmentRead.from_orm_with_control(i) for i in selected]
    return read


@router.post("/recommend", response_model=RecommendationRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def recommend_investments(
    payload: OptimizeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Runs the Investment Optimizer: estimates every not-yet-deployed
    control's risk-reduction potential (via the Phase 3 Risk Engine), then
    uses Google OR-Tools to pick the subset that maximizes total risk
    reduction within budget. Defaults to the organization's configured
    annual_cyber_budget if no budget is given in the request body.
    """
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    budget = payload.budget if payload.budget is not None else (org.annual_cyber_budget or 0.0)

    candidates = estimate_investment_candidates(db, current_user.organization_id)
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate investments available — every control is already active, or no assets exist to assess.",
        )

    investment_by_control_id = investment_crud.upsert_investments(db, current_user.organization_id, candidates)

    config = get_or_create_config(db, current_user.organization_id)
    assets = db.query(Asset).filter(Asset.organization_id == current_user.organization_id).all()
    baseline_total_eal = _total_eal(db, assets, config, {})

    result = optimize_budget_allocation(db, current_user.organization_id, candidates, budget, baseline_total_eal)
    recommendation = investment_crud.create_recommendation(db, current_user.organization_id, result, investment_by_control_id)

    db.add(AuditLog(
        organization_id=current_user.organization_id, user_id=current_user.id,
        action="run_investment_optimization", entity_type="recommendation", entity_id=str(recommendation.id),
    ))
    db.commit()

    return _to_recommendation_read(db, recommendation)


@router.get("/recommendations", response_model=list[RecommendationRead])
def list_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """History of past optimization runs for this organization, most recent first."""
    recommendations = investment_crud.list_recommendations(db, current_user.organization_id)
    return [_to_recommendation_read(db, r) for r in recommendations]
