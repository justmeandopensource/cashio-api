from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.model import Account, Category, Transaction, TransactionSplit


def get_category_trend(
    db: Session,
    ledger_id: int,
    category_id: int,
    period_type: Literal[
        "last_12_months", "monthly_since_beginning", "yearly_since_beginning"
    ],
):
    # Get the category and check if it's a group
    category = db.query(Category).filter(Category.category_id == category_id).first()
    if not category:
        return {"error": "Category not found"}

    category_type = category.type

    # Get all descendant categories if it's a group
    all_category_ids = [category_id]
    if category.is_group is True:
        descendant_categories = _get_descendant_categories(db, category_id)
        all_category_ids.extend([c.category_id for c in descendant_categories])

    # Determine date range based on period type
    now = datetime.now()
    date_filter = None
    if period_type == "last_12_months":
        twelve_months_ago = now - timedelta(days=365)
        date_filter = Transaction.date >= twelve_months_ago

    # Set date grouping based on period type
    if period_type in ["last_12_months", "monthly_since_beginning"]:
        # Monthly grouping
        date_part = func.date_trunc("month", Transaction.date)
        date_format = "%Y-%m"
    else:
        # Yearly grouping
        date_part = func.date_trunc("year", Transaction.date)
        date_format = "%Y"

    # Get data from regular transactions (non-split, non-transfer)
    transaction_data = _get_transaction_data(
        db, ledger_id, all_category_ids, date_part, date_filter, str(category_type)
    )

    # Get data from split transactions
    split_data = _get_split_transaction_data(
        db, ledger_id, all_category_ids, date_part, date_filter, str(category_type)
    )

    # Combine and process results
    combined_data = _combine_transaction_data(transaction_data, split_data)

    # Convert to period-based structure
    periods_data = _structure_data_by_period(combined_data, date_format)

    # Calculate summary statistics
    summary = _calculate_summary(periods_data)

    return {
        "category_name": category.name,
        "category_type": category.type,
        "is_group": category.is_group,
        "trend_data": periods_data,
        "summary": summary,
    }


def _get_descendant_categories(db: Session, parent_id: int):
    """Recursively get all descendant categories."""
    direct_children = (
        db.query(Category).filter(Category.parent_category_id == parent_id).all()
    )

    all_descendants = list(direct_children)
    for child in direct_children:
        if child.is_group is True:
            all_descendants.extend(
                _get_descendant_categories(
                    db,
                    (
                        child.category_id
                        if isinstance(child.category_id, int)
                        else getattr(child, "category_id")
                    ),
                )
            )

    return all_descendants


def _get_transaction_data(
    db: Session,
    ledger_id: int,
    category_ids: List[int],
    date_part,
    date_filter,
    category_type: str,
):
    """Get data from regular transactions."""
    # Determine which calculation to use based on category_type
    if category_type == "income":
        amount_expr = func.sum(Transaction.credit - Transaction.debit).label("amount")
    else:
        amount_expr = func.sum(Transaction.debit - Transaction.credit).label("amount")

    query = (
        db.query(
            date_part.label("period"),
            Category.category_id,
            Category.name.label("category_name"),
            amount_expr,
        )
        .join(Account, Transaction.account_id == Account.account_id)
        .join(Category, Transaction.category_id == Category.category_id)
        .filter(
            Account.ledger_id == ledger_id,
            Transaction.category_id.in_(category_ids),
            Transaction.is_split == False,
            Transaction.is_transfer == False,
        )
        .group_by(date_part, Category.category_id, Category.name)
        .order_by(date_part)
    )

    if date_filter is not None:
        query = query.filter(date_filter)

    return query.all()


def _get_split_transaction_data(
    db: Session,
    ledger_id: int,
    category_ids: List[int],
    date_part,
    date_filter,
    category_type: str,
):
    """Get data from split transactions."""
    # Determine which calculation to use based on category_type
    if category_type == "income":
        amount_expr = func.sum(TransactionSplit.credit - TransactionSplit.debit).label(
            "amount"
        )
    else:
        amount_expr = func.sum(TransactionSplit.debit - TransactionSplit.credit).label(
            "amount"
        )

    query = (
        db.query(
            date_part.label("period"),
            Category.category_id,
            Category.name.label("category_name"),
            amount_expr,
        )
        .join(
            Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
        )
        .join(Account, Transaction.account_id == Account.account_id)
        .join(Category, TransactionSplit.category_id == Category.category_id)
        .filter(
            Account.ledger_id == ledger_id,
            TransactionSplit.category_id.in_(category_ids),
            Transaction.is_split == True,
            Transaction.is_transfer == False,
        )
        .group_by(date_part, Category.category_id, Category.name)
        .order_by(date_part)
    )

    if date_filter is not None:
        query = query.filter(date_filter)

    return query.all()


def _combine_transaction_data(transaction_data, split_data):
    """Combine regular and split transaction data."""
    combined = {}

    # Process both datasets
    for dataset in [transaction_data, split_data]:
        for period, category_id, category_name, amount in dataset:
            if period not in combined:
                combined[period] = {}

            if category_id not in combined[period]:
                combined[period][category_id] = {
                    "name": category_name,
                    "amount": Decimal(0),
                }

            combined[period][category_id]["amount"] += Decimal(amount or 0)

    return combined


def _structure_data_by_period(combined_data, date_format):
    """Structure data by period for the response."""
    periods_data = []

    for period, categories_data in sorted(combined_data.items()):
        period_str = period.strftime(date_format)

        category_data_points = [
            {
                "amount": float(data["amount"]),
                "category_name": data["name"],
            }
            for _, data in categories_data.items()
        ]

        periods_data.append({"period": period_str, "categories": category_data_points})

    return periods_data


def _calculate_summary(periods_data):
    """Calculate summary statistics for the trend data."""
    # Extract amounts across all periods
    all_amounts = []
    period_totals = {}

    for period_data in periods_data:
        period = period_data["period"]
        period_total = sum(cat["amount"] for cat in period_data["categories"])
        period_totals[period] = period_total
        all_amounts.append(period_total)

    # Calculate total amount
    total_amount = sum(all_amounts)

    # Determine max period and amount
    if period_totals:
        max_period = max(period_totals.items(), key=lambda x: x[1])[0]
        max_amount = max(all_amounts)
    else:
        max_period = None
        max_amount = 0

    # Calculate average (excluding periods with zero amount)
    non_zero_periods = sum(1 for amount in all_amounts if amount > 0)
    avg_amount = total_amount / non_zero_periods if non_zero_periods > 0 else 0

    return {
        "total": int(total_amount),
        "highest": {"period": max_period, "amount": int(max_amount)},
        "average": int(avg_amount),
    }
