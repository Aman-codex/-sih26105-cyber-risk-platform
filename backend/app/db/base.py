"""
Import every ORM model here so Alembic's `target_metadata` sees the full
schema when autogenerating migrations. Later phases (Asset, Vulnerability,
Threat, SecurityControl, Risk, ComplianceFramework, Investment, ...) will
add their imports to this file — nothing else needs to change.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.asset import Asset, asset_dependencies  # noqa: F401
from app.models.vulnerability import Vulnerability, asset_vulnerabilities  # noqa: F401
from app.models.threat import Threat, ThreatEvent, threat_asset_relevance  # noqa: F401
from app.models.security_control import SecurityControl, asset_controls  # noqa: F401
from app.models.risk_config import RiskModelConfig  # noqa: F401
from app.models.risk import Risk, FinancialImpact, RiskScenario  # noqa: F401
from app.models.compliance import (  # noqa: F401
    ComplianceFramework, ComplianceRequirement, ComplianceMapping, Evidence, ComplianceStatus,
)
from app.models.investment import Investment, Recommendation  # noqa: F401
