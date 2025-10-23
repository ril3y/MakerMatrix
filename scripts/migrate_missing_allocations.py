#!/usr/bin/env python3
"""
Migration script to create allocations for parts that don't have them.

This script:
1. Finds all parts without allocations
2. Creates a primary allocation for each at their location_id (or Unsorted)
3. Sets quantity_at_location to 0 (user will update manually)

Run with: python scripts/migrate_missing_allocations.py
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session, select
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation


def migrate_missing_allocations():
    """Create allocations for all parts that don't have them."""

    with Session(engine) as session:
        # Get all parts with their allocations
        parts = session.exec(select(PartModel)).all()

        print(f"Found {len(parts)} total parts")

        # Find or create Unsorted location
        unsorted = session.exec(select(LocationModel).where(LocationModel.name == "Unsorted")).first()

        if not unsorted:
            print("Creating 'Unsorted' location...")
            unsorted = LocationModel(
                name="Unsorted", description="Default location for parts without allocations", location_type="storage"
            )
            session.add(unsorted)
            session.commit()
            session.refresh(unsorted)
            print(f"Created Unsorted location: {unsorted.id}")

        # Track statistics
        parts_with_allocations = 0
        parts_without_allocations = 0
        allocations_created = 0

        for part in parts:
            # Check if part has any allocations
            existing_allocs = session.exec(
                select(PartLocationAllocation).where(PartLocationAllocation.part_id == part.id)
            ).all()

            if existing_allocs:
                parts_with_allocations += 1
                continue

            # Part has no allocations - create one
            parts_without_allocations += 1

            # All parts without allocations go to Unsorted
            location_id = unsorted.id

            # Create allocation with quantity = 0
            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=location_id,
                quantity_at_location=0,  # Set to 0 - user will update manually
                is_primary_storage=True,
                notes="Auto-created by migration script - please update quantity",
                allocated_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
            )

            session.add(allocation)
            allocations_created += 1

            if allocations_created % 50 == 0:
                print(f"Created {allocations_created} allocations...")

        # Commit all changes
        session.commit()

        # Print summary
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Total parts: {len(parts)}")
        print(f"Parts with allocations: {parts_with_allocations}")
        print(f"Parts without allocations: {parts_without_allocations}")
        print(f"Allocations created: {allocations_created}")
        print("=" * 60)
        print("\nNOTE: All new allocations have quantity = 0")
        print("Please update quantities manually in the UI or via API")
        print("=" * 60)


if __name__ == "__main__":
    print("Starting allocation migration...")
    print("This will create allocations for parts that don't have them")
    print("All new allocations will have quantity = 0\n")

    response = input("Continue? (yes/no): ")
    if response.lower() in ["yes", "y"]:
        migrate_missing_allocations()
    else:
        print("Migration cancelled")
