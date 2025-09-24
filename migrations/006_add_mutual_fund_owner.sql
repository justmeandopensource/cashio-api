-- Migration: Add owner column to mutual_funds table
-- Description: Adds optional owner field to allow same fund names for different owners
-- Date: 2025-09-24
-- Risk: LOW - Adds new nullable column and updates constraint

-- Add owner column to mutual_funds table
ALTER TABLE mutual_funds
ADD COLUMN IF NOT EXISTS owner VARCHAR(100);

-- Add comment for documentation
COMMENT ON COLUMN mutual_funds.owner IS 'Owner name (optional) - allows same fund names for different owners';

-- Drop existing unique constraint
ALTER TABLE mutual_funds DROP CONSTRAINT IF EXISTS uq_ledger_mutual_fund_name;

-- Create new unique constraint that allows same names with different owners
-- Using COALESCE to treat NULL owners as empty string for uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS idx_mutual_funds_ledger_name_owner 
ON mutual_funds (ledger_id, name, COALESCE(owner, ''));
