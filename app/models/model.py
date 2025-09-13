from datetime import datetime, timezone

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    ledgers = relationship("Ledger", back_populates="user")
    categories = relationship("Category", back_populates="user")
    tags = relationship("Tag", back_populates="user")


class Ledger(Base):
    __tablename__ = "ledgers"

    ledger_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(100), nullable=True)
    currency_symbol = Column(String(10), nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="ledgers")
    accounts = relationship("Account", back_populates="ledger")
    asset_types = relationship("AssetType", back_populates="ledger")
    physical_assets = relationship("PhysicalAsset", back_populates="ledger")
    asset_transactions = relationship("AssetTransaction", back_populates="ledger")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_ledger_name"),)


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    parent_account_id = Column(
        Integer, ForeignKey("accounts.account_id"), nullable=True
    )
    name = Column(String(100), nullable=False)
    description = Column(String(100), nullable=True)
    type = Column(Enum("asset", "liability", name="account_type"), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    opening_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    net_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="accounts")
    parent_account = relationship(
        "Account", remote_side=[account_id], back_populates="child_accounts"
    )
    child_accounts = relationship("Account", back_populates="parent_account")
    transactions = relationship("Transaction", back_populates="account")
    asset_transactions = relationship("AssetTransaction", back_populates="account")

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_account_name"),
    )


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    parent_category_id = Column(
        Integer, ForeignKey("categories.category_id"), nullable=True
    )
    name = Column(String(100), nullable=False)
    type = Column(Enum("income", "expense", name="category_type"), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)

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

    transaction_id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.account_id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=True)
    credit = Column(Numeric(15, 2), default=0.00, nullable=False)
    debit = Column(Numeric(15, 2), default=0.00, nullable=False)
    date = Column(DateTime, nullable=False)
    notes = Column(String(500), nullable=True)
    is_split = Column(Boolean, default=False, nullable=False)
    is_transfer = Column(Boolean, default=False, nullable=False)
    is_asset_transaction = Column(Boolean, default=False, nullable=False)
    transfer_id = Column(UUID, nullable=True)
    transfer_type = Column(
        Enum("source", "destination", name="transfer_type"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

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

    split_id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.transaction_id"), nullable=False
    )
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
    credit = Column(Numeric(15, 2), default=0.00, nullable=False)
    debit = Column(Numeric(15, 2), default=0.00, nullable=False)
    notes = Column(String(500), nullable=True)

    transaction = relationship("Transaction", back_populates="splits")
    category = relationship("Category")


class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    name = Column(String(50), nullable=False)

    user = relationship("User", back_populates="tags")

    transactions = relationship(
        "Transaction", secondary="transaction_tags", back_populates="tags"
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_tag_name"),)


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id = Column(
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

    asset_type_id = Column(Integer, primary_key=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    name = Column(String(100), nullable=False)  # "Gold", "Silver", "Platinum"
    unit_name = Column(String(50), nullable=False)  # "grams", "kilograms", "ounces"
    unit_symbol = Column(String(10), nullable=False)  # "g", "kg", "oz"
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="asset_types")
    physical_assets = relationship("PhysicalAsset", back_populates="asset_type")

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_ledger_asset_type_name"),
        Index("idx_asset_types_ledger_id", "ledger_id"),
    )


class PhysicalAsset(Base):
    __tablename__ = "physical_assets"

    physical_asset_id = Column(Integer, primary_key=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    asset_type_id = Column(
        Integer, ForeignKey("asset_types.asset_type_id"), nullable=False
    )
    name = Column(String(100), nullable=False)  # "My Gold Collection"
    total_quantity = Column(
        Numeric(15, 6), default=0, nullable=False
    )  # Total units owned
    average_cost_per_unit = Column(
        Numeric(15, 2), default=0, nullable=False
    )  # Average cost per unit
    latest_price_per_unit = Column(
        Numeric(15, 2), default=0, nullable=False
    )  # Manual latest price
    last_price_update = Column(DateTime, nullable=True)  # When price was last updated
    current_value = Column(
        Numeric(15, 2), default=0, nullable=False
    )  # Auto-calculated: quantity * latest_price
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

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

    asset_transaction_id = Column(Integer, primary_key=True)
    ledger_id = Column(Integer, ForeignKey("ledgers.ledger_id"), nullable=False)
    physical_asset_id = Column(
        Integer, ForeignKey("physical_assets.physical_asset_id"), nullable=False
    )
    transaction_type = Column(
        Enum("buy", "sell", name="asset_transaction_type"), nullable=False
    )
    quantity = Column(Numeric(15, 6), nullable=False)
    price_per_unit = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.account_id"), nullable=False)
    financial_transaction_id = Column(
        Integer, ForeignKey("transactions.transaction_id"), nullable=False
    )
    transaction_date = Column(DateTime, nullable=False)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="asset_transactions")
    physical_asset = relationship("PhysicalAsset", back_populates="asset_transactions")
    account = relationship("Account", back_populates="asset_transactions")
    financial_transaction = relationship("Transaction")

    __table_args__ = (
        Index("idx_asset_transactions_ledger_id", "ledger_id"),
        Index("idx_asset_transactions_asset_id", "physical_asset_id"),
        Index("idx_asset_transactions_account_id", "account_id"),
        Index("idx_asset_transactions_date", "transaction_date"),
    )
