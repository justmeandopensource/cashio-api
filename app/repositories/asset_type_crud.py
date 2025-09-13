from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.model import AssetType
from app.schemas.physical_assets_schema import AssetTypeCreate, AssetTypeUpdate


def create_asset_type(db: Session, ledger_id: int, asset_type: AssetTypeCreate) -> AssetType:
    """Create a new asset type for a ledger."""
    # Check if asset type with same name already exists in this ledger
    existing_asset_type = (
        db.query(AssetType)
        .filter(AssetType.ledger_id == ledger_id, AssetType.name == asset_type.name)
        .first()
    )

    if existing_asset_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset type with this name already exists in the ledger"
        )

    db_asset_type = AssetType(
        ledger_id=ledger_id,
        name=asset_type.name,
        unit_name=asset_type.unit_name,
        unit_symbol=asset_type.unit_symbol,
        description=asset_type.description,
        created_at=datetime.now(timezone.utc),
    )

    db.add(db_asset_type)
    db.commit()
    db.refresh(db_asset_type)
    return db_asset_type


def get_asset_types_by_ledger_id(db: Session, ledger_id: int) -> List[AssetType]:
    """Get all asset types for a specific ledger."""
    return db.query(AssetType).filter(AssetType.ledger_id == ledger_id).order_by(AssetType.name).all()


def get_asset_type_by_id(db: Session, asset_type_id: int) -> Optional[AssetType]:
    """Get a specific asset type by ID."""
    return db.query(AssetType).filter(AssetType.asset_type_id == asset_type_id).first()


def update_asset_type(db: Session, asset_type_id: int, asset_type_update: AssetTypeUpdate) -> AssetType:
    """Update an asset type."""
    db_asset_type = db.query(AssetType).filter(AssetType.asset_type_id == asset_type_id).first()

    if not db_asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset type not found"
        )

    # Check for name uniqueness if name is being updated
    if asset_type_update.name is not None and asset_type_update.name != db_asset_type.name:
        existing_asset_type = (
            db.query(AssetType)
            .filter(
                AssetType.ledger_id == db_asset_type.ledger_id,
                AssetType.name == asset_type_update.name,
                AssetType.asset_type_id != asset_type_id
            )
            .first()
        )

        if existing_asset_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Asset type with this name already exists in the ledger"
            )

    # Update fields
    if asset_type_update.name is not None:
        db_asset_type.name = asset_type_update.name
    if asset_type_update.unit_name is not None:
        db_asset_type.unit_name = asset_type_update.unit_name
    if asset_type_update.unit_symbol is not None:
        db_asset_type.unit_symbol = asset_type_update.unit_symbol
    if asset_type_update.description is not None:
        db_asset_type.description = asset_type_update.description

    db.commit()
    db.refresh(db_asset_type)
    return db_asset_type


def delete_asset_type(db: Session, asset_type_id: int) -> bool:
    """Delete an asset type if it has no associated physical assets."""
    db_asset_type = db.query(AssetType).filter(AssetType.asset_type_id == asset_type_id).first()

    if not db_asset_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset type not found"
        )

    # Check if there are any physical assets using this asset type
    if db_asset_type.physical_assets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete asset type that has associated physical assets"
        )

    db.delete(db_asset_type)
    db.commit()
    return True