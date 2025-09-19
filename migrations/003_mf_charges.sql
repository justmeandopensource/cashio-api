-- Migration: Add support for other charges in MF transactions
-- Description: Adds columns for amount_excluding_charges, other_charges, and linked_charge_transaction_id to support charges in buy/sell transactions
-- Date: 2025-09-19
-- Risk: LOW - Adds new columns with backward compatibility

-- Add new columns to mf_transactions table
ALTER TABLE mf_transactions
ADD COLUMN IF NOT EXISTS amount_excluding_charges DECIMAL(15,2),
ADD COLUMN IF NOT EXISTS other_charges DECIMAL(15,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS linked_charge_transaction_id INTEGER REFERENCES transactions(transaction_id);

-- Update existing records to set amount_excluding_charges = total_amount for backward compatibility
UPDATE mf_transactions
SET amount_excluding_charges = total_amount
WHERE amount_excluding_charges IS NULL;

-- Ensure other_charges is 0 for existing records
UPDATE mf_transactions
SET other_charges = 0
WHERE other_charges IS NULL;

-- Make amount_excluding_charges NOT NULL after populating existing data
ALTER TABLE mf_transactions
ALTER COLUMN amount_excluding_charges SET NOT NULL,
ALTER COLUMN other_charges SET NOT NULL;

-- Create index for the new foreign key
CREATE INDEX IF NOT EXISTS idx_mf_transactions_linked_charge_transaction_id ON mf_transactions(linked_charge_transaction_id);