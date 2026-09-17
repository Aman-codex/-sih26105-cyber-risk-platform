from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class Risk(Base, TimestampMixin):
    """
    The latest risk calculation for one asset. Recalculated whenever
    /api/v1/risks/recalculate runs (manually now; triggered automatically
    by data changes once Continuous Recalculation lands in a later phase).
    One row per asset — history isn't kept in Phase 3, only the current
    snapshot (a RiskScenario row is created alongside it for the "current"
    scenario, so Phase 6's what-if simulator has somewhere to add
    alternative scenarios later).
    """
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, unique=True)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    likelihood: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0, annual incident probability
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100 composite score
    primary_vulnerability_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vulnerabilities.id"), nullable=True)

    expected_annual_loss: Mapped[float] = mapped_column(Float, nullable=False)  # EAL = likelihood x impact
    financial_impact_given_incident: Mapped[float] = mapped_column(Float, nullable=False)

    # Ordered list of {"factor": str, "impact_pct": float} explaining what
    # drove the likelihood up/down — module 7, Risk Driver Analysis.
    risk_drivers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    asset: Mapped["Asset"] = relationship()  # noqa: F821
    primary_vulnerability: Mapped[Optional["Vulnerability"]] = relationship()  # noqa: F821
    financial_impact: Mapped[Optional["FinancialImpact"]] = relationship(
        back_populates="risk", uselist=False, cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["RiskScenario"]] = relationship(back_populates="risk", cascade="all, delete-orphan")


class FinancialImpact(Base, TimestampMixin):
    """
    Breakdown of what a fully-realized incident on this asset would cost,
    by configurable category (module 6, Financial Quantification). Values
    are business_value x the org's financial_impact_weights for each
    category — never invented ad hoc.
    """
    __tablename__ = "financial_impacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id"), nullable=False, unique=True)

    business_interruption: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    data_loss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recovery_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    incident_response: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    legal_regulatory: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    other_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    risk: Mapped["Risk"] = relationship(back_populates="financial_impact")


class RiskScenario(Base, TimestampMixin):
    """
    A named scenario for an asset's risk (e.g. "current", and later
    "add MFA", "increase budget" once Phase 6's what-if simulator writes
    additional rows here). Stores the scenario-based Value at Risk (VaR)
    Monte Carlo result alongside the point-estimate EAL already on Risk.
    """
    __tablename__ = "risk_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="current")

    likelihood: Mapped[float] = mapped_column(Float, nullable=False)
    expected_annual_loss: Mapped[float] = mapped_column(Float, nullable=False)
    value_at_risk: Mapped[float] = mapped_column(Float, nullable=False)  # VaR at configured confidence level
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False)

    risk: Mapped["Risk"] = relationship(back_populates="scenarios")
