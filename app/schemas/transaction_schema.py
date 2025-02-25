from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime

class TransactionSplitCreate(BaseModel):
    category_id: int
    credit: float = 0.00
    debit: float = 0.00
    notes: Optional[str] = None

class TransactionSplit(BaseModel, str_strip_whitespace=True):
    split_id: int
    transaction_id: int
    category_id: int
    credit: float
    debit: float
    notes: Optional[str]

    class Config:
        from_attributes = True

class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    type: Literal['income', 'expense']
    credit: float = 0.00
    debit: float = 0.00
    date: datetime
    notes: Optional[str] = None
    is_split: bool = False
    splits: Optional[List[TransactionSplitCreate]] = None

class Transaction(BaseModel, str_strip_whitespace=True):
    transaction_id: int
    account_id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    credit: float
    debit: float
    date: datetime
    notes: Optional[str]
    is_split: bool
    is_transfer: bool
    transfer_id: Optional[str]
    transfer_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PaginatedTransactionResponse(BaseModel):
    transactions: List[Transaction]
    total_transactions: int
    total_pages: int
    current_page: int
    per_page: int

