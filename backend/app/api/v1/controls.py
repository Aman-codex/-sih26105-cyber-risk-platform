from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import control as control_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.control import ControlCreate, ControlRead, ControlUpdate

router = APIRouter(prefix="/controls", tags=["controls"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


@router.get("", response_model=list[ControlRead])
def list_controls(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    controls = control_crud.list_controls(db, current_user.organization_id)
    return [ControlRead.from_orm_with_assets(c) for c in controls]


@router.get("/{control_id}", response_model=ControlRead)
def get_control(control_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    control = control_crud.get_control(db, current_user.organization_id, control_id)
    if not control:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    return ControlRead.from_orm_with_assets(control)


@router.post("", response_model=ControlRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def create_control(payload: ControlCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    control = control_crud.create_control(db, current_user.organization_id, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="create_control", entity_type="security_control", entity_id=str(control.id)))
    db.commit()
    return ControlRead.from_orm_with_assets(control)


@router.put("/{control_id}", response_model=ControlRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def update_control(control_id: int, payload: ControlUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    control = control_crud.get_control(db, current_user.organization_id, control_id)
    if not control:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    control = control_crud.update_control(db, control, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="update_control", entity_type="security_control", entity_id=str(control.id)))
    db.commit()
    return ControlRead.from_orm_with_assets(control)


@router.delete("/{control_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CISO))])
def delete_control(control_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    control = control_crud.get_control(db, current_user.organization_id, control_id)
    if not control:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="delete_control", entity_type="security_control", entity_id=str(control.id)))
    control_crud.delete_control(db, control)
    db.commit()
    return None
