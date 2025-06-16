"""
Unit tests for user_repository.py using real in-memory database.

These tests use an in-memory SQLite database for fast, reliable testing
without complex mocking of SQLAlchemy components.
"""

import pytest
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    UserAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.unit_tests.test_database import create_test_db, create_test_db_with_data
from passlib.hash import pbkdf2_sha256


class TestUserRepositoryNew:
    """Test cases for UserRepository using real database."""

    def setup_method(self):
        """Set up test database for each test."""
        self.test_db = create_test_db()
        self.repo = UserRepository()
        self.repo.engine = self.test_db.engine

    def teardown_method(self):
        """Clean up after each test."""
        self.test_db.close()

    def test_create_user_success(self):
        """Test successful user creation."""
        # Create a role first
        session = self.test_db.get_session()
        test_role = RoleModel(
            name="test_role",
            description="Test Role",
            permissions=["read", "write"]
        )
        session.add(test_role)
        session.commit()

        # Create user
        result = self.repo.create_user("testuser", "test@example.com", "hashed_pass", ["test_role"])
        
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        # Note: hashed_password might be excluded from model in some contexts
        assert len(result.roles) == 1
        assert result.roles[0].name == "test_role"

    def test_create_user_duplicate_username(self):
        """Test creating user with duplicate username raises error."""
        # Create initial user
        session = self.test_db.get_session()
        existing_user = UserModel(
            username="duplicate",
            email="first@example.com",
            hashed_password="hash123"
        )
        session.add(existing_user)
        session.commit()

        # Attempt to create user with same username
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            self.repo.create_user("duplicate", "second@example.com", "hash456")
        
        assert "already exists" in str(exc_info.value)

    def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email raises error."""
        # Create initial user
        session = self.test_db.get_session()
        existing_user = UserModel(
            username="first",
            email="duplicate@example.com",
            hashed_password="hash123"
        )
        session.add(existing_user)
        session.commit()

        # Attempt to create user with same email
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            self.repo.create_user("second", "duplicate@example.com", "hash456")
        
        assert "already exists" in str(exc_info.value)

    def test_create_user_invalid_role(self):
        """Test creating user with non-existent role raises error."""
        with pytest.raises(InvalidReferenceError) as exc_info:
            self.repo.create_user("testuser", "test@example.com", "hash123", ["nonexistent_role"])
        
        assert "Role 'nonexistent_role' not found" in str(exc_info.value)

    def test_get_user_by_username_success(self):
        """Test successfully retrieving user by username."""
        # Create user
        session = self.test_db.get_session()
        test_user = UserModel(
            username="findme",
            email="findme@example.com",
            hashed_password="hash123"
        )
        session.add(test_user)
        session.commit()

        # Retrieve user
        result = self.repo.get_user_by_username("findme")
        
        assert result.username == "findme"
        assert result.email == "findme@example.com"

    def test_get_user_by_username_not_found(self):
        """Test retrieving non-existent user raises error."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            self.repo.get_user_by_username("nonexistent")
        
        assert "User with username 'nonexistent' not found" in str(exc_info.value)

    def test_get_user_by_id_success(self):
        """Test successfully retrieving user by ID."""
        # Create user
        session = self.test_db.get_session()
        test_user = UserModel(
            username="testuser",
            email="test@example.com",
            hashed_password="hash123"
        )
        session.add(test_user)
        session.commit()
        user_id = test_user.id

        # Retrieve user
        result = self.repo.get_user_by_id(user_id)
        
        assert result.id == user_id
        assert result.username == "testuser"

    def test_get_user_by_id_not_found(self):
        """Test retrieving user by non-existent ID raises error."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            self.repo.get_user_by_id("nonexistent-id")
        
        assert "User with ID 'nonexistent-id' not found" in str(exc_info.value)

    def test_update_user_success(self):
        """Test successfully updating user."""
        # Create user
        session = self.test_db.get_session()
        test_user = UserModel(
            username="updateme",
            email="old@example.com",
            hashed_password="hash123"
        )
        session.add(test_user)
        session.commit()
        user_id = test_user.id

        # Update user
        result = self.repo.update_user(
            user_id=user_id,
            email="new@example.com",
            is_active=False
        )
        
        assert result.email == "new@example.com"
        assert result.is_active == False
        assert result.username == "updateme"  # Unchanged

    def test_update_user_not_found(self):
        """Test updating non-existent user raises error."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            self.repo.update_user("nonexistent-id", email="new@example.com")
        
        assert "User with ID 'nonexistent-id' not found" in str(exc_info.value)

    def test_delete_user_success(self):
        """Test successfully deleting user."""
        # Create user
        session = self.test_db.get_session()
        test_user = UserModel(
            username="deleteme",
            email="delete@example.com",
            hashed_password="hash123"
        )
        session.add(test_user)
        session.commit()
        user_id = test_user.id

        # Delete user
        result = self.repo.delete_user(user_id)
        
        assert result == True
        
        # Verify user is gone
        with pytest.raises(ResourceNotFoundError):
            self.repo.get_user_by_id(user_id)

    def test_delete_user_not_found(self):
        """Test deleting non-existent user raises error."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            self.repo.delete_user("nonexistent-id")
        
        assert "User with ID 'nonexistent-id' not found" in str(exc_info.value)

    def test_create_role_success(self):
        """Test successfully creating role."""
        result = self.repo.create_role(
            name="new_role",
            description="New Role",
            permissions=["read", "write", "delete"]
        )
        
        assert result.name == "new_role"
        assert result.description == "New Role"
        assert result.permissions == ["read", "write", "delete"]

    def test_get_role_by_name_success(self):
        """Test successfully retrieving role by name."""
        # Create role
        session = self.test_db.get_session()
        test_role = RoleModel(
            name="find_role",
            description="Find Me",
            permissions=["read"]
        )
        session.add(test_role)
        session.commit()

        # Retrieve role
        result = self.repo.get_role_by_name("find_role")
        
        assert result.name == "find_role"
        assert result.description == "Find Me"

    def test_get_role_by_name_not_found(self):
        """Test retrieving non-existent role raises error."""
        with pytest.raises(ResourceNotFoundError) as exc_info:
            self.repo.get_role_by_name("nonexistent_role")
        
        assert "Role with name 'nonexistent_role' not found" in str(exc_info.value)

    def test_verify_password_success(self):
        """Test password verification works correctly."""
        plain_password = "testpassword123"
        hashed_password = pbkdf2_sha256.hash(plain_password)
        
        result = self.repo.verify_password(plain_password, hashed_password)
        
        assert result == True

    def test_verify_password_failure(self):
        """Test password verification fails with wrong password."""
        plain_password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed_password = pbkdf2_sha256.hash(plain_password)
        
        result = self.repo.verify_password(wrong_password, hashed_password)
        
        assert result == False

    def test_get_all_users_success(self):
        """Test retrieving all users with their roles."""
        # Create test data
        test_db_with_data = create_test_db_with_data()
        repo = UserRepository()
        repo.engine = test_db_with_data.engine
        
        try:
            result = repo.get_all_users()
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            # Check first user structure
            user_dict = result[0]
            assert "id" in user_dict
            assert "username" in user_dict
            assert "email" in user_dict
            assert "roles" in user_dict
            assert isinstance(user_dict["roles"], list)
            
        finally:
            test_db_with_data.close()