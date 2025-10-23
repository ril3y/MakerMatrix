"""
Migration script to move part quantities from old partmodel.quantity column
to the new part_location_allocations system.

This script:
1. Finds all parts with quantity > 0 in the old quantity column
2. Creates allocations for them (using their existing location if set, or a default location)
3. Preserves the quantity values
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from sqlmodel import Session
from MakerMatrix.models.models import engine


def migrate_quantities():
    """Migrate quantities from partmodel.quantity to allocations"""

    with Session(engine) as session:
        # Check if we have any parts with quantities
        result = session.execute(
            text(
                """
            SELECT
                COUNT(*) as total_parts,
                SUM(quantity) as total_quantity,
                COUNT(CASE WHEN quantity > 0 THEN 1 END) as parts_with_quantity
            FROM partmodel
        """
            )
        )
        stats = result.fetchone()

        print(f"\n=== Migration Statistics ===")
        print(f"Total parts: {stats.total_parts}")
        print(f"Total quantity in old column: {stats.total_quantity}")
        print(f"Parts with quantity > 0: {stats.parts_with_quantity}")

        # Get parts that need migration (have quantity but no allocations)
        result = session.execute(
            text(
                """
            SELECT
                p.id,
                p.part_name,
                p.quantity as old_quantity,
                p.location_id
            FROM partmodel p
            WHERE p.quantity > 0
            AND NOT EXISTS (
                SELECT 1 FROM part_location_allocations a
                WHERE a.part_id = p.id
            )
            ORDER BY p.quantity DESC
        """
            )
        )
        parts_to_migrate = result.fetchall()

        print(f"\nParts needing migration: {len(parts_to_migrate)}")

        if not parts_to_migrate:
            print("No parts need migration!")
            return

        # Check if we have a default location for parts without location_id
        result = session.execute(text("SELECT id, name FROM locationmodel LIMIT 1"))
        default_location = result.fetchone()

        if not default_location:
            print("\nERROR: No locations exist in database. Creating a default 'Unallocated' location...")
            import uuid

            location_id = str(uuid.uuid4())
            session.execute(
                text(
                    """
                INSERT INTO locationmodel (id, name, description, created_at, updated_at, is_container)
                VALUES (:id, 'Unallocated', 'Parts migrated from old quantity system', :now, :now, 0)
            """
                ),
                {"id": location_id, "now": datetime.utcnow()},
            )
            session.commit()
            print(f"Created default location: {location_id}")
        else:
            print(f"\nDefault location available: {default_location.name} ({default_location.id})")

        # Migrate each part
        migrated_count = 0
        total_qty_migrated = 0

        print("\nMigrating parts...")
        for part in parts_to_migrate:
            import uuid

            allocation_id = str(uuid.uuid4())
            location_id = part.location_id or (default_location.id if default_location else location_id)

            # Create allocation
            session.execute(
                text(
                    """
                INSERT INTO part_location_allocations
                (id, part_id, location_id, quantity_at_location, is_primary_storage,
                 allocated_at, last_updated, auto_synced)
                VALUES
                (:id, :part_id, :location_id, :quantity, 1,
                 :now, :now, 0)
            """
                ),
                {
                    "id": allocation_id,
                    "part_id": part.id,
                    "location_id": location_id,
                    "quantity": part.old_quantity,
                    "now": datetime.utcnow(),
                },
            )

            migrated_count += 1
            total_qty_migrated += part.old_quantity

            print(f"  ✓ {part.part_name[:40]:40} | Qty: {part.old_quantity:5} → Allocation created")

        # Commit all changes
        session.commit()

        print(f"\n=== Migration Complete ===")
        print(f"Parts migrated: {migrated_count}")
        print(f"Total quantity migrated: {total_qty_migrated}")
        print(f"\nAllocations created successfully!")

        # Verify migration
        result = session.execute(
            text(
                """
            SELECT
                COUNT(*) as total_allocations,
                SUM(quantity_at_location) as total_allocated_qty
            FROM part_location_allocations
        """
            )
        )
        verify = result.fetchone()

        print(f"\n=== Verification ===")
        print(f"Total allocations in database: {verify.total_allocations}")
        print(f"Total allocated quantity: {verify.total_allocated_qty}")


if __name__ == "__main__":
    print("Starting quantity → allocation migration...")
    migrate_quantities()
    print("\nMigration script completed!")
