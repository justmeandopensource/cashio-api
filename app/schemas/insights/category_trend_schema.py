from typing import List, Literal, Optional

from pydantic import BaseModel


class CategoryTrendDataPoint(BaseModel):
    amount: float
    category_name: str


class NestedCategoryTrendDataPoint(BaseModel):
    period: str
    categories: List[CategoryTrendDataPoint]


class HighestAmount(BaseModel):
    period: Optional[str]
    amount: int


class CategoryTrendSummary(BaseModel):
    total: int
    highest: HighestAmount
    average: int


class CategoryTrendResponse(BaseModel):
    category_name: str
    category_type: Literal["income", "expense"]
    is_group: bool
    trend_data: List[NestedCategoryTrendDataPoint]
    summary: CategoryTrendSummary
