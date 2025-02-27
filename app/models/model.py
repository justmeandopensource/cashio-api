from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Enum,
    Boolean,
    UUID,
    ForeignKey,
    UniqueConstraint
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
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    name = Column(String(100), nullable=False)
    currency_symbol = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="ledgers")
    accounts = relationship("Account", back_populates="ledger")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_ledger_name'),
    )

class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True)
    ledger_id = Column(Integer, ForeignKey('ledgers.ledger_id'), nullable=False)
    parent_account_id = Column(Integer, ForeignKey('accounts.account_id'), nullable=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum('asset', 'liability', name='account_type'), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    opening_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    net_balance = Column(Numeric(15, 2), default=0.00, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    ledger = relationship("Ledger", back_populates="accounts")
    parent_account = relationship("Account", remote_side=[account_id], back_populates="child_accounts")
    child_accounts = relationship("Account", back_populates="parent_account")
    transactions = relationship("Transaction", back_populates="account")

    __table_args__ = (
        UniqueConstraint('ledger_id', 'name', name='uq_ledger_account_name'),
    )

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    parent_category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum('income', 'expense', name='category_type'), nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="categories")
    parent_category = relationship("Category", remote_side=[category_id], back_populates="child_categories")
    child_categories = relationship("Category", back_populates="parent_category")

    __table_args__ = (
        UniqueConstraint('parent_category_id', 'name', name='uq_parent_category_name'),
    )

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.account_id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=True)
    credit = Column(Numeric(15, 2), default=0.00, nullable=False)
    debit = Column(Numeric(15, 2), default=0.00, nullable=False)
    date = Column(DateTime, nullable=False)
    notes = Column(String(500), nullable=True)
    is_split = Column(Boolean, default=False, nullable=False)
    is_transfer = Column(Boolean, default=False, nullable=False)
    transfer_id = Column(UUID, nullable=True)
    transfer_type = Column(Enum('source', 'destination', name='transfer_type'), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category")
    splits = relationship("TransactionSplit", back_populates="transaction", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="transaction_tags", back_populates="transactions")

class TransactionSplit(Base):
    __tablename__ = "transaction_splits"

    split_id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=False)
    credit = Column(Numeric(15, 2), default=0.00, nullable=False)
    debit = Column(Numeric(15, 2), default=0.00, nullable=False)
    notes = Column(String(500), nullable=True)

    transaction = relationship("Transaction", back_populates="splits")
    category = relationship("Category")

class Tag(Base):
    __tablename__ = "tags"

    tag_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code (e.g., #FF5733)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="tags")
    
    transactions = relationship(
        "Transaction",
        secondary="transaction_tags",
        back_populates="tags"
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )

class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.transaction_id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.tag_id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('transaction_id', 'tag_id', name='uq_transaction_tag'),
    )
