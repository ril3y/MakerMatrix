"""
Test that location renames don't break allocation references.

This test suite verifies that when a location is renamed, parts allocated
to that location maintain their references correctly.
"""

import pytest
import asyncio
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlmodel import Session, select

# Import test fixtures and utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from MakerMatrix.main import app
from MakerMatrix.models.models import engine, LocationModel, PartModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
from MakerMatrix.database.db import get_session
from sqlalchemy.orm import selectinload


class TestLocationRenameAllocations:
    """Test suite for location rename and allocation integrity."""

    API_KEY = "REDACTED_API_KEY"

    @pytest.fixture
    def auth_headers(self):
        """Provide authentication headers for API requests."""
        return {"X-API-Key": self.API_KEY}

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up test data before and after each test."""
        # Clean up before test
        with Session(engine) as session:
            # Delete all test allocations
            session.exec(
                select(PartLocationAllocation)
            ).all()
            for alloc in session.exec(select(PartLocationAllocation)).all():
                session.delete(alloc)
            session.commit()

            # Delete all test parts
            test_parts = session.exec(
                select(PartModel).where(PartModel.part_name.like("TEST_%"))
            ).all()
            for part in test_parts:
                session.delete(part)
            session.commit()

            # Delete all test locations
            test_locations = session.exec(
                select(LocationModel).where(LocationModel.name.like("TEST_%"))
            ).all()
            for location in test_locations:
                session.delete(location)
            session.commit()

        yield

        # Clean up after test
        with Session(engine) as session:
            # Delete allocations first (due to foreign keys)
            for alloc in session.exec(select(PartLocationAllocation)).all():
                session.delete(alloc)
            session.commit()

            # Delete test parts
            test_parts = session.exec(
                select(PartModel).where(PartModel.part_name.like("TEST_%"))
            ).all()
            for part in test_parts:
                session.delete(part)
            session.commit()

            # Delete test locations
            test_locations = session.exec(
                select(LocationModel).where(LocationModel.name.like("TEST_%"))
            ).all()
            for location in test_locations:
                session.delete(location)
            session.commit()

    def test_location_rename_preserves_allocations(self, auth_headers):
        """Test that renaming a location preserves part allocations."""
        with TestClient(app) as client:
            # Step 1: Create a test location
            location_response = client.post(
                "/api/locations/add_location",
                json={"name": "TEST_Storage_Shelf_A", "description": "Test storage location"},
                headers=auth_headers
            )
            assert location_response.status_code == 200
            location_data = location_response.json()
            location_id = location_data["data"]["id"]

            # Step 2: Create a test part
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_name": "TEST_Resistor_10K",
                    "part_number": "TEST_R10K",
                    "description": "Test 10K resistor",
                    "quantity": 100,
                    "location_id": location_id
                },
                headers=auth_headers
            )
            assert part_response.status_code == 200
            part_data = part_response.json()
            part_id = part_data["data"]["id"]

            # Step 3: Verify allocation exists
            allocations_response = client.get(
                f"/api/parts/{part_id}/allocations",
                headers=auth_headers
            )
            assert allocations_response.status_code == 200
            allocations_data = allocations_response.json()
            assert allocations_data["data"]["total_quantity"] == 100
            assert allocations_data["data"]["location_count"] == 1
            assert allocations_data["data"]["allocations"][0]["location"]["name"] == "TEST_Storage_Shelf_A"
            assert allocations_data["data"]["allocations"][0]["quantity_at_location"] == 100

            # Step 4: Rename the location
            rename_response = client.put(
                f"/api/locations/update_location/{location_id}",
                json={"name": "TEST_Storage_Shelf_B_Renamed"},
                headers=auth_headers
            )
            assert rename_response.status_code == 200
            rename_data = rename_response.json()
            assert rename_data["data"]["name"] == "TEST_Storage_Shelf_B_Renamed"

            # Step 5: Verify allocations are still intact with new location name
            allocations_after_response = client.get(
                f"/api/parts/{part_id}/allocations",
                headers=auth_headers
            )
            assert allocations_after_response.status_code == 200
            allocations_after_data = allocations_after_response.json()

            # Verify allocation still exists
            assert allocations_after_data["data"]["total_quantity"] == 100
            assert allocations_after_data["data"]["location_count"] == 1

            # Verify the location name is updated in the allocation
            assert allocations_after_data["data"]["allocations"][0]["location"]["name"] == "TEST_Storage_Shelf_B_Renamed"
            assert allocations_after_data["data"]["allocations"][0]["quantity_at_location"] == 100
            assert allocations_after_data["data"]["allocations"][0]["location_id"] == location_id

            # Step 6: Verify part still shows correct location
            part_response = client.get(
                f"/api/parts/get_part?part_id={part_id}",
                headers=auth_headers
            )
            assert part_response.status_code == 200
            part_data = part_response.json()
            # The part's location_id should still be the same
            assert part_data["data"]["location_id"] == location_id

    def test_multiple_allocations_after_rename(self, auth_headers):
        """Test that multiple allocations remain intact after location rename."""
        with TestClient(app) as client:
            # Create multiple locations
            locations = []
            for i in range(3):
                loc_response = client.post(
                    "/api/locations/add_location",
                    json={"name": f"TEST_Location_{i}", "description": f"Test location {i}"},
                    headers=auth_headers
                )
                assert loc_response.status_code == 200
                locations.append(loc_response.json()["data"])

            # Create a part with initial allocation to first location
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_name": "TEST_MultiAlloc_Part",
                    "part_number": "TEST_MAP",
                    "description": "Test part with multiple allocations",
                    "quantity": 300,
                    "location_id": locations[0]["id"]
                },
                headers=auth_headers
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Transfer some quantity to other locations
            transfer1_response = client.post(
                f"/api/parts/{part_id}/transfer?from_location_id={locations[0]['id']}&to_location_id={locations[1]['id']}&quantity=100",
                headers=auth_headers
            )
            assert transfer1_response.status_code == 200

            transfer2_response = client.post(
                f"/api/parts/{part_id}/transfer?from_location_id={locations[0]['id']}&to_location_id={locations[2]['id']}&quantity=50",
                headers=auth_headers
            )
            assert transfer2_response.status_code == 200

            # Verify allocations before rename
            allocations_before = client.get(
                f"/api/parts/{part_id}/allocations",
                headers=auth_headers
            )
            assert allocations_before.status_code == 200
            alloc_data = allocations_before.json()["data"]
            assert alloc_data["total_quantity"] == 300
            assert alloc_data["location_count"] == 3

            # Rename all locations
            for i, location in enumerate(locations):
                rename_response = client.put(
                    f"/api/locations/update_location/{location['id']}",
                    json={"name": f"TEST_Renamed_Location_{i}"},
                    headers=auth_headers
                )
                assert rename_response.status_code == 200

            # Verify all allocations still exist with correct quantities
            allocations_after = client.get(
                f"/api/parts/{part_id}/allocations",
                headers=auth_headers
            )
            assert allocations_after.status_code == 200
            alloc_data_after = allocations_after.json()["data"]

            assert alloc_data_after["total_quantity"] == 300
            assert alloc_data_after["location_count"] == 3

            # Verify each allocation has the correct renamed location
            allocation_map = {
                alloc["location"]["name"]: alloc["quantity_at_location"]
                for alloc in alloc_data_after["allocations"]
            }

            assert allocation_map["TEST_Renamed_Location_0"] == 150  # 300 - 100 - 50
            assert allocation_map["TEST_Renamed_Location_1"] == 100
            assert allocation_map["TEST_Renamed_Location_2"] == 50

    def test_database_integrity_after_rename(self, auth_headers):
        """Test database-level integrity of allocations after location rename."""
        with TestClient(app) as client:
            # Create location and part
            location_response = client.post(
                "/api/locations/add_location",
                json={"name": "TEST_DB_Location", "description": "Test DB location"},
                headers=auth_headers
            )
            assert location_response.status_code == 200
            location_id = location_response.json()["data"]["id"]

            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_name": "TEST_DB_Part",
                    "part_number": "TEST_DBP",
                    "description": "Test DB part",
                    "quantity": 75,
                    "location_id": location_id
                },
                headers=auth_headers
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Check database state before rename
            with Session(engine) as session:
                allocation_before = session.exec(
                    select(PartLocationAllocation)
                    .where(PartLocationAllocation.part_id == part_id)
                    .where(PartLocationAllocation.location_id == location_id)
                ).first()
                assert allocation_before is not None
                assert allocation_before.quantity_at_location == 75
                assert allocation_before.location_id == location_id

                location_before = session.get(LocationModel, location_id)
                assert location_before.name == "TEST_DB_Location"

            # Rename the location
            rename_response = client.put(
                f"/api/locations/update_location/{location_id}",
                json={"name": "TEST_DB_Location_Renamed"},
                headers=auth_headers
            )
            assert rename_response.status_code == 200

            # Check database state after rename
            with Session(engine) as session:
                # Verify allocation still exists with same IDs
                allocation_after = session.exec(
                    select(PartLocationAllocation)
                    .where(PartLocationAllocation.part_id == part_id)
                    .where(PartLocationAllocation.location_id == location_id)
                ).first()
                assert allocation_after is not None
                assert allocation_after.quantity_at_location == 75
                assert allocation_after.location_id == location_id  # Same ID

                # Verify location has new name but same ID
                location_after = session.get(LocationModel, location_id)
                assert location_after.name == "TEST_DB_Location_Renamed"
                assert location_after.id == location_id  # Same ID

                # Verify the relationship still works
                allocation_with_location = session.exec(
                    select(PartLocationAllocation)
                    .where(PartLocationAllocation.part_id == part_id)
                    .options(selectinload(PartLocationAllocation.location))
                ).first()
                assert allocation_with_location.location.name == "TEST_DB_Location_Renamed"
                assert allocation_with_location.location.id == location_id


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])