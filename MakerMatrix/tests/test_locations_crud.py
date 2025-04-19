import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- CRUD TESTS ---
def test_add_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        response = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["name"] == "Warehouse"

def test_get_location_by_id():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        get_resp = client.get(f"/locations/get_location?location_id={loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == loc_id

def test_update_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        update = {"name": "Warehouse Updated", "description": "Updated desc"}
        update_resp = client.put(f"/locations/update_location/{loc_id}", json=update, headers={"Authorization": f"Bearer {token}"})
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["name"] == "Warehouse Updated"

def test_delete_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        del_resp = client.delete(f"/locations/delete_location/{loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"
