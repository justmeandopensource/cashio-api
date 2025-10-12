from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    UUID as SQLUUID,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledgers = relationship("Ledger", back_populates="user")
    categories = relationship("Category", back_populates="user")
    tags = relationship("Tag", back_populates="user")


class Ledger(Base):
    __tablename__ = "ledgers"

    ledger_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nav_service_type: Mapped[str] = mapped_column(Enum("india", "uk", name="nav_service_type"), default="india", nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="ledgers")
    accounts = relationship("Account", back_populates="ledger")
    asset_types = relationship("AssetType", back_populates="ledger")
    physical_assets = relationship("PhysicalAsset", back_populates="ledger")
    asset_transactions = relationship("AssetTransaction", back_populates="ledger")
    amcs = relationship("Amc", back_populates="ledger")
    mutual_funds = relationship("MutualFund", back_populates="ledger")
    mf_transactions = relationship("MfTransaction", back_populates="ledger")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_ledger_name"),)


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    parent_account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.account_id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str] = mapped_column(Enum("asset", "liability", name="account_type"), nullable=False)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    net_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="accounts")
    parent_account = relationship(
        "Account", remote_side=[account_id], back_populates="child_accounts"
    )
    child_accounts = relationship("Account", back_populates="parent_account")
    transactions = relationship("Transaction", back_populates="account")
    asset_transactions = relationship("AssetTransaction", back_populates="account")
    mf_transactions = relationship("MfTransaction", back_populates="account")

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_account_name"),
    )


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    parent_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.category_id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(Enum("income", "expense", name="category_type"), nullable=False)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="categories")
    parent_category = relationship(
        "Category", remote_side=[category_id], back_populates="child_categories"
    )
    child_categories = relationship("Category", back_populates="parent_category")

    __table_args__ = (
        UniqueConstraint("parent_category_id", "name", name="uq_parent_category_name"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.category_id"), nullable=True)
    credit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    store: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_split: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_asset_transaction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_mf_transaction: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transfer_id: Mapped[UUID | None] = mapped_column(SQLUUID, nullable=True)
    transfer_type: Mapped[str | None] = mapped_column(
        Enum("source", "destination", name="transfer_type"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category")
    splits = relationship(
        "TransactionSplit", back_populates="transaction", cascade="all, delete-orphan"
    )
    tags = relationship(
        "Tag", secondary="transaction_tags", back_populates="transactions"
    )

    __table_args__ = (
        Index("idx_transactions_account_id", "account_id"),
        Index("idx_transactions_category_id", "category_id"),
        Index("idx_transactions_date", "date"),
        Index("idx_transactions_account_id_date", "account_id", "date"),
    )


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"

    split_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transactions.transaction_id"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.category_id"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0.00, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    transaction = relationship("Transaction", back_populates="splits")
    category = relationship("Category")


class Tag(Base):
    __tablename__ = "tags"

    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    user = relationship("User", back_populates="tags")

    transactions = relationship(
        "Transaction", secondary="transaction_tags", back_populates="tags"
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_tag_name"),)


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.tag_id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("transaction_id", "tag_id", name="uq_transaction_tag"),
        Index("idx_transaction_tags_transaction_id", "transaction_id"),
        Index("idx_transaction_tags_tag_id", "tag_id"),
        Index("idx_transaction_tags_transaction_id_tag_id", "transaction_id", "tag_id"),
    )


class AssetType(Base):
    __tablename__ = "asset_types"

    asset_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Gold", "Silver", "Platinum"
    unit_name: Mapped[str] = mapped_column(String(50), nullable=False)  # "grams", "kilograms", "ounces"
    unit_symbol: Mapped[str] = mapped_column(String(10), nullable=False)  # "g", "kg", "oz"
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="asset_types")
    physical_assets = relationship("PhysicalAsset", back_populates="asset_type")

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_asset_type_name"),
        Index("idx_asset_types_ledger_id", "ledger_id"),
    )


class PhysicalAsset(Base):
    __tablename__ = "physical_assets"

    physical_asset_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    asset_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("asset_types.asset_type_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "My Gold Collection"
    total_quantity: Mapped[Decimal] = mapped_column(
        Numeric(15, 6), default=0, nullable=False
    )  # Total units owned
    average_cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )  # Average cost per unit
    latest_price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )  # Manual latest price
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When price was last updated
    current_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )  # Auto-calculated: quantity * latest_price
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="physical_assets")
    asset_type = relationship("AssetType", back_populates="physical_assets")
    asset_transactions = relationship(
        "AssetTransaction", back_populates="physical_asset"
    )

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_physical_asset_name"),
        Index("idx_physical_assets_ledger_id", "ledger_id"),
        Index("idx_physical_assets_asset_type_id", "asset_type_id"),
    )


class AssetTransaction(Base):
    __tablename__ = "asset_transactions"

    asset_transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    physical_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("physical_assets.physical_asset_id"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        Enum("buy", "sell", name="asset_transaction_type"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)
    financial_transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transactions.transaction_id"), nullable=False
    )
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="asset_transactions")
    physical_asset = relationship("PhysicalAsset", back_populates="asset_transactions")
    account = relationship("Account", back_populates="asset_transactions")
    financial_transaction = relationship("Transaction")


class Amc(Base):
    __tablename__ = "amcs"

    amc_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "HDFC", "ICICI", "SBI"
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="amcs")
    mutual_funds = relationship("MutualFund", back_populates="amc")

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_amc_name"),
        Index("idx_amcs_ledger_id", "ledger_id"),
    )


class MutualFund(Base):
    __tablename__ = "mutual_funds"

    mutual_fund_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    amc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("amcs.amc_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "HDFC Mid Cap Fund"
    plan: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "Direct Growth", "Regular Reinvestment"
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Unique code for the fund
    owner: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Owner name (optional)
    total_units: Mapped[Decimal] = mapped_column(
        Numeric(15, 3), default=0, nullable=False
    )  # Balance units held (3 decimal places)
    average_cost_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), default=0, nullable=False
    )  # Average cost per unit
    latest_nav: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )  # Latest NAV price (2 decimal places)
    last_nav_update: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # When NAV was last updated
    current_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )  # Auto-calculated: total_units * latest_nav
    total_realized_gain: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), default=0, nullable=False
    )  # Cumulative realized gains from sales/switches
    total_invested_cash: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), default=0, nullable=False
    )  # Total cost basis of units currently held in this fund (including switches)
    external_cash_invested: Mapped[Decimal] = mapped_column(
        Numeric(15, 4), default=0, nullable=False
    )  # Total cash invested from external sources (excluding switches)
    asset_class: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Equity, Debt, Hybrid, Others
    asset_sub_class: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Sub-classification within asset class
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="mutual_funds")
    amc = relationship("Amc", back_populates="mutual_funds")
    mf_transactions = relationship(
        "MfTransaction", foreign_keys="[MfTransaction.mutual_fund_id]", back_populates="mutual_fund"
    )
    target_fund_transactions = relationship(
        "MfTransaction", foreign_keys="[MfTransaction.target_fund_id]", back_populates="target_fund"
    )

    __table_args__ = (
        Index("idx_mutual_funds_ledger_id", "ledger_id"),
        Index("idx_mutual_funds_amc_id", "amc_id"),
    )


class MfTransaction(Base):
    __tablename__ = "mf_transactions"

    mf_transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_id: Mapped[int] = mapped_column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    mutual_fund_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mutual_funds.mutual_fund_id"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        Enum("buy", "sell", "switch_out", "switch_in", name="mf_transaction_type"),
        nullable=False,
    )
    units: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    nav_per_unit: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount_excluding_charges: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    other_charges: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    account_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=True)
    target_fund_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mutual_funds.mutual_fund_id"), nullable=True)
    financial_transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.transaction_id"), nullable=True
    )
    linked_charge_transaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("transactions.transaction_id"), nullable=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    linked_transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    realized_gain: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    cost_basis_of_units_sold: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    ledger = relationship("Ledger", back_populates="mf_transactions")
    mutual_fund = relationship("MutualFund", foreign_keys=[mutual_fund_id], back_populates="mf_transactions")
    account = relationship("Account", back_populates="mf_transactions")
    target_fund = relationship("MutualFund", foreign_keys=[target_fund_id], back_populates="target_fund_transactions")
    financial_transaction = relationship("Transaction", foreign_keys=[financial_transaction_id])
    linked_charge_transaction = relationship("Transaction", foreign_keys=[linked_charge_transaction_id])

    __table_args__ = (
        Index("idx_mf_transactions_ledger_id", "ledger_id"),
        Index("idx_mf_transactions_mutual_fund_id", "mutual_fund_id"),
        Index("idx_mf_transactions_account_id", "account_id"),
        Index("idx_mf_transactions_target_fund_id", "target_fund_id"),
        Index("idx_mf_transactions_date", "transaction_date"),
        Index("idx_mf_transactions_financial_transaction_id", "financial_transaction_id"),
        Index("idx_mf_transactions_linked_charge_transaction_id", "linked_charge_transaction_id"),
    )
