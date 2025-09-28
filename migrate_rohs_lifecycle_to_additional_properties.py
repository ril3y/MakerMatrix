#!/usr/bin/env python3
"""
Migration Script: Move RoHS and Lifecycle Status to Additional Properties

This script moves rohs_status and lifecycle_status from the core PartModel fields
to the additional_properties JSON field to keep the core model clean and simple.

Usage:
    python migrate_rohs_lifecycle_to_additional_properties.py [--dry-run]

Options:
    --dry-run    Show what would be migrated without making changes
"""

import sys
import json
import argparse
from pathlib import Path

# Add MakerMatrix to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session
from MakerMatrix.models.models import engine
from MakerMatrix.models.part_models import PartModel
from sqlalchemy import text


def migrate_rohs_lifecycle_data(dry_run=False):
    """
    Move rohs_status and lifecycle_status from columns to additional_properties JSON field

    Args:
        dry_run (bool): If True, only show what would be migrated without making changes
    """

    with Session(engine) as session:
        print("🔍 Scanning for parts with rohs_status or lifecycle_status...")

        # Query parts that have rohs_status or lifecycle_status set
        parts_to_migrate = session.execute(
            text("""
                SELECT id, part_name, rohs_status, lifecycle_status, additional_properties
                FROM partmodel
                WHERE rohs_status IS NOT NULL OR lifecycle_status IS NOT NULL
            """)
        ).fetchall()

        if not parts_to_migrate:
            print("✅ No parts found with rohs_status or lifecycle_status. Migration not needed.")
            return

        print(f"📊 Found {len(parts_to_migrate)} parts to migrate:")

        migration_count = 0

        for part_row in parts_to_migrate:
            part_id, part_name, rohs_status, lifecycle_status, additional_properties_json = part_row

            # Parse existing additional_properties or create empty dict
            try:
                additional_properties = json.loads(additional_properties_json) if additional_properties_json else {}
            except (json.JSONDecodeError, TypeError):
                additional_properties = {}

            # Prepare the electronic component data to add
            electronic_data = {}
            if rohs_status:
                electronic_data['rohs_status'] = rohs_status
            if lifecycle_status:
                electronic_data['lifecycle_status'] = lifecycle_status

            if electronic_data:
                # Add electronic component data to additional_properties
                if 'electronic_component' not in additional_properties:
                    additional_properties['electronic_component'] = {}

                additional_properties['electronic_component'].update(electronic_data)

                print(f"  📦 {part_name[:50]:<50} -> RoHS: {rohs_status or 'None':<15} Lifecycle: {lifecycle_status or 'None'}")

                if not dry_run:
                    # Update the database
                    session.execute(
                        text("""
                            UPDATE partmodel
                            SET additional_properties = :props,
                                rohs_status = NULL,
                                lifecycle_status = NULL
                            WHERE id = :part_id
                        """),
                        {
                            'props': json.dumps(additional_properties),
                            'part_id': part_id
                        }
                    )

                migration_count += 1

        if dry_run:
            print(f"\n🔍 DRY RUN: Would migrate {migration_count} parts")
            print("   Run without --dry-run to perform actual migration")
        else:
            session.commit()
            print(f"\n✅ Successfully migrated {migration_count} parts")
            print("   RoHS and lifecycle status moved to additional_properties.electronic_component")


def verify_migration():
    """Verify that the migration was successful"""

    with Session(engine) as session:
        # Check if any parts still have rohs_status or lifecycle_status in columns
        remaining_parts = session.execute(
            text("""
                SELECT COUNT(*)
                FROM partmodel
                WHERE rohs_status IS NOT NULL OR lifecycle_status IS NOT NULL
            """)
        ).scalar()

        # Check how many parts now have electronic_component data
        migrated_parts = session.execute(
            text("""
                SELECT COUNT(*)
                FROM partmodel
                WHERE additional_properties LIKE '%electronic_component%'
            """)
        ).scalar()

        print(f"\n📊 Migration Verification:")
        print(f"   Parts with rohs_status/lifecycle_status in columns: {remaining_parts}")
        print(f"   Parts with electronic_component in additional_properties: {migrated_parts}")

        if remaining_parts == 0:
            print("✅ Migration successful! No parts have rohs/lifecycle in core columns.")
        else:
            print("⚠️  Warning: Some parts still have rohs/lifecycle in core columns.")


def main():
    parser = argparse.ArgumentParser(description="Migrate RoHS and lifecycle status to additional_properties")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')
    parser.add_argument('--verify', action='store_true', help='Verify migration results')

    args = parser.parse_args()

    print("🚀 RoHS/Lifecycle Status Migration Tool")
    print("=" * 50)

    if args.verify:
        verify_migration()
    else:
        migrate_rohs_lifecycle_data(dry_run=args.dry_run)

        if not args.dry_run:
            print("\n🔍 Verifying migration...")
            verify_migration()


if __name__ == "__main__":
    main()