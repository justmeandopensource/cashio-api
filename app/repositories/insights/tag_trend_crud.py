from decimal import Decimal
from typing import List

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models.model import (
    Account,
    Category,
    Tag,
    Transaction,
    TransactionSplit,
    TransactionTag,
)


def get_tag_trend(
    db: Session,
    ledger_id: int,
    tag_ids: List[int],
):
    # Base query to filter transactions for this ledger that have the specified tags
    base_query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .join(
            TransactionTag, Transaction.transaction_id == TransactionTag.transaction_id
        )
        .filter(
            Account.ledger_id == ledger_id,
            TransactionTag.tag_id.in_(tag_ids),
            Transaction.is_transfer == False,  # Exclude transfer transactions
        )
    )

    matching_transactions = base_query.all()
    transaction_ids = [t.transaction_id for t in matching_transactions]

    # 1. TAG BREAKDOWN - Amount spent per tag
    tag_breakdown_query = (
        db.query(
            Tag.name.label("tag"),
            func.sum(
                case(
                    (
                        and_(Transaction.credit > 0, Category.type == "income"),
                        Transaction.credit,
                    ),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (
                        and_(Transaction.debit > 0, Category.type == "expense"),
                        Transaction.debit,
                    ),
                    else_=0,
                )
            ).label("expense"),
        )
        .join(TransactionTag, Tag.tag_id == TransactionTag.tag_id)
        .join(Transaction, TransactionTag.transaction_id == Transaction.transaction_id)
        .join(Account, Transaction.account_id == Account.account_id)
        .outerjoin(Category, Transaction.category_id == Category.category_id)
        .filter(
            Account.ledger_id == ledger_id,
            Tag.tag_id.in_(tag_ids),
            Transaction.is_transfer == False,
        )
        .group_by(Tag.tag_id, Tag.name)
    )

    tag_breakdown_results = tag_breakdown_query.all()

    # 2. CATEGORY BREAKDOWN - Handle both regular and split transactions
    # First, get categories from regular (non-split) transactions
    regular_category_query = (
        db.query(
            Category.name.label("category"),
            func.sum(
                case(
                    (
                        and_(Transaction.credit > 0, Category.type == "income"),
                        Transaction.credit,
                    ),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (
                        and_(Transaction.debit > 0, Category.type == "expense"),
                        Transaction.debit,
                    ),
                    else_=0,
                )
            ).label("expense"),
        )
        .join(Transaction, Category.category_id == Transaction.category_id)
        .filter(
            Transaction.transaction_id.in_(transaction_ids),
            Transaction.is_split == False,
        )
        .group_by(Category.category_id, Category.name)
    )

    # Second, get categories from split transactions
    split_category_query = (
        db.query(
            Category.name.label("category"),
            func.sum(
                case(
                    (
                        and_(TransactionSplit.credit > 0, Category.type == "income"),
                        TransactionSplit.credit,
                    ),
                    else_=0,
                )
            ).label("income"),
            func.sum(
                case(
                    (
                        and_(TransactionSplit.debit > 0, Category.type == "expense"),
                        TransactionSplit.debit,
                    ),
                    else_=0,
                )
            ).label("expense"),
        )
        .join(TransactionSplit, Category.category_id == TransactionSplit.category_id)
        .join(
            Transaction, TransactionSplit.transaction_id == Transaction.transaction_id
        )
        .filter(
            Transaction.transaction_id.in_(transaction_ids),
            Transaction.is_split == True,
        )
        .group_by(Category.category_id, Category.name)
    )

    # Execute queries
    regular_category_results = regular_category_query.all()
    split_category_results = split_category_query.all()

    # Combine regular and split category results
    category_amounts = {}

    # Process regular category results
    for category, income, expense in regular_category_results:
        if category not in category_amounts:
            category_amounts[category] = {"income": Decimal(0), "expense": Decimal(0)}
        category_amounts[category]["income"] += Decimal(income or 0)
        category_amounts[category]["expense"] += Decimal(expense or 0)

    # Process split category results
    for category, income, expense in split_category_results:
        if category not in category_amounts:
            category_amounts[category] = {"income": Decimal(0), "expense": Decimal(0)}
        category_amounts[category]["income"] += Decimal(income or 0)
        category_amounts[category]["expense"] += Decimal(expense or 0)

    # Format tag breakdown results
    tag_breakdown = []
    total_income = Decimal(0)
    total_expense = Decimal(0)

    for tag, income, expense in tag_breakdown_results:
        tag_income = Decimal(income or 0)
        tag_expense = Decimal(expense or 0)

        # Determine if this is primarily income or expense
        amount = tag_income if tag_income > tag_expense else tag_expense

        tag_breakdown.append({"tag": tag, "amount": float(amount)})

        total_income += tag_income
        total_expense += tag_expense

    # Format category breakdown results
    category_breakdown = []

    for category, data in category_amounts.items():
        # Determine if this is primarily income or expense
        if data["income"] > data["expense"]:
            amount = data["income"]
            transaction_type = "income"
        else:
            amount = data["expense"]
            transaction_type = "expense"

        if amount > 0:
            category_breakdown.append(
                {
                    "category": category,
                    "amount": float(amount),
                    "type": transaction_type,
                }
            )

    # Sort breakdowns by amount (descending)
    tag_breakdown.sort(key=lambda x: x["amount"], reverse=True)
    category_breakdown.sort(key=lambda x: x["amount"], reverse=True)

    return {
        "tag_breakdown": tag_breakdown,
        "category_breakdown": category_breakdown,
        "summary": {"total_amount": float(max(total_income, total_expense))},
    }
