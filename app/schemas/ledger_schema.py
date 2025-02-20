from pydantic import BaseModel

class Ledger(BaseModel):
    ledger_id: int
    user_id: int
    name: str
    currency_symbol: str

    class Config:
        from_attributes = True
