from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.threat import Threat, ThreatEvent, threat_asset_relevance
from app.schemas.threat import ThreatCreate, ThreatEventCreate, ThreatUpdate


def get_threat(db: Session, org_id: int, threat_id: int) -> Optional[Threat]:
    return db.query(Threat).filter(Threat.id == threat_id, Threat.organization_id == org_id).first()


def list_threats(db: Session, org_id: int) -> List[Threat]:
    return db.query(Threat).filter(Threat.organization_id == org_id).order_by(Threat.id).all()


def _set_relevance(db: Session, threat: Threat, org_id: int, relevant_assets) -> None:
    # Clear existing relevance rows for this threat, then re-insert.
    db.execute(threat_asset_relevance.delete().where(threat_asset_relevance.c.threat_id == threat.id))
    for item in relevant_assets:
        asset = db.query(Asset).filter(Asset.id == item.asset_id, Asset.organization_id == org_id).first()
        if asset:
            db.execute(
                threat_asset_relevance.insert().values(
                    threat_id=threat.id, asset_id=asset.id, relevance_score=item.relevance_score
                )
            )


def create_threat(db: Session, org_id: int, payload: ThreatCreate) -> Threat:
    threat = Threat(
        organization_id=org_id,
        name=payload.name,
        threat_actor=payload.threat_actor,
        mitre_technique_id=payload.mitre_technique_id,
        mitre_tactic=payload.mitre_tactic,
        description=payload.description,
    )
    db.add(threat)
    db.commit()
    db.refresh(threat)

    if payload.relevant_assets:
        _set_relevance(db, threat, org_id, payload.relevant_assets)
        db.commit()
        db.refresh(threat)

    return threat


def update_threat(db: Session, threat: Threat, payload: ThreatUpdate) -> Threat:
    data = payload.model_dump(exclude_unset=True, exclude={"relevant_assets"})
    for field, value in data.items():
        setattr(threat, field, value)

    if payload.relevant_assets is not None:
        _set_relevance(db, threat, threat.organization_id, payload.relevant_assets)

    db.commit()
    db.refresh(threat)
    return threat


def delete_threat(db: Session, threat: Threat) -> None:
    db.delete(threat)
    db.commit()


def create_threat_event(db: Session, org_id: int, payload: ThreatEventCreate) -> ThreatEvent:
    event = ThreatEvent(
        organization_id=org_id,
        threat_id=payload.threat_id,
        asset_id=payload.asset_id,
        event_type=payload.event_type,
        severity=payload.severity,
        description=payload.description,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_threat_events(db: Session, org_id: int) -> List[ThreatEvent]:
    return (
        db.query(ThreatEvent)
        .filter(ThreatEvent.organization_id == org_id)
        .order_by(ThreatEvent.detected_at.desc())
        .all()
    )
