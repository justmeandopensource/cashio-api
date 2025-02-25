from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from schemas import user_schema, ledger_schema
from repositories import ledger_crud
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

