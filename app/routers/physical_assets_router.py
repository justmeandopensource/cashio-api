from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import ledger_crud
from app.repositories.asset_type_crud import (
    create_asset_type as create_asset_type_repo,
    get_asset_types_by_ledger_id,
    get_asset_type_by_id,
    update_asset_type as update_asset_type_repo,
    delete_asset_type as delete_asset_type_repo,
)
from app.repositories.physical_asset_crud import (
    create_physical_asset as create_physical_asset_repo,
    get_physical_assets_by_ledger_id,
    get_physical_asset_by_id,
    update_physical_asset as update_physical_asset_repo,
    update_physical_asset_price,
    delete_physical_asset as delete_physical_asset_repo,
)
from app.repositories.asset_transaction_crud import (
    create_asset_transaction,
    get_asset_transactions_by_asset_id,
    get_asset_transactions_by_ledger_id,
    update_asset_transaction,
    delete_asset_transaction,
)
from app.schemas import physical_assets_schema, user_schema
from app.security.user_security import get_current_user

physical_assets_router = APIRouter(prefix="/ledger")


# Asset Type Management Endpoints
@physical_assets_router.post(
    "/{ledger_id}/asset-type/create",
    response_model=physical_assets_schema.AssetType,
    tags=["physical-assets"],
)
def create_asset_type(
    ledger_id: int,
    asset_type: physical_assets_schema.AssetTypeCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new asset type for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        new_asset_type = create_asset_type_repo(
            db=db, ledger_id=ledger_id, asset_type=asset_type
        )
        return new_asset_type
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating asset type: {str(e)}",
        )


@physical_assets_router.get(
    "/{ledger_id}/asset-types",
    response_model=List[physical_assets_schema.AssetType],
    tags=["physical-assets"],
)
def get_asset_types(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all asset types for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    asset_types = get_asset_types_by_ledger_id(db=db, ledger_id=ledger_id)
    return asset_types


@physical_assets_router.put(
    "/{ledger_id}/asset-type/{type_id}",
    response_model=physical_assets_schema.AssetType,
    tags=["physical-assets"],
)
def update_asset_type(
    ledger_id: int,
    type_id: int,
    asset_type_update: physical_assets_schema.AssetTypeUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an asset type."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset type belongs to this ledger
    asset_type = get_asset_type_by_id(db=db, asset_type_id=type_id)
    if not asset_type or asset_type.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Asset type not found")

    updated_asset_type = update_asset_type_repo(
        db=db, asset_type_id=type_id, asset_type_update=asset_type_update
    )
    return updated_asset_type


@physical_assets_router.delete(
    "/{ledger_id}/asset-type/{type_id}",
    tags=["physical-assets"],
)
def delete_asset_type(
    ledger_id: int,
    type_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an asset type."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset type belongs to this ledger
    asset_type = get_asset_type_by_id(db=db, asset_type_id=type_id)
    if not asset_type or asset_type.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Asset type not found")

    delete_asset_type_repo(db=db, asset_type_id=type_id)
    return {"message": "Asset type deleted successfully"}


# Physical Asset Management Endpoints
@physical_assets_router.post(
    "/{ledger_id}/physical-asset/create",
    response_model=physical_assets_schema.PhysicalAsset,
    tags=["physical-assets"],
)
def create_physical_asset(
    ledger_id: int,
    asset: physical_assets_schema.PhysicalAssetCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new physical asset for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        new_asset = create_physical_asset_repo(
            db=db, ledger_id=ledger_id, asset=asset
        )
        return new_asset
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating physical asset: {str(e)}",
        )


@physical_assets_router.get(
    "/{ledger_id}/physical-assets",
    response_model=List[physical_assets_schema.PhysicalAsset],
    tags=["physical-assets"],
)
def get_physical_assets(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all physical assets for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    assets = get_physical_assets_by_ledger_id(db=db, ledger_id=ledger_id)
    return assets


@physical_assets_router.get(
    "/{ledger_id}/physical-assets/{asset_id}",
    response_model=physical_assets_schema.PhysicalAsset,
    tags=["physical-assets"],
)
def get_physical_asset(
    ledger_id: int,
    asset_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific physical asset."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    asset = get_physical_asset_by_id(db=db, physical_asset_id=asset_id)
    if not asset or asset.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Physical asset not found")

    return asset


@physical_assets_router.put(
    "/{ledger_id}/physical-asset/{asset_id}",
    response_model=physical_assets_schema.PhysicalAsset,
    tags=["physical-assets"],
)
def update_physical_asset(
    ledger_id: int,
    asset_id: int,
    asset_update: physical_assets_schema.PhysicalAssetUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a physical asset."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset belongs to this ledger
    asset = get_physical_asset_by_id(db=db, physical_asset_id=asset_id)
    if not asset or asset.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Physical asset not found")

    updated_asset = update_physical_asset_repo(
        db=db, physical_asset_id=asset_id, asset_update=asset_update
    )
    return updated_asset


@physical_assets_router.put(
    "/{ledger_id}/physical-asset/{asset_id}/update-price",
    response_model=physical_assets_schema.PhysicalAsset,
    tags=["physical-assets"],
)
def update_asset_price(
    ledger_id: int,
    asset_id: int,
    price_update: physical_assets_schema.PhysicalAssetPriceUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the latest price for a physical asset."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset belongs to this ledger
    asset = get_physical_asset_by_id(db=db, physical_asset_id=asset_id)
    if not asset or asset.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Physical asset not found")

    updated_asset = update_physical_asset_price(
        db=db, physical_asset_id=asset_id, price_update=price_update
    )
    return updated_asset


@physical_assets_router.delete(
    "/{ledger_id}/physical-asset/{asset_id}",
    tags=["physical-assets"],
)
def delete_physical_asset(
    ledger_id: int,
    asset_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a physical asset."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset belongs to this ledger
    asset = get_physical_asset_by_id(db=db, physical_asset_id=asset_id)
    if not asset or asset.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Physical asset not found")

    delete_physical_asset_repo(db=db, physical_asset_id=asset_id)
    return {"message": "Physical asset deleted successfully"}


# Asset Transaction Management Endpoints
@physical_assets_router.post(
    "/{ledger_id}/asset-transaction/buy",
    response_model=physical_assets_schema.AssetTransaction,
    tags=["physical-assets"],
)
def buy_asset(
    ledger_id: int,
    transaction: physical_assets_schema.AssetTransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buy physical assets."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Ensure this is a buy transaction
    if transaction.transaction_type != "buy":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for buy transactions only"
        )

    try:
        new_transaction = create_asset_transaction(
            db=db, ledger_id=ledger_id, transaction_data=transaction
        )
        return new_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing buy transaction: {str(e)}",
        )


@physical_assets_router.post(
    "/{ledger_id}/asset-transaction/sell",
    response_model=physical_assets_schema.AssetTransaction,
    tags=["physical-assets"],
)
def sell_asset(
    ledger_id: int,
    transaction: physical_assets_schema.AssetTransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sell physical assets."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Ensure this is a sell transaction
    if transaction.transaction_type != "sell":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for sell transactions only"
        )

    try:
        new_transaction = create_asset_transaction(
            db=db, ledger_id=ledger_id, transaction_data=transaction
        )
        return new_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing sell transaction: {str(e)}",
        )


@physical_assets_router.get(
    "/{ledger_id}/physical-assets/{asset_id}/transactions",
    response_model=List[physical_assets_schema.AssetTransaction],
    tags=["physical-assets"],
)
def get_asset_transactions(
    ledger_id: int,
    asset_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transaction history for a specific physical asset."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset belongs to this ledger
    asset = get_physical_asset_by_id(db=db, physical_asset_id=asset_id)
    if not asset or asset.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Physical asset not found")

    transactions = get_asset_transactions_by_asset_id(
        db=db, physical_asset_id=asset_id
    )
    for t in transactions:
        if t.account:
            t.account_name = t.account.name
    return transactions


@physical_assets_router.get(
    "/{ledger_id}/asset-transactions",
    response_model=List[physical_assets_schema.AssetTransaction],
    tags=["physical-assets"],
)
def get_all_asset_transactions(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all asset transactions for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    transactions = get_asset_transactions_by_ledger_id(
        db=db, ledger_id=ledger_id
    )
    for t in transactions:
        if t.account:
            t.account_name = t.account.name
    return transactions


@physical_assets_router.delete(
    "/{ledger_id}/asset-transaction/{asset_transaction_id}",
    tags=["physical-assets"],
)
def delete_asset_transaction_endpoint(
    ledger_id: int,
    asset_transaction_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an asset transaction and its linked financial transaction."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset transaction belongs to this ledger
    from app.repositories.asset_transaction_crud import get_asset_transaction_by_id
    asset_transaction = get_asset_transaction_by_id(db=db, asset_transaction_id=asset_transaction_id)
    if not asset_transaction or asset_transaction.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Asset transaction not found")

    try:
        delete_asset_transaction(db=db, asset_transaction_id=asset_transaction_id)
        return {"message": "Asset transaction deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting asset transaction: {str(e)}",
        )


@physical_assets_router.patch(
    "/{ledger_id}/asset-transaction/{asset_transaction_id}",
    response_model=physical_assets_schema.AssetTransaction,
    tags=["physical-assets"],
)
def update_asset_transaction_endpoint(
    ledger_id: int,
    asset_transaction_id: int,
    transaction_update: physical_assets_schema.AssetTransactionUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an asset transaction."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the asset transaction belongs to this ledger
    from app.repositories.asset_transaction_crud import get_asset_transaction_by_id
    asset_transaction = get_asset_transaction_by_id(db=db, asset_transaction_id=asset_transaction_id)
    if not asset_transaction or asset_transaction.ledger_id != ledger_id:
        raise HTTPException(status_code=404, detail="Asset transaction not found")

    try:
        updated_transaction = update_asset_transaction(
            db=db, asset_transaction_id=asset_transaction_id, update_data=transaction_update
        )
        return updated_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating asset transaction: {str(e)}",
        )