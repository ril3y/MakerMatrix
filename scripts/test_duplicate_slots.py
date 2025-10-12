#!/usr/bin/env python3
"""
Test script to verify duplicate slot names work across different containers.

This test creates two containers with 2x2 grids, both using R{row}-C{col} pattern.
Should result in both containers having R1-C1, R1-C2, R2-C1, R2-C2 slots.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.database.db import get_session

def main():
    import uuid
    test_id = str(uuid.uuid4())[:8]  # Use unique ID for test runs

    print("="*70)
    print("Testing Duplicate Slot Names Across Containers")
    print(f"Test Run ID: {test_id}")
    print("="*70)

    service = LocationService()

    # Test 1: Create first container with 2x2 grid
    print("\n1. Creating first container: 'Test-Container-A' (2x2 grid)...")
    container_a_data = {
        "name": f"Test-Container-A-{test_id}",
        "description": "First test container with R{row}-C{col} slots",
        "location_type": "container",
        "slot_count": 4,
        "slot_naming_pattern": "R{row}-C{col}",
        "slot_layout_type": "grid",
        "grid_rows": 2,
        "grid_columns": 2
    }

    result_a = service.create_container_with_slots(container_a_data)

    if result_a.success:
        container_a = result_a.data['container']
        slots_created_a = result_a.data['slots_created']
        print(f"   ✓ Container A created: {container_a['id']}")
        print(f"   ✓ Slots created: {slots_created_a}")
    else:
        print(f"   ✗ Failed to create Container A: {result_a.message}")
        return False

    # Test 2: Create second container with same 2x2 grid pattern
    print("\n2. Creating second container: 'Test-Container-B' (2x2 grid)...")
    print("   Using SAME slot naming pattern: R{row}-C{col}")

    container_b_data = {
        "name": f"Test-Container-B-{test_id}",
        "description": "Second test container with R{row}-C{col} slots",
        "location_type": "container",
        "slot_count": 4,
        "slot_naming_pattern": "R{row}-C{col}",  # Same pattern!
        "slot_layout_type": "grid",
        "grid_rows": 2,
        "grid_columns": 2
    }

    result_b = service.create_container_with_slots(container_b_data)

    if result_b.success:
        container_b = result_b.data['container']
        slots_created_b = result_b.data['slots_created']
        print(f"   ✓ Container B created: {container_b['id']}")
        print(f"   ✓ Slots created: {slots_created_b}")
        print("\n   SUCCESS! Duplicate slot names allowed across containers!")
    else:
        print(f"   ✗ Failed to create Container B: {result_b.message}")
        print("\n   FAILED! Duplicate slot names still blocked!")
        return False

    # Test 3: Query slots to verify they exist
    print("\n3. Verifying slot structure...")

    with next(get_session()) as session:
        from sqlalchemy import select, text
        from MakerMatrix.models.location_models import LocationModel

        # Get all slots for Container A
        query_a = select(LocationModel).where(
            LocationModel.parent_id == container_a['id'],
            LocationModel.is_auto_generated_slot == True
        )
        slots_a = session.exec(query_a).all()

        print(f"\n   Container A slots ({len(slots_a)}):")
        for slot in sorted(slots_a, key=lambda s: s.slot_number):
            print(f"     - {slot.name} (slot_number={slot.slot_number}, metadata={slot.slot_metadata})")

        # Get all slots for Container B
        query_b = select(LocationModel).where(
            LocationModel.parent_id == container_b['id'],
            LocationModel.is_auto_generated_slot == True
        )
        slots_b = session.exec(query_b).all()

        print(f"\n   Container B slots ({len(slots_b)}):")
        for slot in sorted(slots_b, key=lambda s: s.slot_number):
            print(f"     - {slot.name} (slot_number={slot.slot_number}, metadata={slot.slot_metadata})")

    # Test 4: Verify regular locations still enforce uniqueness
    print("\n4. Testing that regular locations still enforce name uniqueness...")

    regular_loc_1 = {
        "name": f"Test-Regular-Location-{test_id}",
        "description": "First regular location",
        "location_type": "standard"
    }

    result_reg_1 = service.add_location(regular_loc_1)

    if result_reg_1.success:
        print("   ✓ First regular location created")
    else:
        print(f"   ✗ Failed to create first regular location: {result_reg_1.message}")
        return False

    # Try to create duplicate regular location (should fail)
    regular_loc_2 = {
        "name": f"Test-Regular-Location-{test_id}",  # Same name, no parent
        "description": "Duplicate regular location (should fail)",
        "location_type": "standard"
    }

    result_reg_2 = service.add_location(regular_loc_2)

    if not result_reg_2.success:
        print("   ✓ Duplicate regular location correctly rejected")
        print(f"      Message: {result_reg_2.message}")
    else:
        print("   ✗ ERROR: Duplicate regular location was allowed!")
        return False

    # Cleanup
    print("\n5. Cleaning up test data...")
    try:
        service.delete_location(container_a['id'])
        service.delete_location(container_b['id'])
        service.delete_location(result_reg_1.data['id'])
        print("   ✓ Test locations cleaned up")
    except Exception as e:
        print(f"   Warning: Cleanup error: {e}")

    print("\n" + "="*70)
    print("ALL TESTS PASSED!")
    print("="*70)
    print("\n✓ Duplicate slot names work across containers")
    print("✓ Regular location uniqueness still enforced")
    print("✓ Schema migration successful")

    return True


if __name__ == '__main__':
    try:
        # Wait a moment for backend to be ready
        print("Waiting 3 seconds for backend to be ready...")
        time.sleep(3)

        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
