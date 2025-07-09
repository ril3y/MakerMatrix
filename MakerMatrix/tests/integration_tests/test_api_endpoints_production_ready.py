from MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n"""
Production-Ready API Endpoint Integration Tests
Tests that would catch real production bugs by making actual HTTP requests
Part of extended testing validation - fills the gap between unit tests and real application
"""

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


@pytest.fixture
def regular_user_token():
    """Create a regular user and get their token."""
    user_repo = UserRepository()
    user_repo.create_user(
        username="testuser",
        email="testuser@example.com",
        hashed_password=user_repo.get_password_hash("testpass"),
        roles=["user"]
    )
    
    # Login as the regular user
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestCriticalAPIEndpoints:
    """Test critical API endpoints that must work in production"""
    
    def test_users_all_endpoint_works(self, admin_token):
        """Test the /users/all endpoint actually works with admin token"""
        response = client.get(
            "/api/users/all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500 - the bug we're fixing
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        
        # Verify admin user is in the list
        admin_user = next((user for user in data["data"] if user["username"] == "admin"), None)
        assert admin_user is not None, "Admin user not found in response"
        assert admin_user["username"] == "admin"
        assert admin_user["is_active"] == True
        
        print("✅ /users/all endpoint works correctly with admin token")
    
    def test_users_all_endpoint_forbidden_for_regular_user(self, regular_user_token):
        """Test that regular users cannot access /users/all"""
        response = client.get(
            "/api/users/all",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        print("✅ /users/all endpoint properly forbidden for regular users")
    
    def test_users_all_endpoint_requires_authentication(self):
        """Test that /users/all requires authentication"""
        response = client.get("/api/users/all")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        
        print("✅ /users/all endpoint requires authentication")
    
    def test_utility_get_counts_endpoint_works(self, admin_token):
        """Test the /utility/get_counts endpoint works"""
        response = client.get(
            "/utility/get_counts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], dict)
        
        # Should have counts for parts, locations, categories
        counts = data["data"]
        assert "parts" in counts
        assert "locations" in counts
        assert "categories" in counts
        assert isinstance(counts["parts"], int)
        assert isinstance(counts["locations"], int)
        assert isinstance(counts["categories"], int)
        
        print("✅ /utility/get_counts endpoint works correctly")
    
    def test_auth_login_endpoint_works(self):
        """Test the /auth/login endpoint works"""
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        
        print("✅ /auth/login endpoint works correctly")
    
    def test_auth_login_rejects_invalid_credentials(self):
        """Test that /auth/login rejects invalid credentials"""
        login_data = {
            "username": "admin",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        
        print("✅ /auth/login endpoint properly rejects invalid credentials")
    
    def test_parts_get_all_endpoint_works(self, admin_token):
        """Test the /parts/get_all_parts endpoint works"""
        response = client.get(
            "/parts/get_all_parts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print("✅ /parts/get_all_parts endpoint works correctly")
    
    def test_locations_get_all_endpoint_works(self, admin_token):
        """Test the /locations/get_all_locations endpoint works"""
        response = client.get(
            "/locations/get_all_locations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print("✅ /locations/get_all_locations endpoint works correctly")
    
    def test_categories_get_all_endpoint_works(self, admin_token):
        """Test the /categories/get_all_categories endpoint works"""
        response = client.get(
            "/categories/get_all_categories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print("✅ /categories/get_all_categories endpoint works correctly")
    
    def test_tasks_get_all_endpoint_works(self, admin_token):
        """Test the /tasks/ endpoint works"""
        response = client.get(
            "/tasks/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print("✅ /tasks/ endpoint works correctly")
    
    def test_import_suppliers_endpoint_works(self, admin_token):
        """Test the /import/suppliers endpoint works"""
        response = client.get(
            "/import/suppliers",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # This should NOT return 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        print("✅ /import/suppliers endpoint works correctly")


class TestAPIEndpointErrorHandling:
    """Test API endpoint error handling"""
    
    def test_endpoint_error_responses_are_structured(self, admin_token):
        """Test that API endpoints return structured error responses"""
        # Test non-existent endpoint
        response = client.get(
            "/nonexistent/endpoint",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404
        
        # Test invalid part ID
        response = client.get(
            "/parts/get_part?part_id=invalid-uuid",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return structured error, not 500
        assert response.status_code in [404, 422]  # Either not found or validation error
        
        print("✅ API endpoints return structured error responses")
    
    def test_authentication_error_handling(self):
        """Test authentication error handling"""
        # Test with invalid token
        response = client.get(
            "/users/all",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
        
        # Test with no token
        response = client.get("/users/all")
        assert response.status_code == 401
        
        print("✅ Authentication error handling works correctly")


class TestAPIEndpointPerformance:
    """Test API endpoint performance"""
    
    def test_endpoints_respond_quickly(self, admin_token):
        """Test that critical endpoints respond within reasonable time"""
        import time
        
        # Test critical endpoints
        endpoints = [
            "/users/all",
            "/parts/get_all_parts",
            "/locations/get_all_locations",
            "/categories/get_all_categories",
            "/utility/get_counts"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Should respond within 5 seconds (reasonable for integration test)
            assert response_time < 5.0, f"Endpoint {endpoint} took {response_time:.2f}s (too slow)"
            assert response.status_code == 200, f"Endpoint {endpoint} returned {response.status_code}"
        
        print("✅ All critical endpoints respond within reasonable time")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])