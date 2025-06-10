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


# --- CLEANUP AND VALIDATION TESTS ---
def test_cleanup_locations(admin_token):
    # Add a location
    location = {"name": "ToDelete", "description": "To be cleaned"}
    add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {admin_token}"})
    assert add_resp.status_code == 200
    # Cleanup - this endpoint might not exist, need to check
    cleanup_resp = client.delete("/locations/cleanup-locations", headers={"Authorization": f"Bearer {admin_token}"})
    assert cleanup_resp.status_code == 200

def test_location_type_validation(admin_token):
    # Invalid location (missing name)
    invalid = {"description": "No name"}
    resp = client.post("/locations/add_location", json=invalid, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code in [400, 422]
