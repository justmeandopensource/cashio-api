from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Asset Type Schemas
class AssetTypeBase(BaseModel, str_strip_whitespace=True):
    asset_type_id: int
    name: str
    unit_name: str
    unit_symbol: str


class AssetTypeCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    unit_name: str = Field(..., min_length=1, max_length=50)
    unit_symbol: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=500)


class AssetTypeUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    unit_name: Optional[str] = Field(None, min_length=1, max_length=50)
    unit_symbol: Optional[str] = Field(None, min_length=1, max_length=10)
    description: Optional[str] = Field(None, max_length=500)


class AssetType(AssetTypeCreate, str_strip_whitespace=True):
    asset_type_id: int
    ledger_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Physical Asset Schemas
class PhysicalAssetBase(BaseModel, str_strip_whitespace=True):
    physical_asset_id: int
    name: str
    asset_type_id: int
    total_quantity: float
    average_cost_per_unit: float
    latest_price_per_unit: float
    current_value: float


class PhysicalAssetCreate(BaseModel, str_strip_whitespace=True):
    name: str = Field(..., min_length=1, max_length=100)
    asset_type_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class PhysicalAssetUpdate(BaseModel, str_strip_whitespace=True):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    asset_type_id: Optional[int] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=500)


class PhysicalAssetPriceUpdate(BaseModel, str_strip_whitespace=True):
    latest_price_per_unit: float = Field(..., gt=0)


class PhysicalAsset(PhysicalAssetCreate, str_strip_whitespace=True):
    physical_asset_id: int
    ledger_id: int
    total_quantity: float
    average_cost_per_unit: float
    latest_price_per_unit: float
    last_price_update: Optional[datetime]
    current_value: float
    created_at: datetime
    updated_at: datetime

    # Related data
    asset_type: Optional[AssetType] = None

    class Config:
        from_attributes = True


# Asset Transaction Schemas
class AssetTransactionBase(BaseModel, str_strip_whitespace=True):
    asset_transaction_id: int
    physical_asset_id: int
    transaction_type: Literal["buy", "sell"]
    quantity: float
    price_per_unit: float
    total_amount: float
    account_id: int
    transaction_date: datetime


class AssetTransactionCreate(BaseModel, str_strip_whitespace=True):
    physical_asset_id: int = Field(..., gt=0)
    transaction_type: Literal["buy", "sell"]
    quantity: float = Field(..., gt=0)
    price_per_unit: float = Field(..., gt=0)
    account_id: int = Field(..., gt=0)
    transaction_date: datetime
    notes: Optional[str] = Field(None, max_length=500)


class AssetTransactionUpdate(BaseModel, str_strip_whitespace=True):
    notes: Optional[str] = Field(None, max_length=500)


class AssetTransaction(AssetTransactionCreate, str_strip_whitespace=True):
    asset_transaction_id: int
    ledger_id: int
    total_amount: float
    created_at: datetime

    # Related data
    physical_asset: Optional[PhysicalAsset] = None
    account_name: Optional[str] = None

    class Config:
        from_attributes = True


# Summary and Analytics Schemas
class PhysicalAssetSummary(BaseModel, str_strip_whitespace=True):
    total_assets: int
    total_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_percentage: float


class AssetTypeSummary(BaseModel, str_strip_whitespace=True):
    asset_type_id: int
    name: str
    unit_name: str
    unit_symbol: str
    total_quantity: float
    average_cost_per_unit: float
    latest_price_per_unit: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float