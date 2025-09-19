from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from fastapi import HTTPException, status

from app.models.model import MfTransaction, Transaction, Account, Category
from app.repositories import transaction_crud, account_crud
from app.schemas import mutual_funds_schema


def create_mf_transaction(
    db: Session, ledger_id: int, transaction_data: mutual_funds_schema.MfTransactionCreate
) -> MfTransaction:
    """Create a new MF transaction and associated financial transaction."""
    from decimal import Decimal
    from app.repositories.mutual_fund_crud import get_mutual_fund_by_id, update_mutual_fund_balances

    # Validate mutual fund exists and belongs to ledger
    fund = get_mutual_fund_by_id(db, transaction_data.mutual_fund_id)
    if not fund or fund.ledger_id != ledger_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found"
        )

    total_amount = Decimal("0")
    financial_transaction_id = None
    nav_per_unit = None
    amount_excluding_charges = None
    other_charges = None
    linked_charge_transaction_id = None
    realized_gain = None
    cost_basis_of_units_sold = None

    if transaction_data.transaction_type in ["buy", "sell", "switch_out", "switch_in"]:
        if transaction_data.transaction_type in ["buy", "sell"]:
            if not transaction_data.account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account ID required for buy/sell transactions",
                )
            account = account_crud.get_account_by_id(db, transaction_data.account_id)
            if not account or account.ledger_id != ledger_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
                )
            if account.is_group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot use group accounts for transactions. Please select a leaf account.",
                )
            if transaction_data.amount_excluding_charges <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount excluding charges must be greater than 0 for buy/sell transactions",
                )
            if transaction_data.other_charges < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Other charges cannot be negative",
                )

            # Validate expense category if charges are present
            if transaction_data.other_charges > 0 and not transaction_data.expense_category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expense category is required when other charges are present",
                )

            # Calculate NAV and total amount
            amount_excluding_charges = Decimal(str(transaction_data.amount_excluding_charges))
            other_charges = Decimal(str(transaction_data.other_charges))
            units = Decimal(str(transaction_data.units))
            nav_per_unit = amount_excluding_charges / units

            if transaction_data.transaction_type == "buy":
                total_amount = amount_excluding_charges + other_charges
            else:  # sell
                total_amount = amount_excluding_charges - other_charges

            # Create main financial transaction for amount_excluding_charges
            transaction_type_financial = "debit" if transaction_data.transaction_type == "buy" else "credit"
            financial_transaction_notes = ""
            if transaction_data.transaction_type == "buy":
                financial_transaction_notes = f"MF Buy: {fund.name} {transaction_data.units:.3f} units at NAV {nav_per_unit:.2f}"
            elif transaction_data.transaction_type == "sell":
                financial_transaction_notes = f"MF Sell: {fund.name} {transaction_data.units:.3f} units at NAV {nav_per_unit:.2f}"

            financial_transaction = Transaction(
                account_id=transaction_data.account_id,
                credit=amount_excluding_charges if transaction_type_financial == "credit" else 0,
                debit=amount_excluding_charges if transaction_type_financial == "debit" else 0,
                date=transaction_data.transaction_date,
                notes=financial_transaction_notes,
                is_mf_transaction=True,
            )
            db.add(financial_transaction)
            db.commit()
            db.refresh(financial_transaction)
            financial_transaction_id = financial_transaction.transaction_id

            # Update account balance for main transaction
            account_amount_change = amount_excluding_charges if transaction_type_financial == "credit" else -amount_excluding_charges
            account.balance = account.balance + account_amount_change
            account.net_balance = account.net_balance + account_amount_change

            # Create charges transaction if other_charges > 0
            linked_charge_transaction_id = None
            if other_charges > 0:
                # Validate category exists and is expense type
                category = db.query(Category).filter(
                    Category.category_id == transaction_data.expense_category_id,
                    Category.user_id == fund.ledger.user_id,
                    Category.type == "expense"
                ).first()
                if not category:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid expense category for charges",
                    )

                charge_transaction_type = "debit"  # Charges are always debited (expenses)
                charge_notes = f"MF {transaction_data.transaction_type.title()} Charges"

                charge_transaction = Transaction(
                    account_id=transaction_data.account_id,
                    credit=0,
                    debit=other_charges,
                    category_id=transaction_data.expense_category_id,
                    date=transaction_data.transaction_date,
                    notes=charge_notes,
                    is_mf_transaction=True,
                )
                db.add(charge_transaction)
                db.commit()
                db.refresh(charge_transaction)
                linked_charge_transaction_id = charge_transaction.transaction_id

                # Update account balance for charges
                account.balance = account.balance - other_charges
                account.net_balance = account.net_balance - other_charges

            db.commit()

            # Calculate realized gain and cost basis for sell transactions
            realized_gain = Decimal("0")
            cost_basis_of_units_sold = Decimal("0")
            if transaction_data.transaction_type == "sell":
                if fund.total_units < transaction_data.units:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient units in fund. Available: {fund.total_units}, Requested: {transaction_data.units}",
                    )
                cost_basis_of_units_sold = Decimal(str(transaction_data.units)) * fund.average_cost_per_unit
                realized_gain = total_amount - cost_basis_of_units_sold
                fund.total_realized_gain += realized_gain
                fund.total_invested_cash -= cost_basis_of_units_sold
                fund.external_cash_invested -= cost_basis_of_units_sold

            # Update fund balances
            units_change = Decimal(str(transaction_data.units)) if transaction_data.transaction_type == "buy" else -Decimal(str(transaction_data.units))
            fund_amount_change = amount_excluding_charges if transaction_data.transaction_type == "buy" else -cost_basis_of_units_sold
            update_mutual_fund_balances(db, fund.mutual_fund_id, units_change, float(fund_amount_change))

            if transaction_data.transaction_type == "buy":
                fund.total_invested_cash += amount_excluding_charges
                fund.external_cash_invested += amount_excluding_charges

            if transaction_data.transaction_type in ["buy", "sell"]:
                fund.latest_nav = nav_per_unit
                fund.last_nav_update = transaction_data.transaction_date
                fund.current_value = fund.total_units * fund.latest_nav
                fund.updated_at = datetime.now(timezone.utc)
                db.commit()

        elif transaction_data.transaction_type == "switch_out":
            if not transaction_data.target_fund_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target fund ID required for switch_out transactions",
                )
            target_fund = get_mutual_fund_by_id(db, transaction_data.target_fund_id)
            if not target_fund or target_fund.ledger_id != ledger_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Target fund not found"
                )
            if transaction_data.target_fund_id == transaction_data.mutual_fund_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot switch to the same fund",
                )
            if fund.total_units < transaction_data.units:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient units in source fund. Available: {fund.total_units}, Requested: {transaction_data.units}",
                )
            if transaction_data.nav_per_unit <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="NAV per unit must be greater than 0 for switch_out transactions",
                )

            from_units = Decimal(str(transaction_data.units))
            from_nav = Decimal(str(transaction_data.nav_per_unit))

            total_value_switched_out = from_units * from_nav
            cost_basis_of_units_sold = from_units * fund.average_cost_per_unit
            realized_gain = total_value_switched_out - cost_basis_of_units_sold

            fund.total_realized_gain += realized_gain

            # Update source fund balances
            update_mutual_fund_balances(db, fund.mutual_fund_id, -from_units, -float(cost_basis_of_units_sold))

            fund.total_invested_cash -= cost_basis_of_units_sold

            fund.latest_nav = from_nav
            fund.last_nav_update = transaction_data.transaction_date
            fund.current_value = fund.total_units * fund.latest_nav
            fund.updated_at = datetime.now(timezone.utc)
            db.commit()

            total_amount = total_value_switched_out

        elif transaction_data.transaction_type == "switch_in":
            if not transaction_data.target_fund_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Source fund ID required for switch_in transactions",
                )
            source_fund = get_mutual_fund_by_id(db, transaction_data.target_fund_id)
            if not source_fund or source_fund.ledger_id != ledger_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Source fund not found"
                )
            if transaction_data.target_fund_id == transaction_data.mutual_fund_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot switch from the same fund",
                )
            if transaction_data.nav_per_unit <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="NAV per unit must be greater than 0 for switch_in transactions",
                )
            if not transaction_data.cost_basis_of_units_sold:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cost basis of units sold from source fund is required for switch_in",
                )

            to_units = Decimal(str(transaction_data.units))
            to_nav = Decimal(str(transaction_data.nav_per_unit))
            cost_basis_of_units_sold = Decimal(str(transaction_data.cost_basis_of_units_sold))

            # Update target fund balances
            update_mutual_fund_balances(db, fund.mutual_fund_id, to_units, float(cost_basis_of_units_sold))

            fund.total_invested_cash += cost_basis_of_units_sold

            fund.latest_nav = to_nav
            fund.last_nav_update = transaction_data.transaction_date
            fund.current_value = fund.total_units * fund.latest_nav
            fund.updated_at = datetime.now(timezone.utc)
            db.commit()

            total_amount = to_units * to_nav # This is the market value of units received

    # Create MF transaction record
    db_transaction = MfTransaction(
        ledger_id=ledger_id,
        mutual_fund_id=transaction_data.mutual_fund_id,
        transaction_type=transaction_data.transaction_type,
        units=transaction_data.units,
        nav_per_unit=nav_per_unit or transaction_data.nav_per_unit,
        total_amount=total_amount,
        amount_excluding_charges=amount_excluding_charges if 'amount_excluding_charges' in locals() else transaction_data.amount_excluding_charges,
        other_charges=other_charges if 'other_charges' in locals() else transaction_data.other_charges,
        account_id=transaction_data.account_id,
        target_fund_id=transaction_data.target_fund_id,
        financial_transaction_id=financial_transaction_id,
        linked_charge_transaction_id=linked_charge_transaction_id,
        transaction_date=transaction_data.transaction_date,
        notes=transaction_data.notes,
        linked_transaction_id=transaction_data.linked_transaction_id,
        realized_gain=realized_gain if 'realized_gain' in locals() else None,
        cost_basis_of_units_sold=cost_basis_of_units_sold if 'cost_basis_of_units_sold' in locals() else None,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return db_transaction


def get_mf_transactions_by_fund_id(db: Session, mutual_fund_id: int) -> list[MfTransaction]:
    """Get all MF transactions for a specific fund."""
    return (
        db.query(MfTransaction)
        .filter(MfTransaction.mutual_fund_id == mutual_fund_id)
        .order_by(MfTransaction.transaction_date.desc())
        .all()
    )


def get_mf_transactions_by_ledger_id(db: Session, ledger_id: int) -> list[MfTransaction]:
    """Get all MF transactions for a ledger."""
    return (
        db.query(MfTransaction)
        .filter(MfTransaction.ledger_id == ledger_id)
        .order_by(MfTransaction.transaction_date.desc())
        .all()
    )


def get_mf_transaction_by_id(db: Session, mf_transaction_id: int) -> MfTransaction | None:
    """Get an MF transaction by ID."""
    return db.query(MfTransaction).filter(MfTransaction.mf_transaction_id == mf_transaction_id).first()


def update_mf_transaction(
    db: Session, mf_transaction_id: int, update_data: mutual_funds_schema.MfTransactionUpdate
) -> MfTransaction:
    """Update MF transaction notes."""
    db_transaction = db.query(MfTransaction).filter(MfTransaction.mf_transaction_id == mf_transaction_id).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MF transaction not found"
        )

    if update_data.notes is not None:
        db_transaction.notes = update_data.notes
        # Also update the linked financial transaction if it exists
        # The financial transaction notes are auto-generated and should not be updated here.

    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def update_mf_transaction_linked_id(db: Session, mf_transaction_id: int, linked_id: int) -> MfTransaction:
    """Update the linked_transaction_id for an MF transaction."""
    db_transaction = db.query(MfTransaction).filter(MfTransaction.mf_transaction_id == mf_transaction_id).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MF transaction not found"
        )
    db_transaction.linked_transaction_id = linked_id
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


def delete_mf_transaction(db: Session, mf_transaction_id: int) -> None:
    """Delete an MF transaction and its linked financial transaction, reversing fund balances."""
    db_transaction = db.query(MfTransaction).filter(MfTransaction.mf_transaction_id == mf_transaction_id).first()
    if not db_transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MF transaction not found"
        )

    from app.repositories.mutual_fund_crud import get_mutual_fund_by_id, update_mutual_fund_balances

    fund = get_mutual_fund_by_id(db, db_transaction.mutual_fund_id)
    if not fund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mutual fund not found for transaction"
        )

    # Reverse the fund balance changes based on transaction type
    if db_transaction.transaction_type == "buy":
        units_change = -db_transaction.units
        amount_change = -db_transaction.amount_excluding_charges
        update_mutual_fund_balances(db, fund.mutual_fund_id, units_change, float(amount_change))
        fund.total_invested_cash -= db_transaction.amount_excluding_charges
        fund.external_cash_invested -= db_transaction.amount_excluding_charges
    elif db_transaction.transaction_type == "sell":
        units_change = db_transaction.units
        amount_change = db_transaction.cost_basis_of_units_sold
        update_mutual_fund_balances(db, fund.mutual_fund_id, units_change, float(amount_change))
        if db_transaction.realized_gain:
            fund.total_realized_gain -= db_transaction.realized_gain
        fund.total_invested_cash += db_transaction.cost_basis_of_units_sold
        fund.external_cash_invested += db_transaction.cost_basis_of_units_sold
    elif db_transaction.transaction_type == "switch_out":
        units_change = db_transaction.units
        amount_change = db_transaction.cost_basis_of_units_sold
        update_mutual_fund_balances(db, fund.mutual_fund_id, units_change, float(amount_change))
        if db_transaction.realized_gain:
            fund.total_realized_gain -= db_transaction.realized_gain
        fund.total_invested_cash += db_transaction.cost_basis_of_units_sold
    elif db_transaction.transaction_type == "switch_in":
        units_change = -db_transaction.units
        amount_change = -db_transaction.cost_basis_of_units_sold
        update_mutual_fund_balances(db, fund.mutual_fund_id, units_change, float(amount_change))
        fund.total_invested_cash -= db_transaction.cost_basis_of_units_sold

    # Delete financial transaction and update account balance
    if db_transaction.financial_transaction_id:
        financial_transaction = db.query(Transaction).filter(Transaction.transaction_id == db_transaction.financial_transaction_id).first()
        if financial_transaction:
            account = financial_transaction.account
            if account:
                amount = financial_transaction.credit if financial_transaction.credit > 0 else financial_transaction.debit
                if db_transaction.transaction_type == "buy":
                    # Buy transaction originally debited the account, so when deleting we need to credit it back
                    account.balance += amount
                    account.net_balance += amount
                elif db_transaction.transaction_type == "sell":
                    # Sell transaction originally credited the account, so when deleting we need to debit it back
                    account.balance -= amount
                    account.net_balance -= amount
            db.delete(financial_transaction)

    # Delete linked charge transaction if it exists
    if db_transaction.linked_charge_transaction_id:
        charge_transaction = db.query(Transaction).filter(Transaction.transaction_id == db_transaction.linked_charge_transaction_id).first()
        if charge_transaction:
            account = charge_transaction.account
            if account:
                # Charge transactions are always debits (expenses), so when deleting we credit back
                amount = charge_transaction.debit
                account.balance += amount
                account.net_balance += amount
            db.delete(charge_transaction)

    # If it's a switch transaction, delete the linked transaction as well
    if db_transaction.linked_transaction_id:
        # Find the linked transaction using the linked_transaction_id from the current transaction
        linked_transaction = db.query(MfTransaction).filter(MfTransaction.mf_transaction_id == db_transaction.linked_transaction_id).first()
        if linked_transaction:
            # To avoid recursion depth issues and ensure proper reversal, we'll delete the linked transaction directly here
            # instead of recursively calling delete_mf_transaction. This ensures the fund balances are reversed once.
            # The current transaction's linked_transaction_id points to the other side of the switch.
            # We need to reverse the linked transaction's impact on its fund.
            linked_fund = get_mutual_fund_by_id(db, linked_transaction.mutual_fund_id)
            if not linked_fund:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Linked mutual fund not found for transaction"
                )

            if linked_transaction.transaction_type == "switch_out":
                linked_units_change = linked_transaction.units
                linked_amount_change = linked_transaction.cost_basis_of_units_sold
                update_mutual_fund_balances(db, linked_fund.mutual_fund_id, linked_units_change, float(linked_amount_change))
                if linked_transaction.realized_gain:
                    linked_fund.total_realized_gain -= linked_transaction.realized_gain
                linked_fund.total_invested_cash += linked_transaction.cost_basis_of_units_sold
            elif linked_transaction.transaction_type == "switch_in":
                linked_units_change = -linked_transaction.units
                linked_amount_change = -linked_transaction.cost_basis_of_units_sold
                update_mutual_fund_balances(db, linked_fund.mutual_fund_id, linked_units_change, float(linked_amount_change))
                linked_fund.total_invested_cash -= linked_transaction.cost_basis_of_units_sold
            
            db.delete(linked_transaction)

    # Delete MF transaction
    db.delete(db_transaction)
    db.commit()