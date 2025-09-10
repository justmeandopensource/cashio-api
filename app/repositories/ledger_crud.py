from datetime import datetime

from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.model import Ledger
from app.repositories.user_crud import get_user_by_username
from app.schemas.ledger_schema import LedgerCreate, LedgerUpdate


def create_ledger(db: Session, user_id: int, ledger: LedgerCreate):
    existing_ledger = (
        db.query(Ledger)
        .filter(Ledger.user_id == user_id, Ledger.name == ledger.name)
        .first()
    )

    if existing_ledger:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ledger name already exists",
        )

    db_ledger = Ledger(
        user_id=user_id,
        name=ledger.name,
        currency_symbol=ledger.currency_symbol,
        description=ledger.description,
        notes=ledger.notes,
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


def update_ledger(
    db: Session, ledger_id: int, user_id: int, ledger_update: LedgerUpdate
):
    db_ledger = (
        db.query(Ledger)
        .filter(Ledger.ledger_id == ledger_id, Ledger.user_id == user_id)
        .first()
    )

    if not db_ledger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found"
        )

    if ledger_update.name is not None:
        # Check if the new name already exists for the user's other ledgers
        existing_ledger_with_name = (
            db.query(Ledger)
            .filter(
                Ledger.user_id == user_id,
                Ledger.name == ledger_update.name,
                Ledger.ledger_id != ledger_id,
            )
            .first()
        )
        if existing_ledger_with_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ledger name already exists for this user",
            )
        db_ledger.name = ledger_update.name

    if ledger_update.currency_symbol is not None:
        db_ledger.currency_symbol = ledger_update.currency_symbol

    if ledger_update.description is not None:
        db_ledger.description = ledger_update.description

    if ledger_update.notes is not None:
        db_ledger.notes = ledger_update.notes

    db_ledger.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_ledger)
    return db_ledger
