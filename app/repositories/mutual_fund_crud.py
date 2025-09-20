from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.model import MutualFund
from app.schemas import mutual_funds_schema


def create_mutual_fund(
    db: Session, ledger_id: int, fund: mutual_funds_schema.MutualFundCreate
) -> MutualFund:
    """Create a new mutual fund for a ledger."""
    try:
        db_fund = MutualFund(
            ledger_id=ledger_id,
            amc_id=fund.amc_id,
            name=fund.name,
            plan=fund.plan,
            code=fund.code,
            notes=fund.notes,
        )



        db.add(db_fund)
        db.commit()
        db.refresh(db_fund)
        return db_fund
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mutual fund with name '{fund.name}' already exists in this ledger",
        )


def get_mutual_funds_by_ledger_id(db: Session, ledger_id: int) -> list[MutualFund]:
    """Get all mutual funds for a ledger."""
    return (
        db.query(MutualFund)
        .filter(MutualFund.ledger_id == ledger_id)
        .all()
    )


def get_mutual_fund_by_id(db: Session, mutual_fund_id: int) -> MutualFund | None:
    """Get a mutual fund by ID."""
    return db.query(MutualFund).filter(MutualFund.mutual_fund_id == mutual_fund_id).first()


def update_mutual_fund(
    db: Session, mutual_fund_id: int, fund_update: mutual_funds_schema.MutualFundUpdate
) -> MutualFund:
    """Update a mutual fund."""
    db_fund = db.query(MutualFund).filter(MutualFund.mutual_fund_id == mutual_fund_id).first()
    if not db_fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found"
        )

    update_data = fund_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_fund

    try:
        for field, value in update_data.items():
            setattr(db_fund, field, value)
        db_fund.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_fund)
        return db_fund
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mutual fund with name '{fund_update.name}' already exists in this ledger",
        )


def update_mutual_fund_nav(
    db: Session, mutual_fund_id: int, nav_update: mutual_funds_schema.MutualFundNavUpdate
) -> MutualFund:
    """Update the latest NAV for a mutual fund and recalculate current value."""
    db_fund = db.query(MutualFund).filter(MutualFund.mutual_fund_id == mutual_fund_id).first()
    if not db_fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found"
        )

    nav_decimal = Decimal(str(nav_update.latest_nav))
    db_fund.latest_nav = nav_decimal  # type: ignore
    db_fund.last_nav_update = datetime.now(timezone.utc)  # type: ignore
    db_fund.current_value = db_fund.total_units * nav_decimal  # type: ignore
    db_fund.updated_at = datetime.now(timezone.utc)  # type: ignore

    db.commit()
    db.refresh(db_fund)
    return db_fund


def update_mutual_fund_balances(
    db: Session, mutual_fund_id: int, units_change: float, total_amount: float
) -> MutualFund:
    """Update mutual fund balances after a transaction."""
    db_fund = db.query(MutualFund).filter(MutualFund.mutual_fund_id == mutual_fund_id).first()
    if not db_fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found"
        )

    # Convert parameters to Decimal for consistent arithmetic
    units_change = Decimal(str(units_change))
    total_amount = Decimal(str(total_amount))

    new_total_units = db_fund.total_units + units_change

    if new_total_units < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient units for transaction",
        )

    # Calculate new average cost per unit
    if new_total_units == 0:
        new_avg_cost = 0
    else:
        current_invested = db_fund.total_units * db_fund.average_cost_per_unit
        new_invested = current_invested + total_amount
        new_avg_cost = new_invested / new_total_units

    db_fund.total_units = new_total_units
    db_fund.average_cost_per_unit = new_avg_cost
    db_fund.current_value = new_total_units * db_fund.latest_nav
    db_fund.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_fund)
    return db_fund





def delete_mutual_fund(db: Session, mutual_fund_id: int) -> None:
    """Delete a mutual fund if it has zero units."""
    db_fund = db.query(MutualFund).filter(MutualFund.mutual_fund_id == mutual_fund_id).first()
    if not db_fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found"
        )

    # Check if fund has any units
    if db_fund.total_units != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete mutual fund with remaining units. Redeem all units first.",
        )

    

    db.delete(db_fund)
    db.commit()