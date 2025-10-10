-- Add nav_service_type and api_key columns to ledgers table
ALTER TABLE ledgers ADD COLUMN nav_service_type VARCHAR(10) NOT NULL DEFAULT 'india' CHECK (nav_service_type IN ('india', 'uk'));
ALTER TABLE ledgers ADD COLUMN api_key VARCHAR(100) NULL;