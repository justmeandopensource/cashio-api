from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.model import Account
from app.repositories import ledger_crud, transaction_crud
from app.schemas import transaction_schema, user_schema
from app.security.user_security import get_current_user

transaction_Router = APIRouter(prefix="/ledger")


@transaction_Router.get(
    "/{ledger_id}/account/{account_id}/transactions",
    response_model=transaction_schema.PaginatedTransactionResponse,
    tags=["transactions"],
)
def get_transactions_by_account(
    ledger_id: int,
    account_id: int,
    page: int = Query(default=1, ge=1, description="Page number (starting from 1)"),
    per_page: int = Query(
        default=15, ge=1, le=50, description="Number of transactions per page (max 50)"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Account not found")

    offset = (page - 1) * per_page

    transactions = transaction_crud.get_transactions_for_account_id(
        db=db, account_id=account_id, offset=offset, limit=per_page
    )

    total_transactions = transaction_crud.get_transactions_count_for_account_id(
        db=db, account_id=account_id
    )

    total_pages = (total_transactions + per_page - 1) // per_page

    return {
        "transactions": transactions,
        "total_transactions": total_transactions,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
    }


@transaction_Router.get(
    "/{ledger_id}/transaction/{transaction_id}",
    response_model=transaction_schema.Transaction,
    tags=["transactions"],
)
def get_transaction_by_id(
    ledger_id: int,
    transaction_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    transaction = transaction_crud.get_transaction_by_id(
        db=db, transaction_id=transaction_id
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": transaction.transaction_id,
        "account_id": transaction.account_id,
        "category_id": transaction.category_id,
        "category_name": (
            transaction.category.name if transaction.category else None
        ),
        "credit": transaction.credit,
        "debit": transaction.debit,
        "date": transaction.date,
        "notes": transaction.notes,
        "is_split": transaction.is_split,
        "is_transfer": transaction.is_transfer,
        "is_asset_transaction": transaction.is_asset_transaction,
        "transfer_id": str(transaction.transfer_id),
        "transfer_type": transaction.transfer_type,
        "created_at": transaction.created_at,
        "tags": [
            {"tag_id": tag.tag_id, "user_id": tag.user_id, "name": tag.name}
            for tag in transaction.tags
        ],
    }


@transaction_Router.post(
    "/{ledger_id}/transaction/income",
    response_model=transaction_schema.Transaction,
    tags=["transactions"],
)
def add_income_transaction(
    transaction: transaction_schema.TransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the transaction type is "income"
    if transaction.type != "income":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction type must be 'income' for this endpoint",
        )

    # Ensure credit is positive and debit is zero for income transactions
    if transaction.credit <= 0 or transaction.debit != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For income transactions, credit must be positive and debit must be zero",
        )

    # Create the transaction
    return transaction_crud.create_transaction(db, transaction)


@transaction_Router.post(
    "/{ledger_id}/transaction/expense",
    response_model=transaction_schema.Transaction,
    tags=["transactions"],
)
def add_expense_transaction(
    transaction: transaction_schema.TransactionCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the transaction type is "expense"
    if transaction.type != "expense":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction type must be 'expense' for this endpoint",
        )

    # Ensure credit is zero for expense transactions
    if transaction.credit != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For expense transactions, credit must be zero",
        )

    # Create the transaction
    return transaction_crud.create_transaction(db, transaction)


@transaction_Router.post(
    "/{ledger_id}/transaction/transfer", response_model=dict, tags=["transactions"]
)
def add_transfer_transaction(
    transfer: transaction_schema.TransferCreate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        transaction_crud.create_transfer_transaction(
            db=db, transfer=transfer, user_id=user.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"message": "Transfer completed successfully"}





@transaction_Router.get(
    "/{ledger_id}/transaction/{transaction_id}/splits",
    response_model=List[transaction_schema.TransactionSplitResponse],
    tags=["transactions"],
)
def get_split_transactions(
    ledger_id: int,
    transaction_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the ledger belongs to the user
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Fetch the split transactions
    splits = transaction_crud.get_split_transactions(
        db=db, transaction_id=transaction_id
    )

    return splits


@transaction_Router.get(
    "/transfer/{transfer_id}",
    response_model=transaction_schema.TransferTransactionResponse,
    tags=["transactions"],
)
def get_transfer_transactions(
    transfer_id: str,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Validate that the transfer_id is a valid UUID
        UUID(transfer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transfer_id. It must be a valid UUID.",
        )
    # Fetch the transfer transactions
    transfer_details = transaction_crud.get_transfer_transactions(
        db=db, transfer_id=transfer_id
    )

    # Ensure the user has access to the source or destination ledger
    source_ledger_id = (
        db.query(Account.ledger_id)
        .filter(Account.account_id == transfer_details["source_transaction"].account_id)
        .first()
    )
    destination_ledger_id = (
        db.query(Account.ledger_id)
        .filter(
            Account.account_id == transfer_details["destination_transaction"].account_id
        )
        .first()
    )

    if not source_ledger_id or not destination_ledger_id:
        raise HTTPException(status_code=404, detail="Ledger not found")

    source_ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=source_ledger_id[0])
    destination_ledger = ledger_crud.get_ledger_by_id(
        db=db, ledger_id=destination_ledger_id[0]
    )

    if (
        source_ledger is None
        or destination_ledger is None
        or source_ledger.user_id != user.user_id
        or destination_ledger.user_id != user.user_id
    ):  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found or access denied")

    return transfer_details


from fastapi import Query


@transaction_Router.delete(
    "/{ledger_id}/transaction/{transaction_id}",
    response_model=dict,
    tags=["transactions"],
)
def delete_transaction(
    ledger_id: int,
    transaction_id: int,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the ledger belongs to the user
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Delete the transaction
    try:
        transaction_crud.delete_transaction(
            db=db, transaction_id=transaction_id, user_id=user.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"message": "Transaction deleted successfully"}


@transaction_Router.put(
    "/{ledger_id}/transaction/{transaction_id}",
    response_model=transaction_schema.Transaction,
    tags=["transactions"],
)
def update_transaction(
    ledger_id: int,
    transaction_id: int,
    transaction_update: transaction_schema.TransactionUpdate,
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the ledger belongs to the user
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Update the transaction
    try:
        return transaction_crud.update_transaction(
            db=db,
            transaction_id=transaction_id,
            transaction_update=transaction_update,
            user_id=user.user_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@transaction_Router.get(
    "/{ledger_id}/transaction/notes/suggestions",
    response_model=List[str],
    tags=["transactions"],
)
def get_note_suggestions(
    ledger_id: int,
    search_text: str = Query(
        ..., min_length=3, description="Text to search for in transaction notes"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ensure the ledger belongs to the user
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    # Fetch the suggestions
    suggestions = transaction_crud.get_transaction_notes_suggestions(
        db=db, ledger_id=ledger_id, search_text=search_text
    )

    return suggestions


@transaction_Router.get(
    "/{ledger_id}/transactions",
    response_model=transaction_schema.PaginatedTransactionResponse,
    tags=["transactions"],
)
def get_transactions_by_ledger(
    ledger_id: int,
    account_id: Optional[int] = Query(
        None, description="Filter transactions by account ID"
    ),
    page: int = Query(default=1, ge=1, description="Page number (starting from 1)"),
    per_page: int = Query(
        default=15, ge=1, le=50, description="Number of transactions per page (max 50)"
    ),
    from_date: Optional[datetime] = Query(
        None, description="Filter transactions from this date"
    ),
    to_date: Optional[datetime] = Query(
        None, description="Filter transactions up to this date"
    ),
    category_id: Optional[int] = Query(
        None, description="Filter transactions by category ID"
    ),
    tags: Optional[List[str]] = Query(None, description="Filter transactions by tags"),
    tags_match: Optional[str] = Query(
        "any", description="Filter transactions by tags match type (any/all)"
    ),
    search_text: Optional[str] = Query(
        None, description="Filter transactions by search text in notes"
    ),
    transaction_type: Optional[str] = Query(
        None, description="Filter transactions by type (income/expense/transfer)"
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if ledger is None or ledger.user_id != user.user_id:  # type: ignore
        raise HTTPException(status_code=404, detail="Ledger not found")

    offset = (page - 1) * per_page

    transactions = transaction_crud.get_transactions_for_ledger_id(
        db=db,
        ledger_id=ledger_id,
        account_id=account_id,
        offset=offset,
        limit=per_page,
        from_date=from_date,
        to_date=to_date,
        category_id=category_id,
        tags=tags,
        tags_match=tags_match,
        search_text=search_text,
        transaction_type=transaction_type,
    )

    total_transactions = transaction_crud.get_transactions_count_for_ledger_id(
        db=db,
        ledger_id=ledger_id,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        category_id=category_id,
        tags=tags,
        tags_match=tags_match,
        search_text=search_text,
        transaction_type=transaction_type,
    )

    total_pages = (total_transactions + per_page - 1) // per_page

    return {
        "transactions": transactions,
        "total_transactions": total_transactions,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
    }
