from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# AMC Schemas
class AmcBase(BaseModel, str_strip_whitespace=True):
    amc_id: int
    name: str
    description: Optional[str] = None


class AmcCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class AmcUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class Amc(AmcCreate, str_strip_whitespace=True):
    amc_id: int
    ledger_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Mutual Fund Schemas
class MutualFundBase(BaseModel, str_strip_whitespace=True):
    mutual_fund_id: int
    name: str
    amc_id: int
    total_units: float
    average_cost_per_unit: float
    latest_nav: float
    current_value: float


class MutualFundCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    amc_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class MutualFundUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    amc_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class MutualFundNavUpdate(BaseModel, str_strip_whitespace=True):
    latest_nav: float = Field(..., gt=0)


class MutualFund(MutualFundCreate, str_strip_whitespace=True):
    mutual_fund_id: int
    ledger_id: int
    total_units: float
    average_cost_per_unit: float
    latest_nav: float
    last_nav_update: Optional[datetime]
    current_value: float
    created_at: datetime
    updated_at: datetime
    total_realized_gain: float
    total_invested_cash: float
    external_cash_invested: float

    # Related data
    amc: Optional[Amc] = None

    class Config:
        from_attributes = True


# MF Transaction Schemas
class MfTransactionBase(BaseModel, str_strip_whitespace=True):
    mf_transaction_id: int
    mutual_fund_id: int
    transaction_type: Literal["buy", "sell", "switch_out", "switch_in"]
    units: float
    nav_per_unit: float
    total_amount: float
    account_id: Optional[int]
    target_fund_id: Optional[int]
    transaction_date: datetime


class MfTransactionCreate(BaseModel, str_strip_whitespace=True):
    mutual_fund_id: int = Field(..., gt=0)
    transaction_type: Literal["buy", "sell", "switch_out", "switch_in"]
    units: float = Field(..., gt=0)
    nav_per_unit: float = Field(..., ge=0)  # Allow 0 for transfers initially
    account_id: Optional[int] = Field(None, gt=0)
    target_fund_id: Optional[int] = Field(None, gt=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)
    to_nav: Optional[float] = Field(None, gt=0)
    linked_transaction_id: Optional[int] = None
    realized_gain: Optional[float] = None
    cost_basis_of_units_sold: Optional[float] = None


class MfTransactionUpdate(BaseModel, str_strip_whitespace=True):
    notes: Optional[str] = Field(None, max_length=500)


class MfTransaction(MfTransactionCreate, str_strip_whitespace=True):
    mf_transaction_id: int
    ledger_id: int
    total_amount: float
    created_at: datetime
    linked_transaction_id: Optional[int] = None
    realized_gain: Optional[float] = None
    cost_basis_of_units_sold: Optional[float] = None

    # Related data
    mutual_fund: Optional[MutualFund] = None
    account_name: Optional[str] = None
    target_fund_name: Optional[str] = None

    class Config:
        from_attributes = True


class MfSwitchCreate(BaseModel, str_strip_whitespace=True):
    source_mutual_fund_id: int = Field(..., gt=0)
    target_mutual_fund_id: int = Field(..., gt=0)
    units_to_switch: float = Field(..., gt=0)
    source_nav_at_switch: float = Field(..., gt=0)
    target_nav_at_switch: float = Field(..., gt=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)


# Summary and Analytics Schemas
class MutualFundSummary(BaseModel, str_strip_whitespace=True):
    mutual_fund_id: int
    name: str
    amc_name: str
    total_units: float
    average_cost_per_unit: float
    latest_nav: float
    current_value: float
    total_invested: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float


class AmcSummary(BaseModel, str_strip_whitespace=True):
    amc_id: int
    name: str
    total_funds: int
    total_units: float
    average_cost_per_unit: float
    latest_nav: float
    current_value: float
    total_invested: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float