import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin


client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)
    

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