from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.model import Amc
from app.schemas import mutual_funds_schema


def create_amc(db: Session, ledger_id: int, amc: mutual_funds_schema.AmcCreate) -> Amc:
    """Create a new AMC for a ledger."""
    try:
        db_amc = Amc(
            ledger_id=ledger_id,
            name=amc.name,
            description=amc.description,
        )
        db.add(db_amc)
        db.commit()
        db.refresh(db_amc)
        return db_amc
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AMC with name '{amc.name}' already exists in this ledger",
        )


def get_amcs_by_ledger_id(db: Session, ledger_id: int) -> list[Amc]:
    """Get all AMCs for a ledger."""
    return db.query(Amc).filter(Amc.ledger_id == ledger_id).all()


def get_amc_by_id(db: Session, amc_id: int) -> Amc | None:
    """Get an AMC by ID."""
    return db.query(Amc).filter(Amc.amc_id == amc_id).first()


def update_amc(
    db: Session, amc_id: int, amc_update: mutual_funds_schema.AmcUpdate
) -> Amc:
    """Update an AMC."""
    db_amc = db.query(Amc).filter(Amc.amc_id == amc_id).first()
    if not db_amc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AMC not found"
        )

    update_data = amc_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_amc

    try:
        for field, value in update_data.items():
            setattr(db_amc, field, value)
        db.commit()
        db.refresh(db_amc)
        return db_amc
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AMC with name '{amc_update.name}' already exists in this ledger",
        )


def delete_amc(db: Session, amc_id: int) -> None:
    """Delete an AMC if it has no associated mutual funds."""
    db_amc = db.query(Amc).filter(Amc.amc_id == amc_id).first()
    if not db_amc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AMC not found"
        )

    # Check if AMC has any mutual funds
    if db_amc.mutual_funds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete AMC with existing mutual funds. Delete all funds first.",
        )

    db.delete(db_amc)
    db.commit()