import pytest
import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select, SQLModel
from MakerMatrix.main import app
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import RoleModel, UserModel, UserRoleLink
from MakerMatrix.database.db import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create database tables and setup default roles and admin user."""
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    # Create user repository
    user_repo = UserRepository()
    
    # Setup default roles and admin user
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # No teardown needed for tests


@pytest.fixture
def test_role():
    """Create a test role for authentication tests."""
    with Session(engine) as session:
        # Check if role already exists
        role = session.exec(select(RoleModel).where(RoleModel.name == "user")).first()
        if role:
            # Update the role with the necessary permissions
            role.permissions = ["parts:read", "parts:create", "locations:read", "categories:read"]
            session.add(role)
            session.commit()
            session.refresh(role)
        else:
            # Create test role
            role = RoleModel(
                name="user",
                description="Regular user role",
                permissions=["parts:read", "parts:create", "locations:read", "categories:read"]
            )
            session.add(role)
            session.commit()
            session.refresh(role)
        return role


@pytest.fixture
def test_user(test_role):
    """Create a test user for authentication tests."""
    user_repo = UserRepository()
    # Check if test user already exists
    try:
        user = user_repo.get_user_by_username("testuser")
        return user
    except Exception:
        # User doesn't exist, create test user
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
    response = client.get("/api/parts/get_all_parts")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


def test_protected_route_with_token(auth_token):
    """Test that a protected route works with a valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/parts/get_all_parts", headers=headers)
    # The endpoint might return 200 or 404 depending on whether there are parts in the database
    # We just want to make sure it's not a 401 Unauthorized
    assert response.status_code != 401


def test_login_endpoint(test_user):
    """Test that the login endpoint is accessible without authentication."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data


def test_public_endpoint():
    """Test that the root endpoint is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MakerMatrix API"}


def test_permission_required_endpoint(auth_token):
    """Test that an endpoint requiring specific permissions works with the right permissions."""
    # Generate a unique part name to avoid conflicts
    unique_part_name = f"Test Part {uuid.uuid4()}"
    
    # This test assumes the test user has the 'parts:create' permission
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/parts/add_part",
        headers=headers,
        json={
            "part_name": unique_part_name,
            "part_number": f"TP-{uuid.uuid4().hex[:8]}",
            "quantity": 10,
            "description": "A test part"
        }
    )
    
    # The endpoint should return 200 OK or 409 Conflict (if the part already exists)
    # We just want to make sure it's not a 401 Unauthorized or 403 Forbidden
    assert response.status_code not in [401, 403] 