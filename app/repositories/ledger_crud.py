from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.model import Ledger
from app.schemas.ledger_schema import LedgerCreate
from app.repositories.user_crud import get_user_by_username

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

    db_ledger = Ledger(
        user_id=user_id,
        name=ledger.name,
        currency_symbol=ledger.currency_symbol
    )

    db.add(db_ledger)
    db.commit()
    db.refresh(db_ledger)
    return db_ledger

def get_ledgers_by_username(db: Session, username: str):
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(Ledger).filter(Ledger.user_id == user.user_id).all()

def get_ledger_by_id(db: Session, ledger_id: int):
    return db.query(Ledger).filter(Ledger.ledger_id == ledger_id).first()

