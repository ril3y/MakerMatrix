#!/usr/bin/env python3
"""
Update database schema to include supplier_part_number field
"""

import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MakerMatrix'))

from MakerMatrix.models.models import engine
from MakerMatrix.database.db import create_db_and_tables
from sqlmodel import SQLModel

def update_database_schema():
    """Update database schema with new supplier_part_number field"""
    print("🔄 Updating database schema...")
    print("=" * 50)
    
    try:
        print("📝 Recreating database tables with new schema...")
        
        # Drop all tables and recreate with new schema
        SQLModel.metadata.drop_all(engine)
        create_db_and_tables()
        
        print("✅ Database schema updated successfully!")
        print("   - Added supplier_part_number field to PartModel")
        print("   - All tables recreated with new schema")
        
        print("\n💡 Next steps:")
        print("   1. Re-import your CSV files")
        print("   2. supplier_part_number will be populated correctly")
        print("   3. Enrichment will use supplier_part_number field")
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🏁 Schema update completed!")
    return True

if __name__ == "__main__":
    update_database_schema()