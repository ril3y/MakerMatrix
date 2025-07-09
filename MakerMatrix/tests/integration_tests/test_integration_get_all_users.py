import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database(isolated_test_engine):
    """Set up isolated test database before running tests."""
    from MakerMatrix.database.db import create_db_and_tables
    from MakerMatrix.repositories.user_repository import UserRepository
    from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
    
    # Create user repository with isolated test engine
    user_repo = UserRepository()
    user_repo.engine = isolated_test_engine
    
    # Setup default roles and admin user in test database
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(isolated_test_engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_get_all_users_admin(admin_token):
    response = client.get(
        "/users/all",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert any(user["username"] == "admin" for user in data["data"])


def test_get_all_users_non_admin(admin_token):
    # Create a non-admin user using the admin token
    user_repo = UserRepository()
    user_repo.create_user(
        username="testuser",
        email="testuser@example.com",
        hashed_password=user_repo.get_password_hash("testpass"),
        roles=["user"]
    )
    
    # Login as the non-admin user
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Try to access all users (should be forbidden)
    response = client.get(
        "/users/all",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
\nfrom MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n