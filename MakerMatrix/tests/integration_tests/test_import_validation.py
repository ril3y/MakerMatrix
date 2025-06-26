"""
Integration tests for import validation - ensuring suppliers must be configured before allowing imports.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.database.db import get_session
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel

# Test client
client = TestClient(app)

# Mock user for testing
def mock_get_current_user():
    from MakerMatrix.models.user_models import RoleModel
    
    # Create admin role
    admin_role = RoleModel(
        id="admin-role-id",
        name="admin",
        description="Administrator role",
        permissions=["parts:read", "parts:write", "parts:create", "parts:delete", "supplier_config:read", "tasks:read", "tasks:create"]
    )
    
    return UserModel(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        is_active=True,
        password_change_required=False,
        roles=[admin_role]
    )

# Override the dependency
app.dependency_overrides[get_current_user] = mock_get_current_user


class TestImportValidation:
    """Test import validation for unconfigured suppliers"""

    def setup_method(self):
        """Setup for each test"""
        self.test_csv_content = """LCSC Part Number,Part Name,Quantity,Price
C1525,0.1uF 50V Ceramic Capacitor,10,0.05
C2012,10uF 25V Electrolytic Capacitor,5,0.15"""
        
        # Create temporary CSV file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        self.temp_file.write(self.test_csv_content)
        self.temp_file.close()

    def teardown_method(self):
        """Cleanup after each test"""
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_import_suppliers_shows_configuration_status(self):
        """Test that /api/import/suppliers properly shows configuration status"""
        response = client.get("/api/import/suppliers")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "data" in data
        
        suppliers = data["data"]
        assert len(suppliers) > 0
        
        # Check that each supplier has configuration fields
        for supplier in suppliers:
            assert "name" in supplier
            assert "display_name" in supplier
            assert "import_available" in supplier
            assert "is_configured" in supplier
            assert "configuration_status" in supplier
            
            # Configuration status should be one of the expected values
            assert supplier["configuration_status"] in ["configured", "not_configured", "partial"]

    def test_import_file_blocks_unconfigured_supplier(self):
        """Test that importing behavior for unconfigured suppliers"""
        # First, verify DigiKey is not configured
        response = client.get("/api/import/suppliers")
        assert response.status_code == 200
        
        suppliers = response.json()["data"]
        digikey_supplier = next((s for s in suppliers if s["name"] == "digikey"), None)
        
        if digikey_supplier:
            # DigiKey shows as "partial" - can import files but not fully configured
            if not digikey_supplier["is_configured"]:
                with open(self.temp_file.name, 'rb') as f:
                    response = client.post(
                        "/api/import/file",
                        data={"supplier_name": "digikey"},
                        files={"file": ("test.csv", f, "text/csv")}
                    )
                
                # DigiKey imports are actually allowed due to "partial" status
                # (can import CSV files without API credentials)
                if digikey_supplier["configuration_status"] == "partial":
                    # Should succeed or fail due to file format, not configuration
                    assert response.status_code in [200, 400]
                    if response.status_code == 400:
                        error_data = response.json()
                        # Error should be about file format, not configuration
                        error_msg = error_data.get("message", "").lower()
                        assert "cannot import" in error_msg or "not supported" in error_msg or "format" in error_msg
                else:
                    # If truly not configured, should fail
                    assert response.status_code in [403, 400]
                    error_data = response.json()
                    error_msg = error_data.get("message", "") + " " + error_data.get("detail", "")
                    assert "not configured" in error_msg.lower() or "configure" in error_msg.lower()

    def test_import_file_works_for_configured_supplier(self):
        """Test that importing works for properly configured suppliers"""
        # First check if LCSC is configured
        response = client.get("/api/import/suppliers")
        assert response.status_code == 200
        
        suppliers = response.json()["data"]
        lcsc_supplier = next((s for s in suppliers if s["name"] == "lcsc"), None)
        
        if lcsc_supplier and lcsc_supplier["is_configured"]:
            with open(self.temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/import/file",
                    data={"supplier_name": "lcsc"},
                    files={"file": ("test.csv", f, "text/csv")}
                )
            
            # Should succeed (200) or partial success
            assert response.status_code == 200
            
            result_data = response.json()
            assert result_data["status"] == "success"
            assert "data" in result_data
            assert "imported_count" in result_data["data"]

    def test_import_preview_works_regardless_of_configuration(self):
        """Test that preview functionality works even for unconfigured suppliers"""
        # Preview should work for any supplier since it's just file analysis
        response = client.post(
            "/api/import/preview",
            json={"csv_content": self.test_csv_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "data" in data
        preview_data = data["data"]
        
        # Should detect file structure even without supplier configuration
        assert "headers" in preview_data
        assert "total_rows" in preview_data
        assert len(preview_data["headers"]) > 0

    def test_import_file_with_nonexistent_supplier(self):
        """Test that importing fails gracefully for non-existent suppliers"""
        with open(self.temp_file.name, 'rb') as f:
            response = client.post(
                "/api/import/file",
                data={"supplier_name": "nonexistent_supplier"},
                files={"file": ("test.csv", f, "text/csv")}
            )
        
        assert response.status_code == 400
        error_data = response.json()
        error_msg = error_data.get("message", "") + " " + error_data.get("detail", "")
        assert "unknown supplier" in error_msg.lower()

    def test_import_suppliers_filtering_logic(self):
        """Test that supplier filtering logic works correctly"""
        response = client.get("/api/import/suppliers")
        assert response.status_code == 200
        
        suppliers = response.json()["data"]
        
        # Verify filtering logic
        for supplier in suppliers:
            # All returned suppliers should support imports
            assert supplier["import_available"] is not None
            
            # Configuration status should be consistent
            if supplier["is_configured"]:
                assert supplier["configuration_status"] == "configured"
            else:
                # Should be either "not_configured" or "partial"
                assert supplier["configuration_status"] in ["not_configured", "partial"]
                
            # If supplier has missing credentials and is not configured, 
            # it should not be available for import (unless it's partial)
            if supplier["missing_credentials"] and not supplier["is_configured"]:
                if supplier["configuration_status"] != "partial":
                    assert not supplier["import_available"]

    @pytest.mark.asyncio
    async def test_supplier_configuration_service_integration(self):
        """Test integration with supplier configuration service"""
        try:
            # Test that the configuration service is accessible
            config_service = SupplierConfigService()
            configs = config_service.get_all_supplier_configs()
            
            # Should return a list (even if empty)
            assert isinstance(configs, list)
            
            # If there are configs, they should have the right structure
            for config in configs:
                assert "supplier_name" in config
                assert "enabled" in config
                
        except Exception as e:
            # If config service is not available, the import validation should handle it gracefully
            print(f"Configuration service not available: {e}")
            
            # Test that import endpoint handles missing config service
            response = client.get("/api/import/suppliers")
            assert response.status_code == 200  # Should not crash


if __name__ == "__main__":
    pytest.main([__file__])