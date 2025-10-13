from typing import List

from pydantic import BaseModel


class ExpenseCalendarData(BaseModel):
    date: str
    amount: float


class ExpenseCalendarResponse(BaseModel):
    expenses: List[ExpenseCalendarData]
    total_expense: float