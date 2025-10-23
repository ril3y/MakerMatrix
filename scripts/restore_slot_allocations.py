#!/usr/bin/env python3
"""
Restore slot allocations from backup database.

This script finds parts that were allocated to slots in the backup
and updates their location in the current database.

Run with: python scripts/restore_slot_allocations.py
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
from sqlmodel import Session, select
from MakerMatrix.models.models import engine
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation


def restore_slot_allocations(backup_path: str, dry_run: bool = False):
    """Restore slot allocations from backup database."""

    # Connect to backup database
    backup_conn = sqlite3.connect(backup_path)
    backup_cursor = backup_conn.cursor()

    # Get slot allocations from backup (parts in slot locations)
    backup_cursor.execute(
        """
        SELECT pla.part_id, l.name as slot_name, pla.quantity_at_location,
               pla.is_primary_storage, pla.notes, p.part_name
        FROM part_location_allocations pla
        JOIN locationmodel l ON pla.location_id = l.id
        JOIN partmodel p ON pla.part_id = p.id
        WHERE l.is_auto_generated_slot = 1 OR l.slot_number IS NOT NULL
    """
    )
    backup_slot_allocations = backup_cursor.fetchall()
    backup_conn.close()

    print(f"Found {len(backup_slot_allocations)} parts in slots in backup")

    if len(backup_slot_allocations) == 0:
        print("No slot allocations to restore")
        return

    # Update current database
    with Session(engine) as session:
        restored = 0
        not_found_parts = 0
        not_found_slots = 0

        for part_id, slot_name, quantity, is_primary, notes, part_name in backup_slot_allocations:
            # Find the slot location in current DB by name
            slot_location = session.exec(select(LocationModel).where(LocationModel.name == slot_name)).first()

            if not slot_location:
                not_found_slots += 1
                print(f"  Warning: Slot '{slot_name}' not found in current DB")
                continue

            # Find the part's current allocation
            current_alloc = session.exec(
                select(PartLocationAllocation).where(PartLocationAllocation.part_id == part_id)
            ).first()

            if not current_alloc:
                not_found_parts += 1
                print(f"  Warning: Part '{part_name}' (ID: {part_id}) not found in current DB")
                continue

            # Update allocation to slot location
            old_location_id = current_alloc.location_id

            if not dry_run:
                current_alloc.location_id = slot_location.id
                current_alloc.quantity_at_location = quantity
                current_alloc.is_primary_storage = bool(is_primary)
                if notes:
                    current_alloc.notes = notes
                current_alloc.last_updated = datetime.now()

            restored += 1
            print(f"  {'Would move' if dry_run else 'Moved'} {part_name} to {slot_name} (qty: {quantity})")

        # Commit changes only if not dry run
        if not dry_run:
            session.commit()

        # Print summary
        print("\n" + "=" * 60)
        print(f"{'DRY RUN - ' if dry_run else ''}SLOT ALLOCATION RESTORATION")
        print("=" * 60)
        print(f"Slot allocations in backup: {len(backup_slot_allocations)}")
        print(f"Successfully {'would be ' if dry_run else ''}restored: {restored}")
        print(f"Parts not found: {not_found_parts}")
        print(f"Slots not found: {not_found_slots}")
        print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Restore slot allocations from backup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    args = parser.parse_args()

    backup_path = "/home/ril3y/MakerMatrix/makermatrix.db.backup_20251012_175714"

    if not os.path.exists(backup_path):
        print(f"Error: Backup file not found: {backup_path}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made\n")
        restore_slot_allocations(backup_path, dry_run=True)
    else:
        print("Restoring slot allocations from backup...")
        print(f"This will move parts back to their slot locations\n")

        response = input("Continue? (yes/no): ")
        if response.lower() in ["yes", "y"]:
            restore_slot_allocations(backup_path, dry_run=False)
        else:
            print("Restoration cancelled")
