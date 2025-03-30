from typing import List

from pydantic import BaseModel


class TagAmount(BaseModel):
    tag: str
    amount: float


class CategoryAmount(BaseModel):
    category: str
    amount: float
    type: str


class TagTrendSummary(BaseModel):
    total_amount: float


class TagTrendResponse(BaseModel):
    tag_breakdown: List[TagAmount]
    category_breakdown: List[CategoryAmount]
    summary: TagTrendSummary
