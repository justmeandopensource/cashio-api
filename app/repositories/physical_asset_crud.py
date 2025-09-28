from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.model import PhysicalAsset, AssetType, AssetTransaction
from app.schemas.physical_assets_schema import PhysicalAssetCreate, PhysicalAssetUpdate, PhysicalAssetPriceUpdate


def create_physical_asset(db: Session, ledger_id: int, asset: PhysicalAssetCreate) -> PhysicalAsset:
    """Create a new physical asset for a ledger."""
    # Check if physical asset with same name already exists in this ledger
    existing_asset = (
        db.query(PhysicalAsset)
        .filter(PhysicalAsset.ledger_id == ledger_id, PhysicalAsset.name == asset.name)
        .first()
    )

    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Physical asset with this name already exists in the ledger"
        )

    # Validate that asset_type_id exists and belongs to the same ledger
    asset_type = (
        db.query(AssetType)
        .filter(AssetType.asset_type_id == asset.asset_type_id, AssetType.ledger_id == ledger_id)
        .first()
    )

    if not asset_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid asset_type_id: Asset type not found or doesn't belong to this ledger"
        )

    db_asset = PhysicalAsset(
        ledger_id=ledger_id,
        asset_type_id=asset.asset_type_id,
        name=asset.name,
        total_quantity=Decimal('0'),
        average_cost_per_unit=Decimal('0'),
        latest_price_per_unit=Decimal('0'),
        current_value=Decimal('0'),
        notes=asset.notes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def get_physical_assets_by_ledger_id(db: Session, ledger_id: int) -> List[PhysicalAsset]:
    """Get all physical assets for a specific ledger with asset type information."""
    return (
        db.query(PhysicalAsset)
        .filter(PhysicalAsset.ledger_id == ledger_id)
        .order_by(PhysicalAsset.name)
        .all()
    )


def get_physical_asset_by_id(db: Session, physical_asset_id: int) -> Optional[PhysicalAsset]:
    """Get a specific physical asset by ID."""
    return db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()


def update_physical_asset(db: Session, physical_asset_id: int, asset_update: PhysicalAssetUpdate) -> PhysicalAsset:
    """Update a physical asset."""
    db_asset = db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical asset not found"
        )

    # Check for name uniqueness if name is being updated
    if asset_update.name is not None and asset_update.name != db_asset.name:
        existing_asset = (
            db.query(PhysicalAsset)
            .filter(
                PhysicalAsset.ledger_id == db_asset.ledger_id,
                PhysicalAsset.name == asset_update.name,
                PhysicalAsset.physical_asset_id != physical_asset_id
            )
            .first()
        )

        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Physical asset with this name already exists in the ledger"
            )

    # Validate asset_type_id if being updated
    if asset_update.asset_type_id is not None:
        asset_type = (
            db.query(AssetType)
            .filter(
                AssetType.asset_type_id == asset_update.asset_type_id,
                AssetType.ledger_id == db_asset.ledger_id
            )
            .first()
        )

        if not asset_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid asset_type_id: Asset type not found or doesn't belong to this ledger"
            )

    # Update fields
    if asset_update.name is not None:
        db_asset.name = asset_update.name  # type: ignore
    if asset_update.asset_type_id is not None:
        db_asset.asset_type_id = asset_update.asset_type_id  # type: ignore
    if asset_update.notes is not None:
        db_asset.notes = asset_update.notes  # type: ignore

    db_asset.updated_at = datetime.now(timezone.utc)  # type: ignore

    db.commit()
    db.refresh(db_asset)
    return db_asset


def update_physical_asset_price(db: Session, physical_asset_id: int, price_update: PhysicalAssetPriceUpdate) -> PhysicalAsset:
    """Update the latest price for a physical asset and recalculate current value."""
    db_asset = db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical asset not found"
        )

    # Update price and recalculate current value
    db_asset.latest_price_per_unit = Decimal(str(price_update.latest_price_per_unit))  # type: ignore
    db_asset.current_value = db_asset.total_quantity * db_asset.latest_price_per_unit  # type: ignore
    db_asset.last_price_update = datetime.now(timezone.utc)  # type: ignore
    db_asset.updated_at = datetime.now(timezone.utc)  # type: ignore

    db.commit()
    db.refresh(db_asset)
    return db_asset


def delete_physical_asset(db: Session, physical_asset_id: int) -> bool:
    """Delete a physical asset if it has no transactions."""
    db_asset = db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical asset not found"
        )

    # Check if there are any transactions for this asset
    transaction_count = db.query(AssetTransaction).filter(
        AssetTransaction.physical_asset_id == physical_asset_id
    ).count()

    if transaction_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete physical asset that has associated transactions"
        )

    db.delete(db_asset)
    db.commit()
    return True


def update_asset_quantities_and_costs(db: Session, physical_asset_id: int, quantity_change: Decimal, total_cost: Decimal, price_per_unit: Optional[Decimal] = None) -> PhysicalAsset:
    """Update asset quantities and average costs after a transaction."""
    db_asset = db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical asset not found"
        )

    new_quantity = db_asset.total_quantity + quantity_change

    if new_quantity < 0:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient asset quantity for sell transaction"
        )

    # Calculate new average cost
    if new_quantity == 0:  # type: ignore
        new_average_cost = Decimal('0')
    else:
        # If buying, recalculate the average cost.
        if quantity_change > 0:  # type: ignore
            current_total_cost = db_asset.total_quantity * db_asset.average_cost_per_unit
            new_total_cost = current_total_cost + total_cost
            new_average_cost = new_total_cost / new_quantity
        # If selling, the average cost of the remaining assets does not change.
        else:
            new_average_cost = db_asset.average_cost_per_unit

    # Update asset
    db_asset.total_quantity = new_quantity  # type: ignore
    db_asset.average_cost_per_unit = new_average_cost  # type: ignore
    
    if price_per_unit is not None:
        db_asset.latest_price_per_unit = price_per_unit  # type: ignore
        db_asset.last_price_update = datetime.now(timezone.utc)  # type: ignore

    db_asset.current_value = new_quantity * db_asset.latest_price_per_unit  # type: ignore
    db_asset.updated_at = datetime.now(timezone.utc)  # type: ignore

    db.commit()
    db.refresh(db_asset)
    return db_asset