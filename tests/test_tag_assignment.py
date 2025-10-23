"""
Tests for Tag Assignment operations to parts and tools
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set JWT secret for testing
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing"

from MakerMatrix.main import app
from MakerMatrix.models.models import engine
from MakerMatrix.models.tag_models import TagModel, PartTagLink, ToolTagLink
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.tool_models import ToolModel


class TestTagAssignment:
    """Test suite for tag assignment operations."""

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
            # Delete all test data
            # Delete tag links first
            session.exec(select(PartTagLink)).all()
            for link in session.exec(select(PartTagLink)).all():
                session.delete(link)
            for link in session.exec(select(ToolTagLink)).all():
                session.delete(link)

            # Delete test tags
            test_tags = session.exec(select(TagModel)).all()
            for tag in test_tags:
                if any(keyword in tag.name.lower() for keyword in ['tag', 'filter', 'bulk', 'remove', 'orphan', 'assoc', 'multi', 'urgent', 'review', 'prototype']):
                    session.delete(tag)

            # Delete test parts
            test_parts = session.exec(
                select(PartModel).where(PartModel.part_name.like("%Test%"))
            ).all()
            for part in test_parts:
                session.delete(part)

            # Delete test tools
            test_tools = session.exec(
                select(ToolModel).where(ToolModel.tool_name.like("%Test%"))
            ).all()
            for tool in test_tools:
                session.delete(tool)

            session.commit()

        yield

        # Clean up after test (same as before)
        with Session(engine) as session:
            # Delete tag links first
            for link in session.exec(select(PartTagLink)).all():
                session.delete(link)
            for link in session.exec(select(ToolTagLink)).all():
                session.delete(link)

            # Delete test tags
            test_tags = session.exec(select(TagModel)).all()
            for tag in test_tags:
                if any(keyword in tag.name.lower() for keyword in ['tag', 'filter', 'bulk', 'remove', 'orphan', 'assoc', 'multi', 'urgent', 'review', 'prototype']):
                    session.delete(tag)

            # Delete test parts
            test_parts = session.exec(
                select(PartModel).where(PartModel.part_name.like("%Test%"))
            ).all()
            for part in test_parts:
                session.delete(part)

            # Delete test tools
            test_tools = session.exec(
                select(ToolModel).where(ToolModel.tool_name.like("%Test%"))
            ).all()
            for tool in test_tools:
                session.delete(tool)

            session.commit()

    def test_assign_tag_to_part(self, auth_headers):
        """Test assigning a tag to a part"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "part-tag", "color": "#FF5733"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create a part
            part_data = {
                "part_name": "Test Resistor",
                "part_number": "R-001",
                "description": "10k Ohm resistor",
                "quantity": 100
            }
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Assign tag to part
            response = client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "success"

            # Verify assignment by getting part tags
            response = client.get(f"/api/tags/parts/{part_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 1
            assert tags[0]["name"] == "part-tag"

    def test_assign_duplicate_tag_to_part(self, auth_headers):
        """Test that assigning the same tag twice returns success without duplication"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "dup-part-tag"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create a part
            part_data = {"part_name": "Dup Test Part", "part_number": "DTP-001"}
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Assign tag to part twice
            response1 = client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
            assert response1.status_code == 200

            response2 = client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
            assert response2.status_code == 200  # Should succeed with message

            # Verify only one assignment exists
            response = client.get(f"/api/tags/parts/{part_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 1

    def test_remove_tag_from_part(self, auth_headers):
        """Test removing a tag from a part"""
        with TestClient(app) as client:
            # Create and assign a tag
            tag_data = {"name": "remove-part-tag"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            part_data = {"part_name": "Remove Test Part", "part_number": "RTP-001"}
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Assign tag
            client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)

            # Remove tag
            response = client.delete(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
            assert response.status_code == 200

            # Verify removal
            response = client.get(f"/api/tags/parts/{part_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 0

    def test_assign_tag_to_tool(self, auth_headers):
        """Test assigning a tag to a tool"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "tool-tag", "color": "#33FF57"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create a tool
            tool_data = {
                "tool_name": "Test Screwdriver",
                "tool_number": "T-001",
                "description": "Phillips screwdriver",
                "quantity": 1
            }
            tool_response = client.post("/api/tools/", json=tool_data, headers=auth_headers)
            assert tool_response.status_code == 200
            tool_id = tool_response.json()["data"]["id"]

            # Assign tag to tool
            response = client.post(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["status"] == "success"

            # Verify assignment by getting tool tags
            response = client.get(f"/api/tags/tools/{tool_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 1
            assert tags[0]["name"] == "tool-tag"

    def test_remove_tag_from_tool(self, auth_headers):
        """Test removing a tag from a tool"""
        with TestClient(app) as client:
            # Create and assign a tag
            tag_data = {"name": "remove-tool-tag"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            tool_data = {"tool_name": "Remove Test Tool", "tool_number": "RTT-001"}
            tool_response = client.post("/api/tools/", json=tool_data, headers=auth_headers)
            assert tool_response.status_code == 200
            tool_id = tool_response.json()["data"]["id"]

            # Assign tag
            client.post(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)

            # Remove tag
            response = client.delete(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)
            assert response.status_code == 200

            # Verify removal
            response = client.get(f"/api/tags/tools/{tool_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 0

    def test_get_parts_by_tag(self, auth_headers):
        """Test getting all parts with a specific tag"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "parts-filter", "color": "#5733FF"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create multiple parts and assign tag
            part_ids = []
            for i in range(3):
                part_data = {"part_name": f"Tagged Test Part {i}", "part_number": f"TTP-{i:03d}"}
                part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
                assert part_response.status_code == 200
                part_id = part_response.json()["data"]["id"]
                part_ids.append(part_id)

                # Assign tag
                client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)

            # Get parts by tag
            response = client.get(f"/api/tags/{tag_id}/parts", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()["data"]
            assert data["total"] == 3
            assert len(data["parts"]) == 3
            assert data["tag"]["name"] == "parts-filter"

    def test_get_tools_by_tag(self, auth_headers):
        """Test getting all tools with a specific tag"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "tools-filter", "color": "#FF3357"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create multiple tools and assign tag
            tool_ids = []
            for i in range(2):
                tool_data = {"tool_name": f"Tagged Test Tool {i}", "tool_number": f"TTT-{i:03d}"}
                tool_response = client.post("/api/tools/", json=tool_data, headers=auth_headers)
                assert tool_response.status_code == 200
                tool_id = tool_response.json()["data"]["id"]
                tool_ids.append(tool_id)

                # Assign tag
                client.post(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)

            # Get tools by tag
            response = client.get(f"/api/tags/{tag_id}/tools", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()["data"]
            assert data["total"] == 2
            assert len(data["tools"]) == 2
            assert data["tag"]["name"] == "tools-filter"

    def test_bulk_tag_operation_add_to_parts(self, auth_headers):
        """Test bulk adding tags to multiple parts"""
        with TestClient(app) as client:
            # Create tags
            tag_ids = []
            for i in range(2):
                tag_data = {"name": f"bulk-tag-{i}"}
                tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
                assert tag_response.status_code == 200
                tag_ids.append(tag_response.json()["data"]["id"])

            # Create parts
            part_ids = []
            for i in range(3):
                part_data = {"part_name": f"Bulk Test Part {i}", "part_number": f"BTP-{i:03d}"}
                part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
                assert part_response.status_code == 200
                part_ids.append(part_response.json()["data"]["id"])

            # Bulk add tags to parts
            bulk_data = {
                "item_ids": part_ids,
                "tag_ids": tag_ids,
                "operation": "add",
                "item_type": "part"
            }
            response = client.post("/api/tags/bulk", json=bulk_data, headers=auth_headers)
            assert response.status_code == 200

            result = response.json()["data"]
            assert len(result["successful"]) > 0

            # Verify tags were added to first part
            response = client.get(f"/api/tags/parts/{part_ids[0]}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 2

    def test_bulk_tag_operation_remove_from_tools(self, auth_headers):
        """Test bulk removing tags from multiple tools"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "bulk-remove-tag"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create tools and assign tag
            tool_ids = []
            for i in range(2):
                tool_data = {"tool_name": f"Bulk Test Tool {i}", "tool_number": f"BTT-{i:03d}"}
                tool_response = client.post("/api/tools/", json=tool_data, headers=auth_headers)
                assert tool_response.status_code == 200
                tool_id = tool_response.json()["data"]["id"]
                tool_ids.append(tool_id)

                # Assign tag
                client.post(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)

            # Bulk remove tag from tools
            bulk_data = {
                "item_ids": tool_ids,
                "tag_ids": [tag_id],
                "operation": "remove",
                "item_type": "tool"
            }
            response = client.post("/api/tags/bulk", json=bulk_data, headers=auth_headers)
            assert response.status_code == 200

            result = response.json()["data"]
            assert len(result["successful"]) > 0

            # Verify tags were removed
            response = client.get(f"/api/tags/tools/{tool_ids[0]}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 0

    def test_assign_nonexistent_tag_fails(self, auth_headers):
        """Test that assigning a non-existent tag fails"""
        with TestClient(app) as client:
            # Create a part
            part_data = {"part_name": "Test Part", "part_number": "TP-404"}
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Try to assign non-existent tag
            response = client.post(f"/api/tags/nonexistent-tag/parts/{part_id}", headers=auth_headers)
            assert response.status_code == 404  # Not found
            assert "not found" in response.json()["message"].lower()

    def test_assign_tag_to_nonexistent_part_fails(self, auth_headers):
        """Test that assigning a tag to non-existent part fails"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "orphan-tag"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Try to assign to non-existent part
            response = client.post(f"/api/tags/{tag_id}/parts/nonexistent-part", headers=auth_headers)
            assert response.status_code == 404  # Not found
            assert "not found" in response.json()["message"].lower()

    def test_delete_tag_removes_associations(self, auth_headers):
        """Test that deleting a tag removes all associations but doesn't delete parts/tools"""
        with TestClient(app) as client:
            # Create a tag
            tag_data = {"name": "delete-assoc-tag", "color": "#ABCDEF"}
            tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
            assert tag_response.status_code == 200
            tag_id = tag_response.json()["data"]["id"]

            # Create a part and tool
            part_data = {"part_name": "Assoc Test Part", "part_number": "ATP-001"}
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            part_id = part_response.json()["data"]["id"]

            tool_data = {"tool_name": "Assoc Test Tool", "tool_number": "ATT-001"}
            tool_response = client.post("/api/tools/", json=tool_data, headers=auth_headers)
            tool_id = tool_response.json()["data"]["id"]

            # Assign tag to both
            client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
            client.post(f"/api/tags/{tag_id}/tools/{tool_id}", headers=auth_headers)

            # Delete the tag
            response = client.delete(f"/api/tags/{tag_id}", headers=auth_headers)
            assert response.status_code == 200

            # Verify part still exists but has no tags
            part_response = client.get(f"/api/parts/get_part?part_id={part_id}", headers=auth_headers)
            assert part_response.status_code == 200

            tags_response = client.get(f"/api/tags/parts/{part_id}/tags", headers=auth_headers)
            assert tags_response.status_code == 200
            assert len(tags_response.json()["data"]) == 0

            # Verify tool still exists but has no tags
            tool_response = client.get(f"/api/tools/{tool_id}", headers=auth_headers)
            assert tool_response.status_code == 200

            tags_response = client.get(f"/api/tags/tools/{tool_id}/tags", headers=auth_headers)
            assert tags_response.status_code == 200
            assert len(tags_response.json()["data"]) == 0

    def test_multiple_tags_per_item(self, auth_headers):
        """Test that parts and tools can have multiple tags"""
        with TestClient(app) as client:
            # Create multiple tags
            tag_names = ["urgent", "review", "prototype"]
            tag_ids = []
            for name in tag_names:
                tag_data = {"name": name, "color": "#FF0000"}
                tag_response = client.post("/api/tags", json=tag_data, headers=auth_headers)
                assert tag_response.status_code == 200
                tag_ids.append(tag_response.json()["data"]["id"])

            # Create a part
            part_data = {"part_name": "Multi-tag Test Part", "part_number": "MTP-001"}
            part_response = client.post("/api/parts/add_part", json=part_data, headers=auth_headers)
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Assign all tags to the part
            for tag_id in tag_ids:
                response = client.post(f"/api/tags/{tag_id}/parts/{part_id}", headers=auth_headers)
                assert response.status_code == 200

            # Verify all tags are assigned
            response = client.get(f"/api/tags/parts/{part_id}/tags", headers=auth_headers)
            assert response.status_code == 200
            tags = response.json()["data"]
            assert len(tags) == 3

            assigned_names = [tag["name"] for tag in tags]
            for name in tag_names:
                assert name in assigned_names


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])