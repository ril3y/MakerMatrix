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


# --- HIERARCHY TESTS ---
def test_parent_child_relationships(admin_token):
    parent = {"name": "Warehouse", "description": "Main warehouse"}
    child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
    parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {admin_token}"})
    parent_id = parent_resp.json()["data"]["id"]
    child["parent_id"] = parent_id
    child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {admin_token}"})
    assert child_resp.status_code == 200
    assert child_resp.json()["data"]["parent_id"] == parent_id

def test_get_location_path(admin_token):
    parent = {"name": "Warehouse", "description": "Main warehouse"}
    child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
    parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {admin_token}"})
    parent_id = parent_resp.json()["data"]["id"]
    child["parent_id"] = parent_id
    child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {admin_token}"})
    child_id = child_resp.json()["data"]["id"]
    path_resp = client.get(f"/locations/get_location_path/{child_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert path_resp.status_code == 200
    
    # The API returns a location object with its parent, not a list of path items
    response_data = path_resp.json()
    location_data = response_data["data"]
    
    # Verify that we get the child location with its parent
    assert location_data["id"] == child_id
    assert location_data["name"] == "Shelf 1"
    assert "parent" in location_data
    assert location_data["parent"]["id"] == parent_id
    assert location_data["parent"]["name"] == "Warehouse"
