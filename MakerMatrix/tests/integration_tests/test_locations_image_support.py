"""
Integration tests for location image support functionality.
Tests creation and update of locations with image_url field.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select
from MakerMatrix.main import app
from MakerMatrix.models.models import LocationModel, engine
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.database.db import create_db_and_tables
import json
import uuid


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Cleanup after test
    SQLModel.metadata.drop_all(engine)


class TestLocationImageSupport:
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        self.client = TestClient(app)
        
        # Get auth token for requests
        login_response = self.client.post("/auth/login", data={
            "username": "admin",
            "password": "Admin123!"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_create_location_with_image_url(self):
        """Test creating a location with an image_url."""
        # Sample image URL (simulating uploaded image)
        image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        
        location_data = {
            "name": "Yellow Toolbox with Image",
            "description": "A bright yellow metal toolbox",
            "location_type": "box",
            "image_url": image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Location added successfully" in data["message"]
        
        # Verify location was created with image_url
        location_id = data["data"]["id"]
        with Session(engine) as session:
            location = session.get(LocationModel, location_id)
            assert location is not None
            assert location.name == "Yellow Toolbox with Image"
            assert location.image_url == image_url
            assert location.location_type == "box"
    
    def test_create_location_without_image_url(self):
        """Test creating a location without an image_url (should be None)."""
        location_data = {
            "name": "Plain Location",
            "description": "Location without image",
            "location_type": "shelf"
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify location was created with None image_url
        location_id = data["data"]["id"]
        with Session(engine) as session:
            location = session.get(LocationModel, location_id)
            assert location is not None
            assert location.name == "Plain Location"
            assert location.image_url is None
    
    def test_update_location_add_image_url(self):
        """Test updating an existing location to add an image_url."""
        # First create a location without image
        location_data = {
            "name": "Location to Update",
            "description": "Will add image later",
            "location_type": "drawer"
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        location_id = response.json()["data"]["id"]
        
        # Now update with image_url
        image_url = f"/utility/get_image/{uuid.uuid4()}.png"
        update_data = {
            "image_url": image_url
        }
        
        response = self.client.put(
            f"/locations/update_location/{location_id}",
            json=update_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify image_url was added
        with Session(engine) as session:
            location = session.get(LocationModel, location_id)
            assert location is not None
            assert location.image_url == image_url
            assert location.name == "Location to Update"  # Other fields unchanged
    
    def test_update_location_change_image_url(self):
        """Test updating a location to change its image_url."""
        # Create location with initial image
        initial_image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Location with Initial Image",
            "description": "Has an image that will be changed",
            "location_type": "cabinet",
            "image_url": initial_image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        location_id = response.json()["data"]["id"]
        
        # Update with new image_url
        new_image_url = f"/utility/get_image/{uuid.uuid4()}.gif"
        update_data = {
            "image_url": new_image_url
        }
        
        response = self.client.put(
            f"/locations/update_location/{location_id}",
            json=update_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        # Verify image_url was changed
        with Session(engine) as session:
            location = session.get(LocationModel, location_id)
            assert location is not None
            assert location.image_url == new_image_url
            assert location.image_url != initial_image_url
    
    def test_update_location_remove_image_url(self):
        """Test updating a location to remove its image_url (set to None)."""
        # Create location with image
        image_url = f"/utility/get_image/{uuid.uuid4()}.webp"
        location_data = {
            "name": "Location to Remove Image",
            "description": "Image will be removed",
            "location_type": "bin",
            "image_url": image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        location_id = response.json()["data"]["id"]
        
        # Update to remove image (set to None/null)
        update_data = {
            "image_url": None
        }
        
        response = self.client.put(
            f"/locations/update_location/{location_id}",
            json=update_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        
        # Verify image_url was removed
        with Session(engine) as session:
            location = session.get(LocationModel, location_id)
            assert location is not None
            assert location.image_url is None
    
    def test_get_location_includes_image_url(self):
        """Test that retrieving a location includes the image_url in response."""
        # Create location with image
        image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        location_data = {
            "name": "Location for Retrieval Test",
            "description": "Testing image_url in response",
            "location_type": "rack",
            "image_url": image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=location_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        location_id = response.json()["data"]["id"]
        
        # Get location by ID
        response = self.client.get(
            f"/locations/get_location?location_id={location_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        location_data = data["data"]
        assert location_data["id"] == location_id
        assert location_data["image_url"] == image_url
        assert location_data["name"] == "Location for Retrieval Test"
    
    def test_get_all_locations_includes_image_urls(self):
        """Test that getting all locations includes image_url for each location."""
        # Create multiple locations, some with images, some without
        locations_to_create = [
            {
                "name": "Location A with Image",
                "description": "Has image",
                "location_type": "box",
                "image_url": f"/utility/get_image/{uuid.uuid4()}.jpg"
            },
            {
                "name": "Location B without Image",
                "description": "No image",
                "location_type": "drawer"
                # No image_url field
            },
            {
                "name": "Location C with Image",
                "description": "Also has image", 
                "location_type": "shelf",
                "image_url": f"/utility/get_image/{uuid.uuid4()}.png"
            }
        ]
        
        created_ids = []
        for location_data in locations_to_create:
            response = self.client.post(
                "/locations/add_location",
                json=location_data,
                headers=self.headers
            )
            assert response.status_code == 200
            created_ids.append(response.json()["data"]["id"])
        
        # Get all locations
        response = self.client.get(
            "/locations/get_all_locations",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        locations = data["data"]
        
        # Find our created locations in the response
        found_locations = []
        for location in locations:
            if location["id"] in created_ids:
                found_locations.append(location)
        
        assert len(found_locations) == 3
        
        # Verify image_url presence/absence
        location_a = next(loc for loc in found_locations if loc["name"] == "Location A with Image")
        location_b = next(loc for loc in found_locations if loc["name"] == "Location B without Image")
        location_c = next(loc for loc in found_locations if loc["name"] == "Location C with Image")
        
        assert location_a["image_url"] is not None
        assert location_a["image_url"].startswith("/utility/get_image/")
        
        assert location_b["image_url"] is None
        
        assert location_c["image_url"] is not None
        assert location_c["image_url"].startswith("/utility/get_image/")
    
    def test_location_hierarchy_with_images(self):
        """Test that hierarchical location data includes image_url for parent and children."""
        # Create parent location with image
        parent_image_url = f"/utility/get_image/{uuid.uuid4()}.jpg"
        parent_data = {
            "name": "Parent Warehouse",
            "description": "Main warehouse with image",
            "location_type": "warehouse", 
            "image_url": parent_image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=parent_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        parent_id = response.json()["data"]["id"]
        
        # Create child location with image
        child_image_url = f"/utility/get_image/{uuid.uuid4()}.png"
        child_data = {
            "name": "Child Room",
            "description": "Room inside warehouse with image",
            "location_type": "room",
            "parent_id": parent_id,
            "image_url": child_image_url
        }
        
        response = self.client.post(
            "/locations/add_location",
            json=child_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        child_id = response.json()["data"]["id"]
        
        # Get location details for parent (includes children)
        response = self.client.get(
            f"/locations/get_location_details/{parent_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify parent has image_url
        parent_location = data["data"]["location"]
        assert parent_location["image_url"] == parent_image_url
        
        # Verify children include image_url
        children = data["data"]["children"]
        assert len(children) >= 1
        
        child_location = next(child for child in children if child["id"] == child_id)
        assert child_location["image_url"] == child_image_url


if __name__ == "__main__":
    pytest.main([__file__])