from sqlalchemy import Float, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin

# Defaults are intentionally visible/editable here (and via the API) rather
# than buried as magic numbers in the risk engine, so every number the Risk
# Engine uses is transparent and tunable — nothing is hard-coded unexplained.
DEFAULT_RISK_MODEL_CONFIG = {
    # Base annual incident likelihood implied by how exploitable the worst
    # open vulnerability on the asset currently is.
    "exploitability_likelihood": {
        "theoretical": 0.05,
        "proof_of_concept": 0.15,
        "functional": 0.35,
        "actively_exploited": 0.65,
    },
    # Multiplies the overall risk score (not likelihood) by how
    # business-critical the asset is.
    "criticality_multiplier": {
        "low": 0.7,
        "medium": 1.0,
        "high": 1.3,
        "critical": 1.6,
    },
    # Applied to likelihood when an asset is directly internet-exposed.
    "internet_exposure_multiplier": 1.3,
    # How strongly active threat-actor relevance (0-1 score) amplifies likelihood.
    "threat_relevance_weight": 0.5,
    # Ceiling on how much combined security controls can reduce likelihood
    # (no combination of controls is modeled as making risk zero).
    "max_control_mitigation": 0.85,
    # Fractions of an asset's business_value assumed to be at stake across
    # each cost category if an incident on that asset is fully realized.
    # These feed the Financial Quantification module (module 6).
    "financial_impact_weights": {
        "business_interruption": 0.30,
        "data_loss": 0.20,
        "recovery_cost": 0.15,
        "incident_response": 0.10,
        "legal_regulatory": 0.15,
        "revenue_impact": 0.10,
    },
    # Scenario-based Value at Risk (Monte Carlo) parameters.
    "var_confidence_level": 0.95,
    "var_simulation_runs": 5000,
    "var_impact_std_dev_fraction": 0.35,
}


class RiskModelConfig(Base, TimestampMixin):
    """
    One configurable risk-model parameter set per organization. Seeded with
    DEFAULT_RISK_MODEL_CONFIG on first use; editable via
    PUT /api/v1/risks/config by admin/ciso so the model stays transparent
    and tunable rather than hard-coded.
    """
    __tablename__ = "risk_model_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, unique=True)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
