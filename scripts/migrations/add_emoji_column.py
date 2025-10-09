#!/usr/bin/env python3
"""
Database migration to add emoji column to partmodel table.

This migration adds support for storing emoji characters on parts,
which can be used for visual representation in printer labels when
no image is available or as an additional visual element.

Usage:
    python scripts/migrations/add_emoji_column.py
"""

import sqlite3
import os
from pathlib import Path


def get_database_path() -> str:
    """Get the path to the makermatrix.db database."""
    # Get the project root directory (where makermatrix.db should be)
    current_dir = Path(__file__).resolve()
    project_root = current_dir.parent.parent.parent
    db_path = project_root / "makermatrix.db"

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    return str(db_path)


def add_emoji_column():
    """Add emoji column to partmodel table."""
    db_path = get_database_path()
    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(partmodel)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'emoji' in columns:
            print("✓ emoji column already exists, skipping migration")
            return

        # Add the column
        print("Adding emoji column to partmodel table...")
        cursor.execute("""
            ALTER TABLE partmodel
            ADD COLUMN emoji VARCHAR(50)
        """)

        conn.commit()
        print("✓ Successfully added emoji column")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(partmodel)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'emoji' in columns:
            print("✓ Verified emoji column exists in table")
        else:
            raise Exception("Failed to add emoji column")

    except Exception as e:
        conn.rollback()
        print(f"✗ Error adding emoji column: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add emoji column to partmodel")
    print("=" * 60)
    add_emoji_column()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
