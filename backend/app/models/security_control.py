from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Column, Date, Enum, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import ControlType

# Which controls protect which assets, and to what extent. coverage_percentage
# lets the same control type (e.g. "MFA") be fully rolled out on one asset
# but only partially on another — the Risk Engine (Phase 3) multiplies
# control effectiveness by this coverage when reducing likelihood.
asset_controls = Table(
    "asset_controls",
    Base.metadata,
    Column("asset_id", Integer, ForeignKey("assets.id"), primary_key=True),
    Column("control_id", Integer, ForeignKey("security_controls.id"), primary_key=True),
    Column("coverage_percentage", Float, nullable=False, default=100.0),  # 0-100
    Column("implemented_on", Date, nullable=True),
)


class SecurityControl(Base, TimestampMixin):
    """
    A security control (MFA, EDR, Firewall, Backup, Patch Management, IAM,
    Monitoring, Incident Response, ...). cost and effectiveness_score are
    the two inputs the Investment Optimization module (Phase 5, OR-Tools)
    will use to pick the best combination of controls under a budget.
    """
    __tablename__ = "security_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    control_type: Mapped[ControlType] = mapped_column(Enum(ControlType, name="control_type"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    annual_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    effectiveness_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # 0.0-1.0: fractional reduction in incident likelihood when fully deployed
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    protected_assets: Mapped[list["Asset"]] = relationship(  # noqa: F821
        "Asset", secondary=asset_controls, backref="controls"
    )
