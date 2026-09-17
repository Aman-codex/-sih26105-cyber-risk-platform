from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud import asset as asset_crud
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate

router = APIRouter(prefix="/assets", tags=["assets"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


@router.get("", response_model=list[AssetRead])
def list_assets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assets = asset_crud.list_assets(db, current_user.organization_id)
    return [AssetRead.from_orm_with_deps(a) for a in assets]


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_crud.get_asset(db, current_user.organization_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return AssetRead.from_orm_with_deps(asset)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def create_asset(payload: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_crud.create_asset(db, current_user.organization_id, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="create_asset", entity_type="asset", entity_id=str(asset.id)))
    db.commit()
    return AssetRead.from_orm_with_deps(asset)


@router.put("/{asset_id}", response_model=AssetRead, dependencies=[Depends(require_roles(*WRITE_ROLES))])
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_crud.get_asset(db, current_user.organization_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    asset = asset_crud.update_asset(db, asset, payload)
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="update_asset", entity_type="asset", entity_id=str(asset.id)))
    db.commit()
    return AssetRead.from_orm_with_deps(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CISO))])
def delete_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    asset = asset_crud.get_asset(db, current_user.organization_id, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    db.add(AuditLog(organization_id=current_user.organization_id, user_id=current_user.id, action="delete_asset", entity_type="asset", entity_id=str(asset.id)))
    asset_crud.delete_asset(db, asset)
    db.commit()
    return None
