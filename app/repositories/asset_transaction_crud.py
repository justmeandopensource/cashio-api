from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.model import AssetTransaction, PhysicalAsset, Account, Transaction
from app.schemas.physical_assets_schema import AssetTransactionCreate, AssetTransactionUpdate


def create_asset_transaction(db: Session, ledger_id: int, transaction_data: AssetTransactionCreate) -> AssetTransaction:
    """Create a new asset transaction (buy or sell)."""
    # Validate physical asset exists and belongs to the ledger
    physical_asset = (
        db.query(PhysicalAsset)
        .filter(
            PhysicalAsset.physical_asset_id == transaction_data.physical_asset_id,
            PhysicalAsset.ledger_id == ledger_id
        )
        .first()
    )

    if not physical_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid physical_asset_id: Physical asset not found or doesn't belong to this ledger"
        )

    # Validate account exists and belongs to the ledger
    account = (
        db.query(Account)
        .filter(Account.account_id == transaction_data.account_id, Account.ledger_id == ledger_id)
        .first()
    )

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account_id: Account not found or doesn't belong to this ledger"
        )

    # Calculate total amount
    total_amount = Decimal(str(transaction_data.quantity)) * Decimal(str(transaction_data.price_per_unit))

    # For sell transactions, validate sufficient quantity
    if transaction_data.transaction_type == "sell":
        if physical_asset.total_quantity < Decimal(str(transaction_data.quantity)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient asset quantity. Available: {physical_asset.total_quantity}, Requested: {transaction_data.quantity}"
            )

    # For buy transactions, validate sufficient account balance
    if transaction_data.transaction_type == "buy":
        if account.net_balance < total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient account balance. Available: {account.net_balance}, Required: {total_amount}"
            )

    # Create corresponding financial transaction first
    financial_transaction = _create_financial_transaction(
        db=db,
        account=account,
        physical_asset=physical_asset,
        transaction_type=transaction_data.transaction_type,
        quantity=Decimal(str(transaction_data.quantity)),
        price_per_unit=Decimal(str(transaction_data.price_per_unit)),
        total_amount=total_amount,
        transaction_date=transaction_data.transaction_date
    )

    # Create asset transaction record
    db_transaction = AssetTransaction(
        ledger_id=ledger_id,
        physical_asset_id=transaction_data.physical_asset_id,
        transaction_type=transaction_data.transaction_type,
        quantity=Decimal(str(transaction_data.quantity)),
        price_per_unit=Decimal(str(transaction_data.price_per_unit)),
        total_amount=total_amount,
        account_id=transaction_data.account_id,
        financial_transaction_id=financial_transaction.transaction_id,
        transaction_date=transaction_data.transaction_date,
        notes=transaction_data.notes,
        created_at=datetime.now(timezone.utc),
    )

    db.add(db_transaction)
    db.flush()  # Flush to get the asset_transaction_id

    # Update physical asset quantities and costs
    from app.repositories.physical_asset_crud import update_asset_quantities_and_costs

    quantity_change = transaction_data.quantity if transaction_data.transaction_type == "buy" else -transaction_data.quantity
    cost_for_update = total_amount if transaction_data.transaction_type == "buy" else Decimal('0')

    update_asset_quantities_and_costs(
        db=db,
        physical_asset_id=transaction_data.physical_asset_id,
        quantity_change=Decimal(str(quantity_change)),
        total_cost=cost_for_update,
        price_per_unit=Decimal(str(transaction_data.price_per_unit))
    )

    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def _create_financial_transaction(db: Session, account: Account, physical_asset: PhysicalAsset, transaction_type: str, quantity: Decimal, price_per_unit: Decimal, total_amount: Decimal, transaction_date: datetime):
    """Create the corresponding financial transaction for the asset transaction."""
    from app.repositories.transaction_crud import create_transaction
    from app.schemas.transaction_schema import TransactionCreate

    # Determine transaction type and category
    if transaction_type == "buy":
        # Buy transaction: Debit asset account (expense)
        financial_transaction_type = "debit"
        type_literal = "expense"
        # For now, we'll use a generic category or create one if needed
        # This might need to be configurable in the future
        category_id = None  # Could be a "Physical Assets" category
    else:
        # Sell transaction: Credit asset account (income)
        financial_transaction_type = "credit"
        type_literal = "income"
        category_id = None  # Could be a "Physical Assets" category

    # Create detailed notes with asset information
    asset_name = physical_asset.name
    unit_symbol = physical_asset.asset_type.unit_symbol if physical_asset.asset_type else ""

    # Create the financial transaction
    transaction_data = TransactionCreate(
        account_id=account.account_id,
        category_id=category_id,
        type=type_literal,
        credit=total_amount if financial_transaction_type == "credit" else Decimal('0'),
        debit=total_amount if financial_transaction_type == "debit" else Decimal('0'),
        date=transaction_date,
        notes=f"Physical Asset {transaction_type.title()}: {asset_name} {quantity:.4f}{unit_symbol} at {price_per_unit:.2f}/{unit_symbol}",
        is_transfer=False,
        transfer_id=None,
        transfer_type=None,
        is_split=False,
        is_asset_transaction=True,
        splits=None,
        tags=None,
    )

    return create_transaction(db=db, transaction=transaction_data)


def get_asset_transactions_by_ledger_id(db: Session, ledger_id: int) -> List[AssetTransaction]:
    """Get all asset transactions for a specific ledger."""
    return (
        db.query(AssetTransaction)
        .options(joinedload(AssetTransaction.account), joinedload(AssetTransaction.physical_asset))
        .filter(AssetTransaction.ledger_id == ledger_id)
        .order_by(AssetTransaction.transaction_date.desc())
        .all()
    )


def get_asset_transactions_by_asset_id(db: Session, physical_asset_id: int) -> List[AssetTransaction]:
    """Get all transactions for a specific physical asset."""
    return (
        db.query(AssetTransaction)
        .options(joinedload(AssetTransaction.account), joinedload(AssetTransaction.physical_asset))
        .filter(AssetTransaction.physical_asset_id == physical_asset_id)
        .order_by(AssetTransaction.transaction_date.desc())
        .all()
    )


def get_asset_transaction_by_id(db: Session, asset_transaction_id: int) -> Optional[AssetTransaction]:
    """Get a specific asset transaction by ID."""
    return db.query(AssetTransaction).filter(AssetTransaction.asset_transaction_id == asset_transaction_id).first()


def update_asset_transaction(db: Session, asset_transaction_id: int, update_data: AssetTransactionUpdate) -> AssetTransaction:
    """Update an asset transaction."""
    db_transaction = db.query(AssetTransaction).filter(AssetTransaction.asset_transaction_id == asset_transaction_id).first()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset transaction not found"
        )

    # Update only the notes field for now
    if update_data.notes is not None:
        db_transaction.notes = update_data.notes

    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def delete_asset_transaction(db: Session, asset_transaction_id: int) -> bool:
    """
    Delete an asset transaction and its linked financial transaction.
    This function recalculates the asset's state from scratch to ensure consistency.
    """
    db_transaction = db.query(AssetTransaction).options(joinedload(AssetTransaction.account)).filter(AssetTransaction.asset_transaction_id == asset_transaction_id).first()

    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset transaction not found"
        )

    physical_asset_id = db_transaction.physical_asset_id
    financial_transaction_id = db_transaction.financial_transaction_id
    account = db_transaction.account

    # --- Step 1: Delete the transactions ---
    # Delete the linked financial transaction first to avoid FK constraints
    financial_transaction = db.query(Transaction).filter(Transaction.transaction_id == financial_transaction_id).first()
    if financial_transaction:
        db.delete(financial_transaction)

    # Delete the asset transaction itself
    db.delete(db_transaction)
    db.flush()  # Ensure deletion is processed before recalculation

    # --- Step 2: Recalculate the asset's state from remaining transactions ---
    physical_asset = db.query(PhysicalAsset).filter(PhysicalAsset.physical_asset_id == physical_asset_id).first()
    if not physical_asset:
        # This should not happen if the transaction existed
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated physical asset not found")

    remaining_transactions = (
        db.query(AssetTransaction)
        .filter(AssetTransaction.physical_asset_id == physical_asset_id)
        .order_by(AssetTransaction.transaction_date.asc(), AssetTransaction.created_at.asc())
        .all()
    )

    # Reset asset state
    new_total_quantity = Decimal('0')
    new_average_cost = Decimal('0')
    current_total_cost = Decimal('0')

    # Replay remaining transactions
    for tx in remaining_transactions:
        if tx.transaction_type == 'buy':
            new_total_quantity += tx.quantity
            current_total_cost += tx.total_amount
            if new_total_quantity > 0:
                new_average_cost = current_total_cost / new_total_quantity
        elif tx.transaction_type == 'sell':
            quantity_to_sell = tx.quantity
            if new_total_quantity >= quantity_to_sell:
                # Cost basis is reduced by the average cost of the sold units
                cost_of_sold_assets = quantity_to_sell * new_average_cost
                current_total_cost -= cost_of_sold_assets
                new_total_quantity -= quantity_to_sell
                # Average cost does not change on a sale
            else:
                # This indicates data inconsistency, should ideally not happen
                new_total_quantity = Decimal('0')
                current_total_cost = Decimal('0')

    # After replaying, if quantity is zero, average cost should also be zero
    if new_total_quantity <= 0:
        new_average_cost = Decimal('0')
        current_total_cost = Decimal('0')
        new_total_quantity = Decimal('0')

    # --- Step 3: Update the asset with the recalculated state ---
    physical_asset.total_quantity = new_total_quantity
    physical_asset.average_cost_per_unit = new_average_cost

    # Update latest price based on the last remaining transaction
    if remaining_transactions:
        last_tx = remaining_transactions[-1]
        physical_asset.latest_price_per_unit = last_tx.price_per_unit
        physical_asset.last_price_update = last_tx.transaction_date
    else:
        # No transactions left, reset price and value
        physical_asset.latest_price_per_unit = Decimal('0')
        physical_asset.last_price_update = None

    # Recalculate current value
    physical_asset.current_value = physical_asset.total_quantity * physical_asset.latest_price_per_unit
    physical_asset.updated_at = datetime.now(timezone.utc)

    # --- Step 4: Reverse account balance ---
    if account:
        if db_transaction.transaction_type == "buy":
            # Buy was a debit (expense), so add back to balance
            account.balance += db_transaction.total_amount
        else:  # sell
            # Sell was a credit (income), so subtract from balance
            account.balance -= db_transaction.total_amount
        
        # Recalculate net_balance
        account.net_balance = account.opening_balance + account.balance

    db.commit()
    return True