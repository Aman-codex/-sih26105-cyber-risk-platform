"""phase 5: investments and recommendations (OR-Tools optimization)

Revision ID: 0005_phase5_investment_optimization
Revises: 0004_phase4_compliance
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_phase5_investment_optimization"
down_revision: Union[str, None] = "0004_phase4_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("security_controls.id"), nullable=False, unique=True),
        sa.Column("estimated_annual_cost", sa.Float(), nullable=False),
        sa.Column("estimated_risk_reduction", sa.Float(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("baseline_total_eal", sa.Float(), nullable=False),
        sa.Column("total_investment", sa.Float(), nullable=False),
        sa.Column("total_risk_reduction", sa.Float(), nullable=False),
        sa.Column("remaining_risk", sa.Float(), nullable=False),
        sa.Column("rosi_percent", sa.Float(), nullable=False),
        sa.Column("selected_investment_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("investments")
