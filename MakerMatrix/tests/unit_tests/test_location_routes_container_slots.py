"""
Unit tests for container slot generation API routes (Phase 1).

Tests the updated LocationCreateRequest schema and add_location endpoint
to support automatic container slot generation.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from MakerMatrix.routers.locations_routes import (
    LocationCreateRequest,
    router,
)
from MakerMatrix.schemas.response import ResponseSchema


# Mock dependencies
def mock_get_current_user():
    """Mock current user for authentication."""
    mock_user = Mock()
    mock_user.id = "test-user-id"
    mock_user.username = "testuser"
    return mock_user


class TestLocationCreateRequestSchema:
    """Test LocationCreateRequest Pydantic schema validation."""

    def test_regular_location_request(self):
        """Test creating regular location without slots - backward compatibility."""
        request = LocationCreateRequest(
            name="Workshop",
            description="Main workshop area",
            location_type="building"
        )

        assert request.name == "Workshop"
        assert request.description == "Main workshop area"
        assert request.location_type == "building"
        assert request.slot_count is None
        assert request.slot_naming_pattern == "Slot {n}"  # Default value
        assert request.slot_layout_type == "simple"  # Default value

    def test_simple_container_request(self):
        """Test creating simple container with auto-generated slots."""
        request = LocationCreateRequest(
            name="32-Slot Box",
            location_type="container",
            slot_count=32,
            slot_naming_pattern="Slot {n}"
        )

        assert request.name == "32-Slot Box"
        assert request.location_type == "container"
        assert request.slot_count == 32
        assert request.slot_naming_pattern == "Slot {n}"
        assert request.slot_layout_type == "simple"

    def test_grid_container_request(self):
        """Test creating grid layout container."""
        request = LocationCreateRequest(
            name="4x8 Grid",
            location_type="container",
            slot_count=32,
            slot_layout_type="grid",
            grid_rows=4,
            grid_columns=8,
            slot_naming_pattern="R{row}-C{col}"
        )

        assert request.name == "4x8 Grid"
        assert request.slot_count == 32
        assert request.slot_layout_type == "grid"
        assert request.grid_rows == 4
        assert request.grid_columns == 8
        assert request.slot_naming_pattern == "R{row}-C{col}"

    def test_slot_count_validation_minimum(self):
        """Test slot_count minimum value validation (ge=1)."""
        with pytest.raises(ValueError) as exc_info:
            LocationCreateRequest(
                name="Invalid Container",
                slot_count=0  # Should fail: minimum is 1
            )
        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_slot_count_validation_maximum(self):
        """Test slot_count maximum value validation (le=200)."""
        with pytest.raises(ValueError) as exc_info:
            LocationCreateRequest(
                name="Invalid Container",
                slot_count=201  # Should fail: maximum is 200
            )
        assert "less than or equal to 200" in str(exc_info.value).lower()

    def test_grid_rows_validation(self):
        """Test grid_rows validation constraints."""
        with pytest.raises(ValueError) as exc_info:
            LocationCreateRequest(
                name="Invalid Grid",
                slot_count=32,
                slot_layout_type="grid",
                grid_rows=0,  # Should fail: minimum is 1
                grid_columns=8
            )
        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_grid_columns_validation(self):
        """Test grid_columns validation constraints."""
        with pytest.raises(ValueError) as exc_info:
            LocationCreateRequest(
                name="Invalid Grid",
                slot_count=32,
                slot_layout_type="grid",
                grid_rows=4,
                grid_columns=21  # Should fail: maximum is 20
            )
        assert "less than or equal to 20" in str(exc_info.value).lower()

    def test_custom_layout_field(self):
        """Test custom layout field for Phase 2+ readiness."""
        request = LocationCreateRequest(
            name="Custom Container",
            slot_count=10,
            slot_layout_type="custom",
            slot_layout={"custom_data": "test"}
        )

        assert request.slot_layout == {"custom_data": "test"}


class TestAddLocationEndpointLogic:
    """Test add_location endpoint routing logic with mocks."""

    def test_regular_location_routing_logic(self):
        """Test that regular location creation routes to add_location()."""
        # Test the routing logic without HTTP client
        location_data = LocationCreateRequest(
            name="Workshop",
            description="Test workshop",
            location_type="building"
        )

        # Verify slot_count is None - should route to add_location()
        assert location_data.slot_count is None
        # This means the condition (slot_count is not None and slot_count > 0) is False

    def test_container_with_slots_routing_logic(self):
        """Test that container creation routes to create_container_with_slots()."""
        # Test the routing logic without HTTP client
        location_data = LocationCreateRequest(
            name="32-Slot Box",
            location_type="container",
            slot_count=32,
            slot_naming_pattern="Slot {n}"
        )

        # Verify slot_count is set - should route to create_container_with_slots()
        assert location_data.slot_count == 32
        assert location_data.slot_count > 0
        # This means the condition (slot_count is not None and slot_count > 0) is True

    def test_container_with_zero_slots_routing(self):
        """Test that slot_count=0 would be rejected by validation."""
        # Edge case: slot_count=0 should fail Pydantic validation
        with pytest.raises(ValueError) as exc_info:
            LocationCreateRequest(
                name="Container",
                slot_count=0  # Should fail: minimum is 1
            )
        assert "greater than or equal to 1" in str(exc_info.value).lower()


class TestGetAllLocationsEndpoint:
    """Test get_all_locations endpoint with hide_auto_slots parameter."""

    @pytest.fixture
    def mock_location_service(self):
        """Mock LocationService for testing."""
        with patch('MakerMatrix.routers.locations_routes.LocationService') as mock:
            yield mock

    def test_get_all_locations_without_filter(self, mock_location_service):
        """Test getting all locations including auto-generated slots."""
        # Setup mock service
        service_instance = mock_location_service.return_value
        service_instance.get_all_locations.return_value = Mock(
            status="success",
            message="Locations retrieved",
            data=[
                {
                    "id": "container-1",
                    "name": "Container",
                    "location_type": "container",
                    "is_auto_generated_slot": False
                },
                {
                    "id": "slot-1",
                    "name": "Slot 1",
                    "location_type": "slot",
                    "parent_id": "container-1",
                    "is_auto_generated_slot": True
                },
                {
                    "id": "slot-2",
                    "name": "Slot 2",
                    "location_type": "slot",
                    "parent_id": "container-1",
                    "is_auto_generated_slot": True
                }
            ]
        )

        # Create test client and make request
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        response = client.get("/get_all_locations")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert len(result["data"]) == 3  # All locations returned

    def test_get_all_locations_with_hide_auto_slots(self, mock_location_service):
        """Test getting locations with auto-generated slots filtered out."""
        # Setup mock service
        service_instance = mock_location_service.return_value
        service_instance.get_all_locations.return_value = Mock(
            status="success",
            message="Locations retrieved",
            data=[
                {
                    "id": "container-1",
                    "name": "Container",
                    "location_type": "container",
                    "is_auto_generated_slot": False
                },
                {
                    "id": "slot-1",
                    "name": "Slot 1",
                    "location_type": "slot",
                    "parent_id": "container-1",
                    "is_auto_generated_slot": True
                },
                {
                    "id": "slot-2",
                    "name": "Slot 2",
                    "location_type": "slot",
                    "parent_id": "container-1",
                    "is_auto_generated_slot": True
                }
            ]
        )

        # Create test client and make request
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        response = client.get("/get_all_locations?hide_auto_slots=true")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert len(result["data"]) == 1  # Only container, slots filtered
        assert result["data"][0]["id"] == "container-1"


class TestBackwardCompatibility:
    """Test that existing API usage patterns continue to work."""

    def test_existing_location_creation_unchanged(self):
        """Verify existing location creation requests work without modifications."""
        # This should work exactly as before
        request = LocationCreateRequest(
            name="Warehouse",
            description="Storage area",
            location_type="building"
        )

        # All original fields present
        assert request.name == "Warehouse"
        assert request.description == "Storage area"
        assert request.location_type == "building"

        # New fields have sensible defaults
        assert request.slot_count is None
        assert request.slot_naming_pattern == "Slot {n}"
        assert request.slot_layout_type == "simple"

    def test_all_new_fields_optional(self):
        """Verify all new fields are optional and have defaults."""
        # Minimum valid request (backward compatible)
        request = LocationCreateRequest(name="Test")

        assert request.name == "Test"
        assert request.slot_count is None
        assert request.slot_naming_pattern == "Slot {n}"
        assert request.slot_layout_type == "simple"
        assert request.grid_rows is None
        assert request.grid_columns is None
        assert request.slot_layout is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
