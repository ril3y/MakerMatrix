"""
Test supplier configuration API endpoints to ensure they work correctly
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.main import app
from MakerMatrix.services.supplier_config_service import SupplierConfigService
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    
    # Set up default roles and admin
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Clean up
    SQLModel.metadata.drop_all(engine)


class TestSupplierConfigurationAPI:
    """Test supplier configuration API endpoints"""
    
    def test_get_configured_suppliers_endpoint_exists(self):
        """Test that the /api/suppliers/configured endpoint exists and is accessible"""
        # First login to get auth token
        login_response = client.post("/auth/login", data={
            "username": "admin",
            "password": "Admin123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Test the configured suppliers endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/suppliers/configured", headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "data" in data
    
    def test_configured_suppliers_with_actual_config(self):
        """Test configured suppliers endpoint with an actual supplier configuration"""
        # First login to get auth token
        login_response = client.post("/auth/login", data={
            "username": "admin", 
            "password": "Admin123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a test supplier configuration
        supplier_config = {
            "supplier_name": "DIGIKEY",
            "display_name": "DigiKey Corporation",
            "base_url": "https://api.digikey.com",
            "enabled": True,
            "credentials": {
                "api_key": "test_api_key_123",
                "client_secret": "test_secret"
            },
            "config": {
                "rate_limit": 100,
                "timeout": 30
            }
        }
        
        # Add the supplier configuration
        config_response = client.post(
            "/api/config/suppliers",
            json=supplier_config,
            headers=headers
        )
        print(f"Config creation response: {config_response.status_code}")
        print(f"Config response body: {config_response.text}")
        
        if config_response.status_code not in [200, 201, 409]:  # 409 if already exists
            pytest.fail(f"Failed to create supplier config: {config_response.status_code} {config_response.text}")
        
        # Now test the configured suppliers endpoint
        response = client.get("/api/suppliers/configured", headers=headers)
        
        print(f"Configured suppliers response status: {response.status_code}")
        print(f"Configured suppliers response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        # Check if DIGIKEY is in the configured suppliers
        configured_suppliers = data["data"]
        digikey_found = False
        for supplier in configured_suppliers:
            # Check both 'name' and 'supplier_name' fields, and also 'id' field
            supplier_identifier = (supplier.get("name", "") or 
                                  supplier.get("supplier_name", "") or 
                                  supplier.get("id", "")).upper()
            if "DIGIKEY" in supplier_identifier:
                digikey_found = True
                assert supplier.get("configured") == True
                assert supplier.get("enabled") == True
                break
        
        assert digikey_found, f"DIGIKEY not found in configured suppliers: {configured_suppliers}"
    
    def test_configured_suppliers_response_format(self):
        """Test that configured suppliers response has the expected format"""
        # Login
        login_response = client.post("/auth/login", data={
            "username": "admin",
            "password": "Admin123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get configured suppliers
        response = client.get("/api/suppliers/configured", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "data" in data
        
        # Check data format
        suppliers = data["data"]
        assert isinstance(suppliers, list)
        
        # If there are suppliers, check their format
        if suppliers:
            for supplier in suppliers:
                assert "supplier_name" in supplier
                assert "configured" in supplier
                assert "enabled" in supplier
                # These fields should exist for configured suppliers
                assert "capabilities" in supplier or "description" in supplier
    
    def test_supplier_config_service_directly(self):
        """Test the SupplierConfigService directly to isolate API vs service issues"""
        supplier_service = SupplierConfigService()
        
        # Test getting all configurations
        try:
            all_configs = supplier_service.get_all_supplier_configs(enabled_only=False)
            print(f"All configs: {all_configs}")
            
            enabled_configs = supplier_service.get_all_supplier_configs(enabled_only=True)
            print(f"Enabled configs: {enabled_configs}")
            
            # This should not raise an exception
            assert isinstance(all_configs, list)
            assert isinstance(enabled_configs, list)
            
        except Exception as e:
            pytest.fail(f"SupplierConfigService failed: {e}")
    
    def test_frontend_api_call_simulation(self):
        """Simulate the exact API call that the frontend makes"""
        # Login first
        login_response = client.post("/auth/login", data={
            "username": "admin",
            "password": "Admin123!"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Simulate the exact frontend call
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/suppliers/configured", headers=headers)
        
        print(f"Frontend simulation - Status: {response.status_code}")
        print(f"Frontend simulation - Headers: {dict(response.headers)}")
        print(f"Frontend simulation - Body: {response.text}")
        
        # Check if response can be parsed as JSON
        try:
            json_data = response.json()
            print(f"Parsed JSON: {json_data}")
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {e}")
        
        assert response.status_code == 200
        assert "data" in json_data
    
    def test_cors_and_headers(self):
        """Test CORS and headers to ensure frontend can access the API"""
        # Login
        login_response = client.post("/auth/login", data={
            "username": "admin",
            "password": "Admin123!"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make request and check headers
        response = client.get("/api/suppliers/configured", headers=headers)
        
        print(f"Response headers: {dict(response.headers)}")
        
        # Check that response doesn't have CORS issues
        assert response.status_code == 200
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])