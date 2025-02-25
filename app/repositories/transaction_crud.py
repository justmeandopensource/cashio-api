from typing import Optional
from decimal import Decimal
from fastapi import HTTPException, status
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from schemas.transaction_schema import TransactionCreate
from models.model import Transaction, TransactionSplit, Account

def get_transactions_for_account_id(db: Session, account_id: int, offset: Optional[int] = 0, limit: Optional[int] = 50):
    transactions = db.query(Transaction)\
        .options(joinedload(Transaction.category))\
        .filter(Transaction.account_id == account_id)\
        .order_by(Transaction.date.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()

    if not transactions:
        return []

    # Format the response to include category name
    formatted_transactions = []
    for transaction in transactions:
        formatted_transaction = {
            "transaction_id": transaction.transaction_id,
            "account_id": transaction.account_id,
            "category_id": transaction.category_id,
            "category_name": transaction.category.name if transaction.category else None,  # Include category name
            "credit": transaction.credit,
            "debit": transaction.debit,
            "date": transaction.date,
            "notes": transaction.notes,
            "is_split": transaction.is_split,
            "is_transfer": transaction.is_transfer,
            "transfer_id": transaction.transfer_id,
            "transfer_type": transaction.transfer_type,
            "created_at": transaction.created_at
        }
        formatted_transactions.append(formatted_transaction)

    return formatted_transactions

def get_transactions_count_for_account_id(db: Session, account_id: int):
    return db.query(Transaction).filter(Transaction.account_id == account_id).count()

def create_transaction(db: Session, transaction: TransactionCreate):
    # Fetch the account to update its balance
    account = db.query(Account).filter(Account.account_id == transaction.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    credit = Decimal(str(transaction.credit)) if transaction.credit is not None else Decimal('0.00')
    debit = Decimal(str(transaction.debit)) if transaction.debit is not None else Decimal('0.00')

    # Create the main transaction
    db_transaction = Transaction(
        account_id=transaction.account_id,
        category_id=transaction.category_id,
        credit=credit,
        debit=debit,
        date=transaction.date,
        notes=transaction.notes,
        is_split=transaction.is_split,
        is_transfer=False,
        transfer_id=None,
        transfer_type=None,
        created_at=datetime.now()
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Update account balance
    if transaction.type == "income":
        account.balance += credit
    elif transaction.type == "expense":
        account.balance -= debit
    account.net_balance = account.opening_balance + account.balance
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)

    # If this is a split transaction, create the splits
    if transaction.is_split and transaction.splits:
        # Validate that the sum of splits matches the main transaction amount
        total_split_credit = sum(Decimal(str(split.credit)) if split.credit is not None else Decimal('0.00')
                               for split in transaction.splits)
        total_split_debit = sum(Decimal(str(split.debit)) if split.debit is not None else Decimal('0.00')
                              for split in transaction.splits)

        # Check if the total of splits matches the main transaction
        if transaction.type == "income" and total_split_credit != credit:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of split credits ({total_split_credit}) does not match main transaction credit ({credit})"
            )
        elif transaction.type == "expense" and total_split_debit != debit:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of split debits ({total_split_debit}) does not match main transaction debit ({debit})"
            )

    # Add splits after validation
    if transaction.is_split and transaction.splits:
        for split in transaction.splits:
            split_credit = Decimal(str(split.credit)) if split.credit is not None else Decimal('0.00')
            split_debit = Decimal(str(split.debit)) if split.debit is not None else Decimal('0.00')
            db_split = TransactionSplit(
                transaction_id=db_transaction.transaction_id,
                category_id=split.category_id,
                credit=split_credit,
                debit=split_debit,
                notes=split.notes
            )
            db.add(db_split)
        db.commit()
        db.refresh(db_transaction)

    return db_transaction
