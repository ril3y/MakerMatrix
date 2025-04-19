import pytest
from fastapi.testclient import TestClient

# Utility: login as admin and get token
def get_admin_token(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def test_get_all_users_admin():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = get_admin_token(client)
        response = client.get(
            "/users/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert any(user["username"] == "admin" for user in data["data"])

def test_get_all_users_non_admin():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        # Register a non-admin user
        client.post("/users/register", json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpass",
            "roles": ["user"]
        })
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        response = client.get(
            "/users/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "Admin privileges required" in response.text
