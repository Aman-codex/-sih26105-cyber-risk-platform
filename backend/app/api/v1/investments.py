from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import investment as investment_crud
from app.db.session import get_db
from app.models.user import User
from app.schemas.investment import InvestmentRead

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("", response_model=list[InvestmentRead])
def list_investments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Lists the current investment candidates (not-yet-deployed controls)
    and their estimated risk reduction, as of the last time
    POST /api/v1/optimization/recommend was run. Available to every role.
    """
    investments = investment_crud.list_investments(db, current_user.organization_id)
    return [InvestmentRead.from_orm_with_control(i) for i in investments]
