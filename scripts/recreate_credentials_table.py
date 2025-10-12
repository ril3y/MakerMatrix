#!/usr/bin/env python3
"""
Recreate Supplier Credentials Table

This script drops the old encrypted supplier_credentials table and creates
a new simplified table for plain text storage.

IMPORTANT: This will delete any existing credentials in the database!
Run migrate_credentials_to_database.py afterwards to restore credentials from .env.

Usage:
    python scripts/recreate_credentials_table.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import MakerMatrix modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, text
from MakerMatrix.database.db import engine, create_db_and_tables


def recreate_credentials_table():
    """Drop old encrypted credentials table and create new plain text table"""

    print("=" * 70)
    print("Recreate Supplier Credentials Table")
    print("=" * 70)
    print()

    with Session(engine) as session:
        # Check if table exists
        result = session.exec(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='supplier_credentials'"
        ))
        table_exists = result.first() is not None

        if table_exists:
            print("✓ Found existing supplier_credentials table")

            # Check if it has data
            result = session.exec(text("SELECT COUNT(*) FROM supplier_credentials"))
            count = result.first()

            if count and count[0] > 0:
                print(f"⚠️  WARNING: Table contains {count[0]} credentials!")
                print("   These will be DELETED when the table is dropped.")
                print()
                response = input("Continue? (yes/no): ")
                if response.lower() != "yes":
                    print("Aborted.")
                    return False
            else:
                print("✓ Table is empty")

            print()
            print("Dropping old supplier_credentials table...")
            session.exec(text("DROP TABLE IF EXISTS supplier_credentials"))
            session.commit()
            print("✓ Old table dropped")
        else:
            print("✓ No existing supplier_credentials table found")

        print()
        print("Creating new supplier_credentials table...")

        # Recreate all tables (will only create missing ones)
        create_db_and_tables()

        print("✓ New table created with simplified schema")

    print()
    print("=" * 70)
    print("✓ Table recreated successfully!")
    print()
    print("Next steps:")
    print("  1. Run: python scripts/migrate_credentials_to_database.py --dry-run")
    print("  2. Run: python scripts/migrate_credentials_to_database.py")
    print("  3. Test supplier connections")
    print()

    return True


def main():
    try:
        success = recreate_credentials_table()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Failed to recreate table: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
