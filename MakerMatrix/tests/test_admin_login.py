import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

client = TestClient(app)


def test_admin_login():
    """Test that the admin user can log in."""
    response = client.post(
        "/auth/login",
        data={"username": DEFAULT_ADMIN_USERNAME, "password": DEFAULT_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    
    # Get the token
    token = response_data["access_token"]
    
    # Test that the token works for a protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/parts/get_all_parts", headers=headers)
    assert response.status_code != 401  # Should not be unauthorized 