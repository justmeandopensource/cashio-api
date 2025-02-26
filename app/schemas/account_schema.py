from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime

class AccountBase(BaseModel, str_strip_whitespace=True):
    account_id: int
    name: str

class AccountCreate(BaseModel, str_strip_whitespace=True):
    name: str
    type: Literal['asset', 'liability']
    is_group: bool = False
    opening_balance: Optional[float] = None
    parent_account_id: Optional[int] = None

class AccountUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = None
    opening_balance: Optional[float] = None
    parent_account_id: Optional[int] = None

class Account(AccountCreate, str_strip_whitespace=True):
    account_id: int
    ledger_id: int
    balance: float
    net_balance: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
