from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

from app.schemas.tag_schema import Tag, TagCreate


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


class TransactionSplitResponse(TransactionSplit):
    category_name: Optional[str] = None


class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    type: Literal["income", "expense"]
    credit: float = 0.00
    debit: float = 0.00
    date: datetime
    notes: Optional[str] = None
    is_transfer: bool
    transfer_id: Optional[str]
    transfer_type: Optional[str]
    is_split: bool = False
    splits: Optional[List[TransactionSplitCreate]] = None
    tags: Optional[List[TagCreate]] = None


class TransactionSplitUpdate(BaseModel):
    category_id: Optional[int] = None
    credit: Optional[float] = None
    debit: Optional[float] = None
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    type: Optional[Literal["income", "expense"]] = None
    credit: Optional[float] = None
    debit: Optional[float] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None
    is_split: Optional[bool] = None
    splits: Optional[List[TransactionSplitUpdate]] = None
    tags: Optional[List[TagCreate]] = None


class Transaction(BaseModel, str_strip_whitespace=True):
    transaction_id: int
    account_id: int
    account_name: Optional[str] = None
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
    tags: Optional[List[Tag]] = None

    class Config:
        from_attributes = True


class PaginatedTransactionResponse(BaseModel):
    transactions: List[Transaction]
    total_transactions: int
    total_pages: int
    current_page: int
    per_page: int


class TransferCreate(BaseModel):
    source_account_id: int
    destination_account_id: int
    source_amount: float
    destination_amount: Optional[float] = None
    date: datetime
    notes: Optional[str] = None
    tags: Optional[List[TagCreate]] = None





class TransferTransactionResponse(BaseModel):
    source_transaction: Transaction
    destination_transaction: Transaction
    source_account_name: str
    destination_account_name: str
    source_ledger_name: str
    destination_ledger_name: str
