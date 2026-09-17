from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import vulnerability as vuln_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.vulnerability import VulnerabilityCreate, VulnerabilityRead, VulnerabilityUpdate

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


@router.get("", response_model=list[VulnerabilityRead])
def list_vulnerabilities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vulns = vuln_crud.list_vulnerabilities(db, current_user.organization_id)
    return [VulnerabilityRead.from_orm_with_assets(v) for v in vulns]


@router.get("/{vuln_id}", response_model=VulnerabilityRead)
def get_vulnerability(vuln_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vuln = vuln_crud.get_vulnerability(db, current_user.organization_id, vuln_id)
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")
    return VulnerabilityRead.from_orm_with_assets(vuln)


@router.post("", response_model=VulnerabilityRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def create_vulnerability(payload: VulnerabilityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vuln = vuln_crud.create_vulnerability(db, current_user.organization_id, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="create_vulnerability", entity_type="vulnerability", entity_id=str(vuln.id)))
    db.commit()
    return VulnerabilityRead.from_orm_with_assets(vuln)


@router.put("/{vuln_id}", response_model=VulnerabilityRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def update_vulnerability(vuln_id: int, payload: VulnerabilityUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vuln = vuln_crud.get_vulnerability(db, current_user.organization_id, vuln_id)
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")
    vuln = vuln_crud.update_vulnerability(db, vuln, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="update_vulnerability", entity_type="vulnerability", entity_id=str(vuln.id)))
    db.commit()
    return VulnerabilityRead.from_orm_with_assets(vuln)


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CISO))])
def delete_vulnerability(vuln_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vuln = vuln_crud.get_vulnerability(db, current_user.organization_id, vuln_id)
    if not vuln:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="delete_vulnerability", entity_type="vulnerability", entity_id=str(vuln.id)))
    vuln_crud.delete_vulnerability(db, vuln)
    db.commit()
    return None
