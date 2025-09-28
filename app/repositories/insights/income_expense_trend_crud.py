from datetime import datetime, timedelta
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, func, select, union_all
from sqlalchemy.orm import Session

from app.models.model import Account, Category, Transaction, TransactionSplit


def get_income_expense_trend(
    db: Session,
    ledger_id: int,
    period_type: Literal[
        "last_12_months", "monthly_since_beginning", "yearly_since_beginning"
    ],
):
    now = datetime.now()
    if period_type == "last_12_months":
        start_date = now - timedelta(days=365)
    else:
        start_date = None

    if period_type in ["last_12_months", "monthly_since_beginning"]:
        date_format = "month"
    else:
        date_format = "year"

    # Query for regular transactions
    regular_transactions_query = select(
        func.date_trunc(date_format, Transaction.date).label("period"),
        func.sum(Transaction.credit).label("income"),
        (func.sum(Transaction.debit) - func.sum(Transaction.credit)).label(
            "expense"
        ),
    ).select_from(
        Transaction.join(Account, Transaction.account_id == Account.account_id).join(Category, Transaction.category_id == Category.category_id)
    ).where(
        and_(
            Account.ledger_id == ledger_id,
            Transaction.is_split == False,
            Transaction.is_transfer == False,
        )
    )

    # Query for split transactions
    split_transactions_query = select(
        func.date_trunc(date_format, Transaction.date).label("period"),
        func.sum(TransactionSplit.credit).label("income"),
        (
            func.sum(TransactionSplit.debit) - func.sum(TransactionSplit.credit)
        ).label("expense"),
    ).select_from(
        TransactionSplit.join(
            Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
        ).join(Account, Transaction.account_id == Account.account_id).join(Category, TransactionSplit.category_id == Category.category_id)
    ).where(
        and_(
            Account.ledger_id == ledger_id,
            Transaction.is_split == True,
            Transaction.is_transfer == False,
        )
    )

    if start_date:
        regular_transactions_query = regular_transactions_query.where(
            Transaction.date >= start_date
        )
        split_transactions_query = split_transactions_query.where(
            Transaction.date >= start_date
        )

    # Separate queries for income and expense
    income_regular = regular_transactions_query.where(Category.type == "income").group_by(func.date_trunc(date_format, Transaction.date))
    expense_regular = regular_transactions_query.where(Category.type == "expense").group_by(func.date_trunc(date_format, Transaction.date))

    income_split = split_transactions_query.where(Category.type == "income").group_by(func.date_trunc(date_format, Transaction.date))
    expense_split = split_transactions_query.where(Category.type == "expense").group_by(func.date_trunc(date_format, Transaction.date))

    # Union all the queries
    all_income = union_all(income_regular, income_split).alias("all_income")
    all_expense = union_all(expense_regular, expense_split).alias("all_expense")

    # Combine income and expense results
    income_results = db.query(
        all_income.c.period, func.sum(all_income.c.income).label("income_amount")
    ).group_by(all_income.c.period).all()

    expense_results = db.query(
        all_expense.c.period, func.sum(all_expense.c.expense).label("expense_amount")
    ).group_by(all_expense.c.period).all()

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
