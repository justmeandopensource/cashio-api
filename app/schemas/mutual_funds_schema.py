from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


# AMC Schemas
class AmcBase(BaseModel, str_strip_whitespace=True):
    amc_id: int
    name: str
    notes: Optional[str] = None


class AmcCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


class AmcUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


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
    total_units: Decimal
    average_cost_per_unit: Decimal
    latest_nav: Decimal
    current_value: Decimal


class MutualFundCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    plan: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=50)
    owner: Optional[str] = Field(None, max_length=100)
    amc_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class MutualFundUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=50)
    owner: Optional[str] = Field(None, max_length=100)
    amc_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class MutualFundNavUpdate(BaseModel, str_strip_whitespace=True):
    latest_nav: Decimal = Field(..., gt=0)


class MutualFund(MutualFundCreate, str_strip_whitespace=True):
    mutual_fund_id: int
    ledger_id: int
    total_units: Decimal
    average_cost_per_unit: Decimal
    latest_nav: Decimal
    last_nav_update: Optional[datetime]
    current_value: Decimal
    created_at: datetime
    updated_at: datetime
    total_realized_gain: Decimal
    total_invested_cash: Decimal
    external_cash_invested: Decimal

    # Related data
    amc: Optional[Amc] = None

    class Config:
        from_attributes = True


# MF Transaction Schemas
class MfTransactionBase(BaseModel, str_strip_whitespace=True):
    mf_transaction_id: int
    mutual_fund_id: int
    transaction_type: Literal["buy", "sell", "switch_out", "switch_in"]
    units: Decimal
    nav_per_unit: Decimal
    total_amount: Decimal
    amount_excluding_charges: Decimal
    other_charges: Decimal
    account_id: Optional[int]
    target_fund_id: Optional[int]
    transaction_date: datetime
    linked_charge_transaction_id: Optional[int] = None


class MfTransactionCreate(BaseModel, str_strip_whitespace=True):
    mutual_fund_id: int = Field(..., gt=0)
    transaction_type: Literal["buy", "sell", "switch_out", "switch_in"]
    units: Decimal = Field(..., gt=0)
    nav_per_unit: Optional[Decimal] = Field(None, ge=0)  # For switches, buy/sell use amount_excluding_charges
    amount_excluding_charges: Decimal = Field(..., gt=0)  # For buy/sell transactions
    other_charges: Decimal = Field(Decimal('0'), ge=0)
    expense_category_id: Optional[int] = Field(None, gt=0)
    account_id: Optional[int] = Field(None, gt=0)
    target_fund_id: Optional[int] = Field(None, gt=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)
    to_nav: Optional[Decimal] = Field(None, gt=0)
    linked_transaction_id: Optional[int] = None
    realized_gain: Optional[Decimal] = None
    cost_basis_of_units_sold: Optional[Decimal] = None


class MfTransactionUpdate(BaseModel, str_strip_whitespace=True):
    notes: Optional[str] = Field(None, max_length=500)


class MfTransaction(MfTransactionCreate, str_strip_whitespace=True):
    mf_transaction_id: int
    ledger_id: int
    total_amount: Decimal
    amount_excluding_charges: Decimal
    other_charges: Decimal
    created_at: datetime
    linked_transaction_id: Optional[int] = None
    linked_charge_transaction_id: Optional[int] = None
    realized_gain: Optional[Decimal] = None
    cost_basis_of_units_sold: Optional[Decimal] = None

    # Related data
    mutual_fund: Optional[MutualFund] = None
    account_name: Optional[str] = None
    target_fund_name: Optional[str] = None

    class Config:
        from_attributes = True


class MfSwitchCreate(BaseModel, str_strip_whitespace=True):
    source_mutual_fund_id: int = Field(..., gt=0)
    target_mutual_fund_id: int = Field(..., gt=0)
    source_units: Decimal = Field(..., gt=0)
    source_amount: Decimal = Field(..., gt=0)
    target_units: Decimal = Field(..., gt=0)
    target_amount: Decimal = Field(..., gt=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)


# Summary and Analytics Schemas
class MutualFundSummary(BaseModel, str_strip_whitespace=True):
    mutual_fund_id: int
    name: str
    plan: Optional[str] = None
    code: Optional[str] = None
    owner: Optional[str] = None
    amc_name: str
    total_units: Decimal
    average_cost_per_unit: Decimal
    latest_nav: Decimal
    current_value: Decimal
    total_invested: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percentage: Decimal


class AmcSummary(BaseModel, str_strip_whitespace=True):
    amc_id: int
    name: str
    total_funds: int
    total_units: Decimal
    average_cost_per_unit: Decimal
    latest_nav: Decimal
    current_value: Decimal
    total_invested: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percentage: Decimal


# Bulk NAV Fetch Schemas
class NavFetchResult(BaseModel, str_strip_whitespace=True):
    scheme_code: str
    fund_name: Optional[str] = None
    nav_value: Optional[float] = None
    nav_date: Optional[str] = None
    success: bool
    error_message: Optional[str] = None


class BulkNavFetchRequest(BaseModel, str_strip_whitespace=True):
    scheme_codes: list[str] = Field(..., min_length=1)


class BulkNavFetchResponse(BaseModel, str_strip_whitespace=True):
    results: list[NavFetchResult]
    total_requested: int
    total_successful: int
    total_failed: int


class BulkNavUpdateRequest(BaseModel, str_strip_whitespace=True):
    updates: list[dict] = Field(..., description="List of {mutual_fund_id: int, latest_nav: Decimal}")


class BulkNavUpdateResponse(BaseModel, str_strip_whitespace=True):
    updated_funds: list[int]  # List of mutual_fund_ids that were updated
    total_updated: int


class YearlyInvestment(BaseModel, str_strip_whitespace=True):
    year: int
    total_invested: Decimal