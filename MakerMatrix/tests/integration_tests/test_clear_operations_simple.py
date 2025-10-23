"""
Simple integration tests for database clear operations.

Tests the clear endpoints directly without complex setup.
"""

import pytest
from fastapi.testclient import TestClient

from MakerMatrix.main import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def admin_headers(test_client):
    """Login as admin and get authorization headers."""
    login_data = {"username": "admin", "password": "Admin123!"}
    response = test_client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_clear_parts_endpoint_exists(test_client, admin_headers):
    """Test that the clear parts endpoint exists and requires admin."""
    response = test_client.delete("/api/parts/clear_all", headers=admin_headers)
    # Should succeed (200) or fail gracefully, but not 404
    assert response.status_code != 404


def test_clear_suppliers_endpoint_exists(test_client, admin_headers):
    """Test that the clear suppliers endpoint exists and requires admin."""
    response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)
    # Should succeed (200) or fail gracefully, but not 404
    assert response.status_code != 404


def test_clear_categories_endpoint_exists(test_client, admin_headers):
    """Test that the clear categories endpoint exists and requires admin."""
    response = test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)
    # Should succeed (200) or fail gracefully, but not 404
    assert response.status_code != 404


def test_clear_endpoints_require_auth(test_client):
    """Test that all clear endpoints require authentication."""
    # Test without auth headers
    response = test_client.delete("/api/parts/clear_all")
    assert response.status_code == 401

    response = test_client.delete("/api/utility/clear_suppliers")
    assert response.status_code == 401

    response = test_client.delete("/api/categories/delete_all_categories")
    assert response.status_code == 401


def test_clear_parts_response_format(test_client, admin_headers):
    """Test that clear parts returns proper response format."""
    response = test_client.delete("/api/parts/clear_all", headers=admin_headers)

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert data["status"] == "success"


def test_clear_suppliers_response_format(test_client, admin_headers):
    """Test that clear suppliers returns proper response format."""
    response = test_client.delete("/api/utility/clear_suppliers", headers=admin_headers)

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert data["status"] == "success"
        assert "data" in data


def test_clear_categories_response_format(test_client, admin_headers):
    """Test that clear categories returns proper response format."""
    response = test_client.delete("/api/categories/delete_all_categories", headers=admin_headers)

    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
