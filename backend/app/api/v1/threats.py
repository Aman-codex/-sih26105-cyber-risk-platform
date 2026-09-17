from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import threat as threat_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.threat import ThreatCreate, ThreatEventCreate, ThreatEventRead, ThreatRead, ThreatUpdate

router = APIRouter(prefix="/threats", tags=["threats"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


@router.get("", response_model=list[ThreatRead])
def list_threats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threats = threat_crud.list_threats(db, current_user.organization_id)
    return [ThreatRead.from_orm_with_assets(t) for t in threats]


@router.get("/events", response_model=list[ThreatEventRead])
def list_threat_events(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return threat_crud.list_threat_events(db, current_user.organization_id)


@router.get("/{threat_id}", response_model=ThreatRead)
def get_threat(threat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threat = threat_crud.get_threat(db, current_user.organization_id, threat_id)
    if not threat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat not found")
    return ThreatRead.from_orm_with_assets(threat)


@router.post("", response_model=ThreatRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def create_threat(payload: ThreatCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threat = threat_crud.create_threat(db, current_user.organization_id, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="create_threat", entity_type="threat", entity_id=str(threat.id)))
    db.commit()
    return ThreatRead.from_orm_with_assets(threat)


@router.put("/{threat_id}", response_model=ThreatRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def update_threat(threat_id: int, payload: ThreatUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threat = threat_crud.get_threat(db, current_user.organization_id, threat_id)
    if not threat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat not found")
    threat = threat_crud.update_threat(db, threat, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="update_threat", entity_type="threat", entity_id=str(threat.id)))
    db.commit()
    return ThreatRead.from_orm_with_assets(threat)


@router.delete("/{threat_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CISO))])
def delete_threat(threat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    threat = threat_crud.get_threat(db, current_user.organization_id, threat_id)
    if not threat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat not found")
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="delete_threat", entity_type="threat", entity_id=str(threat.id)))
    threat_crud.delete_threat(db, threat)
    db.commit()
    return None


@router.post("/events", response_model=ThreatEventRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def create_threat_event(payload: ThreatEventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Records a concrete threat occurrence (e.g. 'active exploitation detected').
    This is the event type that will trigger Continuous Recalculation in later phases.
    """
    threat = threat_crud.get_threat(db, current_user.organization_id, payload.threat_id)
    if not threat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referenced threat not found")
    event = threat_crud.create_threat_event(db, current_user.organization_id, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="create_threat_event", entity_type="threat_event", entity_id=str(event.id)))
    db.commit()
    return event
