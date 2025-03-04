import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.models.user_models import UserModel, RoleModel, UserCreate, UserUpdate
from passlib.context import CryptContext

client = TestClient(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def setup_test_roles():
    """Create test roles."""
    roles_data = [
        {"name": "admin", "description": "Administrator", "permissions": ["all"]},
        {"name": "manager", "description": "Manager", "permissions": ["read", "write", "update"]},
        {"name": "user", "description": "Regular User", "permissions": ["read"]}
    ]
    
    added_roles = []
    for role_data in roles_data:
        response = client.post("/roles/add_role", json=role_data)
        assert response.status_code == 200
        added_roles.append(response.json()["data"])
    
    return added_roles


@pytest.fixture
def setup_test_user(setup_test_roles):
    """Create a test user with roles."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123",
        "roles": ["user", "manager"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 200
    return response.json()["data"]


def test_create_user(setup_test_roles):
    """Test user creation with roles."""
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "NewPass123",
        "roles": ["user"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "hashed_password" not in data
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_get_user_by_id(setup_test_user):
    """Test retrieving a user by ID."""
    user_id = setup_test_user["id"]
    response = client.get(f"/users/{user_id}")
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == user_id
    assert data["username"] == "testuser"
    assert "hashed_password" not in data


def test_get_user_by_username(setup_test_user):
    """Test retrieving a user by username."""
    response = client.get("/users/by-username/testuser")
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


def test_update_user(setup_test_user):
    """Test updating user information."""
    user_id = setup_test_user["id"]
    update_data = {
        "email": "updated@example.com",
        "roles": ["user"]  # Remove manager role
    }
    
    response = client.put(f"/users/{user_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["email"] == update_data["email"]
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_update_password(setup_test_user):
    """Test password update."""
    user_id = setup_test_user["id"]
    
    # First, login to get the access token using OAuth2 form data
    login_data = {
        "username": "testuser",
        "password": "TestPass123",
        "grant_type": "password",
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }
    login_response = client.post(
        "/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    
    # Now update the password with the token
    password_data = {
        "current_password": "TestPass123",
        "new_password": "NewTestPass123"
    }
    
    response = client.put(
        f"/users/{user_id}/password",
        json=password_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    
    # Try logging in with new password using OAuth2 form data
    new_login_data = {
        "username": "testuser",
        "password": "NewTestPass123",
        "grant_type": "password",
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }
    login_response = client.post(
        "/auth/login",
        data=new_login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200


def test_delete_user(setup_test_user):
    """Test user deletion."""
    user_id = setup_test_user["id"]
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    
    # Verify user is deleted
    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 404


def test_create_role():
    """Test role creation."""
    role_data = {
        "name": "supervisor",
        "description": "Supervisor role",
        "permissions": ["read", "write"]
    }
    
    response = client.post("/roles/add_role", json=role_data)
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["name"] == role_data["name"]
    assert data["description"] == role_data["description"]
    assert data["permissions"] == role_data["permissions"]


def test_get_role_by_name(setup_test_roles):
    """Test retrieving a role by name."""
    response = client.get("/roles/by-name/admin")
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "admin"
    assert data["permissions"] == ["all"]


def test_update_role(setup_test_roles):
    """Test updating role information."""
    role_id = setup_test_roles[1]["id"]  # manager role
    update_data = {
        "description": "Updated manager description",
        "permissions": ["read", "write", "update", "delete"]
    }
    
    response = client.put(f"/roles/{role_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["description"] == update_data["description"]
    assert data["permissions"] == update_data["permissions"]


def test_delete_role(setup_test_roles):
    """Test role deletion."""
    role_id = setup_test_roles[2]["id"]  # user role
    response = client.delete(f"/roles/{role_id}")
    assert response.status_code == 200
    
    # Verify role is deleted
    get_response = client.get(f"/roles/{role_id}")
    assert get_response.status_code == 404


def test_invalid_password_format():
    """Test user creation with invalid password format."""
    user_data = {
        "username": "invaliduser",
        "email": "invalid@example.com",
        "password": "weak",  # Too short, no uppercase, no number
        "roles": ["user"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 422  # Validation error


def test_duplicate_username(setup_test_user):
    """Test creating user with duplicate username."""
    user_data = {
        "username": "testuser",  # Same as in setup_test_user
        "email": "another@example.com",
        "password": "TestPass123",
        "roles": ["user"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "already exists" in response.json()["message"].lower()


def test_invalid_role_assignment():
    """Test assigning non-existent role to user."""
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "TestPass123",
        "roles": ["nonexistent_role"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "role not found" in response.json()["message"].lower() 