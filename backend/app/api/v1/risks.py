from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import asset as asset_crud
from app.crud import risk as risk_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.risk import RiskModelConfigRead, RiskModelConfigUpdate, RiskRead
from app.services.risk_engine import get_or_create_config

router = APIRouter(prefix="/risks", tags=["risks"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)
CONFIG_ROLES = (UserRole.ADMIN, UserRole.CISO)


@router.get("/config", response_model=RiskModelConfigRead)
def get_risk_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the organization's current risk-model parameters (exploitability
    likelihoods, criticality multipliers, financial impact weights, etc.) so
    they're fully visible rather than hidden constants in code.
    """
    config = get_or_create_config(db, current_user.organization_id)
    return config


@router.put("/config", response_model=RiskModelConfigRead, dependencies=[Depends(require_roles(*CONFIG_ROLES))])
def update_risk_config(
    payload: RiskModelConfigUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Admin/CISO can tune the risk model. Top-level keys are merged (not replaced wholesale)."""
    config = get_or_create_config(db, current_user.organization_id)
    updated = dict(config.parameters)
    updated.update(payload.parameters)
    config.parameters = updated
    db.add(AuditLog(
        organization_id=current_user.organization_id, user_id=current_user.id,
        action="update_risk_config", entity_type="risk_model_config", entity_id=str(config.id),
    ))
    db.commit()
    db.refresh(config)
    return config


@router.post("/recalculate", response_model=list[RiskRead], dependencies=[Depends(require_roles(*WRITE_ROLES))])
def recalculate_risks(
    asset_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Recalculates risk for one asset (?asset_id=) or every asset in the
    organization. This is the manual trigger for "Continuous Recalculation"
    — later phases will call the same underlying engine automatically
    whenever a new vulnerability/threat event is ingested.
    """
    if asset_id is not None:
        asset = asset_crud.get_asset(db, current_user.organization_id, asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        risks = [risk_crud.recalculate_asset_risk(db, current_user.organization_id, asset)]
    else:
        risks = risk_crud.recalculate_all_risks(db, current_user.organization_id)

    db.add(AuditLog(
        organization_id=current_user.organization_id, user_id=current_user.id,
        action="recalculate_risk", entity_type="risk",
        entity_id=str(asset_id) if asset_id else "all_assets",
    ))
    db.commit()
    return risks


@router.get("", response_model=list[RiskRead])
def list_risks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return risk_crud.list_risks(db, current_user.organization_id)


@router.get("/{asset_id}", response_model=RiskRead)
def get_risk(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    risk = risk_crud.get_risk_for_asset(db, current_user.organization_id, asset_id)
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk calculated for this asset yet — POST /risks/recalculate first",
        )
    return risk
