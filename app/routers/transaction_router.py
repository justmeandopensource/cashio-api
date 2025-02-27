from fastapi import Depends, APIRouter, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.schemas import user_schema, transaction_schema
from app.repositories import ledger_crud, transaction_crud
from app.database.connection import get_db
from app.security.user_security import get_current_user
from app.models.model import Account

transaction_Router = APIRouter(prefix="/ledger")

@transaction_Router.get("/{ledger_id}/account/{account_id}/transactions", response_model=transaction_schema.PaginatedTransactionResponse, tags=["transactions"])
def get_transactions_by_account(
    ledger_id: int,
    account_id: int,
    page: int = Query(default=1, ge=1, description="Page number (starting from 1)"),
    per_page: int = Query(default=25, ge=1, le=100, description="Number of transactions per page (max 50)"),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Account not found")

    offset = (page - 1) * per_page

    transactions = transaction_crud.get_transactions_for_account_id(
        db=db,
        account_id=account_id,
        offset=offset,
        limit=per_page
    )

    total_transactions = transaction_crud.get_transactions_count_for_account_id(db=db, account_id=account_id)

    total_pages = (total_transactions + per_page - 1) // per_page

    return {
        "transactions": transactions,
        "total_transactions": total_transactions,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page
    }

@transaction_Router.post("/{ledger_id}/transaction/income", response_model=transaction_schema.Transaction, tags=["transactions"])
def add_income_transaction(
    transaction: transaction_schema.TransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure the transaction type is "income"
    if transaction.type != 'income':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction type must be 'income' for this endpoint"
        )

    # Ensure credit is positive and debit is zero for income transactions
    if transaction.credit <= 0 or transaction.debit != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For income transactions, credit must be positive and debit must be zero"
        )

    # Create the transaction
    return transaction_crud.create_transaction(db, transaction)

@transaction_Router.post("/{ledger_id}/transaction/expense", response_model=transaction_schema.Transaction, tags=["transactions"])
def add_expense_transaction(
    transaction: transaction_schema.TransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure the transaction type is "expense"
    if transaction.type != 'expense':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction type must be 'expense' for this endpoint"
        )

    # Ensure debit is positive and credit is zero for expense transactions
    if transaction.debit <= 0 or transaction.credit != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For expense transactions, debit must be positive and credit must be zero"
        )

    # Create the transaction
    return transaction_crud.create_transaction(db, transaction)

@transaction_Router.post("/{ledger_id}/transaction/transfer", response_model=dict, tags=["transactions"])
def add_transfer_transaction(
    transfer: transaction_schema.TransferCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        transaction_crud.create_transfer_transaction(db=db, transfer=transfer, user_id=user.user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": "Transfer completed successfully"}
