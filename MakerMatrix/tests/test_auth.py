import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user for authentication tests."""
    user_repo = UserRepository()
    # Check if test user already exists
    user = user_repo.get_user_by_username("testuser")
    if not user:
        # Create test user
        hashed_password = user_repo.get_password_hash("testpassword")
        user = user_repo.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed_password,
            roles=["user"]
        )
    return user


@pytest.fixture
def auth_token(test_user):
    """Get an authentication token for the test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": test_user.username})
    return token


def test_protected_route_without_token():
    """Test that a protected route returns 401 without a token."""
    response = client.get("/parts/get_all_parts")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


def test_protected_route_with_token(auth_token):
    """Test that a protected route works with a valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/parts/get_all_parts", headers=headers)
    assert response.status_code == 200


def test_login_endpoint():
    """Test that the login endpoint returns a token."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]


def test_public_endpoint():
    """Test that the root endpoint is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MakerMatrix API"} 