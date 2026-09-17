import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """
    RBAC roles for SIH26105.

    - ADMIN: full platform control, user management, org configuration
    - CISO: security leadership; full read/write on risk, controls,
            investment optimization, compliance
    - RISK_ANALYST: manages assets, vulnerabilities, threats, runs
            what-if simulations; cannot manage users or budget
    - COMPLIANCE_OFFICER: manages compliance mappings and evidence;
            read-only on risk/financial data
    - EXECUTIVE: read-only dashboard access (for CFO/board reporting)
    """
    ADMIN = "admin"
    CISO = "ciso"
    RISK_ANALYST = "risk_analyst"
    COMPLIANCE_OFFICER = "compliance_officer"
    EXECUTIVE = "executive"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="users")
