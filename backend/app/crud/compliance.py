from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.compliance import (
    ComplianceFramework,
    ComplianceMapping,
    ComplianceRequirement,
    ComplianceStatus,
    Evidence,
)
from app.schemas.compliance import ComplianceMappingUpsert, EvidenceCreate


def list_frameworks(db: Session) -> List[dict]:
    frameworks = db.query(ComplianceFramework).order_by(ComplianceFramework.id).all()
    counts = dict(
        db.query(ComplianceRequirement.framework_id, func.count(ComplianceRequirement.id))
        .group_by(ComplianceRequirement.framework_id)
        .all()
    )
    result = []
    for f in frameworks:
        result.append({
            "id": f.id, "name": f.name, "short_code": f.short_code,
            "version": f.version, "description": f.description,
            "requirement_count": counts.get(f.id, 0),
        })
    return result


def get_framework(db: Session, framework_id: int) -> Optional[ComplianceFramework]:
    return db.query(ComplianceFramework).filter(ComplianceFramework.id == framework_id).first()


def _mapping_query(db: Session):
    return db.query(ComplianceMapping).options(
        joinedload(ComplianceMapping.requirement),
        joinedload(ComplianceMapping.evidence),
    )


def get_framework_mappings(db: Session, org_id: int, framework_id: int) -> List[ComplianceMapping]:
    """
    Returns one entry per requirement in the framework: either the org's
    real (persisted) mapping if one exists, or a not-yet-assessed
    placeholder that reflects the requirement without writing a row until
    someone actually sets a status.
    """
    requirements = (
        db.query(ComplianceRequirement)
        .filter(ComplianceRequirement.framework_id == framework_id)
        .order_by(ComplianceRequirement.code)
        .all()
    )
    existing = {
        m.requirement_id: m
        for m in _mapping_query(db).filter(
            ComplianceMapping.organization_id == org_id,
            ComplianceMapping.requirement_id.in_([r.id for r in requirements]),
        ).all()
    }

    results = []
    for req in requirements:
        if req.id in existing:
            results.append(existing[req.id])
        else:
            placeholder = ComplianceMapping(
                organization_id=org_id, requirement_id=req.id, status=ComplianceStatus.NOT_ASSESSED,
            )
            placeholder.requirement = req
            placeholder.evidence = []
            results.append(placeholder)
    return results


def upsert_mapping(db: Session, org_id: int, payload: ComplianceMappingUpsert) -> ComplianceMapping:
    mapping = (
        db.query(ComplianceMapping)
        .filter(ComplianceMapping.organization_id == org_id, ComplianceMapping.requirement_id == payload.requirement_id)
        .first()
    )
    if not mapping:
        mapping = ComplianceMapping(organization_id=org_id, requirement_id=payload.requirement_id)
        db.add(mapping)

    mapping.status = payload.status
    mapping.control_id = payload.control_id
    mapping.notes = payload.notes
    db.commit()
    db.refresh(mapping)
    return _mapping_query(db).filter(ComplianceMapping.id == mapping.id).first()


def add_evidence(db: Session, mapping: ComplianceMapping, payload: EvidenceCreate, user_id: int) -> Evidence:
    evidence = Evidence(
        mapping_id=mapping.id, description=payload.description, url=payload.url, uploaded_by_user_id=user_id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def get_mapping_by_id(db: Session, org_id: int, mapping_id: int) -> Optional[ComplianceMapping]:
    return _mapping_query(db).filter(ComplianceMapping.id == mapping_id, ComplianceMapping.organization_id == org_id).first()


def compute_gap_analysis(db: Session, org_id: int, framework: ComplianceFramework) -> dict:
    mappings = get_framework_mappings(db, org_id, framework.id)

    counts = {status: 0 for status in ComplianceStatus}
    for m in mappings:
        counts[m.status] += 1

    applicable = len(mappings) - counts[ComplianceStatus.NOT_APPLICABLE]
    if applicable > 0:
        # Partially compliant counts as half credit — a defensible, simple
        # convention that avoids pretending partial coverage is either
        # full compliance or a complete gap.
        score = (
            (counts[ComplianceStatus.COMPLIANT] + 0.5 * counts[ComplianceStatus.PARTIALLY_COMPLIANT])
            / applicable * 100
        )
    else:
        score = 100.0  # nothing applicable means nothing to fail

    gaps = [
        m for m in mappings
        if m.status in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.PARTIALLY_COMPLIANT, ComplianceStatus.NOT_ASSESSED)
    ]

    return {
        "framework": {
            "id": framework.id, "name": framework.name, "short_code": framework.short_code,
            "version": framework.version, "description": framework.description,
            "requirement_count": len(mappings),
        },
        "compliance_score": round(score, 1),
        "compliant_count": counts[ComplianceStatus.COMPLIANT],
        "partially_compliant_count": counts[ComplianceStatus.PARTIALLY_COMPLIANT],
        "non_compliant_count": counts[ComplianceStatus.NON_COMPLIANT],
        "not_applicable_count": counts[ComplianceStatus.NOT_APPLICABLE],
        "not_assessed_count": counts[ComplianceStatus.NOT_ASSESSED],
        "gaps": gaps,
    }


def compute_overall_summary(db: Session, org_id: int) -> dict:
    frameworks = db.query(ComplianceFramework).order_by(ComplianceFramework.id).all()
    analyses = [compute_gap_analysis(db, org_id, f) for f in frameworks]
    overall = sum(a["compliance_score"] for a in analyses) / len(analyses) if analyses else 100.0
    return {"overall_score": round(overall, 1), "frameworks": analyses}
