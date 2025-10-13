from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy.orm import Session

from app.models.model import Account, Category, Transaction, TransactionSplit


def get_expense_by_store(
    db: Session,
    ledger_id: int,
    period_type: Literal["all_time", "last_12_months", "this_month"],
):
    now = datetime.now()

    # Determine date range based on period_type
    if period_type == "this_month":
        start_date = now.replace(day=1)
    elif period_type == "last_12_months":
        start_date = now - timedelta(days=365)
    else:  # all_time
        start_date = None

    # Query for regular expense transactions with store data
    base_regular_query = db.query(Transaction).join(
        Account, Transaction.account_id == Account.account_id
    ).join(
        Category, Transaction.category_id == Category.category_id
    ).filter(
        Account.ledger_id == ledger_id,
        Transaction.is_split == False,
        Transaction.is_transfer == False,
        Transaction.is_asset_transaction == False,
        Transaction.is_mf_transaction == False,
        Category.type == "expense",
        Transaction.store.isnot(None),
        Transaction.store != "",
    )

    # Query for split expense transactions with store data
    base_split_query = db.query(TransactionSplit).join(
        Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
    ).join(
        Account, Transaction.account_id == Account.account_id
    ).join(
        Category, TransactionSplit.category_id == Category.category_id
    ).filter(
        Account.ledger_id == ledger_id,
        Transaction.is_split == True,
        Transaction.is_transfer == False,
        Transaction.is_asset_transaction == False,
        Transaction.is_mf_transaction == False,
        Category.type == "expense",
        Transaction.store.isnot(None),
        Transaction.store != "",
    )

    # Apply date filter if specified
    if start_date:
        base_regular_query = base_regular_query.filter(Transaction.date >= start_date)
        base_split_query = base_split_query.filter(Transaction.date >= start_date)

    # Aggregate results by store
    store_totals = {}

    # Process regular transactions
    for transaction in base_regular_query.all():
        store = transaction.store
        amount = float(transaction.debit - transaction.credit)
        if amount > 0:
            store_totals[store] = store_totals.get(store, 0) + amount

    # Process split transactions
    for split in base_split_query.all():
        store = split.transaction.store  # Access store from the related transaction
        amount = float(split.debit - split.credit)
        if amount > 0:
            store_totals[store] = store_totals.get(store, 0) + amount

    # Convert to list and sort by amount descending, take top 10
    store_data = [
        {"store": store, "amount": amount, "percentage": 0.0}
        for store, amount in store_totals.items()
        if amount > 0
    ]
    store_data.sort(key=lambda x: x["amount"], reverse=True)
    top_stores = store_data[:10]

    # Calculate total and percentages
    total_amount = sum(store["amount"] for store in top_stores)
    for store in top_stores:
        store["percentage"] = (store["amount"] / total_amount * 100) if total_amount > 0 else 0

    return {
        "store_data": top_stores,
        "total_expense": total_amount,
        "period_type": period_type,
    }


def get_expense_by_location(
    db: Session,
    ledger_id: int,
    period_type: Literal["all_time", "last_12_months", "this_month"],
):
    now = datetime.now()

    # Determine date range based on period_type
    if period_type == "this_month":
        start_date = now.replace(day=1)
    elif period_type == "last_12_months":
        start_date = now - timedelta(days=365)
    else:  # all_time
        start_date = None

    # Query for regular expense transactions with location data
    base_regular_query = db.query(Transaction).join(
        Account, Transaction.account_id == Account.account_id
    ).join(
        Category, Transaction.category_id == Category.category_id
    ).filter(
        Account.ledger_id == ledger_id,
        Transaction.is_split == False,
        Transaction.is_transfer == False,
        Transaction.is_asset_transaction == False,
        Transaction.is_mf_transaction == False,
        Category.type == "expense",
        Transaction.location.isnot(None),
        Transaction.location != "",
    )

    # Query for split expense transactions with location data
    base_split_query = db.query(TransactionSplit).join(
        Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
    ).join(
        Account, Transaction.account_id == Account.account_id
    ).join(
        Category, TransactionSplit.category_id == Category.category_id
    ).filter(
        Account.ledger_id == ledger_id,
        Transaction.is_split == True,
        Transaction.is_transfer == False,
        Transaction.is_asset_transaction == False,
        Transaction.is_mf_transaction == False,
        Category.type == "expense",
        Transaction.location.isnot(None),
        Transaction.location != "",
    )

    # Apply date filter if specified
    if start_date:
        base_regular_query = base_regular_query.filter(Transaction.date >= start_date)
        base_split_query = base_split_query.filter(Transaction.date >= start_date)

    # Aggregate results by location
    location_totals = {}

    # Process regular transactions
    for transaction in base_regular_query.all():
        location = transaction.location
        amount = float(transaction.debit - transaction.credit)
        if amount > 0:
            location_totals[location] = location_totals.get(location, 0) + amount

    # Process split transactions
    for split in base_split_query.all():
        location = split.transaction.location  # Access location from the related transaction
        amount = float(split.debit - split.credit)
        if amount > 0:
            location_totals[location] = location_totals.get(location, 0) + amount

    # Convert to list and sort by amount descending, take top 10
    location_data = [
        {"location": location, "amount": amount, "percentage": 0.0}
        for location, amount in location_totals.items()
        if amount > 0
    ]
    location_data.sort(key=lambda x: x["amount"], reverse=True)
    top_locations = location_data[:10]

    # Calculate total and percentages
    total_amount = sum(location["amount"] for location in top_locations)
    for location in top_locations:
        location["percentage"] = (location["amount"] / total_amount * 100) if total_amount > 0 else 0

    return {
        "location_data": top_locations,
        "total_expense": total_amount,
        "period_type": period_type,
    }