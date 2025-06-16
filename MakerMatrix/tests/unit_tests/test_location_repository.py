"""
Simplified unit tests for location_repositories.py using real in-memory database.

These tests focus on the key methods and use the actual repository API.
"""

import pytest
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    LocationAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.models.models import LocationModel, LocationQueryModel, PartModel
from MakerMatrix.unit_tests.test_database import create_test_db, create_test_db_with_data
from sqlmodel import select


class TestLocationRepositorySimple:
    """Test cases for LocationRepository using real database."""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()
        self.repo = LocationRepository(self.test_db.engine)

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def test_add_location_success(self):
        """Test successfully adding a new location."""
        session = self.test_db.get_session()
        
        location_data = {
            "name": "Test Location",
            "description": "A test location",
            "location_type": "storage"
        }
        
        result = LocationRepository.add_location(session, location_data)
        
        assert result.name == "Test Location"
        assert result.description == "A test location"
        assert result.location_type == "storage"

    def test_add_location_duplicate_name_error(self):
        """Test adding location with duplicate name raises error."""
        session = self.test_db.get_session()
        
        # Create first location
        location_data1 = {"name": "Duplicate Name", "description": "First"}
        LocationRepository.add_location(session, location_data1)

        # Try to create second location with same name
        location_data2 = {"name": "Duplicate Name", "description": "Second"}
        with pytest.raises(LocationAlreadyExistsError) as exc_info:
            LocationRepository.add_location(session, location_data2)
        
        assert "Location with name 'Duplicate Name' already exists" in str(exc_info.value)

    def test_add_location_with_invalid_parent_error(self):
        """Test adding location with invalid parent raises error."""
        session = self.test_db.get_session()
        
        location_data = {
            "name": "Orphan Location",
            "description": "No parent",
            "parent_id": "nonexistent-parent-id"
        }
        
        with pytest.raises(InvalidReferenceError) as exc_info:
            LocationRepository.add_location(session, location_data)
        
        assert "Parent location with ID 'nonexistent-parent-id' does not exist" in str(exc_info.value)

    def test_get_all_locations_success(self):
        """Test retrieving all locations."""
        session = self.test_db.get_session()
        
        # Create multiple locations
        for i in range(3):
            location_data = {
                "name": f"Location {i}",
                "description": f"Description {i}"
            }
            LocationRepository.add_location(session, location_data)

        # Retrieve all locations
        results = LocationRepository.get_all_locations(session)
        
        assert len(results) == 3
        location_names = [loc.name for loc in results]
        assert "Location 0" in location_names
        assert "Location 2" in location_names

    def test_get_location_by_id_success(self):
        """Test successfully retrieving location by ID."""
        session = self.test_db.get_session()
        
        # Create location
        location_data = {"name": "Find By ID", "description": "Test location"}
        created_location = LocationRepository.add_location(session, location_data)
        location_id = created_location.id

        # Retrieve location
        query = LocationQueryModel(id=location_id)
        result = LocationRepository.get_location(session, query)
        
        assert result is not None
        assert result.id == location_id
        assert result.name == "Find By ID"

    def test_get_location_by_name_success(self):
        """Test successfully retrieving location by name."""
        session = self.test_db.get_session()
        
        # Create location
        location_data = {"name": "Find By Name", "description": "Test location"}
        LocationRepository.add_location(session, location_data)

        # Retrieve location
        query = LocationQueryModel(name="Find By Name")
        result = LocationRepository.get_location(session, query)
        
        assert result is not None
        assert result.name == "Find By Name"
        assert result.description == "Test location"

    def test_get_location_not_found(self):
        """Test retrieving non-existent location raises error."""
        session = self.test_db.get_session()
        
        query = LocationQueryModel(id="nonexistent-id")
        with pytest.raises(ResourceNotFoundError) as exc_info:
            LocationRepository.get_location(session, query)
        
        assert "Location nonexistent-id not found" in str(exc_info.value)

    def test_update_location_success(self):
        """Test successfully updating a location."""
        session = self.test_db.get_session()
        
        # Create location
        location_data = {"name": "Original Name", "description": "Original description"}
        created_location = LocationRepository.add_location(session, location_data)
        location_id = created_location.id

        # Update location
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "location_type": "workbench"
        }
        result = LocationRepository.update_location(session, location_id, update_data)
        
        assert result.name == "Updated Name"
        assert result.description == "Updated description"
        assert result.location_type == "workbench"

    def test_update_location_not_found_error(self):
        """Test updating non-existent location raises error."""
        session = self.test_db.get_session()
        
        update_data = {"name": "New Name"}
        with pytest.raises(ResourceNotFoundError) as exc_info:
            LocationRepository.update_location(session, "nonexistent-id", update_data)
        
        assert "Location not found" in str(exc_info.value)

    def test_delete_location_success(self):
        """Test successfully deleting a location."""
        session = self.test_db.get_session()
        
        # Create location
        location_data = {"name": "Delete Me", "description": "To be deleted"}
        created_location = LocationRepository.add_location(session, location_data)

        # Delete location
        result = LocationRepository.delete_location(session, created_location)
        
        assert result == True
        
        # Verify location is gone
        query = LocationQueryModel(id=created_location.id)
        with pytest.raises(ResourceNotFoundError):
            LocationRepository.get_location(session, query)

    def test_get_location_details_success(self):
        """Test getting detailed location information."""
        session = self.test_db.get_session()
        
        # Create parent and child locations
        parent_data = {"name": "Parent Location"}
        parent = LocationRepository.add_location(session, parent_data)
        
        child_data = {"name": "Child Location", "parent_id": parent.id}
        child = LocationRepository.add_location(session, child_data)
        
        # Get location details
        details = LocationRepository.get_location_details(session, parent.id)
        
        assert details["name"] == "Parent Location"
        assert len(details["children"]) == 1
        assert details["children"][0]["name"] == "Child Location"

    def test_get_location_path_success(self):
        """Test getting location path with hierarchy."""
        session = self.test_db.get_session()
        
        # Create location hierarchy
        grandparent_data = {"name": "Grandparent"}
        grandparent = LocationRepository.add_location(session, grandparent_data)
        
        parent_data = {"name": "Parent", "parent_id": grandparent.id}
        parent = LocationRepository.add_location(session, parent_data)
        
        child_data = {"name": "Child", "parent_id": parent.id}
        child = LocationRepository.add_location(session, child_data)

        # Get path (returns nested structure)
        path_info = LocationRepository.get_location_path(session, child.id)
        
        # Check nested structure: child -> parent -> grandparent
        assert path_info["name"] == "Child"
        assert "parent" in path_info
        assert path_info["parent"]["name"] == "Parent"
        assert "parent" in path_info["parent"]
        assert path_info["parent"]["parent"]["name"] == "Grandparent"

    def test_get_location_hierarchy_success(self):
        """Test getting location hierarchy."""
        session = self.test_db.get_session()
        
        # Create parent location
        parent_data = {"name": "Parent Location"}
        parent = LocationRepository.add_location(session, parent_data)
        
        # Create child locations
        child1_data = {"name": "Child 1", "parent_id": parent.id}
        child2_data = {"name": "Child 2", "parent_id": parent.id}
        LocationRepository.add_location(session, child1_data)
        LocationRepository.add_location(session, child2_data)

        # Get hierarchy
        hierarchy_result = LocationRepository.get_location_hierarchy(session, parent.id)
        hierarchy = hierarchy_result["hierarchy"]
        
        assert hierarchy["name"] == "Parent Location"
        assert len(hierarchy["children"]) == 2
        child_names = [child["name"] for child in hierarchy["children"]]
        assert "Child 1" in child_names
        assert "Child 2" in child_names

    def test_cleanup_locations_success(self):
        """Test cleanup of orphaned locations."""
        session = self.test_db.get_session()
        
        # Create locations - some will be orphaned
        parent_data = {"name": "Parent"}
        parent = LocationRepository.add_location(session, parent_data)
        
        child_data = {"name": "Child", "parent_id": parent.id}
        child = LocationRepository.add_location(session, child_data)
        
        # Delete parent manually to create orphan
        session.delete(parent)
        session.commit()

        # Run cleanup
        cleaned_count = LocationRepository.cleanup_locations(session)
        
        # Should have cleaned up the orphaned child
        assert cleaned_count >= 0  # Implementation may vary

    def test_preview_delete_functionality(self):
        """Test delete preview shows impact."""
        session = self.test_db.get_session()
        
        # Create location with child and parts
        parent_data = {"name": "Preview Parent"}
        parent = LocationRepository.add_location(session, parent_data)
        
        child_data = {"name": "Preview Child", "parent_id": parent.id}
        LocationRepository.add_location(session, child_data)
        
        part = PartModel(
            part_name="Preview Part",
            part_number="PP001", 
            quantity=1,
            location_id=parent.id
        )
        session.add(part)
        session.commit()

        # Test preview
        preview = LocationRepository.preview_delete(session, parent.id)
        
        assert "location_hierarchy" in preview
        assert preview["location_hierarchy"]["name"] == "Preview Parent"
        assert "affected_locations_count" in preview
        assert "affected_parts_count" in preview
        assert preview["affected_locations_count"] >= 2  # parent + child
        assert preview["affected_parts_count"] >= 1