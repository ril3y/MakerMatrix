"""
Integration tests for import workflow with dynamic supplier capability detection.

This test suite verifies:
1. Import with configured suppliers and enrichment capabilities
2. Import with no suppliers configured
3. Import with supplier not added to system
4. Enrichment capability detection and selection
5. Error handling for various scenarios
"""
import pytest
import json
import tempfile
import io
from typing import Dict, Any

from MakerMatrix.main import app
from fastapi.testclient import TestClient
from MakerMatrix.models.database_schema import *
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.suppliers.base import SupplierCapability


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for API calls."""
    # Login with default admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_lcsc_csv():
    """Sample LCSC CSV data for testing."""
    return """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
1kΩ,R1,R_0805_2012Metric,C17513,UNI-ROYAL(Uniroyal Elec),0805W8F1001T5E,LCSC,C17513,1
"""


@pytest.fixture
def sample_digikey_csv():
    """Sample DigiKey CSV data for testing."""
    return """Index,Quantity,Part Number,Manufacturer,Description,Customer Reference
1,1,296-8903-1-ND,Texas Instruments,IC REG LINEAR 3.3V 1A SOT223,U1
2,2,399-1168-1-ND,KEMET,CAP CER 10UF 25V X7R 0805,C1
3,1,311-1.00KCRCT-ND,Yageo,RES SMD 1K OHM 1% 1/8W 0805,R1
"""


def clear_all_suppliers():
    """Clear all supplier configurations."""
    try:
        config_service = SupplierConfigService()
        configs = config_service.get_all_supplier_configs()
        for config in configs:
            config_service.delete_supplier_config(config['supplier_name'])
    except Exception as e:
        print(f"Error clearing suppliers: {e}")


def clear_all_parts(client, auth_headers):
    """Clear all parts from database."""
    try:
        response = client.delete("/api/parts/clear_all", headers=auth_headers)
        print(f"Clear parts response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error clearing parts: {e}")
        return False


class TestImportCapabilityDetection:
    """Test suite for import workflow with capability detection."""

    def test_import_suppliers_endpoint_no_suppliers_configured(self, client, auth_headers):
        """Test GET /api/import/suppliers when no suppliers are configured."""
        # Clear all suppliers first
        clear_all_suppliers()
        
        response = client.get("/api/import/suppliers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Should return suppliers that don't require configuration (like LCSC)
        # or show them as not configured
        suppliers = data["data"]
        print(f"Found {len(suppliers)} suppliers when none configured")
        
        for supplier in suppliers:
            assert "enrichment_capabilities" in supplier
            assert "enrichment_available" in supplier
            assert "enrichment_missing_credentials" in supplier
            
            # Suppliers should either be not configured or partially configured
            assert supplier["configuration_status"] in ["not_configured", "partial"]

    def test_import_suppliers_endpoint_with_lcsc_configured(self, client, auth_headers):
        """Test GET /api/import/suppliers with LCSC configured."""
        # Configure LCSC (no credentials needed)
        config_service = SupplierConfigService()
        lcsc_config = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        config_service.create_or_update_supplier_config("lcsc", lcsc_config)
        
        response = client.get("/api/import/suppliers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        suppliers = data["data"]
        lcsc_supplier = next((s for s in suppliers if s["name"] == "lcsc"), None)
        
        assert lcsc_supplier is not None
        assert lcsc_supplier["import_available"] is True
        assert lcsc_supplier["is_configured"] is True
        assert lcsc_supplier["configuration_status"] == "configured"
        
        # Check enrichment capabilities
        assert "enrichment_capabilities" in lcsc_supplier
        assert lcsc_supplier["enrichment_available"] is True
        assert len(lcsc_supplier["enrichment_capabilities"]) > 0
        
        # LCSC should support these capabilities
        expected_capabilities = ["get_part_details", "fetch_datasheet", "fetch_pricing_stock"]
        for cap in expected_capabilities:
            assert cap in lcsc_supplier["enrichment_capabilities"]

    def test_import_file_with_no_suppliers_configured(self, client, auth_headers, sample_lcsc_csv):
        """Test importing a file when no suppliers are configured."""
        clear_all_suppliers()
        clear_all_parts(client, auth_headers)
        
        # Create a temporary CSV file
        csv_file = io.StringIO(sample_lcsc_csv)
        files = {"file": ("test_lcsc.csv", csv_file, "text/csv")}
        data = {"supplier_name": "lcsc"}
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        # Should succeed for LCSC as it doesn't require configuration
        if response.status_code == 200:
            result = response.json()
            assert result["status"] == "success"
            assert result["data"]["imported_count"] > 0
        else:
            # If it fails, should be due to supplier not configured
            assert response.status_code in [403, 400]
            assert "not configured" in response.json()["detail"].lower()

    def test_import_file_with_configured_supplier_no_enrichment(self, client, auth_headers, sample_lcsc_csv):
        """Test importing a file with configured supplier but no enrichment."""
        # Configure LCSC
        config_service = SupplierConfigService()
        lcsc_config = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        config_service.create_or_update_supplier_config("lcsc", lcsc_config)
        
        clear_all_parts(client, auth_headers)
        
        # Create a temporary CSV file
        csv_file = io.StringIO(sample_lcsc_csv)
        files = {"file": ("test_lcsc.csv", csv_file, "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "false"
        }
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["data"]["imported_count"] > 0
        assert result["data"]["failed_count"] == 0
        
        # Verify parts were created
        parts_response = client.get("/api/parts/get_all_parts", headers=auth_headers)
        assert parts_response.status_code == 200
        parts_data = parts_response.json()
        assert len(parts_data["data"]) == result["data"]["imported_count"]

    def test_import_file_with_enrichment_capabilities(self, client, auth_headers, sample_lcsc_csv):
        """Test importing a file with enrichment capabilities enabled."""
        # Configure LCSC
        config_service = SupplierConfigService()
        lcsc_config = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        config_service.create_or_update_supplier_config("lcsc", lcsc_config)
        
        clear_all_parts(client, auth_headers)
        
        # Create a temporary CSV file
        csv_file = io.StringIO(sample_lcsc_csv)
        files = {"file": ("test_lcsc.csv", csv_file, "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "true",
            "enrichment_capabilities": "get_part_details,fetch_datasheet"
        }
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["data"]["imported_count"] > 0
        
        # Check that enrichment task was created
        warnings = result["data"]["warnings"]
        task_created = any("Enrichment task created" in warning for warning in warnings)
        assert task_created, f"No enrichment task created. Warnings: {warnings}"

    def test_import_file_invalid_supplier(self, client, auth_headers, sample_lcsc_csv):
        """Test importing a file with an invalid/unknown supplier."""
        clear_all_parts(client, auth_headers)
        
        # Create a temporary CSV file
        csv_file = io.StringIO(sample_lcsc_csv)
        files = {"file": ("test_lcsc.csv", csv_file, "text/csv")}
        data = {"supplier_name": "invalid_supplier"}
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        assert response.status_code == 400
        assert "Unknown supplier" in response.json()["detail"]

    def test_import_file_unsupported_supplier_capability(self, client, auth_headers, sample_digikey_csv):
        """Test importing with supplier that requires configuration but isn't configured."""
        clear_all_suppliers()
        clear_all_parts(client, auth_headers)
        
        # Try to import DigiKey file without configuring DigiKey
        csv_file = io.StringIO(sample_digikey_csv)
        files = {"file": ("test_digikey.csv", csv_file, "text/csv")}
        data = {"supplier_name": "digikey"}
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        # Should fail because DigiKey requires OAuth configuration
        assert response.status_code == 403
        assert "not configured" in response.json()["detail"].lower()

    def test_enrichment_capabilities_validation(self, client, auth_headers, sample_lcsc_csv):
        """Test that invalid enrichment capabilities are filtered out."""
        # Configure LCSC
        config_service = SupplierConfigService()
        lcsc_config = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        config_service.create_or_update_supplier_config("lcsc", lcsc_config)
        
        clear_all_parts(client, auth_headers)
        
        # Create a temporary CSV file
        csv_file = io.StringIO(sample_lcsc_csv)
        files = {"file": ("test_lcsc.csv", csv_file, "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "true",
            "enrichment_capabilities": "get_part_details,invalid_capability,fetch_datasheet"
        }
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        
        # Should still create enrichment task with valid capabilities only
        warnings = result["data"]["warnings"]
        task_created = any("Enrichment task created" in warning for warning in warnings)
        assert task_created

    def test_task_capabilities_suppliers_endpoint(self, client, auth_headers):
        """Test the task capabilities endpoint for suppliers."""
        response = client.get("/api/tasks/capabilities/suppliers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        capabilities = data["data"]
        assert isinstance(capabilities, dict)
        
        # Should have capabilities for available suppliers
        for supplier_name, caps in capabilities.items():
            assert isinstance(caps, list)
            # Each capability should be a valid SupplierCapability
            for cap in caps:
                assert cap in [c.value for c in SupplierCapability]

    def test_task_capabilities_specific_supplier(self, client, auth_headers):
        """Test getting capabilities for a specific supplier."""
        response = client.get("/api/tasks/capabilities/suppliers/lcsc", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        capabilities = data["data"]
        assert isinstance(capabilities, list)
        
        # LCSC should support these capabilities
        expected_capabilities = ["get_part_details", "fetch_datasheet", "fetch_pricing_stock", "import_orders"]
        for cap in expected_capabilities:
            assert cap in capabilities

    def test_import_with_order_info_extraction(self, client, auth_headers):
        """Test that order information is correctly extracted from filename."""
        # Configure LCSC
        config_service = SupplierConfigService()
        lcsc_config = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        config_service.create_or_update_supplier_config("lcsc", lcsc_config)
        
        clear_all_parts(client, auth_headers)
        
        # Create CSV with filename that contains order info
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
"""
        csv_file = io.StringIO(sample_csv)
        files = {"file": ("LCSC_Exported__20241201_143022.csv", csv_file, "text/csv")}
        data = {"supplier_name": "lcsc"}
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["data"]["imported_count"] > 0
        
        # Should have created an order with extracted date
        assert result["data"]["order_id"] is not None

    def test_file_format_validation(self, client, auth_headers):
        """Test that unsupported file formats are rejected."""
        clear_all_parts(client, auth_headers)
        
        # Try to upload a text file as CSV
        txt_content = "This is not a CSV file"
        files = {"file": ("test.txt", io.StringIO(txt_content), "text/plain")}
        data = {"supplier_name": "lcsc"}
        
        response = client.post("/api/import/file", headers=auth_headers, files=files, data=data)
        
        # Should fail due to file format validation
        assert response.status_code == 400
        assert "cannot import" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestImportCapabilityDetectionAsync:
    """Async tests for import capability detection."""

    async def test_supplier_capability_detection_performance(self, client, auth_headers):
        """Test that supplier capability detection is performant."""
        import time
        
        start_time = time.time()
        response = client.get("/api/import/suppliers", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should complete within 2 seconds
        
        data = response.json()
        suppliers = data["data"]
        
        # Each supplier should have capability information
        for supplier in suppliers:
            assert "enrichment_capabilities" in supplier
            assert "enrichment_available" in supplier
            assert isinstance(supplier["enrichment_capabilities"], list)
            assert isinstance(supplier["enrichment_available"], bool)


if __name__ == "__main__":
    # Run specific tests for manual verification
    import subprocess
    import sys
    
    # Clear parts first
    print("🧹 Clearing parts database...")
    try:
        result = subprocess.run([
            "curl", "-X", "DELETE", "http://localhost:8080/api/parts/clear_all"
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Parts cleared successfully")
        else:
            print(f"⚠️  Failed to clear parts: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Error clearing parts: {e}")
    
    print("\n🧪 Running import capability detection tests...")
    
    # Run the test suite
    pytest_args = [
        "-v",
        "-s", 
        __file__,
        "--tb=short"
    ]
    
    sys.exit(pytest.main(pytest_args))