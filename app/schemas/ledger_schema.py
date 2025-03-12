from datetime import datetime

from pydantic import BaseModel


class LedgerCreate(BaseModel, str_strip_whitespace=True):
    name: str
    currency_symbol: str


class Ledger(LedgerCreate, str_strip_whitespace=True):
    user_id: int
    ledger_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
