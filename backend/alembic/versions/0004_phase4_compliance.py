"""phase 4: compliance frameworks, requirements, mappings, evidence

Revision ID: 0004_phase4_compliance
Revises: 0003_phase3_risk_engine
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_phase4_compliance"
down_revision: Union[str, None] = "0003_phase3_risk_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

compliance_status_enum = sa.Enum(
    "compliant", "partially_compliant", "non_compliant", "not_applicable", "not_assessed",
    name="compliance_status",
)


def upgrade() -> None:
    compliance_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "compliance_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("short_code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "compliance_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("framework_id", sa.Integer(), sa.ForeignKey("compliance_frameworks.id"), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("framework_id", "code", name="uq_requirement_framework_code"),
    )

    op.create_table(
        "compliance_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("compliance_requirements.id"), nullable=False),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("security_controls.id"), nullable=True),
        sa.Column("status", compliance_status_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "requirement_id", name="uq_mapping_org_requirement"),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("compliance_mappings.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("compliance_mappings")
    op.drop_table("compliance_requirements")
    op.drop_table("compliance_frameworks")
    compliance_status_enum.drop(op.get_bind(), checkfirst=True)
