"""phase 2: assets, vulnerabilities, threats, threat events, security controls

Revision ID: 0002_phase2_asset_vuln_threat_control
Revises: 0001_initial_schema
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_phase2_asset_vuln_threat_control"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

business_criticality_enum = sa.Enum("low", "medium", "high", "critical", name="business_criticality")
vuln_severity_enum = sa.Enum("low", "medium", "high", "critical", name="vuln_severity")
threat_event_severity_enum = sa.Enum("low", "medium", "high", "critical", name="threat_event_severity")
exploitability_enum = sa.Enum(
    "theoretical", "proof_of_concept", "functional", "actively_exploited", name="exploitability"
)
vulnerability_status_enum = sa.Enum(
    "open", "mitigated", "accepted_risk", "false_positive", name="vulnerability_status"
)
control_type_enum = sa.Enum(
    "mfa", "edr", "firewall", "backup", "patch_management", "iam", "monitoring",
    "incident_response", "other", name="control_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    business_criticality_enum.create(bind, checkfirst=True)
    vuln_severity_enum.create(bind, checkfirst=True)
    exploitability_enum.create(bind, checkfirst=True)
    vulnerability_status_enum.create(bind, checkfirst=True)
    threat_event_severity_enum.create(bind, checkfirst=True)
    control_type_enum.create(bind, checkfirst=True)

    # --- assets ---
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("business_criticality", business_criticality_enum, nullable=False),
        sa.Column("business_value", sa.Float(), nullable=False),
        sa.Column("internet_exposure", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "asset_dependencies",
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("depends_on_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
    )

    # --- vulnerabilities ---
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("cve_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=False),
        sa.Column("severity", vuln_severity_enum, nullable=False),
        sa.Column("exploitability", exploitability_enum, nullable=False),
        sa.Column("status", vulnerability_status_enum, nullable=False),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vulnerabilities_cve_id", "vulnerabilities", ["cve_id"])

    op.create_table(
        "asset_vulnerabilities",
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("vulnerability_id", sa.Integer(), sa.ForeignKey("vulnerabilities.id"), primary_key=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- threats ---
    op.create_table(
        "threats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("threat_actor", sa.String(length=255), nullable=True),
        sa.Column("mitre_technique_id", sa.String(length=20), nullable=True),
        sa.Column("mitre_tactic", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "threat_asset_relevance",
        sa.Column("threat_id", sa.Integer(), sa.ForeignKey("threats.id"), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("relevance_score", sa.Float(), nullable=False),
    )

    op.create_table(
        "threat_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("threat_id", sa.Integer(), sa.ForeignKey("threats.id"), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", threat_event_severity_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- security controls ---
    op.create_table(
        "security_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("control_type", control_type_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("annual_cost", sa.Float(), nullable=False),
        sa.Column("effectiveness_score", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "asset_controls",
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), primary_key=True),
        sa.Column("control_id", sa.Integer(), sa.ForeignKey("security_controls.id"), primary_key=True),
        sa.Column("coverage_percentage", sa.Float(), nullable=False),
        sa.Column("implemented_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("asset_controls")
    op.drop_table("security_controls")
    op.drop_table("threat_events")
    op.drop_table("threat_asset_relevance")
    op.drop_table("threats")
    op.drop_table("asset_vulnerabilities")
    op.drop_index("ix_vulnerabilities_cve_id", table_name="vulnerabilities")
    op.drop_table("vulnerabilities")
    op.drop_table("asset_dependencies")
    op.drop_table("assets")

    bind = op.get_bind()
    control_type_enum.drop(bind, checkfirst=True)
    threat_event_severity_enum.drop(bind, checkfirst=True)
    vulnerability_status_enum.drop(bind, checkfirst=True)
    exploitability_enum.drop(bind, checkfirst=True)
    vuln_severity_enum.drop(bind, checkfirst=True)
    business_criticality_enum.drop(bind, checkfirst=True)
