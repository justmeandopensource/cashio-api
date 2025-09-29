from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.model import MutualFund
from app.repositories import ledger_crud
from app.repositories.amc_crud import (
    create_amc as create_amc_repo,
    get_amcs_by_ledger_id,
    get_amc_by_id,
    update_amc as update_amc_repo,
    delete_amc as delete_amc_repo,
)
from app.repositories.mutual_fund_crud import (
    create_mutual_fund as create_mutual_fund_repo,
    get_mutual_funds_by_ledger_id,
    get_mutual_fund_by_id,
    update_mutual_fund as update_mutual_fund_repo,
    update_mutual_fund_nav,
    bulk_update_mutual_fund_navs,
    delete_mutual_fund as delete_mutual_fund_repo,
)
from app.repositories.mf_transaction_crud import (
    create_mf_transaction,
    get_mf_transactions_by_fund_id,
    get_mf_transactions_by_ledger_id,
    update_mf_transaction,
    delete_mf_transaction,
)
from app.schemas import mutual_funds_schema, user_schema
from sqlalchemy import func, extract
from app.security.user_security import get_current_user
from app.services.nav_service import NavService
from app.utils.xirr_calculator import calculate_xirr

mutual_funds_router = APIRouter(prefix="/ledger")


# AMC Management Endpoints
@mutual_funds_router.post(
    "/{ledger_id}/amc/create",
    response_model=mutual_funds_schema.Amc,
    tags=["mutual-funds"],
)
def create_amc(
    ledger_id: int,
    amc: mutual_funds_schema.AmcCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new AMC for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        new_amc = create_amc_repo(
            db=db, ledger_id=ledger_id, amc=amc
        )
        return new_amc
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating AMC: {str(e)}",
        )


@mutual_funds_router.get(
    "/{ledger_id}/amcs",
    response_model=List[mutual_funds_schema.Amc],
    tags=["mutual-funds"],
)
def get_amcs(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all AMCs for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    amcs = get_amcs_by_ledger_id(db=db, ledger_id=ledger_id)
    return amcs


@mutual_funds_router.put(
    "/{ledger_id}/amc/{amc_id}",
    response_model=mutual_funds_schema.Amc,
    tags=["mutual-funds"],
)
def update_amc(
    ledger_id: int,
    amc_id: int,
    amc_update: mutual_funds_schema.AmcUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an AMC."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the AMC belongs to this ledger
    amc = get_amc_by_id(db=db, amc_id=amc_id)
    if amc is None or amc.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="AMC not found")

    updated_amc = update_amc_repo(
        db=db, amc_id=amc_id, amc_update=amc_update
    )
    return updated_amc


@mutual_funds_router.delete(
    "/{ledger_id}/amc/{amc_id}",
    tags=["mutual-funds"],
)
def delete_amc(
    ledger_id: int,
    amc_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an AMC."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the AMC belongs to this ledger
    amc = get_amc_by_id(db=db, amc_id=amc_id)
    if amc is None or amc.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="AMC not found")

    delete_amc_repo(db=db, amc_id=amc_id)
    return {"message": "AMC deleted successfully"}


# Mutual Fund Management Endpoints
@mutual_funds_router.post(
    "/{ledger_id}/mutual-fund/create",
    response_model=mutual_funds_schema.MutualFund,
    tags=["mutual-funds"],
)
def create_mutual_fund(
    ledger_id: int,
    fund: mutual_funds_schema.MutualFundCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new mutual fund for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        new_fund = create_mutual_fund_repo(
            db=db, ledger_id=ledger_id, fund=fund
        )
        return new_fund
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating mutual fund: {str(e)}",
        )


@mutual_funds_router.get(
    "/{ledger_id}/mutual-funds",
    response_model=List[mutual_funds_schema.MutualFund],
    tags=["mutual-funds"],
)
def get_mutual_funds(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all mutual funds for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    funds = get_mutual_funds_by_ledger_id(db=db, ledger_id=ledger_id)

    # Calculate XIRR for each fund
    current_date = datetime.now()
    for fund in funds:
        transactions = get_mf_transactions_by_fund_id(db=db, mutual_fund_id=fund.mutual_fund_id)
        tx_data = [
            {
                'transaction_date': tx.transaction_date,
                'transaction_type': tx.transaction_type,
                'amount_excluding_charges': float(tx.amount_excluding_charges)
            }
            for tx in transactions
        ]
        fund.xirr_percentage = calculate_xirr(tx_data, float(fund.current_value), current_date)

    return funds


@mutual_funds_router.get(
    "/{ledger_id}/mutual-fund/{fund_id}",
    response_model=mutual_funds_schema.MutualFund,
    tags=["mutual-funds"],
)
def get_mutual_fund(
    ledger_id: int,
    fund_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific mutual fund."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    fund = get_mutual_fund_by_id(db=db, mutual_fund_id=fund_id)
    if fund is None or fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Mutual fund not found")

    return fund


@mutual_funds_router.put(
    "/{ledger_id}/mutual-fund/{fund_id}",
    response_model=mutual_funds_schema.MutualFund,
    tags=["mutual-funds"],
)
def update_mutual_fund(
    ledger_id: int,
    fund_id: int,
    fund_update: mutual_funds_schema.MutualFundUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a mutual fund."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the fund belongs to this ledger
    fund = get_mutual_fund_by_id(db=db, mutual_fund_id=fund_id)
    if fund is None or fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Mutual fund not found")

    updated_fund = update_mutual_fund_repo(
        db=db, mutual_fund_id=fund_id, fund_update=fund_update
    )
    return updated_fund


@mutual_funds_router.put(
    "/{ledger_id}/mutual-fund/{fund_id}/update-nav",
    response_model=mutual_funds_schema.MutualFund,
    tags=["mutual-funds"],
)
def update_fund_nav(
    ledger_id: int,
    fund_id: int,
    nav_update: mutual_funds_schema.MutualFundNavUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the latest NAV for a mutual fund."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the fund belongs to this ledger
    fund = get_mutual_fund_by_id(db=db, mutual_fund_id=fund_id)
    if fund is None or fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Mutual fund not found")

    updated_fund = update_mutual_fund_nav(
        db=db, mutual_fund_id=fund_id, nav_update=nav_update
    )
    return updated_fund


@mutual_funds_router.delete(
    "/{ledger_id}/mutual-fund/{fund_id}",
    tags=["mutual-funds"],
)
def delete_mutual_fund(
    ledger_id: int,
    fund_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a mutual fund."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the fund belongs to this ledger
    fund = get_mutual_fund_by_id(db=db, mutual_fund_id=fund_id)
    if fund is None or fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Mutual fund not found")

    delete_mutual_fund_repo(db=db, mutual_fund_id=fund_id)
    return {"message": "Mutual fund deleted successfully"}


# MF Transaction Management Endpoints
@mutual_funds_router.post(
    "/{ledger_id}/mf-transaction/buy",
    response_model=mutual_funds_schema.MfTransaction,
    tags=["mutual-funds"],
)
def buy_mutual_fund(
    ledger_id: int,
    transaction: mutual_funds_schema.MfTransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Buy mutual fund units."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Ensure this is a buy transaction
    if transaction.transaction_type != "buy":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for buy transactions only"
        )

    try:
        new_transaction = create_mf_transaction(
            db=db, ledger_id=ledger_id, transaction_data=transaction
        )
        return new_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing buy transaction: {str(e)}",
        )


@mutual_funds_router.post(
    "/{ledger_id}/mf-transaction/sell",
    response_model=mutual_funds_schema.MfTransaction,
    tags=["mutual-funds"],
)
def sell_mutual_fund(
    ledger_id: int,
    transaction: mutual_funds_schema.MfTransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sell mutual fund units."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Ensure this is a sell transaction
    if transaction.transaction_type != "sell":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for sell transactions only"
        )

    try:
        new_transaction = create_mf_transaction(
            db=db, ledger_id=ledger_id, transaction_data=transaction
        )
        return new_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing sell transaction: {str(e)}",
        )





@mutual_funds_router.post(
    "/{ledger_id}/mf-transaction/switch",
    response_model=List[mutual_funds_schema.MfTransaction],
    tags=["mutual-funds"],
)
def switch_mutual_fund_units(
    ledger_id: int,
    switch_data: mutual_funds_schema.MfSwitchCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Switch mutual fund units from one fund to another."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    source_fund = get_mutual_fund_by_id(db, switch_data.source_mutual_fund_id)
    target_fund = get_mutual_fund_by_id(db, switch_data.target_mutual_fund_id)

    if source_fund is None or source_fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Source mutual fund not found")
    if target_fund is None or target_fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Target mutual fund not found")
    if source_fund.mutual_fund_id == target_fund.mutual_fund_id:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot switch to the same fund",
        )

    # Calculate NAVs from amounts and units
    source_nav = switch_data.source_amount / switch_data.source_units
    target_nav = switch_data.target_amount / switch_data.target_units

    # Create switch_out transaction (selling from source fund)
    switch_out_transaction_data = mutual_funds_schema.MfTransactionCreate(
        mutual_fund_id=switch_data.source_mutual_fund_id,
        transaction_type="switch_out",
        units=switch_data.source_units,
        nav_per_unit=source_nav,
        amount_excluding_charges=switch_data.source_amount,
        other_charges=Decimal('0'),
        expense_category_id=None,
        account_id=None,  # No direct account involvement for switch
        target_fund_id=switch_data.target_mutual_fund_id,
        transaction_date=switch_data.transaction_date,
        notes=switch_data.notes,
        to_nav=target_nav, # This is not used in switch_out logic, but kept for schema consistency
        # linked_transaction_id will be set after both transactions are created
    )
    switch_out_transaction = create_mf_transaction(
        db=db, ledger_id=ledger_id, transaction_data=switch_out_transaction_data
    )

    # Create switch_in transaction (buying into target fund)
    switch_in_transaction_data = mutual_funds_schema.MfTransactionCreate(
        mutual_fund_id=switch_data.target_mutual_fund_id,
        transaction_type="switch_in",
        units=switch_data.target_units,
        nav_per_unit=target_nav,
        amount_excluding_charges=switch_data.target_amount,
        other_charges=Decimal('0'),
        expense_category_id=None,
        account_id=None,  # No direct account involvement for switch
        target_fund_id=switch_data.source_mutual_fund_id,
        transaction_date=switch_data.transaction_date,
        notes=switch_data.notes,
        to_nav=source_nav, # This is not used in switch_in logic, but kept for schema consistency
        # linked_transaction_id will be set after both transactions are created
        cost_basis_of_units_sold=Decimal(str(switch_data.target_amount)) # Use target amount as cost basis for target fund
    )
    switch_in_transaction = create_mf_transaction(
        db=db, ledger_id=ledger_id, transaction_data=switch_in_transaction_data
    )

    # Now link the two transactions
    from app.repositories.mf_transaction_crud import update_mf_transaction_linked_id
    update_mf_transaction_linked_id(db, switch_out_transaction.mf_transaction_id, switch_in_transaction.mf_transaction_id)  # type: ignore
    update_mf_transaction_linked_id(db, switch_in_transaction.mf_transaction_id, switch_out_transaction.mf_transaction_id)  # type: ignore

    return [switch_out_transaction, switch_in_transaction]


@mutual_funds_router.get(
    "/{ledger_id}/mutual-fund/{fund_id}/transactions",
    response_model=List[mutual_funds_schema.MfTransaction],
    tags=["mutual-funds"],
)
def get_fund_transactions(
    ledger_id: int,
    fund_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transaction history for a specific mutual fund."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the fund belongs to this ledger
    fund = get_mutual_fund_by_id(db=db, mutual_fund_id=fund_id)
    if fund is None or fund.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Mutual fund not found")

    transactions = get_mf_transactions_by_fund_id(
        db=db, mutual_fund_id=fund_id
    )
    for t in transactions:
        if t.account:
            t.account_name = t.account.name
        if t.target_fund:
            t.target_fund_name = t.target_fund.name
    return transactions


@mutual_funds_router.get(
    "/{ledger_id}/mf-transactions",
    response_model=List[mutual_funds_schema.MfTransaction],
    tags=["mutual-funds"],
)
def get_all_mf_transactions(
    ledger_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all MF transactions for a ledger."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    transactions = get_mf_transactions_by_ledger_id(
        db=db, ledger_id=ledger_id
    )
    for t in transactions:
        if t.account:
            t.account_name = t.account.name
        if t.target_fund:
            t.target_fund_name = t.target_fund.name
    return transactions


@mutual_funds_router.delete(
    "/{ledger_id}/mf-transaction/{transaction_id}",
    tags=["mutual-funds"],
)
def delete_mf_transaction_endpoint(
    ledger_id: int,
    transaction_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an MF transaction and its linked financial transaction."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the transaction belongs to this ledger
    from app.repositories.mf_transaction_crud import get_mf_transaction_by_id
    transaction = get_mf_transaction_by_id(db=db, mf_transaction_id=transaction_id)
    if transaction is None or transaction.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="MF transaction not found")

    try:
        delete_mf_transaction(db=db, mf_transaction_id=transaction_id)
        return {"message": "MF transaction deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting MF transaction: {str(e)}",
        )


@mutual_funds_router.patch(
    "/{ledger_id}/mf-transaction/{transaction_id}",
    response_model=mutual_funds_schema.MfTransaction,
    tags=["mutual-funds"],
)
def update_mf_transaction_endpoint(
    ledger_id: int,
    transaction_id: int,
    transaction_update: mutual_funds_schema.MfTransactionUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an MF transaction."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Verify the transaction belongs to this ledger
    from app.repositories.mf_transaction_crud import get_mf_transaction_by_id
    transaction = get_mf_transaction_by_id(db=db, mf_transaction_id=transaction_id)
    if transaction is None or transaction.ledger_id != ledger_id:  # type: ignore
        raise HTTPException(status_code=404, detail="MF transaction not found")

    try:
        updated_transaction = update_mf_transaction(
            db=db, mf_transaction_id=transaction_id, update_data=transaction_update
        )
        return updated_transaction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating MF transaction: {str(e)}",
        )


# Bulk NAV Operations Endpoints
@mutual_funds_router.post(
    "/{ledger_id}/mutual-funds/bulk-fetch-nav",
    response_model=mutual_funds_schema.BulkNavFetchResponse,
    tags=["mutual-funds"],
)
def bulk_fetch_nav(
    ledger_id: int,
    request: mutual_funds_schema.BulkNavFetchRequest,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch latest NAV for multiple mutual funds by scheme codes."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        # Fetch NAV data for all scheme codes
        results = NavService.fetch_nav_bulk_sync(request.scheme_codes)

        # Calculate summary stats
        total_requested = len(request.scheme_codes)
        total_successful = sum(1 for r in results if r.success)
        total_failed = total_requested - total_successful

        return mutual_funds_schema.BulkNavFetchResponse(
            results=results,
            total_requested=total_requested,
            total_successful=total_successful,
            total_failed=total_failed
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching NAV data: {str(e)}",
        )


@mutual_funds_router.put(
    "/{ledger_id}/mutual-funds/bulk-update-nav",
    response_model=mutual_funds_schema.BulkNavUpdateResponse,
    tags=["mutual-funds"],
)
def bulk_update_nav(
    ledger_id: int,
    request: mutual_funds_schema.BulkNavUpdateRequest,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update NAV for multiple mutual funds."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    try:
        # Validate that all funds belong to this ledger
        fund_ids = [update['mutual_fund_id'] for update in request.updates]
        funds = db.query(MutualFund).filter(
            MutualFund.mutual_fund_id.in_(fund_ids),
            MutualFund.ledger_id == ledger_id
        ).all()

        if len(funds) != len(fund_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some mutual funds not found or don't belong to this ledger"
            )

        # Perform bulk update
        updated_ids = bulk_update_mutual_fund_navs(db=db, nav_updates=request.updates)

        return mutual_funds_schema.BulkNavUpdateResponse(
            updated_funds=updated_ids,
            total_updated=len(updated_ids)
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating NAV data: {str(e)}",
        )


@mutual_funds_router.get(
    "/{ledger_id}/mutual-funds/yearly-investments",
    response_model=List[mutual_funds_schema.YearlyInvestment],
    tags=["mutual-funds"],
)
def get_yearly_investments(
    ledger_id: int,
    owner: Optional[str] = None,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get yearly investment summary for mutual funds."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    from app.models.model import MfTransaction

    # Build query for buy transactions
    query = db.query(
        extract('year', MfTransaction.transaction_date).label('year'),
        func.sum(MfTransaction.amount_excluding_charges).label('total_invested')
    ).filter(
        MfTransaction.ledger_id == ledger_id,
        MfTransaction.transaction_type == 'buy'
    )

    # Filter by owner if specified
    if owner and owner != 'all':
        from app.models.model import MutualFund
        query = query.join(
            MutualFund,
            MfTransaction.mutual_fund_id == MutualFund.mutual_fund_id
        ).filter(MutualFund.owner == owner)

    # Group by year and order by year
    query = query.group_by(extract('year', MfTransaction.transaction_date)).order_by(extract('year', MfTransaction.transaction_date))

    results = query.all()

    # Convert to response format
    yearly_investments = []
    for result in results:
        yearly_investments.append(mutual_funds_schema.YearlyInvestment(
            year=int(result.year),
            total_invested=result.total_invested or Decimal('0')
        ))

    # Fill in missing years from earliest to current year
    if yearly_investments:
        current_year = datetime.now().year
        min_year = min(inv.year for inv in yearly_investments)

        # Create a complete list from min_year to current_year
        complete_years = {}
        for year in range(min_year, current_year + 1):
            complete_years[year] = Decimal('0')

        # Fill in actual values
        for inv in yearly_investments:
            complete_years[inv.year] = inv.total_invested

        # Convert back to list
        yearly_investments = [
            mutual_funds_schema.YearlyInvestment(year=year, total_invested=amount)
            for year, amount in sorted(complete_years.items())
        ]

    return yearly_investments


@mutual_funds_router.get(
    "/{ledger_id}/mutual-funds/corpus-growth",
    response_model=List[mutual_funds_schema.YearlyInvestment],
    tags=["mutual-funds"],
)
def get_corpus_growth(
    ledger_id: int,
    owner: Optional[str] = None,
    granularity: str = "monthly",
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get cumulative corpus growth for mutual funds by month."""
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    from app.models.model import MfTransaction

    # Build query for buy transactions - group by year and optionally month
    if granularity == "yearly":
        query = db.query(
            extract('year', MfTransaction.transaction_date).label('year'),
            func.sum(MfTransaction.amount_excluding_charges).label('total_invested')
        ).filter(
            MfTransaction.ledger_id == ledger_id,
            MfTransaction.transaction_type == 'buy'
        )

        # Filter by owner if specified
        if owner and owner != 'all':
            from app.models.model import MutualFund
            query = query.join(
                MutualFund,
                MfTransaction.mutual_fund_id == MutualFund.mutual_fund_id
            ).filter(MutualFund.owner == owner)

        # Group by year, order by year
        query = query.group_by(extract('year', MfTransaction.transaction_date)).order_by(extract('year', MfTransaction.transaction_date))
    else:  # monthly
        query = db.query(
            extract('year', MfTransaction.transaction_date).label('year'),
            extract('month', MfTransaction.transaction_date).label('month'),
            func.sum(MfTransaction.amount_excluding_charges).label('total_invested')
        ).filter(
            MfTransaction.ledger_id == ledger_id,
            MfTransaction.transaction_type == 'buy'
        )

        # Filter by owner if specified
        if owner and owner != 'all':
            from app.models.model import MutualFund
            query = query.join(
                MutualFund,
                MfTransaction.mutual_fund_id == MutualFund.mutual_fund_id
            ).filter(MutualFund.owner == owner)

        # Group by year and month, order by year and month
        query = query.group_by(
            extract('year', MfTransaction.transaction_date),
            extract('month', MfTransaction.transaction_date)
        ).order_by(
            extract('year', MfTransaction.transaction_date),
            extract('month', MfTransaction.transaction_date)
        )

    results = query.all()

    # Convert to response format
    investments = []
    for result in results:
        if granularity == "yearly":
            investments.append(mutual_funds_schema.YearlyInvestment(
                year=int(result.year),
                total_invested=result.total_invested or Decimal('0')
            ))
        else:  # monthly
            investments.append(mutual_funds_schema.YearlyInvestment(
                year=int(result.year),
                month=int(result.month),
                total_invested=result.total_invested or Decimal('0')
            ))

    # Fill in missing periods from earliest to current period
    if investments:
        current_year = datetime.now().year
        min_year = min(inv.year for inv in investments)

        if granularity == "yearly":
            # Fill in missing years
            complete_years = {}
            for year in range(min_year, current_year + 1):
                complete_years[year] = Decimal('0')

            # Fill in actual values
            for inv in investments:
                complete_years[inv.year] = inv.total_invested

            # Calculate cumulative corpus
            cumulative_corpus = Decimal('0')
            corpus_growth = []
            for year, amount in sorted(complete_years.items()):
                cumulative_corpus += amount
                corpus_growth.append(mutual_funds_schema.YearlyInvestment(
                    year=year,
                    total_invested=cumulative_corpus
                ))

            return corpus_growth
        else:  # monthly
            current_month = datetime.now().month

            # Get the minimum month for the minimum year, defaulting to 1 if no months found
            min_month_investments = [inv.month for inv in investments if inv.year == min_year and inv.month is not None]
            min_month = min(min_month_investments) if min_month_investments else 1

            # Create a complete list from earliest month to current month
            complete_months = {}
            for year in range(min_year, current_year + 1):
                start_month = min_month if year == min_year else 1
                end_month = current_month if year == current_year else 12
                for month in range(start_month, end_month + 1):
                    complete_months[f"{year}-{month:02d}"] = Decimal('0')

            # Fill in actual values
            for inv in investments:
                if inv.month is not None:
                    key = f"{inv.year}-{inv.month:02d}"
                    complete_months[key] = inv.total_invested

            # Calculate cumulative corpus
            cumulative_corpus = Decimal('0')
            corpus_growth = []
            for key, amount in sorted(complete_months.items()):
                cumulative_corpus += amount
                year, month = map(int, key.split('-'))
                corpus_growth.append(mutual_funds_schema.YearlyInvestment(
                    year=year,
                    month=month,
                    total_invested=cumulative_corpus
                ))

            return corpus_growth

    return []