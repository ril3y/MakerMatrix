#!/usr/bin/env python
"""
Migration script to ensure datasheet URLs are properly stored in additional_properties.datasheet_url

This script will:
1. Find parts with datasheet URLs stored in nested locations
2. Move them to the standardized location: additional_properties.datasheet_url
3. Preserve the original data in case it's needed

Run with: python scripts/migrate_datasheet_urls.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from MakerMatrix.models.models import PartModel
from MakerMatrix.database.db import DATABASE_URL
import json
from datetime import datetime


def migrate_datasheet_urls():
    """Migrate datasheet URLs to standardized location"""

    # Create database connection
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all parts with additional_properties
        parts = session.query(PartModel).filter(PartModel.additional_properties != None).all()

        migrated_count = 0
        already_correct = 0
        no_datasheet = 0

        print(f"Checking {len(parts)} parts for datasheet URL migration...")

        for part in parts:
            if not part.additional_properties:
                continue

            additional_props = part.additional_properties
            modified = False

            # Check if datasheet_url already exists at root level
            if "datasheet_url" in additional_props and additional_props["datasheet_url"]:
                already_correct += 1
                continue

            # Look for datasheet URLs in various nested locations
            datasheet_url = None

            # Check supplier_data nested structure
            if "supplier_data" in additional_props:
                supplier_data = additional_props["supplier_data"]
                if isinstance(supplier_data, dict):
                    for supplier_key, supplier_info in supplier_data.items():
                        if isinstance(supplier_info, dict):
                            if "datasheet_url" in supplier_info and supplier_info["datasheet_url"]:
                                datasheet_url = supplier_info["datasheet_url"]
                                break
                            if "DataSheetUrl" in supplier_info and supplier_info["DataSheetUrl"]:
                                datasheet_url = supplier_info["DataSheetUrl"]
                                break

            # Check for LCSC-specific datasheet URL
            if not datasheet_url and "lcsc_datasheet_url" in additional_props:
                datasheet_url = additional_props["lcsc_datasheet_url"]

            # Check for other variations
            if not datasheet_url:
                datasheet_keys = ["DataSheetUrl", "datasheet_link", "datasheet", "pdf_url"]
                for key in datasheet_keys:
                    if key in additional_props and additional_props[key]:
                        datasheet_url = additional_props[key]
                        break

            # If we found a datasheet URL, migrate it
            if datasheet_url:
                print(f"  Migrating datasheet URL for part: {part.part_name} (ID: {part.id})")
                print(f"    URL: {datasheet_url}")

                # Store at the standardized location
                additional_props["datasheet_url"] = datasheet_url

                # Add migration metadata
                if "migration_history" not in additional_props:
                    additional_props["migration_history"] = []

                additional_props["migration_history"].append(
                    {
                        "migration": "datasheet_url_standardization",
                        "timestamp": datetime.utcnow().isoformat(),
                        "original_location": "nested or alternative key",
                        "new_location": "additional_properties.datasheet_url",
                    }
                )

                # Mark the part as modified
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(part, "additional_properties")

                migrated_count += 1
                modified = True
            else:
                no_datasheet += 1

        # Commit all changes
        if migrated_count > 0:
            session.commit()
            print(f"\n✅ Migration complete!")
        else:
            print(f"\n✅ No migration needed!")

        print(f"  - {migrated_count} parts migrated")
        print(f"  - {already_correct} parts already had correct datasheet_url location")
        print(f"  - {no_datasheet} parts have no datasheet URL")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        session.rollback()
        return False

    finally:
        session.close()


def check_datasheet_urls():
    """Check current state of datasheet URLs in the database"""

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all parts with additional_properties
        parts = session.query(PartModel).filter(PartModel.additional_properties != None).all()

        stats = {
            "total_parts": len(parts),
            "has_datasheet_url_root": 0,
            "has_datasheet_url_nested": 0,
            "has_lcsc_datasheet_url": 0,
            "has_other_datasheet_key": 0,
            "no_datasheet": 0,
        }

        for part in parts:
            if not part.additional_properties:
                stats["no_datasheet"] += 1
                continue

            additional_props = part.additional_properties

            # Check root level datasheet_url
            if "datasheet_url" in additional_props and additional_props["datasheet_url"]:
                stats["has_datasheet_url_root"] += 1
            # Check nested locations
            elif "supplier_data" in additional_props:
                has_nested = False
                supplier_data = additional_props["supplier_data"]
                if isinstance(supplier_data, dict):
                    for supplier_key, supplier_info in supplier_data.items():
                        if isinstance(supplier_info, dict):
                            if "datasheet_url" in supplier_info or "DataSheetUrl" in supplier_info:
                                stats["has_datasheet_url_nested"] += 1
                                has_nested = True
                                break

                if not has_nested:
                    # Check for other keys
                    if "lcsc_datasheet_url" in additional_props:
                        stats["has_lcsc_datasheet_url"] += 1
                    elif any(key in additional_props for key in ["DataSheetUrl", "datasheet_link", "datasheet"]):
                        stats["has_other_datasheet_key"] += 1
                    else:
                        stats["no_datasheet"] += 1
            else:
                # Check for other keys at root
                if "lcsc_datasheet_url" in additional_props:
                    stats["has_lcsc_datasheet_url"] += 1
                elif any(key in additional_props for key in ["DataSheetUrl", "datasheet_link", "datasheet"]):
                    stats["has_other_datasheet_key"] += 1
                else:
                    stats["no_datasheet"] += 1

        print("\n📊 Datasheet URL Statistics:")
        print(f"  Total parts: {stats['total_parts']}")
        print(f"  ✅ Correct location (additional_properties.datasheet_url): {stats['has_datasheet_url_root']}")
        print(f"  ⚠️  Nested in supplier_data: {stats['has_datasheet_url_nested']}")
        print(f"  ⚠️  Using lcsc_datasheet_url key: {stats['has_lcsc_datasheet_url']}")
        print(f"  ⚠️  Using other datasheet keys: {stats['has_other_datasheet_key']}")
        print(f"  ❌ No datasheet URL: {stats['no_datasheet']}")

        needs_migration = (
            stats["has_datasheet_url_nested"] + stats["has_lcsc_datasheet_url"] + stats["has_other_datasheet_key"]
        )

        if needs_migration > 0:
            print(f"\n⚠️  {needs_migration} parts need datasheet URL migration")
            return False
        else:
            print(f"\n✅ All parts have correct datasheet URL location!")
            return True

    finally:
        session.close()


if __name__ == "__main__":
    print("🔍 Checking current datasheet URL state...")
    needs_migration = not check_datasheet_urls()

    if needs_migration:
        print("\n🔧 Starting datasheet URL migration...")
        success = migrate_datasheet_urls()

        if success:
            print("\n🔍 Verifying migration results...")
            check_datasheet_urls()
    else:
        print("\n✅ No migration needed - all datasheet URLs are already in the correct location!")
