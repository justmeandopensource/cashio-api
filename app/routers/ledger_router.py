from typing import Optional
from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from schemas import user_schema, ledger_schema, account_schema
from repositories import ledger_crud, account_crud
from database.connection import get_db
from security.user_security import get_current_user

ledger_Router = APIRouter(prefix="/ledger")

@ledger_Router.get("/list", response_model=list[ledger_schema.Ledger], tags=["ledgers"])
def get_user_ledgers(
        user: user_schema.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    ledgers = ledger_crud.get_ledgers_by_username(db=db, username=user.username)
    
    if not ledgers:
        return []
    
    return ledgers

@ledger_Router.post("/create", response_model=ledger_schema.Ledger, tags=["ledgers"])
def create_ledger(
    ledger: ledger_schema.LedgerCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not ledger.name or not ledger.currency_symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name and currency symbol cannot be empty",
        )
    try:
        new_ledger = ledger_crud.create_ledger(
            db=db,
            user_id=user.user_id,
            ledger=ledger
        )
        return new_ledger
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the ledger.",
        )

@ledger_Router.get("/{ledger_id}/accounts", response_model=list[account_schema.Account], tags=["accounts"])
def get_ledger_accounts(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    accounts = account_crud.get_accounts_by_ledger_id(db=db, ledger_id=ledger_id)
    if not accounts:
        return []

    return accounts

@ledger_Router.get("/{ledger_id}", response_model=ledger_schema.Ledger, tags=["ledgers"])
def get_ledger(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    return ledger

@ledger_Router.post("/{ledger_id}/account/create", response_model=account_schema.Account, tags=["accounts"])
def create_account(
    ledger_id: int,
    account: account_schema.AccountCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ledger not found"
        )

    try:
        new_account = account_crud.create_account(
            db=db,
            ledger_id=ledger_id,
            account=account
        )
        return new_account
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating account: {str(e)}",
        )

@ledger_Router.get("/{ledger_id}/accounts/group", response_model=list[account_schema.AccountBase], tags=["accounts"])
def get_group_accounts_by_type(
    ledger_id: int,
    account_type: Optional[str] = None,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ledger not found"
        )

    group_accounts = account_crud.get_group_accounts_by_type(db=db, ledger_id=ledger_id, account_type=account_type)
    return group_accounts
