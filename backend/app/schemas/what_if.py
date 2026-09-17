from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WhatIfRequest(BaseModel):
    scenario_type: Literal[
        "add_control", "remove_control", "fix_vulnerability", "improve_control_effectiveness", "increase_budget"
    ]
    control_id: Optional[int] = None
    asset_ids: Optional[List[int]] = None  # for add_control — defaults to all org assets if omitted
    vulnerability_id: Optional[int] = None
    new_effectiveness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    new_budget: Optional[float] = Field(default=None, ge=0.0)
    old_budget: Optional[float] = None  # defaults to the org's current annual_cyber_budget if omitted


class AssetSnapshotRead(BaseModel):
    asset_id: int
    asset_name: str
    risk_score: float
    likelihood: float
    expected_annual_loss: float


class WhatIfResponse(BaseModel):
    scenario_type: str
    description: str
    before: List[AssetSnapshotRead]
    after: List[AssetSnapshotRead]
    total_eal_before: float
    total_eal_after: float
    eal_change: float
    investment_change: float
    rosi_percent: Optional[float]
    affected_asset_ids: List[int]


class BudgetWhatIfResponse(BaseModel):
    scenario_type: str
    description: str
    old_budget: float
    new_budget: float
    old_total_investment: float
    new_total_investment: float
    old_risk_reduction: float
    new_risk_reduction: float
    additional_risk_reduction: float
    newly_affordable_controls: List[str]
