"""
Migration: Add encryption_password column to backup_config table

This adds the encryption_password field to store passwords for scheduled backups.
"""

import sqlite3
from pathlib import Path

def run_migration():
    """Add encryption_password column to backup_config table"""
    # Get database path - try multiple locations
    possible_paths = [
        Path(__file__).parent.parent.parent / "makers_matrix.db",
        Path(__file__).parent.parent.parent / "makermatrix.db",
        Path("/home/ril3y/MakerMatrix/makermatrix.db"),
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if not db_path:
        print("Database not found in any expected location")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(backup_config)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'encryption_password' not in columns:
            print("Adding encryption_password column to backup_config table...")
            cursor.execute("""
                ALTER TABLE backup_config
                ADD COLUMN encryption_password TEXT
            """)
            conn.commit()
            print("✓ Migration completed successfully")
        else:
            print("✓ Column already exists, skipping migration")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False

if __name__ == "__main__":
    run_migration()
