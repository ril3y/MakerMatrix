#!/usr/bin/env python3
"""
Migration script to add smart location fields to locationmodel table

Adds the following fields to existing production database:
- is_mobile (bool)
- container_capacity (int)
- is_smart_location (bool)
- smart_device_id (str)
- smart_slot_number (int)
- smart_capabilities (json)
- auto_created (bool)
- hidden_by_default (bool)
- is_connected (bool)
- last_seen (datetime)
- firmware_version (str)
"""

import sqlite3
import sys
from pathlib import Path

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database(db_path="makermatrix.db"):
    """Add missing columns to locationmodel table"""

    print(f"🔧 Migrating database: {db_path}")

    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # List of columns to add with their SQLite type and default
        new_columns = [
            ("is_mobile", "BOOLEAN", "0"),
            ("container_capacity", "INTEGER", "NULL"),
            ("is_smart_location", "BOOLEAN", "0"),
            ("smart_device_id", "VARCHAR", "NULL"),
            ("smart_slot_number", "INTEGER", "NULL"),
            ("smart_capabilities", "JSON", "NULL"),
            ("auto_created", "BOOLEAN", "0"),
            ("hidden_by_default", "BOOLEAN", "0"),
            ("is_connected", "BOOLEAN", "0"),
            ("last_seen", "DATETIME", "NULL"),
            ("firmware_version", "VARCHAR", "NULL"),
        ]

        # Check and add missing columns
        columns_added = []
        columns_skipped = []

        for column_name, column_type, default_value in new_columns:
            if check_column_exists(cursor, "locationmodel", column_name):
                columns_skipped.append(column_name)
                print(f"  ✓ Column already exists: {column_name}")
            else:
                # Add the column
                alter_sql = f"ALTER TABLE locationmodel ADD COLUMN {column_name} {column_type}"
                if default_value != "NULL":
                    alter_sql += f" DEFAULT {default_value}"

                cursor.execute(alter_sql)
                columns_added.append(column_name)
                print(f"  ✅ Added column: {column_name} ({column_type})")

        # Commit changes
        conn.commit()

        # Print summary
        print(f"\n📊 Migration Summary:")
        print(f"  • Columns added: {len(columns_added)}")
        print(f"  • Columns skipped (already exist): {len(columns_skipped)}")

        if columns_added:
            print(f"\n✅ Migration completed successfully!")
            print(f"  Added columns: {', '.join(columns_added)}")
        else:
            print(f"\n✅ Database schema is up to date!")

        # Close connection
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "makermatrix.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
