from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.compliance import ComplianceStatus


class ComplianceRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    framework_id: int
    code: str
    category: Optional[str]
    title: str
    description: Optional[str]


class ComplianceFrameworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    short_code: str
    version: Optional[str]
    description: Optional[str]
    requirement_count: int = 0


class EvidenceCreate(BaseModel):
    description: str
    url: Optional[str] = None


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    url: Optional[str]
    uploaded_at: datetime
    uploaded_by_user_id: Optional[int]


class ComplianceMappingUpsert(BaseModel):
    requirement_id: int
    status: ComplianceStatus
    control_id: Optional[int] = None
    notes: Optional[str] = None


class ComplianceMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None  # None for requirements that haven't been assessed yet (no mapping row persisted)
    organization_id: int
    requirement_id: int
    control_id: Optional[int] = None
    status: ComplianceStatus
    notes: Optional[str] = None
    requirement: ComplianceRequirementRead
    evidence: List[EvidenceRead] = []


class FrameworkGapAnalysis(BaseModel):
    framework: ComplianceFrameworkRead
    compliance_score: float  # 0-100, computed over applicable (non-N/A) requirements
    compliant_count: int
    partially_compliant_count: int
    non_compliant_count: int
    not_applicable_count: int
    not_assessed_count: int
    gaps: List[ComplianceMappingRead]  # non-compliant + partially-compliant + not-assessed requirements


class ComplianceSummary(BaseModel):
    """Overall compliance posture across every framework — dashboard-ready."""
    overall_score: float
    frameworks: List[FrameworkGapAnalysis]
