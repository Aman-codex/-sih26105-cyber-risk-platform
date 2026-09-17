from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import risk as risk_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.risk import RiskSummary

router = APIRouter(prefix="/financial-risk", tags=["financial-risk"])


@router.get("/summary", response_model=RiskSummary)
def financial_risk_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Aggregate financial exposure across the organization: total EAL, total
    scenario-based VaR, total financial exposure, and a risk-band breakdown
    — the numbers the Management Dashboard (Phase 9) will show front and
    center. Available to every role, including read-only Executive/Compliance.
    """
    return risk_crud.get_risk_summary(db, current_user.organization_id)
