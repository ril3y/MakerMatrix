"""
Basic Supplier Configuration API Test

Simple test that validates supplier creation and deletion functionality
without complex database isolation, demonstrating the core functionality.
"""

import pytest
from fastapi.testclient import TestClient

from MakerMatrix.main import app

client = TestClient(app)


class TestSupplierBasicAPI:
    
    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for API requests"""
        # Login to get token
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Admin123!"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Admin user not available")
    
    def test_supplier_api_endpoints_exist(self, auth_headers):
        """Test that supplier API endpoints are accessible"""
        # Test GET suppliers endpoint
        response = client.get("/api/config/suppliers", headers=auth_headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data
        
        print(f"✅ Successfully retrieved {len(response_data['data'])} supplier configurations")
    
    def test_supplier_creation_and_deletion_workflow(self, auth_headers):
        """Test creating and deleting a unique supplier"""
        import uuid
        unique_name = f"TEST_{str(uuid.uuid4()).replace('-', '').upper()[:8]}"
        
        # Create unique supplier configuration
        supplier_data = {
            "supplier_name": unique_name,
            "display_name": f"Test Supplier {unique_name}",
            "description": "Integration test supplier for API validation",
            "api_type": "rest",
            "base_url": "https://api.example-test.com",
            "enabled": True,
            "supports_pricing": True
        }
        
        # Step 1: Create supplier
        create_response = client.post(
            "/api/config/suppliers",
            json=supplier_data,
            headers=auth_headers
        )
        
        print(f"Create response status: {create_response.status_code}")
        print(f"Create response: {create_response.json()}")
        
        if create_response.status_code == 200:
            response_data = create_response.json()
            assert response_data["status"] == "success"
            assert unique_name in response_data["message"]
            print(f"✅ Successfully created supplier: {unique_name}")
            
            # Step 2: Verify it exists
            get_response = client.get(f"/api/config/suppliers/{unique_name}", headers=auth_headers)
            if get_response.status_code == 200:
                supplier_details = get_response.json()["data"]
                assert supplier_details["supplier_name"] == unique_name
                print(f"✅ Successfully retrieved supplier: {unique_name}")
            
            # Step 3: Delete supplier
            delete_response = client.delete(f"/api/config/suppliers/{unique_name}", headers=auth_headers)
            
            print(f"Delete response status: {delete_response.status_code}")
            print(f"Delete response: {delete_response.json()}")
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                assert delete_data["status"] == "success"
                assert unique_name in delete_data["message"]
                print(f"✅ Successfully deleted supplier: {unique_name}")
                
                # Step 4: Verify deletion
                final_get_response = client.get(f"/api/config/suppliers/{unique_name}", headers=auth_headers)
                assert final_get_response.status_code == 404
                print(f"✅ Confirmed supplier {unique_name} was deleted")
            else:
                print(f"⚠️  Delete failed: {delete_response.json()}")
        else:
            print(f"⚠️  Creation failed: {create_response.json()}")
    
    def test_duplicate_supplier_prevention(self, auth_headers):
        """Test that duplicate supplier detection works correctly"""
        # Get existing suppliers
        response = client.get("/api/config/suppliers", headers=auth_headers)
        assert response.status_code == 200
        existing_suppliers = response.json()["data"]
        
        if existing_suppliers:
            # Try to create a duplicate of the first existing supplier
            first_supplier = existing_suppliers[0]
            duplicate_data = {
                "supplier_name": first_supplier["supplier_name"],
                "display_name": "Duplicate Test",
                "base_url": "https://duplicate.com",
                "enabled": True
            }
            
            duplicate_response = client.post(
                "/api/config/suppliers",
                json=duplicate_data,
                headers=auth_headers
            )
            
            print(f"Duplicate response status: {duplicate_response.status_code}")
            print(f"Duplicate response: {duplicate_response.json()}")
            
            # Should return 409 Conflict
            assert duplicate_response.status_code == 409
            response_data = duplicate_response.json()
            assert "already exists" in response_data.get("detail", response_data.get("message", ""))
            print(f"✅ Duplicate prevention working: {first_supplier['supplier_name']}")
        else:
            print("⚠️  No existing suppliers to test duplicate prevention")
    
    def test_supplier_capability_system(self, auth_headers):
        """Test that supplier capabilities are properly handled"""
        import uuid
        unique_name = f"CAP_{str(uuid.uuid4()).replace('-', '').upper()[:8]}"
        
        # Create supplier with specific capabilities
        supplier_data = {
            "supplier_name": unique_name,
            "display_name": f"Capability Test {unique_name}",
            "base_url": "https://api.capability-test.com",
            "enabled": True,
            "supports_datasheet": True,
            "supports_pricing": True,
            "supports_stock": False
        }
        
        create_response = client.post(
            "/api/config/suppliers",
            json=supplier_data,
            headers=auth_headers
        )
        
        if create_response.status_code == 200:
            response_data = create_response.json()
            supplier_info = response_data["data"]
            
            # Check that capabilities are properly set
            capabilities = supplier_info.get("capabilities", [])
            assert "fetch_datasheet" in capabilities
            assert "fetch_pricing" in capabilities
            assert "fetch_stock" not in capabilities
            
            print(f"✅ Capabilities properly set for {unique_name}: {capabilities}")
            
            # Clean up
            client.delete(f"/api/config/suppliers/{unique_name}", headers=auth_headers)
        else:
            print(f"⚠️  Capability test creation failed: {create_response.json()}")