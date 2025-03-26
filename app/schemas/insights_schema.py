from typing import List, Literal, Optional

from pydantic import BaseModel


class TrendDataPoint(BaseModel):
    period: str
    income: float
    expense: float


class HighestAmount(BaseModel):
    period: Optional[str]
    amount: float


class CategorySummary(BaseModel):
    total: float
    highest: HighestAmount
    average: float


class IncomeExpenseTrendResponse(BaseModel):
    trend_data: List[TrendDataPoint]
    summary: dict[Literal["income", "expense"], CategorySummary]
