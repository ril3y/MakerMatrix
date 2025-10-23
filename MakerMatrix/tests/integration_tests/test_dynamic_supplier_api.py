"""
Integration tests for the dynamic supplier API

Tests the actual API endpoints by calling the running server.
This verifies that the supplier system works end-to-end.
"""

import pytest
import requests
import json
from typing import Dict, Any

# Base URL for the API (should match the running server)
API_BASE_URL = "http://localhost:57891"


class TestSupplierAPIIntegration:
    """Integration tests for supplier API endpoints"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for API requests"""
        login_data = {"username": "admin", "password": "Admin123!"}
        response = requests.post(
            f"{API_BASE_URL}/auth/login", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        token_data = response.json()
        return token_data["access_token"]

    @pytest.fixture
    def auth_headers(self, auth_token):
        """Headers with authentication token"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_get_suppliers_list(self, auth_headers):
        """Test GET /api/suppliers/ endpoint"""
        response = requests.get(f"{API_BASE_URL}/api/suppliers/", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 3

        # Check expected suppliers are present
        suppliers = data["data"]
        assert "digikey" in suppliers
        assert "lcsc" in suppliers
        assert "mouser" in suppliers

    def test_get_all_suppliers_info(self, auth_headers):
        """Test GET /api/suppliers/info endpoint"""
        response = requests.get(f"{API_BASE_URL}/api/suppliers/info", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], dict)

        # Verify structure and content
        suppliers_info = data["data"]
        assert len(suppliers_info) >= 3

        # Check each expected supplier
        for supplier_name in ["digikey", "lcsc", "mouser"]:
            assert supplier_name in suppliers_info
            supplier_info = suppliers_info[supplier_name]

            # Verify required fields
            assert "name" in supplier_info
            assert "display_name" in supplier_info
            assert "description" in supplier_info
            assert "capabilities" in supplier_info
            assert "supports_oauth" in supplier_info

            assert supplier_info["name"] == supplier_name
            assert isinstance(supplier_info["capabilities"], list)
            assert len(supplier_info["capabilities"]) > 0
            assert isinstance(supplier_info["supports_oauth"], bool)

    def test_get_individual_supplier_info(self, auth_headers):
        """Test GET /api/suppliers/{supplier_name}/info endpoints"""
        for supplier_name in ["digikey", "lcsc", "mouser"]:
            response = requests.get(f"{API_BASE_URL}/api/suppliers/{supplier_name}/info", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            supplier_info = data["data"]
            assert supplier_info["name"] == supplier_name
            assert "display_name" in supplier_info
            assert "description" in supplier_info
            assert "capabilities" in supplier_info

    def test_get_credential_schemas(self, auth_headers):
        """Test GET /api/suppliers/{supplier_name}/credentials-schema endpoints"""
        # Test DigiKey (should have credentials)
        response = requests.get(f"{API_BASE_URL}/api/suppliers/digikey/credentials-schema", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2  # Should have client_id and client_secret

        # Check field structure
        for field in data["data"]:
            assert "name" in field
            assert "label" in field
            assert "field_type" in field
            assert "required" in field

        # Test LCSC (should have no credentials - public API)
        response = requests.get(f"{API_BASE_URL}/api/suppliers/lcsc/credentials-schema", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["data"] == []  # No credentials needed

        # Test Mouser (should have API key)
        response = requests.get(f"{API_BASE_URL}/api/suppliers/mouser/credentials-schema", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) >= 1  # Should have api_key

    def test_get_configuration_schemas(self, auth_headers):
        """Test GET /api/suppliers/{supplier_name}/config-schema endpoints"""
        for supplier_name in ["digikey", "lcsc", "mouser"]:
            response = requests.get(f"{API_BASE_URL}/api/suppliers/{supplier_name}/config-schema", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert isinstance(data["data"], list)

            # Check field structure
            for field in data["data"]:
                assert "name" in field
                assert "label" in field
                assert "field_type" in field
                assert "required" in field

    def test_get_supplier_capabilities(self, auth_headers):
        """Test GET /api/suppliers/{supplier_name}/capabilities endpoints"""
        for supplier_name in ["digikey", "lcsc", "mouser"]:
            response = requests.get(f"{API_BASE_URL}/api/suppliers/{supplier_name}/capabilities", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert isinstance(data["data"], list)
            assert len(data["data"]) > 0

    def test_supplier_info_consistency(self, auth_headers):
        """Test that supplier info is consistent between endpoints"""
        # Get all suppliers info
        response = requests.get(f"{API_BASE_URL}/api/suppliers/info", headers=auth_headers)
        all_suppliers_data = response.json()["data"]

        # Compare with individual supplier info
        for supplier_name in ["digikey", "lcsc", "mouser"]:
            response = requests.get(f"{API_BASE_URL}/api/suppliers/{supplier_name}/info", headers=auth_headers)
            individual_data = response.json()["data"]

            # Data should be consistent
            all_supplier_data = all_suppliers_data[supplier_name]
            assert all_supplier_data["name"] == individual_data["name"]
            assert all_supplier_data["display_name"] == individual_data["display_name"]
            assert all_supplier_data["description"] == individual_data["description"]
            assert all_supplier_data["capabilities"] == individual_data["capabilities"]

    def test_frontend_integration_scenario(self, auth_headers):
        """Test the complete frontend integration scenario"""
        # This simulates what the frontend does:
        # 1. Get all suppliers info for the modal
        # 2. For a selected supplier, get its schemas
        # 3. Verify data structure matches frontend expectations

        # Step 1: Get all suppliers (for supplier selection modal)
        response = requests.get(f"{API_BASE_URL}/api/suppliers/info", headers=auth_headers)
        assert response.status_code == 200

        suppliers_data = response.json()
        assert suppliers_data["status"] == "success"
        assert "data" in suppliers_data

        suppliers_info = suppliers_data["data"]
        assert isinstance(suppliers_info, dict)
        assert len(suppliers_info) >= 3

        # Step 2: For each supplier, test getting schemas (like the frontend would)
        for supplier_name, supplier_info in suppliers_info.items():
            # Get credential schema
            cred_response = requests.get(
                f"{API_BASE_URL}/api/suppliers/{supplier_name}/credentials-schema", headers=auth_headers
            )
            assert cred_response.status_code == 200
            cred_data = cred_response.json()

            # Get config schema
            config_response = requests.get(
                f"{API_BASE_URL}/api/suppliers/{supplier_name}/config-schema", headers=auth_headers
            )
            assert config_response.status_code == 200
            config_data = config_response.json()

            # Verify data structure
            assert "data" in cred_data
            assert "data" in config_data
            assert isinstance(cred_data["data"], list)
            assert isinstance(config_data["data"], list)

            # Verify field definitions have required structure
            for field in cred_data["data"] + config_data["data"]:
                assert "name" in field
                assert "label" in field
                assert "field_type" in field
                assert "required" in field

    def test_error_handling(self, auth_headers):
        """Test error handling for invalid requests"""
        # Test invalid supplier name
        response = requests.get(f"{API_BASE_URL}/api/suppliers/invalid_supplier/info", headers=auth_headers)
        assert response.status_code == 404

        # Test without authentication
        response = requests.get(f"{API_BASE_URL}/api/suppliers/info")
        assert response.status_code == 401


def test_api_server_is_running():
    """Basic test to ensure the API server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        # Should get some response (even if it's 404 for non-existent route)
        assert response.status_code in [200, 404]
    except requests.exceptions.ConnectionError:
        pytest.fail("API server is not running. Please start the server with 'python -m MakerMatrix.main'")


def test_api_endpoints_are_registered():
    """Test that supplier API endpoints are properly registered"""
    # This test verifies the routes exist in the OpenAPI spec
    try:
        response = requests.get(f"{API_BASE_URL}/openapi.json", timeout=5)
        assert response.status_code == 200

        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})

        # Check that our supplier endpoints are registered
        expected_paths = [
            "/api/suppliers/",
            "/api/suppliers/info",
            "/api/suppliers/{supplier_name}/info",
            "/api/suppliers/{supplier_name}/credentials-schema",
            "/api/suppliers/{supplier_name}/config-schema",
            "/api/suppliers/{supplier_name}/capabilities",
        ]

        for expected_path in expected_paths:
            # The path might have different parameter syntax in OpenAPI
            path_exists = any(
                expected_path.replace("{supplier_name}", "{supplier_name}") in path
                or expected_path.replace("{supplier_name}", "{supplier_name:path}") in path
                for path in paths.keys()
            )
            assert path_exists, f"Expected API path {expected_path} not found in OpenAPI spec"

    except requests.exceptions.ConnectionError:
        pytest.fail("API server is not running")
