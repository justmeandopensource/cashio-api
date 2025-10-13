from typing import List, Literal

from pydantic import BaseModel


class StoreExpenseData(BaseModel):
    store: str
    amount: float
    percentage: float


class LocationExpenseData(BaseModel):
    location: str
    amount: float
    percentage: float


class ExpenseByStoreResponse(BaseModel):
    store_data: List[StoreExpenseData]
    total_expense: float
    period_type: Literal["all_time", "last_12_months", "this_month"]


class ExpenseByLocationResponse(BaseModel):
    location_data: List[LocationExpenseData]
    total_expense: float
    period_type: Literal["all_time", "last_12_months", "this_month"]