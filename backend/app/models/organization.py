from typing import Optional

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """
    An organization is the top-level tenant boundary. Every asset, user,
    control, risk and compliance record belongs to exactly one organization,
    which keeps the platform multi-tenant-ready even though Phase 1 ships
    with a single demo tenant.
    """
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Annual cybersecurity budget used later by the Investment Optimization
    # module (Phase 5). Stored here since it's an org-level constraint.
    annual_cyber_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
