from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.model import Account, Category, Transaction


def get_income_expense_trend(
    db: Session,
    ledger_id: int,
    period_type: Literal[
        "last_12_months", "monthly_since_beginning", "yearly_since_beginning"
    ],
):
    # Base query to filter transactions for this ledger
    base_query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .filter(Account.ledger_id == ledger_id)
    )

    # Determine date range based on period type
    now = datetime.now()
    if period_type == "last_12_months":
        twelve_months_ago = now - timedelta(days=365)
        base_query = base_query.filter(Transaction.date >= twelve_months_ago)

    # Group by and aggregate based on period type
    if period_type in ["last_12_months", "monthly_since_beginning"]:
        # Monthly grouping
        date_part = func.date_trunc("month", Transaction.date)
    else:
        # Yearly grouping
        date_part = func.date_trunc("year", Transaction.date)

    # Query for income (credits in income categories)
    income_query = (
        base_query.join(Category, Transaction.category_id == Category.category_id)
        .filter(Category.type == "income")
        .with_entities(
            date_part.label("period"),
            func.sum(Transaction.credit).label("income_amount"),
        )
        .group_by(date_part)
        .order_by(date_part)
    )

    # Query for expense (net of debits minus credits in expense categories)
    expense_query = (
        base_query.join(Category, Transaction.category_id == Category.category_id)
        .filter(Category.type == "expense")
        .with_entities(
            date_part.label("period"),
            (func.sum(Transaction.debit) - func.sum(Transaction.credit)).label(
                "expense_amount"
            ),
        )
        .group_by(date_part)
        .order_by(date_part)
    )

    # Execute queries
    income_results = income_query.all()
    expense_results = expense_query.all()

    # Combine and process results
    periods = {}

    # Process income results
    for period, income_amount in income_results:
        if period not in periods:
            periods[period] = {"income": Decimal(0), "expense": Decimal(0)}
        periods[period]["income"] += Decimal(income_amount or 0)

    # Process expense results
    for period, expense_amount in expense_results:
        if period not in periods:
            periods[period] = {"income": Decimal(0), "expense": Decimal(0)}
        periods[period]["expense"] += Decimal(expense_amount or 0)

    # Convert to sorted list of periods
    sorted_periods = sorted(periods.items())

    trend_data = [
        {
            "period": (
                period.strftime("%Y-%m")
                if period_type in ["last_12_months", "monthly_since_beginning"]
                else period.strftime("%Y")
            ),
            "income": float(data["income"]),
            "expense": float(data["expense"]),
        }
        for period, data in sorted_periods
    ]

    # Calculate summary statistics
    income_values = [item["income"] for item in trend_data]
    expense_values = [item["expense"] for item in trend_data]

    total_income = sum(income_values)
    total_expense = sum(expense_values)

    # Handling max income
    max_income = max(income_values) if income_values else 0
    max_income_period = next(
        (item["period"] for item in trend_data if item["income"] == max_income), None
    )

    # Handling max expense
    max_expense = max(expense_values) if expense_values else 0
    max_expense_period = next(
        (item["period"] for item in trend_data if item["expense"] == max_expense), None
    )

    # Calculate averages
    months_with_income = sum(1 for i in income_values if i > 0)
    months_with_expense = sum(1 for e in expense_values if e > 0)
    avg_income = int(total_income / months_with_income) if months_with_income else 0
    avg_expense = int(total_expense / months_with_expense) if months_with_expense else 0

    return {
        "trend_data": trend_data,
        "summary": {
            "income": {
                "total": int(total_income),
                "highest": {"period": max_income_period, "amount": int(max_income)},
                "average": avg_income,
            },
            "expense": {
                "total": int(total_expense),
                "highest": {"period": max_expense_period, "amount": int(max_expense)},
                "average": avg_expense,
            },
        },
    }
