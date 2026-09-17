from typing import Optional

from sqlalchemy import Boolean, Column, Enum, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import BusinessCriticality

# Self-referential many-to-many: an asset can depend on other assets
# (e.g. "Online Banking App" depends on "Core Banking DB").
asset_dependencies = Table(
    "asset_dependencies",
    Base.metadata,
    Column("asset_id", Integer, ForeignKey("assets.id"), primary_key=True),
    Column("depends_on_asset_id", Integer, ForeignKey("assets.id"), primary_key=True),
)


class Asset(Base, TimestampMixin):
    """
    A business asset (application, database, server, API, etc.) whose
    compromise would create financial/operational impact. Criticality,
    value and exposure feed directly into the Risk Engine (Phase 3).
    """
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "web_app", "database", "server"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    business_criticality: Mapped[BusinessCriticality] = mapped_column(
        Enum(BusinessCriticality, name="business_criticality"), nullable=False, default=BusinessCriticality.MEDIUM
    )
    business_value: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # estimated financial value / replacement or impact cost, used by Financial Quantification (Phase 3)
    internet_exposure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    depends_on: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=asset_dependencies,
        primaryjoin=id == asset_dependencies.c.asset_id,
        secondaryjoin=id == asset_dependencies.c.depends_on_asset_id,
        backref="depended_on_by",
    )
