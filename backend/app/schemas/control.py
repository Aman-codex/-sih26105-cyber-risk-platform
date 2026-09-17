from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ControlType


class ControlBase(BaseModel):
    name: str
    control_type: ControlType
    description: Optional[str] = None
    annual_cost: float = Field(default=0.0, ge=0)
    effectiveness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_active: bool = True


class ProtectedAsset(BaseModel):
    asset_id: int
    coverage_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    implemented_on: Optional[date] = None


class ControlCreate(ControlBase):
    protected_assets: List[ProtectedAsset] = Field(default_factory=list)


class ControlUpdate(BaseModel):
    name: Optional[str] = None
    control_type: Optional[ControlType] = None
    description: Optional[str] = None
    annual_cost: Optional[float] = Field(default=None, ge=0)
    effectiveness_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None
    protected_assets: Optional[List[ProtectedAsset]] = None


class ControlRead(ControlBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    protected_asset_ids: List[int] = Field(default_factory=list)

    @classmethod
    def from_orm_with_assets(cls, control) -> "ControlRead":
        obj = cls.model_validate(control)
        obj.protected_asset_ids = [a.id for a in control.protected_assets]
        return obj
