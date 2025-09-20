-- Migration: Add plan and code columns to mutual_funds table
-- Description: Adds optional plan and code fields to store mutual fund plan type and unique code
-- Date: 2025-09-20
-- Risk: LOW - Adds new columns with default NULL values

-- Add plan column to mutual_funds table
ALTER TABLE mutual_funds
ADD COLUMN IF NOT EXISTS plan VARCHAR(50);

-- Add code column to mutual_funds table
ALTER TABLE mutual_funds
ADD COLUMN IF NOT EXISTS code VARCHAR(50);

-- Add comment for documentation
COMMENT ON COLUMN mutual_funds.plan IS 'Plan type (e.g., Direct Growth, Regular Reinvestment)';
COMMENT ON COLUMN mutual_funds.code IS 'Unique code for the mutual fund';