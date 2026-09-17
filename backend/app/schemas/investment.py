from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InvestmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    control_id: int
    estimated_annual_cost: float
    estimated_risk_reduction: float
    calculated_at: datetime
    control_name: str = ""
    control_type: str = ""

    @classmethod
    def from_orm_with_control(cls, investment) -> "InvestmentRead":
        obj = cls.model_validate(investment)
        obj.control_name = investment.control.name
        obj.control_type = investment.control.control_type.value
        return obj


class OptimizeRequest(BaseModel):
    budget: Optional[float] = Field(default=None, ge=0, description="Defaults to the organization's annual_cyber_budget if omitted")


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    budget: float
    baseline_total_eal: float
    total_investment: float
    total_risk_reduction: float
    remaining_risk: float
    rosi_percent: float
    created_at: datetime
    selected_investments: List[InvestmentRead] = []
