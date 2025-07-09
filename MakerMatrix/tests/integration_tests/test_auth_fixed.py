"""
Authentication Integration Tests - Fixed Version

This is an example of properly isolated authentication tests that don't
contaminate the main application database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from MakerMatrix.main import app
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.tests.test_database_config import setup_test_database_with_admin


@pytest.fixture(scope="function")
def test_client():
    """Create a test client for the application"""
    return TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database(isolated_test_engine):
    """Set up isolated test database before running tests."""
    # Database tables are already created by isolated_test_engine fixture
    # Admin user and roles are already set up by isolated_test_engine fixture
    yield
    # Cleanup is handled by the isolated_test_engine fixture


@pytest.fixture
def auth_token(isolated_test_engine):
    """Get an authentication token for the test admin user."""
    # Use the isolated test engine to avoid database contamination
    with Session(isolated_test_engine) as session:
        auth_service = AuthService()
        
        # Get admin user from test database
        user_repo = UserRepository()
        user_repo.engine = isolated_test_engine
        
        admin_user = user_repo.get_user_by_username(session, "admin")
        if not admin_user:
            pytest.fail("Admin user not found in test database")
        
        token = auth_service.create_access_token(data={"sub": admin_user.username})
        return token


@pytest.fixture
def admin_token(test_client):
    """Get an admin token for authentication via API."""
    login_data = {"username": "admin", "password": "Admin123!"}
    response = test_client.post("/auth/login", json=login_data)
    
    if response.status_code != 200:
        pytest.fail(f"Authentication failed: {response.json()}")
    
    return response.json()["access_token"]


class TestAuthenticationIsolated:
    """Test authentication functionality with database isolation"""
    
    def test_login_success(self, test_client):
        """Test successful login with admin credentials"""
        login_data = {"username": "admin", "password": "Admin123!"}
        response = test_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "access_token" in response_data
        assert response_data["token_type"] == "bearer"
        assert response_data["status"] == "success"
    
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials"""
        login_data = {"username": "admin", "password": "wrongpassword"}
        response = test_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["status"] == "error"
    
    def test_login_nonexistent_user(self, test_client):
        """Test login with non-existent user"""
        login_data = {"username": "nonexistent", "password": "password"}
        response = test_client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["status"] == "error"
    
    def test_mobile_login_success(self, test_client):
        """Test successful mobile login"""
        login_data = {"username": "admin", "password": "Admin123!"}
        response = test_client.post("/auth/mobile-login", json=login_data)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert "access_token" in response_data
        assert response_data["token_type"] == "bearer"
        assert response_data["status"] == "success"
    
    def test_token_refresh(self, test_client, admin_token):
        """Test token refresh functionality"""
        # First, login to get a refresh token (stored in cookie)
        login_data = {"username": "admin", "password": "Admin123!"}
        login_response = test_client.post("/auth/login", json=login_data)
        
        # Extract cookies from login response
        cookies = login_response.cookies
        
        # Test token refresh
        refresh_response = test_client.post("/auth/refresh", cookies=cookies)
        
        assert refresh_response.status_code == 200
        response_data = refresh_response.json()
        assert "access_token" in response_data
    
    def test_logout(self, test_client, admin_token):
        """Test logout functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.post("/auth/logout", headers=headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
    
    def test_protected_endpoint_with_valid_token(self, test_client, admin_token):
        """Test accessing protected endpoint with valid token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = test_client.get("/api/users/all", headers=headers)
        
        # Should succeed (200) or return empty list
        assert response.status_code in [200, 404]
    
    def test_protected_endpoint_without_token(self, test_client):
        """Test accessing protected endpoint without token"""
        response = test_client.get("/api/users/all")
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["status"] == "error"
    
    def test_protected_endpoint_with_invalid_token(self, test_client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = test_client.get("/api/users/all", headers=headers)
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["status"] == "error"
    
    def test_database_isolation_validation(self, isolated_test_engine):
        """Test that we're using isolated database and not main database"""
        # This test validates that our test database is isolated
        # Check that we can access the admin user in test database
        user_repo = UserRepository()
        user_repo.engine = isolated_test_engine
        
        admin_user = user_repo.get_user_by_username("admin")
        assert admin_user is not None
        assert admin_user.username == "admin"
        
        # Verify that the isolated engine is not the main engine
        from MakerMatrix.models.models import engine as main_engine
        assert isolated_test_engine != main_engine
        
        # Verify that the database URLs are different
        assert str(isolated_test_engine.url) != str(main_engine.url)
        assert "memory" in str(isolated_test_engine.url) or "tmp" in str(isolated_test_engine.url)
        assert "makermatrix.db" in str(main_engine.url)