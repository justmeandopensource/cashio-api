from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.model import Account
from app.schemas.account_schema import AccountCreate, AccountUpdate


def create_account(db: Session, ledger_id: int, account: AccountCreate):
    existing_account = (
        db.query(Account)
        .filter(Account.ledger_id == ledger_id, Account.name == account.name)
        .first()
    )

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account already exists"
        )

    # Validate parent_account_id (if provided)
    if account.parent_account_id is not None:
        parent_account = (
            db.query(Account)
            .filter(
                Account.account_id == account.parent_account_id,
                Account.ledger_id == ledger_id,
                Account.is_group == True,
            )
            .first()
        )

        if not parent_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent_account_id: The parent account must exist and be a group account in the same ledger",
            )

    db_account = Account(
        ledger_id=ledger_id,
        name=account.name,
        type=account.type,
        is_group=account.is_group,
        opening_balance=account.opening_balance,
        net_balance=account.opening_balance,
        parent_account_id=account.parent_account_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def get_accounts_by_ledger_id(
    db: Session,
    ledger_id: int,
    account_type: Optional[str] = None,
    ignore_group: Optional[bool] = False,
):
    query = db.query(Account).filter(Account.ledger_id == ledger_id)

    # Filter by account type if provided
    if account_type:
        query = query.filter(Account.type == account_type)

    # Exclude group account if ignore_group is True
    if ignore_group:
        query = query.filter(Account.is_group == False)

    query = query.order_by(Account.name.asc())

    accounts = query.all()
    return accounts


def get_account_by_id(db: Session, account_id: int):
    return db.query(Account).filter(Account.account_id == account_id).first()


def get_group_accounts_by_type(
    db: Session, ledger_id: int, account_type: Optional[str] = None
):
    query = db.query(Account).filter(
        Account.ledger_id == ledger_id, Account.is_group == True
    )
    if account_type:
        query = query.filter(Account.type == account_type)

    return query.all()


def update_account(db: Session, account_id: int, account_update: AccountUpdate):
    db_account = db.query(Account).filter(Account.account_id == account_id).first()
    if not db_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    # Validate parent account
    if account_update.parent_account_id is not None:
        parent_account = (
            db.query(Account)
            .filter(Account.account_id == account_update.parent_account_id)
            .first()
        )
        if not parent_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent account not found",
            )
        if not parent_account.is_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent account must be a group account",
            )

    if account_update.name is not None:
        db_account.name = account_update.name
    if account_update.opening_balance is not None:
        db_account.opening_balance = Decimal(str(account_update.opening_balance))
        db_account.net_balance = db_account.opening_balance + db_account.balance
    if account_update.parent_account_id is not None:
        db_account.parent_account_id = account_update.parent_account_id

    db_account.updated_at = datetime.now()

    db.commit()
    db.refresh(db_account)
    return db_account
