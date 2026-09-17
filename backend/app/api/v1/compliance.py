from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import compliance as compliance_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.compliance import (
    ComplianceFrameworkRead,
    ComplianceMappingRead,
    ComplianceMappingUpsert,
    ComplianceSummary,
    EvidenceCreate,
    EvidenceRead,
    FrameworkGapAnalysis,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.COMPLIANCE_OFFICER)


@router.get("/frameworks", response_model=list[ComplianceFrameworkRead])
def list_frameworks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Lists the reference frameworks available (NIST CSF, ISO/IEC 27001, CIS
    Controls, RBI Cyber Security Framework, SEBI Cyber Resilience
    Framework). Framework/requirement text is shared reference data, not
    specific to any one organization.
    """
    return compliance_crud.list_frameworks(db)


@router.get("/frameworks/{framework_id}/mappings", response_model=list[ComplianceMappingRead])
def get_framework_mappings(framework_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    framework = compliance_crud.get_framework(db, framework_id)
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")
    return compliance_crud.get_framework_mappings(db, current_user.organization_id, framework_id)


@router.get("/frameworks/{framework_id}/gap-analysis", response_model=FrameworkGapAnalysis)
def get_gap_analysis(framework_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Compliance score (0-100) and the list of gaps (non-compliant,
    partially-compliant, or not-yet-assessed requirements) for one
    framework. NOTE: this reflects the organization's self-reported
    mapping status — it is not, and does not constitute, an official
    regulatory certification or audit finding.
    """
    framework = compliance_crud.get_framework(db, framework_id)
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")
    return compliance_crud.compute_gap_analysis(db, current_user.organization_id, framework)


@router.get("/summary", response_model=ComplianceSummary)
def get_compliance_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Overall compliance posture across every framework — for the Management Dashboard."""
    return compliance_crud.compute_overall_summary(db, current_user.organization_id)


@router.post("/mappings", response_model=ComplianceMappingRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def upsert_mapping(payload: ComplianceMappingUpsert, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Sets (or updates) the organization's compliance status for one
    requirement, optionally linking the security control that satisfies
    it. Admin, CISO, and Compliance Officer roles only.
    """
    mapping = compliance_crud.upsert_mapping(db, current_user.organization_id, payload)
    db.add(AuditLog(
        organization_id=current_user.organization_id, user_id=current_user.id,
        action="update_compliance_mapping", entity_type="compliance_mapping", entity_id=str(mapping.id),
    ))
    db.commit()
    return mapping


@router.post(
    "/mappings/{mapping_id}/evidence", response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
def add_evidence(mapping_id: int, payload: EvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Attaches evidence (a note and/or link — no file storage in this
    phase) to an existing compliance mapping. The mapping must already
    have a status set via POST /compliance/mappings first.
    """
    mapping = compliance_crud.get_mapping_by_id(db, current_user.organization_id, mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found — set a status via POST /compliance/mappings before attaching evidence",
        )
    evidence = compliance_crud.add_evidence(db, mapping, payload, current_user.id)
    db.add(AuditLog(
        organization_id=current_user.organization_id, user_id=current_user.id,
        action="add_compliance_evidence", entity_type="evidence", entity_id=str(evidence.id),
    ))
    db.commit()
    return evidence
