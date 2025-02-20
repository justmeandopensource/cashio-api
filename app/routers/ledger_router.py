from fastapi import Depends, APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from schemas.ledger_schema import Ledger
from schemas.user_schema import User
from repositories.ledger_crud import get_ledgers_by_username
from database.connection import get_db
from security.user_security import get_current_user

ledger_Router = APIRouter(prefix="/ledger")

@ledger_Router.get("/list", response_model=list[Ledger], tags=["ledgers"])
def get_user_ledgers(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ledgers = get_ledgers_by_username(db=db, username=user.username)
    
    if not ledgers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ledgers found for this user",
        )
    
    return ledgers
