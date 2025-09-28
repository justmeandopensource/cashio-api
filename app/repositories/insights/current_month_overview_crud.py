from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.model import Account, Category, Ledger, Transaction, TransactionSplit


def get_current_month_overview(db: Session, ledger_id: int):
    # Get first and last day of current month
    today = datetime.now()
    first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    last_day = last_day.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Base query for transactions in current month (excluding transfers)
    base_transaction_query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .filter(
            Account.ledger_id == ledger_id,
            Transaction.date >= first_day,
            Transaction.date <= last_day,
            Transaction.is_transfer == False,
        )
    )

    # Query for split transactions in current month
    base_split_query = (
        db.query(TransactionSplit)
        .join(
            Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
        )
        .join(Account, Transaction.account_id == Account.account_id)
        .filter(
            Account.ledger_id == ledger_id,
            Transaction.date >= first_day,
            Transaction.date <= last_day,
            Transaction.is_transfer == False,
            Transaction.is_split == True,
        )
    )

    # Calculate total income and expense
    def calculate_totals():
        income = expense = Decimal(0)

        # regular transactions
        for t in base_transaction_query.filter(Transaction.is_split == False).all():
            if t.category and t.category.type == "income":
                income += t.credit
            elif t.category and t.category.type == "expense":
                expense += t.debit - t.credit

        # split transactions
        for s in base_split_query.all():
            if s.category and s.category.type == "income":
                income += s.credit
            elif s.category and s.category.type == "expense":
                expense += s.debit - s.credit

        return float(income), float(expense)  # type: ignore

    # Get category breakdown
    def get_category_breakdown(category_type: str) -> List[Dict]:
        # Get all categories of this type
        ledger = db.query(Ledger).filter(Ledger.ledger_id == ledger_id).first()
        if not ledger:
            return []
        categories = (
            db.query(Category)
            .filter(
                Category.type == category_type,
                Category.user_id
                == Ledger.user_id,  # Ensure category belongs to ledger's user
                or_(Category.parent_category_id.is_(None), Category.is_group == True),
            )
            .join(Account, Account.ledger_id == ledger_id)
            .distinct()
            .all()
        )

        breakdown = []
        color_index = 0

        for category in categories:
            # Calculate total for this category (including children)
            total = Decimal(0)
            children = []

            # Get direct transactions for this category
            if category.is_group:  # type: ignore
                # For group categories, sum up all child categories
                child_categories = [c.category_id for c in category.child_categories]

                # Regular transactions
                cat_transactions = base_transaction_query.filter(
                    Transaction.is_split == False,
                    Transaction.category_id.in_(child_categories),
                ).all()

                # Split transactions
                cat_splits = base_split_query.filter(
                    TransactionSplit.category_id.in_(child_categories)
                ).all()
            else:
                # Regular transactions
                cat_transactions = base_transaction_query.filter(
                    Transaction.is_split == False,
                    Transaction.category_id == category.category_id,
                ).all()

                # Split transactions
                cat_splits = base_split_query.filter(
                    TransactionSplit.category_id == category.category_id
                ).all()

            # Calculate total for this category
            for t in cat_transactions:
                if category_type == "income":
                    total += t.credit
                else:
                    total += t.debit - t.credit

            for s in cat_splits:
                if category_type == "income":
                    total += s.credit
                else:
                    total += s.debit - s.credit

            # Only include categories with actual transactions
            if total > 0:  # type: ignore
                # Get children if this is a group category
                if category.is_group and category.child_categories:  # type: ignore
                    for child in category.child_categories:
                        child_total = Decimal(0)

                        # Regular transactions
                        child_transactions = base_transaction_query.filter(
                            Transaction.is_split == False,
                            Transaction.category_id == child.category_id,
                        ).all()

                        # Split transactions
                        child_splits = base_split_query.filter(
                            TransactionSplit.category_id == child.category_id
                        ).all()

                        # Calculate child total
                        for t in child_transactions:
                            if category_type == "income":
                                child_total += t.credit
                            else:
                                child_total += t.debit - t.credit

                        for s in child_splits:
                            if category_type == "income":
                                child_total += s.credit
                            else:
                                child_total += s.debit - s.credit

                        if child_total > 0:  # type: ignore
                            children.append(
                                {
                                    "name": child.name,
                                    "value": float(child_total),  # type: ignore
                                }
                            )

                breakdown.append(
                    {
                        "name": category.name,
                        "value": float(total),  # type: ignore
                        "children": children if children else None,
                    }
                )

                color_index += 1

        return breakdown

    total_income, total_expense = calculate_totals()
    income_breakdown = get_category_breakdown("income")
    expense_breakdown = get_category_breakdown("expense")

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "income_categories_breakdown": income_breakdown,
        "expense_categories_breakdown": expense_breakdown,
    }
