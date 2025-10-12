"""
Tests for Tag CRUD operations
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set JWT secret for testing
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing"

from MakerMatrix.main import app
from MakerMatrix.models.models import engine
from MakerMatrix.models.tag_models import TagModel


class TestTagCRUD:
    """Test suite for tag CRUD operations."""

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
            # Delete all test tags (be careful with patterns to avoid deleting real data)
            test_tags = session.exec(
                select(TagModel)
            ).all()
            for tag in test_tags:
                # Only delete tags created by our tests
                if any(keyword in tag.name.lower() for keyword in ['test', 'urgent', 'duplicate', 'case', 'list', 'frontend', 'backend', 'database', 'active', 'inactive', 'update', 'old', 'new', 'tag1', 'tag2', 'delete', 'system', 'stat']):
                    session.delete(tag)
            session.commit()

        yield

        # Clean up after test
        with Session(engine) as session:
            test_tags = session.exec(
                select(TagModel)
            ).all()
            for tag in test_tags:
                # Only delete tags created by our tests
                if any(keyword in tag.name.lower() for keyword in ['test', 'urgent', 'duplicate', 'case', 'list', 'frontend', 'backend', 'database', 'active', 'inactive', 'update', 'old', 'new', 'tag1', 'tag2', 'delete', 'system', 'stat']):
                    session.delete(tag)
            session.commit()

    def test_create_tag(self, auth_headers):
        """Test creating a new tag"""
        with TestClient(app) as client:
            tag_data = {
                "name": "urgent",
                "color": "#FF0000",
                "description": "Urgent items that need immediate attention",
                "icon": "⚡",
                "is_system": False
            }

            response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "urgent"
            assert data["data"]["color"] == "#FF0000"
            assert data["data"]["description"] == tag_data["description"]
            assert data["data"]["icon"] == "⚡"
            assert data["data"]["is_system"] is False
            assert data["data"]["usage_count"] == 0

    def test_create_tag_strips_hash(self, auth_headers):
        """Test that creating a tag with # prefix strips it"""
        with TestClient(app) as client:
            tag_data = {
                "name": "#testing",
                "color": "#00FF00",
                "description": "Test tag with hash prefix"
            }

            response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["data"]["name"] == "testing"  # Hash should be stripped

    def test_create_duplicate_tag_fails(self, auth_headers):
        """Test that creating a duplicate tag fails"""
        with TestClient(app) as client:
            tag_data = {
                "name": "duplicate",
                "color": "#0000FF"
            }

            # Create first tag
            response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert response.status_code == 200

            # Try to create duplicate
            response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert response.status_code == 409  # Conflict status for duplicates
            assert "already exists" in response.json()["message"].lower()

    def test_create_tag_case_insensitive(self, auth_headers):
        """Test that tag names are case-insensitive for duplicates"""
        with TestClient(app) as client:
            # Create first tag
            tag_data1 = {"name": "CaseTest", "color": "#123456"}
            response = client.post("/api/tags/", json=tag_data1, headers=auth_headers)
            assert response.status_code == 200

            # Try to create with different case
            tag_data2 = {"name": "casetest", "color": "#654321"}
            response = client.post("/api/tags/", json=tag_data2, headers=auth_headers)
            assert response.status_code == 409  # Conflict status for duplicates
            assert "already exists" in response.json()["message"].lower()

    def test_get_tag_by_id(self, auth_headers):
        """Test getting a tag by ID"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "get-test", "color": "#AABBCC"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200
            tag_id = create_response.json()["data"]["id"]

            # Get the tag
            response = client.get(f"/api/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["id"] == tag_id
            assert data["data"]["name"] == "get-test"
            assert data["data"]["color"] == "#AABBCC"

    def test_get_tag_by_name(self, auth_headers):
        """Test getting a tag by name"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "name-test", "description": "Test by name"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200

            # Get by name
            response = client.get("/api/tags/name/name-test", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["name"] == "name-test"
            assert data["data"]["description"] == "Test by name"

    def test_get_tag_by_name_with_hash(self, auth_headers):
        """Test getting a tag by name with # prefix"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "hash-test"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200

            # Get by name with hash
            response = client.get("/api/tags/name/%23hash-test", headers=auth_headers)  # %23 is URL-encoded #
            assert response.status_code == 200
            assert response.json()["data"]["name"] == "hash-test"

    def test_get_nonexistent_tag(self, auth_headers):
        """Test getting a non-existent tag returns 404"""
        with TestClient(app) as client:
            response = client.get("/api/tags/nonexistent-id-123", headers=auth_headers)
            assert response.status_code == 404
            assert "not found" in response.json()["message"].lower()

    def test_get_all_tags(self, auth_headers):
        """Test getting all tags with pagination"""
        with TestClient(app) as client:
            # Create multiple tags
            for i in range(5):
                tag_data = {"name": f"list-test-{i}", "color": f"#00{i}{i}{i}{i}"}
                response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
                assert response.status_code == 200

            # Get all tags
            response = client.get("/api/tags/", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "tags" in data["data"]
            assert "total" in data["data"]
            assert "page" in data["data"]
            assert data["data"]["page"] == 1

    def test_get_tags_with_search(self, auth_headers):
        """Test searching tags"""
        with TestClient(app) as client:
            # Create tags
            tags = [
                {"name": "frontend", "description": "Frontend related"},
                {"name": "backend", "description": "Backend related"},
                {"name": "database", "description": "Database operations"}
            ]

            for tag_data in tags:
                response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
                assert response.status_code == 200

            # Search for "end"
            response = client.get("/api/tags/?search=end", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert len(data["data"]["tags"]) == 2  # frontend and backend

    def test_get_tags_with_filters(self, auth_headers):
        """Test filtering tags"""
        with TestClient(app) as client:
            # Create active and inactive tags
            active_tag = {"name": "active-tag", "color": "#112233"}
            response = client.post("/api/tags/", json=active_tag, headers=auth_headers)
            assert response.status_code == 200
            active_id = response.json()["data"]["id"]

            # Create a tag and then deactivate it
            inactive_tag = {"name": "inactive-tag", "color": "#445566"}
            response = client.post("/api/tags/", json=inactive_tag, headers=auth_headers)
            assert response.status_code == 200
            inactive_id = response.json()["data"]["id"]

            # Update to inactive
            update_data = {"is_active": False}
            response = client.put(f"/api/tags/{inactive_id}", json=update_data, headers=auth_headers)
            assert response.status_code == 200

            # Filter active only
            response = client.get("/api/tags/?is_active=true", headers=auth_headers)
            assert response.status_code == 200

            active_tags = response.json()["data"]["tags"]
            active_names = [tag["name"] for tag in active_tags]
            assert "active-tag" in active_names
            assert "inactive-tag" not in active_names

    def test_update_tag(self, auth_headers):
        """Test updating a tag"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "update-test", "color": "#000000"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200
            tag_id = create_response.json()["data"]["id"]

            # Update the tag
            update_data = {
                "color": "#FFFFFF",
                "description": "Updated description",
                "icon": "📝"
            }
            response = client.put(f"/api/tags/{tag_id}", json=update_data, headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["color"] == "#FFFFFF"
            assert data["data"]["description"] == "Updated description"
            assert data["data"]["icon"] == "📝"
            assert data["data"]["name"] == "update-test"  # Name unchanged

    def test_update_tag_name(self, auth_headers):
        """Test updating a tag name"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "old-name", "color": "#123123"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200
            tag_id = create_response.json()["data"]["id"]

            # Update the name
            update_data = {"name": "new-name"}
            response = client.put(f"/api/tags/{tag_id}", json=update_data, headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["data"]["name"] == "new-name"

    def test_update_tag_to_duplicate_name_fails(self, auth_headers):
        """Test that updating a tag to a duplicate name fails"""
        with TestClient(app) as client:
            # Create two tags
            tag1_data = {"name": "tag1"}
            tag2_data = {"name": "tag2"}

            response1 = client.post("/api/tags/", json=tag1_data, headers=auth_headers)
            response2 = client.post("/api/tags/", json=tag2_data, headers=auth_headers)
            assert response1.status_code == 200
            assert response2.status_code == 200

            tag2_id = response2.json()["data"]["id"]

            # Try to rename tag2 to tag1
            update_data = {"name": "tag1"}
            response = client.put(f"/api/tags/{tag2_id}", json=update_data, headers=auth_headers)
            assert response.status_code == 409  # Conflict status for duplicates
            assert "already exists" in response.json()["message"].lower()

    def test_delete_tag(self, auth_headers):
        """Test deleting a tag"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "delete-test"}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200
            tag_id = create_response.json()["data"]["id"]

            # Delete the tag
            response = client.delete(f"/api/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 200

            # Verify it's deleted
            response = client.get(f"/api/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 404  # Not found after deletion
            assert "not found" in response.json()["message"].lower()

    def test_delete_system_tag_fails(self, auth_headers):
        """Test that deleting a system tag fails"""
        with TestClient(app) as client:
            # Create a system tag
            tag_data = {"name": "system-tag", "is_system": True}
            create_response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
            assert create_response.status_code == 200
            tag_id = create_response.json()["data"]["id"]

            # Try to delete system tag
            response = client.delete(f"/api/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 400  # Bad Request - can't delete system tag
            assert "system tag" in response.json()["message"].lower()

    def test_delete_nonexistent_tag(self, auth_headers):
        """Test deleting a non-existent tag returns appropriate error"""
        with TestClient(app) as client:
            response = client.delete("/api/tags/nonexistent-id", headers=auth_headers)
            assert response.status_code == 404  # Not found
            assert "not found" in response.json()["message"].lower()

    def test_tag_statistics(self, auth_headers):
        """Test getting tag statistics"""
        with TestClient(app) as client:
            # Create some tags
            for i in range(3):
                tag_data = {"name": f"stat-test-{i}", "is_system": i == 0}
                response = client.post("/api/tags/", json=tag_data, headers=auth_headers)
                assert response.status_code == 200

            # Get statistics
            response = client.get("/api/tags/statistics", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            stats = data["data"]

            assert "total_tags" in stats
            assert "active_tags" in stats
            assert "system_tags" in stats
            assert "user_tags" in stats
            assert "unused_tags" in stats
            assert "most_used_tags" in stats
            assert "recently_used_tags" in stats


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])