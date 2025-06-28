"""
Integration tests for Supplier Configuration API

Tests the REST API endpoints for creating and deleting supplier configurations.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from MakerMatrix.main import app
from MakerMatrix.database.db import get_session
from sqlmodel import SQLModel
from MakerMatrix.models.supplier_config_models import SupplierConfigModel
from MakerMatrix.services.system.auth_service import AuthService


# Test database setup - use in-memory database for complete isolation
import tempfile
import os
TEST_DB_FILE = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = override_get_db
client = TestClient(app)


def cleanup_test_db():
    """Clean up test database file"""
    try:
        if os.path.exists(TEST_DB_FILE):
            os.unlink(TEST_DB_FILE)
    except Exception:
        pass  # Ignore cleanup errors


class TestSupplierConfigAPI:
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Create test database tables before each test"""
        # Clean up any existing test database file
        cleanup_test_db()
        # Create all tables fresh
        SQLModel.metadata.create_all(bind=engine)
        # Add debug to see what tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        print(f"Tables after creation: {inspector.get_table_names()}")
        yield
        # Clean up after test
        SQLModel.metadata.drop_all(bind=engine)
        cleanup_test_db()
    
    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for API requests"""
        # Create test admin user and get token
        auth_service = AuthService()
        
        # Login to get token
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Admin123!"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        else:
            # If admin doesn't exist in test DB, this test will need to handle user creation
            pytest.skip("Admin user not available in test database")
    
    @pytest.fixture
    def sample_supplier_data(self):
        """Sample supplier configuration data for API testing"""
        return {
            "supplier_name": "TestSupplier",
            "display_name": "Test Electronics",
            "description": "Test electronic component supplier for API testing",
            "api_type": "rest",
            "base_url": "https://api.testsupplier.com",
            "api_version": "v1",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_backoff": 1.0,
            "enabled": True,
            "supports_datasheet": True,
            "supports_image": False,
            "supports_pricing": True,
            "supports_stock": True,
            "supports_specifications": False,
            "custom_headers": {"Accept": "application/json"},
            "custom_parameters": {"format": "json"}
        }
    
    @pytest.fixture 
    def lcsc_supplier_data(self):
        """LCSC supplier configuration data"""
        return {
            "supplier_name": "LCSC",
            "display_name": "LCSC Electronics",
            "description": "Chinese electronics component supplier with EasyEDA integration",
            "api_type": "rest",
            "base_url": "https://easyeda.com",
            "enabled": True,
            "supports_datasheet": True,
            "supports_specifications": True
        }
    
    def test_create_supplier_success(self, auth_headers, sample_supplier_data):
        """Test successful creation of supplier configuration via API"""
        # Debug: Check what suppliers already exist
        existing_response = client.get("/api/config/suppliers", headers=auth_headers)
        print(f"Existing suppliers: {existing_response.json()}")
        
        response = client.post(
            "/api/config/suppliers",
            json=sample_supplier_data,
            headers=auth_headers
        )
        
        print(f"Create response status: {response.status_code}")
        print(f"Create response body: {response.json()}")
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert "Created supplier configuration: TESTSUPPLIER" in response_data["message"]
        
        # Verify the returned data structure
        supplier_data = response_data["data"]
        assert supplier_data["supplier_name"] == "TESTSUPPLIER"  # Should be normalized to uppercase
        assert supplier_data["display_name"] == "Test Electronics"
        assert supplier_data["enabled"] is True
        assert supplier_data["api_type"] == "rest"
        assert supplier_data["base_url"] == "https://api.testsupplier.com"
        
        # Verify capabilities are set correctly
        expected_capabilities = ["fetch_datasheet", "fetch_pricing", "fetch_stock"]
        assert set(supplier_data["capabilities"]) == set(expected_capabilities)
    
    def test_create_lcsc_supplier(self, auth_headers, lcsc_supplier_data):
        """Test creating LCSC supplier configuration"""
        response = client.post(
            "/api/config/suppliers",
            json=lcsc_supplier_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        supplier_data = response_data["data"]
        assert supplier_data["supplier_name"] == "LCSC"
        assert supplier_data["display_name"] == "LCSC Electronics"
        
        # Verify LCSC-specific capabilities
        expected_capabilities = ["fetch_datasheet", "fetch_specifications"]
        assert set(supplier_data["capabilities"]) == set(expected_capabilities)
    
    def test_create_duplicate_supplier_error(self, auth_headers, sample_supplier_data):
        """Test that creating duplicate supplier returns error"""
        # Create first supplier
        response1 = client.post(
            "/api/config/suppliers",
            json=sample_supplier_data,
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Try to create duplicate
        response2 = client.post(
            "/api/config/suppliers", 
            json=sample_supplier_data,
            headers=auth_headers
        )
        
        assert response2.status_code == 409  # Conflict
        response_data = response2.json()
        assert "already exists" in response_data["detail"]
        assert "Only one configuration per supplier type is allowed" in response_data["detail"]
    
    def test_create_case_insensitive_duplicate(self, auth_headers, lcsc_supplier_data):
        """Test that duplicate check is case-insensitive"""
        # Create LCSC supplier (uppercase)
        response1 = client.post(
            "/api/config/suppliers",
            json=lcsc_supplier_data,
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Try to create lcsc supplier (lowercase)
        lowercase_data = lcsc_supplier_data.copy()
        lowercase_data["supplier_name"] = "lcsc"
        lowercase_data["display_name"] = "LCSC Electronics (lowercase)"
        
        response2 = client.post(
            "/api/config/suppliers",
            json=lowercase_data,
            headers=auth_headers
        )
        
        assert response2.status_code == 409  # Should be rejected as duplicate
    
    def test_get_suppliers_empty(self, auth_headers):
        """Test getting suppliers when none exist"""
        response = client.get("/api/config/suppliers", headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert response_data["data"] == []
        assert "0 supplier configurations" in response_data["message"]
    
    def test_get_suppliers_with_data(self, auth_headers, sample_supplier_data, lcsc_supplier_data):
        """Test getting suppliers when some exist"""
        # Create test suppliers
        client.post("/api/config/suppliers", json=sample_supplier_data, headers=auth_headers)
        client.post("/api/config/suppliers", json=lcsc_supplier_data, headers=auth_headers)
        
        # Get all suppliers
        response = client.get("/api/config/suppliers", headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["status"] == "success"
        assert len(response_data["data"]) == 2
        assert "2 supplier configurations" in response_data["message"]
        
        # Verify supplier names
        supplier_names = [s["supplier_name"] for s in response_data["data"]]
        assert "TESTSUPPLIER" in supplier_names
        assert "LCSC" in supplier_names
    
    def test_delete_supplier_success(self, auth_headers, sample_supplier_data):
        """Test successful deletion of supplier configuration"""
        # Create supplier first
        create_response = client.post(
            "/api/config/suppliers",
            json=sample_supplier_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Delete the supplier
        delete_response = client.delete(
            "/api/config/suppliers/TESTSUPPLIER",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        response_data = delete_response.json()
        
        assert response_data["status"] == "success"
        assert "Deleted supplier configuration: TESTSUPPLIER" in response_data["message"]
        assert response_data["data"]["supplier_name"] == "TESTSUPPLIER"
        assert response_data["data"]["deleted"] == "true"
        
        # Verify supplier is actually deleted
        get_response = client.get("/api/config/suppliers", headers=auth_headers)
        assert get_response.status_code == 200
        assert len(get_response.json()["data"]) == 0
    
    def test_delete_nonexistent_supplier(self, auth_headers):
        """Test deleting supplier that doesn't exist"""
        response = client.delete(
            "/api/config/suppliers/NonExistentSupplier",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"]
    
    def test_delete_case_insensitive(self, auth_headers, lcsc_supplier_data):
        """Test that deletion works with different case"""
        # Create LCSC supplier
        create_response = client.post(
            "/api/config/suppliers",
            json=lcsc_supplier_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Delete using lowercase name
        delete_response = client.delete(
            "/api/config/suppliers/lcsc",  # lowercase
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        response_data = delete_response.json()
        assert response_data["status"] == "success"
    
    def test_unauthorized_access(self, sample_supplier_data):
        """Test that API requires authentication"""
        # Try to create supplier without auth headers
        response = client.post("/api/config/suppliers", json=sample_supplier_data)
        assert response.status_code == 401
        
        # Try to delete supplier without auth headers  
        response = client.delete("/api/config/suppliers/TestSupplier")
        assert response.status_code == 401
        
        # Try to get suppliers without auth headers
        response = client.get("/api/config/suppliers")
        assert response.status_code == 401
    
    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"supplier_name": ""}, "validation"),  # Empty name
        ({"supplier_name": "Test", "base_url": "invalid-url"}, "validation"),  # Invalid URL
        ({"supplier_name": "Test"}, "validation"),  # Missing base_url
        ({}, "validation"),  # Missing required fields
    ])
    def test_create_supplier_validation_errors(self, auth_headers, invalid_data, expected_error):
        """Test validation errors when creating suppliers"""
        response = client.post(
            "/api/config/suppliers",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_supplier_workflow_complete(self, auth_headers):
        """Test complete workflow: create, verify, delete, verify deletion"""
        # Step 1: Create supplier
        supplier_data = {
            "supplier_name": "WorkflowTest", 
            "display_name": "Workflow Test Supplier",
            "base_url": "https://api.workflowtest.com",
            "enabled": True,
            "supports_pricing": True
        }
        
        create_response = client.post(
            "/api/config/suppliers",
            json=supplier_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        created_supplier = create_response.json()["data"]
        
        # Step 2: Verify it exists in the list
        list_response = client.get("/api/config/suppliers", headers=auth_headers)
        assert list_response.status_code == 200
        suppliers = list_response.json()["data"]
        assert len(suppliers) == 1
        assert suppliers[0]["supplier_name"] == "WORKFLOWTEST"
        
        # Step 3: Get specific supplier
        get_response = client.get(
            "/api/config/suppliers/WORKFLOWTEST",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        supplier_details = get_response.json()["data"]
        assert supplier_details["display_name"] == "Workflow Test Supplier"
        
        # Step 4: Delete supplier
        delete_response = client.delete(
            "/api/config/suppliers/WORKFLOWTEST",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # Step 5: Verify deletion
        final_list_response = client.get("/api/config/suppliers", headers=auth_headers)
        assert final_list_response.status_code == 200
        assert len(final_list_response.json()["data"]) == 0
        
        # Step 6: Verify getting deleted supplier returns 404
        get_deleted_response = client.get(
            "/api/config/suppliers/WORKFLOWTEST",
            headers=auth_headers
        )
        assert get_deleted_response.status_code == 404