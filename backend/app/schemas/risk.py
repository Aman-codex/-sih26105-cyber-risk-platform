from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class RiskModelConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    parameters: dict


class RiskModelConfigUpdate(BaseModel):
    """Partial update — only the top-level keys provided are merged into the existing config."""
    parameters: Dict[str, object]


class RiskDriverRead(BaseModel):
    factor: str
    impact_pct: float


class FinancialImpactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_interruption: float
    data_loss: float
    recovery_cost: float
    incident_response: float
    legal_regulatory: float
    revenue_impact: float
    other_cost: float
    total_impact: float


class RiskScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    likelihood: float
    expected_annual_loss: float
    value_at_risk: float
    confidence_level: float


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    asset_id: int
    calculated_at: datetime
    likelihood: float
    risk_score: float
    primary_vulnerability_id: Optional[int]
    expected_annual_loss: float
    financial_impact_given_incident: float
    risk_drivers: List[RiskDriverRead]
    financial_impact: Optional[FinancialImpactRead] = None
    scenarios: List[RiskScenarioRead] = []


class RiskSummary(BaseModel):
    """Aggregate view for the dashboard / financial-risk endpoint."""
    total_expected_annual_loss: float
    total_value_at_risk: float
    total_financial_exposure: float  # sum of financial_impact_given_incident across all assets
    asset_count: int
    critical_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    top_risks: List[RiskRead]
