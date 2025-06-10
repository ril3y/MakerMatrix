import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    # Login data for the admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    return response.json()["access_token"]


# --- CRUD TESTS ---
def test_add_location(admin_token):
    location = {"name": "Warehouse", "description": "Main warehouse storage"}
    response = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["name"] == "Warehouse"

def test_get_location_by_id(admin_token):
    location = {"name": "Warehouse", "description": "Main warehouse storage"}
    add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {admin_token}"})
    loc_id = add_resp.json()["data"]["id"]
    get_resp = client.get(f"/locations/get_location?location_id={loc_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == loc_id

def test_update_location(admin_token):
    location = {"name": "Warehouse", "description": "Main warehouse storage"}
    add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {admin_token}"})
    loc_id = add_resp.json()["data"]["id"]
    update = {"name": "Warehouse Updated", "description": "Updated desc"}
    update_resp = client.put(f"/locations/update_location/{loc_id}", json=update, headers={"Authorization": f"Bearer {admin_token}"})
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Warehouse Updated"

def test_delete_location(admin_token):
    location = {"name": "Warehouse", "description": "Main warehouse storage"}
    add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {admin_token}"})
    loc_id = add_resp.json()["data"]["id"]
    del_resp = client.delete(f"/locations/delete_location/{loc_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"
