from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from schemas.account_schema import AccountCreate
from models.model import Account

def create_account(db: Session, ledger_id: int, account: AccountCreate):
    existing_account = db.query(Account).filter(
        Account.ledger_id == ledger_id,
        Account.name == account.name
    ).first()

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists"
        )

    # Validate parent_account_id (if provided)
    if account.parent_account_id is not None:
        parent_account = db.query(Account).filter(
            Account.account_id == account.parent_account_id,
            Account.ledger_id == ledger_id,
            Account.is_group == True
        ).first()

        if not parent_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent_account_id: The parent account must exist and be a group account in the same ledger"
            )

    db_account = Account(
        ledger_id=ledger_id,
        name=account.name,
        type=account.type,
        is_group=account.is_group,
        opening_balance=account.opening_balance,
        net_balance=account.opening_balance,
        parent_account_id=account.parent_account_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

def get_accounts_by_ledger_id(db: Session, ledger_id: int):
    return db.query(Account).filter(Account.ledger_id == ledger_id).all()

def get_account_by_id(db: Session, account_id: int):
    return db.query(Account).filter(Account.account_id == account_id).first()

def get_group_accounts_by_type(db: Session, ledger_id: int, account_type: Optional[str] = None):
    query = db.query(Account).filter(
        Account.ledger_id == ledger_id,
        Account.is_group == True
    )
    if account_type:
        query = query.filter(Account.type == account_type)
    return query.all()
