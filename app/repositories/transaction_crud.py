from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.model import (Account, Category, Ledger, Tag, Transaction,
                              TransactionSplit, TransactionTag)
from app.schemas.transaction_schema import (TransactionCreate,
                                            TransactionSplitResponse,
                                            TransferCreate)


def get_transactions_for_account_id(
    db: Session, account_id: int, offset: Optional[int] = 0, limit: Optional[int] = 50
):
    transactions = (
        db.query(Transaction)
        .options(joinedload(Transaction.category), joinedload(Transaction.tags))
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not transactions:
        return []

    # Format the response to include category name
    formatted_transactions = []
    for transaction in transactions:
        formatted_transaction = {
            "transaction_id": transaction.transaction_id,
            "account_id": transaction.account_id,
            "category_id": transaction.category_id,
            "category_name": (
                transaction.category.name if transaction.category else None
            ),  # Include category name
            "credit": transaction.credit,
            "debit": transaction.debit,
            "date": transaction.date,
            "notes": transaction.notes,
            "is_split": transaction.is_split,
            "is_transfer": transaction.is_transfer,
            "transfer_id": str(transaction.transfer_id),
            "transfer_type": transaction.transfer_type,
            "created_at": transaction.created_at,
            "tags": [
                {"tag_id": tag.tag_id, "user_id": tag.user_id, "name": tag.name}
                for tag in transaction.tags
            ],
        }
        formatted_transactions.append(formatted_transaction)

    return formatted_transactions


def get_transactions_count_for_account_id(db: Session, account_id: int):
    return db.query(Transaction).filter(Transaction.account_id == account_id).count()


def create_transaction(db: Session, transaction: TransactionCreate):
    # Fetch the account to update its balance
    account = (
        db.query(Account).filter(Account.account_id == transaction.account_id).first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    if account.is_group is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation can be performed on group accounts",
        )

    credit = (
        Decimal(str(transaction.credit))
        if transaction.credit is not None
        else Decimal("0.00")
    )
    debit = (
        Decimal(str(transaction.debit))
        if transaction.debit is not None
        else Decimal("0.00")
    )

    # Create the main transaction
    db_transaction = Transaction(
        account_id=transaction.account_id,
        category_id=transaction.category_id,
        credit=credit,
        debit=debit,
        date=transaction.date,
        notes=transaction.notes,
        is_split=transaction.is_split,
        is_transfer=transaction.is_transfer,
        transfer_id=transaction.transfer_id,
        transfer_type=transaction.transfer_type,
        created_at=datetime.now(),
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Update account balance based on account type
    if "asset" in account.type:
        if "income" in transaction.type:
            account.balance += credit
        elif "expense" in transaction.type:
            account.balance -= debit
    elif "liability" in account.type:
        if "income" in transaction.type:
            account.balance -= credit
        elif "expense" in transaction.type:
            account.balance += debit

    account.net_balance = account.opening_balance + account.balance
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)

    # If this is a split transaction, create the splits
    if transaction.is_split and transaction.splits:
        # Validate that the sum of splits matches the main transaction amount
        total_split_credit = sum(
            Decimal(str(split.credit)) if split.credit is not None else Decimal("0.00")
            for split in transaction.splits
        )
        total_split_debit = sum(
            Decimal(str(split.debit)) if split.debit is not None else Decimal("0.00")
            for split in transaction.splits
        )

        # Check if the total of splits matches the main transaction
        if transaction.type == "income" and total_split_credit != credit:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of split credits ({total_split_credit}) does not match main transaction credit ({credit})",
            )
        elif transaction.type == "expense" and total_split_debit != debit:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sum of split debits ({total_split_debit}) does not match main transaction debit ({debit})",
            )

        for split in transaction.splits:
            split_credit = (
                Decimal(str(split.credit))
                if split.credit is not None
                else Decimal("0.00")
            )
            split_debit = (
                Decimal(str(split.debit))
                if split.debit is not None
                else Decimal("0.00")
            )
            db_split = TransactionSplit(
                transaction_id=db_transaction.transaction_id,
                category_id=split.category_id,
                credit=split_credit,
                debit=split_debit,
                notes=split.notes,
            )
            db.add(db_split)
        db.commit()
        db.refresh(db_transaction)

    if transaction.tags:
        for tag in transaction.tags:
            db_tag = (
                db.query(Tag)
                .filter(Tag.name == tag.name, Tag.user_id == account.ledger.user_id)
                .first()
            )
            if not db_tag:
                db_tag = Tag(name=tag.name, user_id=account.ledger.user_id)
                db.add(db_tag)
                db.commit()
                db.refresh(db_tag)
            db_transaction_tag = TransactionTag(
                transaction_id=db_transaction.transaction_id, tag_id=db_tag.tag_id
            )
            db.add(db_transaction_tag)
        db.commit()
        db.refresh(db_transaction)

    return db_transaction


def create_transfer_transaction(db: Session, transfer: TransferCreate, user_id: int):
    # Fetch source and destination accounts
    source_account = (
        db.query(Account)
        .filter(Account.account_id == transfer.source_account_id)
        .first()
    )
    destination_account = (
        db.query(Account)
        .filter(Account.account_id == transfer.destination_account_id)
        .first()
    )

    # Ensure the source and destination accounts exist
    if not source_account or not destination_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or destination account not found",
        )

    # Ensure they are not the same accounts
    if source_account == destination_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transferring to same account not allowed",
        )

    # Ensure accounts belong to the users
    if (
        source_account.ledger.user_id != user_id
        or destination_account.ledger.user_id != user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source or destination account does not belong to the user",
        )

    # Ensure the accounts are not group accounts
    if source_account.is_group is True or destination_account.is_group is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source or destination account is a group account. Operation cannot be performed on group accounts",
        )

    # Check if the accounts are in the same ledger
    if source_account.ledger_id == destination_account.ledger_id:
        # Same ledger, same currency
        if transfer.destination_amount is not None:
            raise ValueError(
                "Destination amount should not be provided for same ledger transfers"
            )
        destination_amount = transfer.source_amount
    else:
        # Different ledgers, different currencies
        if transfer.destination_amount is None:
            raise ValueError(
                "Destination amount is required for cross-ledger transfers"
            )
        destination_amount = transfer.destination_amount

    # Ensure amounts are non-zero
    if transfer.source_amount <= 0 or destination_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer amount is not valid",
        )

    # Generate a unique transfer_id
    transfer_id = uuid4()

    # Create expense transaction on source account
    transferOut = TransactionCreate(
        account_id=transfer.source_account_id,
        category_id=None,
        type="expense",
        credit=0.00,
        debit=transfer.source_amount,
        date=transfer.date,
        notes=transfer.notes,
        is_split=False,
        is_transfer=True,
        transfer_id=str(transfer_id),
        transfer_type="source",
        tags=transfer.tags,
    )
    create_transaction(db=db, transaction=transferOut)

    # Create income transaction on destination account
    transferIn = TransactionCreate(
        account_id=transfer.destination_account_id,
        category_id=None,
        type="income",
        credit=destination_amount,
        debit=0.00,
        date=transfer.date,
        notes=transfer.notes,
        is_split=False,
        is_transfer=True,
        transfer_id=str(transfer_id),
        transfer_type="destination",
        tags=transfer.tags,
    )
    create_transaction(db=db, transaction=transferIn)

    return {"message": "funds transferred successfully"}


def get_split_transactions(
    db: Session, transaction_id: int
) -> List[TransactionSplitResponse]:
    # Fetch the splits for the transaction and join with the Category table to get the category name
    splits = (
        db.query(
            TransactionSplit.split_id,
            TransactionSplit.transaction_id,
            TransactionSplit.category_id,
            Category.name.label("category_name"),  # Include category name
            TransactionSplit.credit,
            TransactionSplit.debit,
            TransactionSplit.notes,
        )
        .join(
            Category, TransactionSplit.category_id == Category.category_id, isouter=True
        )
        .filter(TransactionSplit.transaction_id == transaction_id)
        .all()
    )

    if not splits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No splits found for the given transaction ID",
        )

    # Format the response using the TransactionSplitResponse schema
    formatted_splits = []
    for split in splits:
        formatted_splits.append(
            {
                "split_id": split.split_id,
                "transaction_id": split.transaction_id,
                "category_id": split.category_id,
                "category_name": split.category_name,
                "credit": split.credit,
                "debit": split.debit,
                "notes": split.notes,
            }
        )

    return formatted_splits


def get_transfer_transactions(db: Session, transfer_id: str):
    # Fetch both transactions (source and destination) for the given transfer_id
    transactions = (
        db.query(Transaction).filter(Transaction.transfer_id == transfer_id).all()
    )

    if not transactions or len(transactions) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer transactions not found or incomplete",
        )

    # Identify source and destination transactions
    source_transaction = next(
        (t for t in transactions if t.transfer_type == "source"), None
    )
    destination_transaction = next(
        (t for t in transactions if t.transfer_type == "destination"), None
    )

    if not source_transaction or not destination_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or destination transaction not found",
        )

    # Fetch account and ledger details for the source transaction
    source_account = (
        db.query(Account)
        .filter(Account.account_id == source_transaction.account_id)
        .first()
    )
    source_ledger = (
        db.query(Ledger).filter(Ledger.ledger_id == source_account.ledger_id).first()
    )

    # Fetch account and ledger details for the destination transaction
    destination_account = (
        db.query(Account)
        .filter(Account.account_id == destination_transaction.account_id)
        .first()
    )
    destination_ledger = (
        db.query(Ledger)
        .filter(Ledger.ledger_id == destination_account.ledger_id)
        .first()
    )

    if (
        not source_account
        or not destination_account
        or not source_ledger
        or not destination_ledger
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account or ledger details not found",
        )

    source_transaction.transfer_id = str(source_transaction.transfer_id)
    destination_transaction.transfer_id = str(destination_transaction.transfer_id)

    return {
        "source_transaction": source_transaction,
        "destination_transaction": destination_transaction,
        "source_account_name": source_account.name,
        "destination_account_name": destination_account.name,
        "source_ledger_name": source_ledger.name,
        "destination_ledger_name": destination_ledger.name,
    }


def delete_transaction(db: Session, transaction_id: int, user_id: int):
    # Fetch the transaction
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    # Fetch the account associated with the transaction
    account = (
        db.query(Account).filter(Account.account_id == transaction.account_id).first()
    )
    if not account or account.ledger.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied",
        )

    # If it's a transfer transaction, fetch the associated transaction
    if transaction.is_transfer is True:
        transfer_transactions = (
            db.query(Transaction)
            .filter(Transaction.transfer_id == transaction.transfer_id)
            .all()
        )
        if len(transfer_transactions) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transfer transaction",
            )

        # Delete both transactions
        for trans in transfer_transactions:
            # Update account balance
            update_account_balance(db, trans, reverse=True)
            db.delete(trans)
    else:
        # Update account balance
        update_account_balance(db, transaction, reverse=True)
        db.delete(transaction)

    # Commit the changes
    db.commit()

    return {"message": "Transaction deleted successfully"}


def update_account_balance(
    db: Session, transaction: Transaction, reverse: bool = False
):
    account = (
        db.query(Account).filter(Account.account_id == transaction.account_id).first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    # Determine the transaction type based on credit and debit values
    if transaction.credit > 0 and transaction.debit == 0:
        # This is an income transaction
        if "asset" in account.type:
            account.balance -= transaction.credit
        elif "liability" in account.type:
            account.balance += transaction.credit
    elif transaction.debit > 0 and transaction.credit == 0:
        # This is an expense transaction
        if "asset" in account.type:
            account.balance += transaction.debit
        elif "liability" in account.type:
            account.balance -= transaction.debit
    else:
        # Handle cases where both credit and debit are non-zero (if applicable)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction: both credit and debit are non-zero",
        )

    account.net_balance = account.opening_balance + account.balance
    account.updated_at = datetime.now()
    db.commit()
    db.refresh(account)


def get_transaction_notes_suggestions(
    db: Session, ledger_id: int, search_text: str, limit: int = 5
) -> List[str]:
    suggestions = (
        db.query(Transaction.notes)
        .filter(Transaction.notes.ilike(f"%{search_text}%"))
        .filter(
            Transaction.account_id.in_(
                db.query(Account.account_id).filter(Account.ledger_id == ledger_id)
            )
        )
        .order_by(Transaction.date.desc())
        .limit(limit)
        .all()
    )

    return [suggestion[0] for suggestion in suggestions]

def get_transactions_for_ledger_id(
    db: Session,
    ledger_id: int,
    account_id: Optional[int] = None,
    offset: Optional[int] = 0,
    limit: Optional[int] = 50,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    category_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    tags_match: Optional[str] = "any",
    search_text: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .filter(Account.ledger_id == ledger_id)
        .options(joinedload(Transaction.category), joinedload(Transaction.tags))
    )

    if from_date:
        query = query.filter(Transaction.date >= from_date)
    if to_date:
        query = query.filter(Transaction.date <= to_date)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if tags:
        if tags_match == "all":
            for tag in tags:
                query = query.filter(Transaction.tags.any(Tag.name == tag))
        else:
            query = query.filter(Transaction.tags.any(Tag.name.in_(tags)))
    if search_text:
        query = query.filter(Transaction.notes.ilike(f"%{search_text}%"))
    if transaction_type:
        if transaction_type == "income":
            query = query.filter(Transaction.credit > 0)
        elif transaction_type == "expense":
            query = query.filter(Transaction.debit > 0)
    if account_id:  # Add this filter
        query = query.filter(Transaction.account_id == account_id)

    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    formatted_transactions = []
    for transaction in transactions:
        formatted_transaction = {
            "transaction_id": transaction.transaction_id,
            "account_id": transaction.account_id,
            "account_name": transaction.account.name,  # Include account name
            "category_id": transaction.category_id,
            "category_name": transaction.category.name if transaction.category else None,
            "credit": transaction.credit,
            "debit": transaction.debit,
            "date": transaction.date,
            "notes": transaction.notes,
            "is_split": transaction.is_split,
            "is_transfer": transaction.is_transfer,
            "transfer_id": str(transaction.transfer_id),
            "transfer_type": transaction.transfer_type,
            "created_at": transaction.created_at,
            "tags": [
                {"tag_id": tag.tag_id, "user_id": tag.user_id, "name": tag.name}
                for tag in transaction.tags
            ],
        }
        formatted_transactions.append(formatted_transaction)

    return formatted_transactions


def get_transactions_count_for_ledger_id(
    db: Session,
    ledger_id: int,
    account_id: Optional[int] = None,  # Add this parameter
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    category_id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    tags_match: Optional[str] = "any",
    search_text: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .filter(Account.ledger_id == ledger_id)
    )

    if from_date:
        query = query.filter(Transaction.date >= from_date)
    if to_date:
        query = query.filter(Transaction.date <= to_date)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if tags:
        if tags_match == "all":
            for tag in tags:
                query = query.filter(Transaction.tags.any(Tag.name == tag))
        else:
            query = query.filter(Transaction.tags.any(Tag.name.in_(tags)))
    if search_text:
        query = query.filter(Transaction.notes.ilike(f"%{search_text}%"))
    if transaction_type:
        if transaction_type == "income":
            query = query.filter(Transaction.credit > 0)
        elif transaction_type == "expense":
            query = query.filter(Transaction.debit > 0)
    if account_id:  # Add this filter
        query = query.filter(Transaction.account_id == account_id)

    return query.count()
