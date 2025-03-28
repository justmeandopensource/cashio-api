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


class CategoryBreakdown(BaseModel):
    name: str
    value: float
    children: Optional[List["CategoryBreakdown"]] = None


class MonthOverviewResponse(BaseModel):
    total_income: float
    total_expense: float
    income_categories_breakdown: List[CategoryBreakdown]
    expense_categories_breakdown: List[CategoryBreakdown]
