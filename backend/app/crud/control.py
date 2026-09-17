from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.security_control import SecurityControl, asset_controls
from app.schemas.control import ControlCreate, ControlUpdate


def get_control(db: Session, org_id: int, control_id: int) -> Optional[SecurityControl]:
    return (
        db.query(SecurityControl)
        .filter(SecurityControl.id == control_id, SecurityControl.organization_id == org_id)
        .first()
    )


def list_controls(db: Session, org_id: int) -> List[SecurityControl]:
    return (
        db.query(SecurityControl)
        .filter(SecurityControl.organization_id == org_id)
        .order_by(SecurityControl.id)
        .all()
    )


def _set_protected_assets(db: Session, control: SecurityControl, org_id: int, protected_assets) -> None:
    db.execute(asset_controls.delete().where(asset_controls.c.control_id == control.id))
    for item in protected_assets:
        asset = db.query(Asset).filter(Asset.id == item.asset_id, Asset.organization_id == org_id).first()
        if asset:
            db.execute(
                asset_controls.insert().values(
                    control_id=control.id,
                    asset_id=asset.id,
                    coverage_percentage=item.coverage_percentage,
                    implemented_on=item.implemented_on,
                )
            )


def create_control(db: Session, org_id: int, payload: ControlCreate) -> SecurityControl:
    control = SecurityControl(
        organization_id=org_id,
        name=payload.name,
        control_type=payload.control_type,
        description=payload.description,
        annual_cost=payload.annual_cost,
        effectiveness_score=payload.effectiveness_score,
        is_active=payload.is_active,
    )
    db.add(control)
    db.commit()
    db.refresh(control)

    if payload.protected_assets:
        _set_protected_assets(db, control, org_id, payload.protected_assets)
        db.commit()
        db.refresh(control)

    return control


def update_control(db: Session, control: SecurityControl, payload: ControlUpdate) -> SecurityControl:
    data = payload.model_dump(exclude_unset=True, exclude={"protected_assets"})
    for field, value in data.items():
        setattr(control, field, value)

    if payload.protected_assets is not None:
        _set_protected_assets(db, control, control.organization_id, payload.protected_assets)

    db.commit()
    db.refresh(control)
    return control


def delete_control(db: Session, control: SecurityControl) -> None:
    db.delete(control)
    db.commit()
