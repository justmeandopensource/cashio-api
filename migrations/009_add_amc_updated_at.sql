-- Migration: Add updated_at column to amcs table
-- Description: Adds updated_at timestamp field to AMC table for tracking modifications
-- Date: 2025-10-11
-- Risk: LOW - Adds new column with default value

-- Add updated_at column to amcs table
ALTER TABLE amcs
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add comment for documentation
COMMENT ON COLUMN amcs.updated_at IS 'Timestamp when the AMC was last updated';