from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.repositories import ledger_crud
from app.repositories.insights import income_expense_trend_crud
from app.schemas import insights_schema, user_schema
from app.security.user_security import get_current_user

insights_router = APIRouter(prefix="/ledger/{ledger_id}/insights", tags=["insights"])


@insights_router.get(
    "/income-expense-trend",
    response_model=insights_schema.IncomeExpenseTrendResponse,
)
def get_income_expense_trend(
    ledger_id: int,
    period_type: Literal[
        "last_12_months", "monthly_since_beginning", "yearly_since_beginning"
    ] = Query(
        default="last_12_months",
        description="Type of period to analyze: last_12_months, monthly_since_beginning, or yearly_since_beginning",
    ),
    user: user_schema.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ledger = ledger_crud.get_ledger_by_id(db=db, ledger_id=ledger_id)
    if not ledger or ledger.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ledger not found"
        )

    try:
        return income_expense_trend_crud.get_income_expense_trend(
            db=db, ledger_id=ledger_id, period_type=period_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating insights: {str(e)}",
        )
