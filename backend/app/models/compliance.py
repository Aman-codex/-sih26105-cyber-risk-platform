import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    NOT_ASSESSED = "not_assessed"  # default before anyone has looked at it


class ComplianceFramework(Base, TimestampMixin):
    """
    A regulatory/industry framework (NIST CSF, ISO/IEC 27001, CIS Controls,
    RBI Cyber Security Framework, SEBI Cyber Resilience Framework, ...).
    Frameworks and their requirements are shared reference data, not
    per-organization — every org maps against the same requirement text.
    """
    __tablename__ = "compliance_frameworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    short_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # e.g. "NIST_CSF"
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requirements: Mapped[list["ComplianceRequirement"]] = relationship(back_populates="framework")


class ComplianceRequirement(Base, TimestampMixin):
    """One control/requirement within a framework, e.g. NIST CSF 'PR.AC-1'."""
    __tablename__ = "compliance_requirements"
    __table_args__ = (UniqueConstraint("framework_id", "code", name="uq_requirement_framework_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("compliance_frameworks.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "PR.AC-1", "A.9.2.1"
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. "Protect", "Identify"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    framework: Mapped["ComplianceFramework"] = relationship(back_populates="requirements")


class ComplianceMapping(Base, TimestampMixin):
    """
    One organization's current compliance status against one requirement,
    optionally linking the security control that satisfies it. This is the
    per-org, changeable state — frameworks/requirements above are shared
    reference data that never change per organization.
    """
    __tablename__ = "compliance_mappings"
    __table_args__ = (UniqueConstraint("organization_id", "requirement_id", name="uq_mapping_org_requirement"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("compliance_requirements.id"), nullable=False)
    control_id: Mapped[Optional[int]] = mapped_column(ForeignKey("security_controls.id"), nullable=True)

    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status"), nullable=False, default=ComplianceStatus.NOT_ASSESSED
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    requirement: Mapped["ComplianceRequirement"] = relationship()
    control: Mapped[Optional["SecurityControl"]] = relationship()  # noqa: F821
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="mapping", cascade="all, delete-orphan")


class Evidence(Base, TimestampMixin):
    """
    A piece of evidence attached to a compliance mapping (a note, a link to
    a document, a policy reference). This phase stores text/URL evidence
    only — actual file upload/storage is out of scope for the prototype.
    """
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("compliance_mappings.id"), nullable=False)
    uploaded_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    mapping: Mapped["ComplianceMapping"] = relationship(back_populates="evidence")
