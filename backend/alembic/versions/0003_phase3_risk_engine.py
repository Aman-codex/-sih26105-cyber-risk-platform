"""phase 3: risk model config, risks, financial impacts, risk scenarios

Revision ID: 0003_phase3_risk_engine
Revises: 0002_phase2_asset_vuln_threat_control
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase3_risk_engine"
down_revision: Union[str, None] = "0002_phase2_asset_vuln_threat_control"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_model_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "risks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False, unique=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("likelihood", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("primary_vulnerability_id", sa.Integer(), sa.ForeignKey("vulnerabilities.id"), nullable=True),
        sa.Column("expected_annual_loss", sa.Float(), nullable=False),
        sa.Column("financial_impact_given_incident", sa.Float(), nullable=False),
        sa.Column("risk_drivers", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "financial_impacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risks.id"), nullable=False, unique=True),
        sa.Column("business_interruption", sa.Float(), nullable=False),
        sa.Column("data_loss", sa.Float(), nullable=False),
        sa.Column("recovery_cost", sa.Float(), nullable=False),
        sa.Column("incident_response", sa.Float(), nullable=False),
        sa.Column("legal_regulatory", sa.Float(), nullable=False),
        sa.Column("revenue_impact", sa.Float(), nullable=False),
        sa.Column("other_cost", sa.Float(), nullable=False),
        sa.Column("total_impact", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "risk_scenarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("risk_id", sa.Integer(), sa.ForeignKey("risks.id"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("likelihood", sa.Float(), nullable=False),
        sa.Column("expected_annual_loss", sa.Float(), nullable=False),
        sa.Column("value_at_risk", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("risk_scenarios")
    op.drop_table("financial_impacts")
    op.drop_table("risks")
    op.drop_table("risk_model_configs")
