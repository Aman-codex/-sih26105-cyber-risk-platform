from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Investment(Base, TimestampMixin):
    """
    A candidate investment: one not-yet-deployed security control, with
    its estimated risk-reduction if deployed. Recomputed (upserted) every
    time the optimizer runs, so this table always reflects the latest
    estimate rather than accumulating stale historical rows.
    """
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    control_id: Mapped[int] = mapped_column(ForeignKey("security_controls.id"), nullable=False, unique=True)

    estimated_annual_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_risk_reduction: Mapped[float] = mapped_column(Float, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    control: Mapped["SecurityControl"] = relationship()  # noqa: F821


class Recommendation(Base, TimestampMixin):
    """
    One optimization run's output: given a budget, which investments were
    recommended and what they'd achieve. selected_investment_ids stores
    which Investment rows were chosen — kept as a simple JSON list rather
    than an association table since a Recommendation is an immutable
    snapshot of a past run, not something that gets edited afterward.
    """
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)

    budget: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_total_eal: Mapped[float] = mapped_column(Float, nullable=False)
    total_investment: Mapped[float] = mapped_column(Float, nullable=False)
    total_risk_reduction: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_risk: Mapped[float] = mapped_column(Float, nullable=False)
    rosi_percent: Mapped[float] = mapped_column(Float, nullable=False)
    selected_investment_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
