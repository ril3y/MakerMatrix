import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.user_models import UserModel, RoleModel, UserCreate, UserUpdate
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

client = TestClient(app)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


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
    
    yield
    SQLModel.metadata.drop_all(isolated_test_engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication using the mobile login endpoint."""
    # Use the mobile login endpoint which accepts JSON
    login_data = {
        "username": DEFAULT_ADMIN_USERNAME,
        "password": DEFAULT_ADMIN_PASSWORD
    }
    
    response = client.post(
        "/auth/login",
        json=login_data
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    return response.json()["access_token"]


@pytest.fixture
def setup_test_roles(admin_token):
    """Get existing roles or create them if they don't exist."""
    # First, try to get the roles
    roles = []
    role_names = ["admin", "manager", "user"]
    
    for role_name in role_names:
        response = client.get(
            f"/roles/by-name/{role_name}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            # Role exists, add it to the list
            roles.append(response.json()["data"])
        else:
            # Role doesn't exist, create it
            role_data = {
                "name": role_name,
                "description": f"{role_name.capitalize()} role",
                "permissions": ["all"] if role_name == "admin" else 
                              ["read", "write", "update"] if role_name == "manager" else 
                              ["read"]
            }
            
            create_response = client.post(
                "/roles/add_role",
                json=role_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert create_response.status_code == 200
            roles.append(create_response.json()["data"])
    
    return roles


@pytest.fixture
def setup_test_user(setup_test_roles, admin_token):
    """Create a test user with roles or get it if it already exists."""
    # First, try to get the user
    response = client.get(
        "/users/by-username/testuser",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        # User exists, return it
        return response.json()["data"]
    
    # User doesn't exist, create it
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123",
        "roles": ["user", "manager"]
    }
    
    create_response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_response.status_code == 200
    return create_response.json()["data"]


def test_create_user(setup_test_roles, admin_token):
    """Test user creation with roles."""
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "NewPass123",
        "roles": ["user"]
    }
    
    response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "hashed_password" not in data
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_get_user_by_id(setup_test_user, admin_token):
    """Test retrieving a user by ID."""
    user_id = setup_test_user["id"]
    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == user_id
    assert data["username"] == "testuser"
    assert "hashed_password" not in data


def test_get_user_by_username(setup_test_user, admin_token):
    """Test retrieving a user by username."""
    response = client.get(
        "/users/by-username/testuser",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


def test_update_user(setup_test_user, admin_token):
    """Test updating a user."""
    user_id = setup_test_user["id"]
    update_data = {
        "email": "updated@example.com",
        "roles": ["user"]  # Remove manager role
    }
    
    response = client.put(
        f"/users/{user_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == update_data["email"]
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_update_password(setup_test_user, admin_token):
    """Test updating a user's password."""
    # First login with the test user
    login_data = {
        "username": "testuser",
        "password": "TestPass123"
    }
    login_response = client.post(
        "/auth/login",
        json=login_data
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    access_token = login_response.json()["access_token"]
    
    # Now update the password with the token
    password_data = {
        "current_password": "TestPass123",
        "new_password": "NewPass456"
    }
    
    user_id = setup_test_user["id"]
    response = client.put(
        f"/users/{user_id}/password",
        json=password_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    
    # Try logging in with the new password
    new_login_data = {
        "username": "testuser",
        "password": "NewPass456"
    }
    
    new_login_response = client.post(
        "/auth/login",
        json=new_login_data
    )
    
    assert new_login_response.status_code == 200
    assert "access_token" in new_login_response.json()
    new_access_token = new_login_response.json()["access_token"]


def test_delete_user(setup_test_user, admin_token):
    """Test deleting a user."""
    user_id = setup_test_user["id"]
    
    response = client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    
    # Verify the user is deleted
    get_response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 404


def test_create_role(admin_token):
    """Test role creation."""
    role_data = {
        "name": "supervisor",
        "description": "Supervisor role",
        "permissions": ["read", "write"]
    }
    
    response = client.post(
        "/roles/add_role", 
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["name"] == role_data["name"]
    assert data["description"] == role_data["description"]
    assert data["permissions"] == role_data["permissions"]


def test_get_role_by_name(setup_test_roles, admin_token):
    """Test retrieving a role by name."""
    response = client.get(
        "/roles/by-name/manager",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "manager"
    assert data["description"] == "Manager with write access"
    assert "write" in data["permissions"]


def test_update_role(setup_test_roles, admin_token):
    """Test updating a role."""
    # Get the role ID
    role_response = client.get(
        "/roles/by-name/user",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    role_id = role_response.json()["data"]["id"]
    
    update_data = {
        "description": "Updated User Role",
        "permissions": ["read", "write"]  # Add write permission
    }
    
    response = client.put(
        f"/roles/{role_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == update_data["description"]
    assert set(data["permissions"]) == set(update_data["permissions"])


def test_delete_role(setup_test_roles, admin_token):
    """Test deleting a role."""
    # Create a new role to delete
    role_data = {
        "name": "temp_role",
        "description": "Temporary Role",
        "permissions": ["read"]
    }
    
    create_response = client.post(
        "/roles/add_role", 
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    role_id = create_response.json()["data"]["id"]
    
    # Delete the role
    response = client.delete(
        f"/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    
    # Verify the role is deleted
    get_response = client.get(
        f"/roles/by-name/temp_role",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 404


def test_invalid_password_format():
    """Test validation for password format."""
    user_data = {
        "username": "badpassuser",
        "email": "badpass@example.com",
        "password": "weak",  # Too short, no uppercase, no digit
        "roles": ["user"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 422  # Validation error


def test_duplicate_username(setup_test_user, admin_token):
    """Test that duplicate usernames are rejected."""
    user_data = {
        "username": "testuser",  # Same as existing user
        "email": "another@example.com",
        "password": "AnotherPass123",
        "roles": ["user"]
    }
    
    response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Should return 409 Conflict for duplicate username
    assert response.status_code == 409
    response_data = response.json()
    assert "already exists" in response_data.get("detail", "").lower() or "already exists" in str(response_data).lower()


def test_invalid_role_assignment():
    """Test that invalid role assignments are rejected."""
    user_data = {
        "username": "invalidroleuser",
        "email": "invalid@example.com",
        "password": "ValidPass123",
        "roles": ["nonexistent_role"]
    }
    
    response = client.post("/users/register", json=user_data)
    
    # Should return 400 Bad Request for invalid role
    assert response.status_code == 400
    response_data = response.json()
    assert "not found" in response_data.get("detail", "").lower() or "not found" in str(response_data).lower() \nfrom MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n