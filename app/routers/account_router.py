from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import account_crud, ledger_crud
from app.schemas import account_schema, user_schema
from app.security.user_security import get_current_user

account_Router = APIRouter(prefix="/ledger")


@account_Router.get(
    "/{ledger_id}/accounts",
    response_model=list[account_schema.Account],
    tags=["accounts"],
)
def get_ledger_accounts(
    ledger_id: int,
    type: Optional[Literal["asset", "liability"]] = Query(
        default=None, description="Filter by account type (asset or liability)"
    ),
    ignore_group: Optional[bool] = Query(
        default=False, description="Exclude group accounts if set to true"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    accounts = account_crud.get_accounts_by_ledger_id(
        db=db, ledger_id=ledger_id, account_type=type, ignore_group=ignore_group
    )
    if not accounts:
        return []

    return accounts


@account_Router.get(
    "/{ledger_id}/account/{account_id}",
    response_model=account_schema.Account,
    tags=["accounts"],
)
def get_account(
    ledger_id: int,
    account_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    account = account_crud.get_account_by_id(db=db, account_id=account_id)
    return account


@account_Router.post(
    "/{ledger_id}/account/create",
    response_model=account_schema.Account,
    tags=["accounts"],
)
def create_account(
    ledger_id: int,
    account: account_schema.AccountCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found"
        )

    try:
        new_account = account_crud.create_account(
            db=db, ledger_id=ledger_id, account=account
        )
        return new_account
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating account: {str(e)}",
        )


@account_Router.get(
    "/{ledger_id}/accounts/group",
    response_model=list[account_schema.AccountBase],
    tags=["accounts"],
)
def get_group_accounts_by_type(
    ledger_id: int,
    account_type: Optional[str] = None,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found"
        )

    group_accounts = account_crud.get_group_accounts_by_type(
        db=db, ledger_id=ledger_id, account_type=account_type
    )
    return group_accounts


@account_Router.put(
    "/{ledger_id}/account/{account_id}/update",
    response_model=account_schema.Account,
    tags=["accounts"],
)
def update_account_details(
    ledger_id: int,
    account_id: int,
    account_update: account_schema.AccountUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found"
        )

    account = account_crud.get_account_by_id(db=db, account_id=account_id)
    if not account or account.ledger_id != ledger_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    updated_account = account_crud.update_account(
        db=db, account_id=account_id, account_update=account_update
    )
    return updated_account
