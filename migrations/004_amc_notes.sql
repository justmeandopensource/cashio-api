-- Migration: Rename AMC description column to notes
-- Description: Renames the description column to notes in the amcs table to match the MutualFund table structure
-- Date: 2025-09-20
-- Risk: LOW - Only renames a column, preserves data

-- Check if description column exists and rename it to notes
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'amcs' AND column_name = 'description') THEN
        ALTER TABLE amcs RENAME COLUMN description TO notes;
    END IF;
END $$;

-- If notes column doesn't exist, add it
ALTER TABLE amcs ADD COLUMN IF NOT EXISTS notes VARCHAR(500);