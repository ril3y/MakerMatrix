import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- HIERARCHY TESTS ---
def test_parent_child_relationships():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        parent = {"name": "Warehouse", "description": "Main warehouse"}
        child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
        parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {token}"})
        parent_id = parent_resp.json()["data"]["id"]
        child["parent_id"] = parent_id
        child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {token}"})
        assert child_resp.status_code == 200
        assert child_resp.json()["data"]["parent_id"] == parent_id

def test_get_location_path():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        parent = {"name": "Warehouse", "description": "Main warehouse"}
        child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
        parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {token}"})
        parent_id = parent_resp.json()["data"]["id"]
        child["parent_id"] = parent_id
        child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {token}"})
        child_id = child_resp.json()["data"]["id"]
        path_resp = client.get(f"/locations/get_location_path?location_id={child_id}", headers={"Authorization": f"Bearer {token}"})
        assert path_resp.status_code == 200
        path = path_resp.json()["data"]
        assert path[0]["id"] == parent_id
        assert path[-1]["id"] == child_id
