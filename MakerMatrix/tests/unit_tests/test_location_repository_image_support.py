"""
Unit tests for location repository image support functionality.
Tests LocationRepository methods with image_url field.
"""

import pytest
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.tests.unit_tests.test_database import create_test_db
from sqlmodel import Session
import uuid


class TestLocationRepositoryImageSupport:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database engine and repository."""
        self.test_db = create_test_db()
        self.session = self.test_db.get_session()
    
    def test_add_location_with_image_url(self):
        """Test adding a location with image_url via repository."""
        image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Test Location with Image",
            "description": "Repository test location",
            "location_type": "box",
            "image_url": image_url
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        
        assert location is not None
        assert location.name == "Test Location with Image"
        assert location.image_url == image_url
        assert location.location_type == "box"
        
        # Verify it was saved to database
        saved_location = self.session.get(LocationModel, location.id)
        assert saved_location is not None
        assert saved_location.image_url == image_url
    
    def test_add_location_without_image_url(self):
        """Test adding a location without image_url (should default to None)."""
        location_data = {
            "name": "Test Location without Image",
            "description": "No image repository test",
            "location_type": "shelf"
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        
        assert location is not None
        assert location.name == "Test Location without Image"
        assert location.image_url is None
        
        # Verify it was saved to database
        saved_location = self.session.get(LocationModel, location.id)
        assert saved_location is not None
        assert saved_location.image_url is None
    
    def test_update_location_add_image_url(self):
        """Test updating a location to add image_url."""
        # First create location without image
        location_data = {
            "name": "Location to Update",
            "description": "Will add image",
            "location_type": "drawer"
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        assert location.image_url is None
        
        # Update with image_url
        image_url = f"/utility/get_image/{uuid.uuid4()}.png"
        update_data = {"image_url": image_url}
        
        updated_location = LocationRepository.update_location(self.session, location.id, update_data)
        
        assert updated_location is not None
        assert updated_location.image_url == image_url
        assert updated_location.name == "Location to Update"  # Other fields unchanged
        
        # Verify in database
        saved_location = self.session.get(LocationModel, location.id)
        assert saved_location.image_url == image_url
    
    def test_update_location_change_image_url(self):
        """Test updating a location to change existing image_url."""
        # Create location with initial image
        initial_image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Location with Image",
            "description": "Has initial image",
            "location_type": "cabinet",
            "image_url": initial_image_url
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        assert location.image_url == initial_image_url
        
        # Update with new image_url
        new_image_url = f"/utility/get_image/{uuid.uuid4()}.gif"
        update_data = {"image_url": new_image_url}
        
        updated_location = LocationRepository.update_location(self.session, location.id, update_data)
        
        assert updated_location is not None
        assert updated_location.image_url == new_image_url
        assert updated_location.image_url != initial_image_url
        
        # Verify in database
        saved_location = self.session.get(LocationModel, location.id)
        assert saved_location.image_url == new_image_url
    
    def test_update_location_remove_image_url(self):
        """Test updating a location to remove image_url (set to None)."""
        # Create location with image
        image_url = f"/utility/get_image/{uuid.uuid4()}.webp"
        location_data = {
            "name": "Location to Remove Image",
            "description": "Image will be removed",
            "location_type": "bin",
            "image_url": image_url
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        assert location.image_url == image_url
        
        # Update to remove image (set to None)
        update_data = {"image_url": None}
        
        updated_location = LocationRepository.update_location(self.session, location.id, update_data)
        
        assert updated_location is not None
        assert updated_location.image_url is None
        
        # Verify in database
        saved_location = self.session.get(LocationModel, location.id)
        assert saved_location.image_url is None
    
    def test_get_location_includes_image_url(self):
        """Test that getting a location includes image_url in the result."""
        # Create location with image
        image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Location for Get Test",
            "description": "Testing get with image",
            "location_type": "rack",
            "image_url": image_url
        }
        
        created_location = LocationRepository.add_location(self.session, location_data)
        
        # Get location by ID
        query = LocationQueryModel(id=created_location.id)
        retrieved_location = LocationRepository.get_location(self.session, query)
        
        assert retrieved_location is not None
        assert retrieved_location.image_url == image_url
        assert retrieved_location.name == "Location for Get Test"
        
        # Get location by name
        query_by_name = LocationQueryModel(name="Location for Get Test")
        retrieved_by_name = LocationRepository.get_location(self.session, query_by_name)
        
        assert retrieved_by_name is not None
        assert retrieved_by_name.image_url == image_url
    
    def test_get_all_locations_includes_image_urls(self):
        """Test that getting all locations includes image_urls."""
        # Create test locations with and without images
        locations_data = [
            {
                "name": "Location 1 with Image",
                "description": "Has image",
                "location_type": "box",
                "image_url": f"/utility/get_image/{uuid.uuid4()}.jpg"
            },
            {
                "name": "Location 2 without Image",
                "description": "No image",
                "location_type": "drawer"
            },
            {
                "name": "Location 3 with Image",
                "description": "Also has image",
                "location_type": "shelf",
                "image_url": f"/utility/get_image/{uuid.uuid4()}.png"
            }
        ]
        
        created_locations = []
        for data in locations_data:
            location = LocationRepository.add_location(self.session, data)
            created_locations.append(location)
        
        # Get all locations
        all_locations = LocationRepository.get_all_locations(self.session)
        
        # Find our test locations
        test_locations = []
        for location in all_locations:
            if location.name.startswith("Location ") and "with Image" in location.name or "without Image" in location.name:
                test_locations.append(location)
        
        assert len(test_locations) >= 3
        
        # Check that image_urls are preserved
        location_1 = next(loc for loc in test_locations if loc.name == "Location 1 with Image")
        location_2 = next(loc for loc in test_locations if loc.name == "Location 2 without Image")
        location_3 = next(loc for loc in test_locations if loc.name == "Location 3 with Image")
        
        assert location_1.image_url is not None
        assert location_1.image_url.startswith("/utility/get_image/")
        
        assert location_2.image_url is None
        
        assert location_3.image_url is not None
        assert location_3.image_url.startswith("/utility/get_image/")
    
    def test_location_to_dict_includes_image_url(self):
        """Test that LocationModel.to_dict() includes image_url."""
        # Create location with image
        image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Location for to_dict Test",
            "description": "Testing serialization",
            "location_type": "cabinet",
            "image_url": image_url
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        
        # Test to_dict method
        location_dict = location.to_dict()
        
        assert "image_url" in location_dict
        assert location_dict["image_url"] == image_url
        assert location_dict["name"] == "Location for to_dict Test"
        assert location_dict["id"] == location.id
    
    def test_location_to_dict_with_null_image_url(self):
        """Test that LocationModel.to_dict() handles None image_url."""
        # Create location without image
        location_data = {
            "name": "Location without Image for to_dict",
            "description": "Testing serialization with null image",
            "location_type": "drawer"
        }
        
        location = LocationRepository.add_location(self.session, location_data)
        
        # Test to_dict method
        location_dict = location.to_dict()
        
        assert "image_url" in location_dict
        assert location_dict["image_url"] is None
        assert location_dict["name"] == "Location without Image for to_dict"
    
    def test_hierarchical_locations_with_images(self):
        """Test that parent-child relationships preserve image_urls."""
        # Create parent with image
        parent_image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        parent_data = {
            "name": "Parent Location",
            "description": "Parent with image",
            "location_type": "warehouse",
            "image_url": parent_image_url
        }
        
        parent_location = LocationRepository.add_location(self.session, parent_data)
        
        # Create child with different image
        child_image_url = f"/utility/get_image/{uuid.uuid4()}.png"
        child_data = {
            "name": "Child Location",
            "description": "Child with image",
            "location_type": "room",
            "parent_id": parent_location.id,
            "image_url": child_image_url
        }
        
        child_location = LocationRepository.add_location(self.session, child_data)
        
        # Get parent location details (should include children)
        parent_details = LocationRepository.get_location_details(self.session, parent_location.id)
        
        assert parent_details is not None
        assert parent_details["image_url"] == parent_image_url
        
        # Verify child has correct image_url
        assert len(parent_details["children"]) >= 1
        child_in_hierarchy = next(child for child in parent_details["children"] if child["id"] == child_location.id)
        assert child_in_hierarchy["image_url"] == child_image_url


if __name__ == "__main__":
    pytest.main([__file__])