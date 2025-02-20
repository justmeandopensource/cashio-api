from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from models.model import Ledger
from schemas.ledger_schema import LedgerCreate
from repositories.user_crud import get_user_by_username

def get_ledgers_by_username(db: Session, username: str):
    user = get_user_by_username(db, username)

    if not user:
        return []

    return db.query(Ledger).filter(Ledger.user_id == user.user_id).all()

def create_ledger(db: Session, user_id: int, ledger: LedgerCreate):
    existing_ledger = db.query(Ledger).filter(
        Ledger.user_id == user_id,
        Ledger.name == ledger.name
    ).first()

    if existing_ledger:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ledger name already exists",
        )

    new_ledger = Ledger(
        user_id=user_id,
        name=ledger.name,
        currency_symbol=ledger.currency_symbol
    )

    db.add(new_ledger)
    db.commit()
    db.refresh(new_ledger)
    return new_ledger
