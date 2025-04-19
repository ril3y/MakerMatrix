import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- CLEANUP AND VALIDATION TESTS ---
def test_cleanup_locations():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        # Add a location
        location = {"name": "ToDelete", "description": "To be cleaned"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        assert add_resp.status_code == 200
        # Cleanup
        cleanup_resp = client.delete("/locations/delete_all_locations", headers={"Authorization": f"Bearer {token}"})
        assert cleanup_resp.status_code == 200
        assert cleanup_resp.json()["status"] == "success"

def test_location_type_validation():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        # Invalid location (missing name)
        invalid = {"description": "No name"}
        resp = client.post("/locations/add_location", json=invalid, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in [400, 422]
