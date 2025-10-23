#!/usr/bin/env python3
"""
Database Migration: Add product_url column to PartModel

This migration adds a new 'product_url' column to the partmodel table to store
specific product page URLs separately from the supplier homepage URL.

Usage:
    python scripts/migrations/add_product_url_column.py
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def migrate():
    """Add product_url column to partmodel table"""

    # Default database path
    db_path = Path(__file__).parent.parent.parent / "makermatrix.db"

    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        sys.exit(1)

    print(f"📊 Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(partmodel)")
        columns = [column[1] for column in cursor.fetchall()]

        if "product_url" in columns:
            print("✅ Column 'product_url' already exists. Migration not needed.")
            return

        # Add the new column
        print("➕ Adding 'product_url' column to partmodel table...")
        cursor.execute(
            """
            ALTER TABLE partmodel
            ADD COLUMN product_url TEXT
        """
        )

        conn.commit()
        print("✅ Migration completed successfully!")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(partmodel)")
        columns = [column[1] for column in cursor.fetchall()]
        if "product_url" in columns:
            print("✅ Verified: 'product_url' column exists in partmodel table")
        else:
            print("❌ Warning: Could not verify column was added")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add product_url column")
    print("=" * 60)
    migrate()
    print("=" * 60)
