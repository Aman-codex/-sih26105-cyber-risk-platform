from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Severity


class ThreatBase(BaseModel):
    name: str
    threat_actor: Optional[str] = None
    mitre_technique_id: Optional[str] = None
    mitre_tactic: Optional[str] = None
    description: Optional[str] = None


class RelevantAsset(BaseModel):
    asset_id: int
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class ThreatCreate(ThreatBase):
    relevant_assets: List[RelevantAsset] = Field(default_factory=list)


class ThreatUpdate(BaseModel):
    name: Optional[str] = None
    threat_actor: Optional[str] = None
    mitre_technique_id: Optional[str] = None
    mitre_tactic: Optional[str] = None
    description: Optional[str] = None
    relevant_assets: Optional[List[RelevantAsset]] = None


class ThreatRead(ThreatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    relevant_asset_ids: List[int] = Field(default_factory=list)

    @classmethod
    def from_orm_with_assets(cls, threat) -> "ThreatRead":
        obj = cls.model_validate(threat)
        obj.relevant_asset_ids = [a.id for a in threat.relevant_assets]
        return obj


class ThreatEventBase(BaseModel):
    threat_id: int
    asset_id: Optional[int] = None
    event_type: str
    severity: Severity = Severity.MEDIUM
    description: Optional[str] = None


class ThreatEventCreate(ThreatEventBase):
    pass


class ThreatEventRead(ThreatEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    detected_at: datetime
