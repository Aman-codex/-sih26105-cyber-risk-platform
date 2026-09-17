from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate


def get_asset(db: Session, org_id: int, asset_id: int) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id, Asset.organization_id == org_id).first()


def list_assets(db: Session, org_id: int) -> List[Asset]:
    return db.query(Asset).filter(Asset.organization_id == org_id).order_by(Asset.id).all()


def _resolve_dependencies(db: Session, org_id: int, depends_on_ids: List[int]) -> List[Asset]:
    if not depends_on_ids:
        return []
    return db.query(Asset).filter(Asset.id.in_(depends_on_ids), Asset.organization_id == org_id).all()


def create_asset(db: Session, org_id: int, payload: AssetCreate) -> Asset:
    asset = Asset(
        organization_id=org_id,
        name=payload.name,
        asset_type=payload.asset_type,
        description=payload.description,
        business_criticality=payload.business_criticality,
        business_value=payload.business_value,
        internet_exposure=payload.internet_exposure,
    )
    asset.depends_on = _resolve_dependencies(db, org_id, payload.depends_on_ids)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset: Asset, payload: AssetUpdate) -> Asset:
    data = payload.model_dump(exclude_unset=True, exclude={"depends_on_ids"})
    for field, value in data.items():
        setattr(asset, field, value)

    if payload.depends_on_ids is not None:
        asset.depends_on = _resolve_dependencies(db, asset.organization_id, payload.depends_on_ids)

    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    db.delete(asset)
    db.commit()
