-- Migration: Add store and location columns to transactions table
-- Description: Adds optional store and location fields to transactions for better categorization
-- Date: 2025-10-12
-- Risk: LOW - Adds new nullable columns

-- Add store column to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS store VARCHAR(200);

-- Add location column to transactions table
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS location VARCHAR(200);

-- Add comments for documentation
COMMENT ON COLUMN transactions.store IS 'Optional store name where the transaction occurred';
COMMENT ON COLUMN transactions.location IS 'Optional location where the transaction occurred';