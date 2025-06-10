import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app

def test_users_all_route_available():
    with TestClient(app) as client:
        # Log in as admin
        login_data = {"username": "admin", "password": "Admin123!"}
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        # Call /users/all
        response = client.get("/users/all", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert any(user["username"] == "admin" for user in data["data"])
        print("[DEBUG] /users/all route smoke test passed.")

def test_print_routes():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        print("[DEBUG ROUTES]", [route.path for route in app.routes])
