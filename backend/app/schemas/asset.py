from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BusinessCriticality


class AssetBase(BaseModel):
    name: str
    asset_type: str
    description: Optional[str] = None
    business_criticality: BusinessCriticality = BusinessCriticality.MEDIUM
    business_value: float = Field(default=0.0, ge=0)
    internet_exposure: bool = False


class AssetCreate(AssetBase):
    depends_on_ids: List[int] = Field(default_factory=list)


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    description: Optional[str] = None
    business_criticality: Optional[BusinessCriticality] = None
    business_value: Optional[float] = Field(default=None, ge=0)
    internet_exposure: Optional[bool] = None
    depends_on_ids: Optional[List[int]] = None


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    depends_on_ids: List[int] = Field(default_factory=list)

    @classmethod
    def from_orm_with_deps(cls, asset) -> "AssetRead":
        obj = cls.model_validate(asset)
        obj.depends_on_ids = [dep.id for dep in asset.depends_on]
        return obj
