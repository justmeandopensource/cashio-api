from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from app.models.model import Account, Category, Transaction, TransactionSplit


def get_expense_calendar(
    db: Session,
    ledger_id: int,
    year: int,
):
    # Define date range for the year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)

    # Query for regular expense transactions
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
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    )

    # Query for split expense transactions
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
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    )

    # Aggregate results by date
    daily_totals = {}

    # Process regular transactions
    for transaction in base_regular_query.all():
        date_str = transaction.date.strftime("%Y-%m-%d")
        amount = float(transaction.debit - transaction.credit)
        if amount > 0:
            daily_totals[date_str] = daily_totals.get(date_str, 0) + amount

    # Process split transactions
    for split in base_split_query.all():
        date_str = split.transaction.date.strftime("%Y-%m-%d")
        amount = float(split.debit - split.credit)
        if amount > 0:
            daily_totals[date_str] = daily_totals.get(date_str, 0) + amount

    # Convert to list format expected by frontend
    expenses = [
        {"date": date, "amount": amount}
        for date, amount in daily_totals.items()
    ]

    # Sort by date
    expenses.sort(key=lambda x: x["date"])

    # Calculate total expense
    total_expense = sum(expense["amount"] for expense in expenses)

    return {
        "expenses": expenses,
        "total_expense": total_expense,
    }