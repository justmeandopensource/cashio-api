-- Migration: Add Physical Assets Tables and is_asset_transaction column
-- Description: Adds tables for managing physical assets
-- Date: 2025-01-10
-- Risk: LOW - Adds new tables

-- Create asset_types table
CREATE TABLE IF NOT EXISTS asset_types (
    asset_type_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    name VARCHAR(100) NOT NULL, -- "Gold", "Silver", "Platinum"
    unit_name VARCHAR(50) NOT NULL, -- "grams", "kilograms", "ounces"
    unit_symbol VARCHAR(10) NOT NULL, -- "g", "kg", "oz"
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create physical_assets table
CREATE TABLE IF NOT EXISTS physical_assets (
    physical_asset_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    asset_type_id INTEGER NOT NULL REFERENCES asset_types(asset_type_id),
    name VARCHAR(100) NOT NULL, -- "My Gold Collection"
    total_quantity DECIMAL(15,6) DEFAULT 0, -- Total units owned
    average_cost_per_unit DECIMAL(15,2) DEFAULT 0, -- Average cost per unit
    latest_price_per_unit DECIMAL(15,2) DEFAULT 0, -- Manual latest price
    last_price_update TIMESTAMP NULL, -- When price was last updated
    current_value DECIMAL(15,2) DEFAULT 0, -- Auto-calculated: quantity * latest_price
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create enum type for asset transaction types (if not exists)
DO $$ BEGIN
    CREATE TYPE asset_transaction_type AS ENUM ('buy', 'sell');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create asset_transactions table
CREATE TABLE IF NOT EXISTS asset_transactions (
    asset_transaction_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    physical_asset_id INTEGER NOT NULL REFERENCES physical_assets(physical_asset_id),
    transaction_type asset_transaction_type NOT NULL, -- "buy", "sell"
    quantity DECIMAL(15,6) NOT NULL,
    price_per_unit DECIMAL(15,2) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    financial_transaction_id INTEGER NOT NULL REFERENCES transactions(transaction_id),
    transaction_date TIMESTAMP NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_asset_types_ledger_id ON asset_types(ledger_id);
CREATE INDEX IF NOT EXISTS idx_physical_assets_ledger_id ON physical_assets(ledger_id);
CREATE INDEX IF NOT EXISTS idx_physical_assets_asset_type_id ON physical_assets(asset_type_id);
CREATE INDEX IF NOT EXISTS idx_asset_transactions_ledger_id ON asset_transactions(ledger_id);
CREATE INDEX IF NOT EXISTS idx_asset_transactions_asset_id ON asset_transactions(physical_asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_transactions_account_id ON asset_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_asset_transactions_date ON asset_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_asset_transactions_financial_transaction_id ON asset_transactions(financial_transaction_id);

-- Create unique constraints
DO $$ BEGIN
    ALTER TABLE asset_types ADD CONSTRAINT uq_ledger_asset_type_name UNIQUE(ledger_id, name);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE physical_assets ADD CONSTRAINT uq_ledger_physical_asset_name UNIQUE(ledger_id, name);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Update asset_transactions to use enum (if not already using it)
-- Note: This is handled in the SQLAlchemy model, so we don't need to alter the table structure

-- Add is_asset_transaction column to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS is_asset_transaction BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_transactions_is_asset_transaction ON transactions(is_asset_transaction);

-- Update existing asset transactions to set is_asset_transaction = true
-- This ensures existing asset transactions are properly flagged
UPDATE transactions
SET is_asset_transaction = TRUE
WHERE transaction_id IN (
    SELECT financial_transaction_id
    FROM asset_transactions
);
