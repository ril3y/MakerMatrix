#!/usr/bin/env python3
"""
Restore quantity data from backup database.

This script:
1. Reads allocations with quantities from backup database
2. Updates matching allocations in current database
3. Matches by part_id and location_id

Run with: python scripts/restore_quantities_from_backup.py
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from sqlmodel import Session, select
from MakerMatrix.models.models import engine
from MakerMatrix.models.part_allocation_models import PartLocationAllocation


def restore_quantities_from_backup(backup_path: str, dry_run: bool = False):
    """Restore allocation quantities from backup database."""

    # Connect to backup database
    backup_conn = sqlite3.connect(backup_path)
    backup_cursor = backup_conn.cursor()

    # Get all allocations from backup with quantity > 0, including part identifiers and location name
    backup_cursor.execute("""
        SELECT pla.part_id, pla.location_id, pla.quantity_at_location,
               pla.is_primary_storage, pla.notes, p.part_name,
               p.manufacturer_part_number, p.part_number, p.supplier,
               l.name as location_name
        FROM part_location_allocations pla
        JOIN partmodel p ON pla.part_id = p.id
        JOIN locationmodel l ON pla.location_id = l.id
        WHERE pla.quantity_at_location > 0
    """)
    backup_allocations = backup_cursor.fetchall()
    backup_conn.close()

    print(f"Found {len(backup_allocations)} allocations with quantity > 0 in backup")

    # Get current database info
    with Session(engine) as session:
        current_parts_count = session.exec(select(PartLocationAllocation)).all()
        print(f"Current database has {len(current_parts_count)} total allocations")

    # Update current database
    from MakerMatrix.models.models import PartModel

    with Session(engine) as session:
        matched = 0
        updated = 0
        not_found = 0
        examples = []

        for part_id, location_id, quantity, is_primary, notes, part_name, mpn, pn, supplier, backup_location_name in backup_allocations:
            # Try to find matching part in current DB by multiple criteria
            current_part = None

            # First try: exact match by manufacturer part number (most reliable)
            if mpn:
                current_part = session.exec(
                    select(PartModel).where(PartModel.manufacturer_part_number == mpn)
                ).first()

            # Second try: match by part_number if we didn't find it
            if not current_part and pn:
                current_part = session.exec(
                    select(PartModel).where(PartModel.part_number == pn)
                ).first()

            # Third try: match by part_name and supplier
            if not current_part and part_name and supplier:
                current_part = session.exec(
                    select(PartModel).where(
                        PartModel.part_name == part_name,
                        PartModel.supplier == supplier
                    )
                ).first()

            if not current_part:
                not_found += 1
                continue

            # Find the allocation for this part
            current_alloc = session.exec(
                select(PartLocationAllocation).where(
                    PartLocationAllocation.part_id == current_part.id
                )
            ).first()

            if current_alloc:
                matched += 1
                # Check if quantity OR location changed
                qty_changed = current_alloc.quantity_at_location != quantity

                # Try to find matching location by name from backup
                from MakerMatrix.models.location_models import LocationModel
                location_changed = False
                target_location = None

                if backup_location_name:
                    target_location = session.exec(
                        select(LocationModel).where(LocationModel.name == backup_location_name)
                    ).first()

                    if target_location and current_alloc.location_id != target_location.id:
                        location_changed = True

                if qty_changed or location_changed:
                    old_qty = current_alloc.quantity_at_location
                    old_location = session.get(LocationModel, current_alloc.location_id)
                    old_location_name = old_location.name if old_location else "Unknown"

                    if not dry_run:
                        current_alloc.quantity_at_location = quantity
                        if location_changed and target_location:
                            current_alloc.location_id = target_location.id
                        current_alloc.is_primary_storage = bool(is_primary)
                        if notes and "Auto-created by migration" not in (current_alloc.notes or ""):
                            current_alloc.notes = notes
                        current_alloc.last_updated = datetime.now()

                    updated += 1

                    # Save first 10 examples
                    if len(examples) < 10:
                        if location_changed:
                            examples.append(f"  {part_name}: {old_qty} → {quantity}, Location: {old_location_name} → {backup_location_name}")
                        else:
                            examples.append(f"  {part_name}: {old_qty} → {quantity}")

                    if updated % 50 == 0:
                        print(f"{'Would update' if dry_run else 'Updated'} {updated} allocations...")

        # Commit changes only if not dry run
        if not dry_run:
            session.commit()

        # Print examples
        if examples:
            print(f"\nExample updates:")
            for ex in examples:
                print(ex)

        # Print summary
        print("\n" + "="*60)
        print("QUANTITY RESTORATION COMPLETE")
        print("="*60)
        print(f"Backup allocations found: {len(backup_allocations)}")
        print(f"Matched in current DB: {matched}")
        print(f"Updated with new quantity: {updated}")
        print(f"Not found in current DB: {not_found}")
        print("="*60)


if __name__ == "__main__":
    import argparse
    import zipfile
    import tempfile

    parser = argparse.ArgumentParser(description="Restore quantities from backup database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    args = parser.parse_args()

    # Use the October 22 backup (most recent with LCSC quantities)
    backup_zip = "/home/ril3y/MakerMatrix/MakerMatrix/backups/makermatrix_backup_20251022_173543.zip"

    # Extract database from zip to temp location
    temp_dir = tempfile.mkdtemp()
    backup_path = os.path.join(temp_dir, "makers_matrix.db")

    print(f"Extracting backup from: {backup_zip}")
    with zipfile.ZipFile(backup_zip, 'r') as zip_ref:
        zip_ref.extract("makers_matrix.db", temp_dir)

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print(f"Analyzing backup: {backup_path}\n")
        restore_quantities_from_backup(backup_path, dry_run=True)
    else:
        print(f"Restoring quantities from backup: {backup_path}")
        print(f"This will update allocation quantities in the current database")
        print(f"Your new parts added after the backup will NOT be affected\n")

        response = input("Continue? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            restore_quantities_from_backup(backup_path, dry_run=False)
        else:
            print("Restoration cancelled")
