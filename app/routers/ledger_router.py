from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from schemas import user_schema, ledger_schema, general_schema
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ledgers found for this user",
        )
    
    return ledgers

@ledger_Router.post("/create", response_model=general_schema.RegisterResponse, tags=["ledgers"])
def create_ledger(
    ledger: ledger_schema.LedgerCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ledger_crud.create_ledger(
            db=db,
            user_id=user.user_id,
            ledger=ledger
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the ledger.",
        )
    return {"message": "ledger created successfully"}

