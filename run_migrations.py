#!/usr/bin/env python3
"""
Migration Runner Script
Runs SQL migration files in order against the database.
"""

import os
import sys
from pathlib import Path
from app.database.connection import engine
from sqlalchemy import text


def run_migrations():
    """Run all migration files in order."""
    migrations_dir = Path(__file__).parent / "migrations"

    if not migrations_dir.exists():
        print("Migrations directory not found!")
        return

    # Get all SQL files and sort them by filename
    migration_files = sorted([f for f in migrations_dir.glob("*.sql")])

    if not migration_files:
        print("No migration files found!")
        return

    print(f"Found {len(migration_files)} migration files")

    with engine.connect() as conn:
        for migration_file in migration_files:
            print(f"Running migration: {migration_file.name}")

            try:
                # Read the SQL file
                with open(migration_file, 'r') as f:
                    sql_content = f.read()

                # Execute the entire file as one batch
                conn.execute(text(sql_content))
                conn.commit()
                print(f"✓ Migration {migration_file.name} completed successfully")

            except Exception as e:
                error_msg = str(e)
                # Check if it's a "already exists" type error, which we can ignore
                if any(keyword in error_msg.lower() for keyword in [
                    'already exists', 'duplicate', 'relation', 'constraint'
                ]):
                    print(f"⚠ Migration {migration_file.name} already applied (skipping)")
                    conn.rollback()  # Reset transaction state
                else:
                    print(f"✗ Error running migration {migration_file.name}: {e}")
                    conn.rollback()
                    sys.exit(1)

    print("All migrations completed successfully!")


if __name__ == "__main__":
    run_migrations()