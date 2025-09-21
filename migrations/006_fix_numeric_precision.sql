-- Fix numeric precision for mutual fund financial fields to prevent rounding errors
ALTER TABLE mutual_funds ALTER COLUMN average_cost_per_unit TYPE numeric(15,4);
ALTER TABLE mutual_funds ALTER COLUMN total_realized_gain TYPE numeric(15,4);
ALTER TABLE mutual_funds ALTER COLUMN total_invested_cash TYPE numeric(15,4);
ALTER TABLE mutual_funds ALTER COLUMN external_cash_invested TYPE numeric(15,4);