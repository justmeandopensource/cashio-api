from pydantic import BaseModel

class LedgerCreate(BaseModel):
    name: str
    currency_symbol: str

class Ledger(LedgerCreate):
    user_id: int
    ledger_id: int

    class Config:
        from_attributes = True
