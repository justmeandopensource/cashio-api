-- Migration: Add asset_class and asset_sub_class columns to mutual_funds table
-- Description: Adds optional asset classification fields for mutual funds
-- Date: 2025-10-03
-- Risk: LOW - Adds new nullable columns

-- Add asset_class column to mutual_funds table
ALTER TABLE mutual_funds
ADD COLUMN IF NOT EXISTS asset_class VARCHAR(50);

-- Add asset_sub_class column to mutual_funds table
ALTER TABLE mutual_funds
ADD COLUMN IF NOT EXISTS asset_sub_class VARCHAR(50);

-- Add comments for documentation
COMMENT ON COLUMN mutual_funds.asset_class IS 'Asset class (Equity, Debt, Hybrid, Others)';
COMMENT ON COLUMN mutual_funds.asset_sub_class IS 'Asset sub-class (e.g., large cap, mid cap for equity)';