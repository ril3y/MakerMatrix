"""
Test that location updates preserve existing images.

This test suite verifies that when a location is updated, images are not lost
if they are not included in the update request.
"""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlmodel import Session, select

# Import test fixtures and utilities
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from MakerMatrix.main import app
from MakerMatrix.models.models import engine, LocationModel
from MakerMatrix.database.db import get_session


class TestLocationImagePersistence:
    """Test suite for location image persistence during updates."""

    API_KEY = os.getenv("MAKERMATRIX_API_KEY", "")  # Set in .env

    @pytest.fixture
    def auth_headers(self):
        """Provide authentication headers for API requests."""
        return {"X-API-Key": self.API_KEY}

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up test data before and after each test."""
        # Clean up before test
        with Session(engine) as session:
            # Delete all test locations
            test_locations = session.exec(select(LocationModel).where(LocationModel.name.like("TEST_IMAGE_%"))).all()
            for location in test_locations:
                session.delete(location)
            session.commit()

        yield

        # Clean up after test
        with Session(engine) as session:
            # Delete test locations
            test_locations = session.exec(select(LocationModel).where(LocationModel.name.like("TEST_IMAGE_%"))).all()
            for location in test_locations:
                session.delete(location)
            session.commit()

    def test_location_update_preserves_image(self, auth_headers):
        """Test that updating a location name preserves the existing image."""
        with TestClient(app) as client:
            # Step 1: Create a test location with an image
            location_response = client.post(
                "/api/locations/add_location",
                json={
                    "name": "TEST_IMAGE_Storage_A",
                    "description": "Test storage location with image",
                    "image_url": "https://example.com/images/storage-a.jpg",
                },
                headers=auth_headers,
            )
            assert location_response.status_code == 200
            location_data = location_response.json()
            location_id = location_data["data"]["id"]
            original_image_url = location_data["data"]["image_url"]

            assert original_image_url == "https://example.com/images/storage-a.jpg"
            print(f"Created location with image: {original_image_url}")

            # Step 2: Update only the location name (not the image)
            update_response = client.put(
                f"/api/locations/update_location/{location_id}",
                json={"name": "TEST_IMAGE_Storage_B_Renamed"},
                headers=auth_headers,
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the image is still present
            assert updated_data["data"]["name"] == "TEST_IMAGE_Storage_B_Renamed"
            assert (
                updated_data["data"]["image_url"] == original_image_url
            ), f"Image was lost! Expected '{original_image_url}', got '{updated_data['data'].get('image_url')}'"

            print(f"✓ Image preserved after name update: {updated_data['data']['image_url']}")

    def test_location_update_can_clear_image(self, auth_headers):
        """Test that explicitly setting image_url to None clears the image."""
        with TestClient(app) as client:
            # Step 1: Create a test location with an image
            location_response = client.post(
                "/api/locations/add_location",
                json={
                    "name": "TEST_IMAGE_Storage_C",
                    "description": "Test location",
                    "image_url": "https://example.com/images/storage-c.jpg",
                },
                headers=auth_headers,
            )
            assert location_response.status_code == 200
            location_id = location_response.json()["data"]["id"]

            # Step 2: Explicitly clear the image by setting it to null
            update_response = client.put(
                f"/api/locations/update_location/{location_id}", json={"image_url": None}, headers=auth_headers
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the image was cleared
            assert updated_data["data"]["image_url"] is None, "Image should be cleared when explicitly set to None"

            print("✓ Image successfully cleared when explicitly set to None")

    def test_location_update_preserves_emoji(self, auth_headers):
        """Test that updating a location preserves the existing emoji."""
        with TestClient(app) as client:
            # Step 1: Create a test location with an emoji
            location_response = client.post(
                "/api/locations/add_location",
                json={"name": "TEST_IMAGE_Storage_D", "description": "Test location with emoji", "emoji": "📦"},
                headers=auth_headers,
            )
            assert location_response.status_code == 200
            location_data = location_response.json()
            location_id = location_data["data"]["id"]
            original_emoji = location_data["data"]["emoji"]

            assert original_emoji == "📦"
            print(f"Created location with emoji: {original_emoji}")

            # Step 2: Update only the description (not the emoji)
            update_response = client.put(
                f"/api/locations/update_location/{location_id}",
                json={"description": "Updated description"},
                headers=auth_headers,
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the emoji is still present
            assert updated_data["data"]["description"] == "Updated description"
            assert (
                updated_data["data"]["emoji"] == original_emoji
            ), f"Emoji was lost! Expected '{original_emoji}', got '{updated_data['data'].get('emoji')}'"

            print(f"✓ Emoji preserved after description update: {updated_data['data']['emoji']}")

    def test_database_level_image_persistence(self, auth_headers):
        """Test image persistence at the database level."""
        with TestClient(app) as client:
            # Step 1: Create location with image
            location_response = client.post(
                "/api/locations/add_location",
                json={
                    "name": "TEST_IMAGE_Storage_E",
                    "description": "DB test location",
                    "image_url": "https://example.com/images/storage-e.jpg",
                    "emoji": "🏢",
                },
                headers=auth_headers,
            )
            assert location_response.status_code == 200
            location_id = location_response.json()["data"]["id"]

            # Step 2: Check database state before update
            with Session(engine) as session:
                location_before = session.get(LocationModel, location_id)
                assert location_before.image_url == "https://example.com/images/storage-e.jpg"
                assert location_before.emoji == "🏢"
                assert location_before.name == "TEST_IMAGE_Storage_E"

            # Step 3: Update location name via API
            update_response = client.put(
                f"/api/locations/update_location/{location_id}",
                json={"name": "TEST_IMAGE_Storage_E_Renamed"},
                headers=auth_headers,
            )
            assert update_response.status_code == 200

            # Step 4: Check database state after update
            with Session(engine) as session:
                location_after = session.get(LocationModel, location_id)
                assert location_after.name == "TEST_IMAGE_Storage_E_Renamed"
                assert (
                    location_after.image_url == "https://example.com/images/storage-e.jpg"
                ), "Image URL was lost in database!"
                assert location_after.emoji == "🏢", "Emoji was lost in database!"

            print("✓ Database-level verification passed: image and emoji preserved")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
