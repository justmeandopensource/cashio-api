-- Migration: Add Mutual Funds Tables and is_mf_transaction column
-- Description: Adds tables for managing mutual fund portfolios, including switch transactions and invested cash tracking
-- Date: 2025-09-14
-- Risk: LOW - Adds new tables and columns

-- Create amcs table (Asset Management Companies)
CREATE TABLE IF NOT EXISTS amcs (
    amc_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    name VARCHAR(100) NOT NULL, -- "HDFC", "ICICI", "SBI"
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create mutual_funds table
CREATE TABLE IF NOT EXISTS mutual_funds (
    mutual_fund_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    amc_id INTEGER NOT NULL REFERENCES amcs(amc_id),
    name VARCHAR(100) NOT NULL, -- "HDFC Mid Cap Fund", "ICICI Prudential Bluechip Fund"
    total_units DECIMAL(15,3) DEFAULT 0, -- Balance units held (3 decimal places)
    average_cost_per_unit DECIMAL(15,2) DEFAULT 0, -- Average cost per unit
    latest_nav DECIMAL(15,2) DEFAULT 0, -- Latest NAV price (2 decimal places)
    last_nav_update TIMESTAMP NULL, -- When NAV was last updated
    current_value DECIMAL(15,2) DEFAULT 0, -- Auto-calculated: total_units * latest_nav
    total_realized_gain DECIMAL(15,2) DEFAULT 0, -- Cumulative realized gains from sales/switches
    total_invested_cash DECIMAL(15,2) DEFAULT 0, -- Total cash invested in this fund (excluding switches)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create enum type for MF transaction types (if not exists)
DO $$ BEGIN
    CREATE TYPE mf_transaction_type AS ENUM ('buy', 'sell', 'switch_out', 'switch_in');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create mf_transactions table
CREATE TABLE IF NOT EXISTS mf_transactions (
    mf_transaction_id SERIAL PRIMARY KEY,
    ledger_id INTEGER NOT NULL REFERENCES ledgers(ledger_id),
    mutual_fund_id INTEGER NOT NULL REFERENCES mutual_funds(mutual_fund_id),
    transaction_type mf_transaction_type NOT NULL, -- "buy", "sell", "switch_out", "switch_in"
    units DECIMAL(15,3) NOT NULL,
    nav_per_unit DECIMAL(15,2) NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    account_id INTEGER REFERENCES accounts(account_id),
    target_fund_id INTEGER REFERENCES mutual_funds(mutual_fund_id),
    financial_transaction_id INTEGER REFERENCES transactions(transaction_id),
    transaction_date TIMESTAMP NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linked_transaction_id INTEGER, -- To link switch_out and switch_in transactions
    realized_gain DECIMAL(15,2),
    cost_basis_of_units_sold DECIMAL(15,2)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_amcs_ledger_id ON amcs(ledger_id);
CREATE INDEX IF NOT EXISTS idx_mutual_funds_ledger_id ON mutual_funds(ledger_id);
CREATE INDEX IF NOT EXISTS idx_mutual_funds_amc_id ON mutual_funds(amc_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_ledger_id ON mf_transactions(ledger_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_mutual_fund_id ON mf_transactions(mutual_fund_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_account_id ON mf_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_target_fund_id ON mf_transactions(target_fund_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_date ON mf_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_financial_transaction_id ON mf_transactions(financial_transaction_id);
CREATE INDEX IF NOT EXISTS idx_mf_transactions_linked_transaction_id ON mf_transactions (linked_transaction_id);

-- Create unique constraints
DO $$ BEGIN
    ALTER TABLE amcs ADD CONSTRAINT uq_ledger_amc_name UNIQUE(ledger_id, name);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    ALTER TABLE mutual_funds ADD CONSTRAINT uq_ledger_mutual_fund_name UNIQUE(ledger_id, name);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add is_mf_transaction column to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS is_mf_transaction BOOLEAN DEFAULT FALSE NOT NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_transactions_is_mf_transaction ON transactions(is_mf_transaction);

-- Update existing MF transactions to set is_mf_transaction = true
-- This ensures existing MF transactions are properly flagged
UPDATE transactions
SET is_mf_transaction = TRUE
WHERE transaction_id IN (
    SELECT financial_transaction_id
    FROM mf_transactions
);