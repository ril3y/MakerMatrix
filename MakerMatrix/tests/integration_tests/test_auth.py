import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.main import app
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

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
def test_user():
    """Get the admin user for authentication tests."""
    user_repo = UserRepository()
    user = user_repo.get_user_by_username("admin")
    if not user:
        raise ValueError("Admin user not found. Make sure setup_database fixture is running.")
    return user


@pytest.fixture
def auth_token(test_user):
    """Get an authentication token for the test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": test_user.username})
    return token


def test_protected_route_without_token():
    """Test that a protected route returns 401 without a token."""
    response = client.get("/api/parts/get_all_parts")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


def test_protected_route_with_token(auth_token):
    """Test that a protected route works with a valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/parts/get_part_counts", headers=headers)
    assert response.status_code == 200


def test_login_endpoint():
    """Test that the login endpoint returns a token."""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "Admin123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_public_endpoint():
    """Test that the root endpoint is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MakerMatrix API"} \nfrom MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n