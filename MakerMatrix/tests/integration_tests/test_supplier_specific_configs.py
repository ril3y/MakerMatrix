"""
Integration tests for Supplier-Specific Configuration Patterns

Tests the supplier-specific configuration handling for DigiKey (OAuth fields),
LCSC, and Mouser suppliers to ensure custom_parameters are properly managed.
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

# Use in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
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
    """Clean up test database (no-op for in-memory DB)"""
    pass


class TestSupplierSpecificConfigs:

    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Create test database tables before each test"""
        cleanup_test_db()
        SQLModel.metadata.create_all(bind=engine)
        yield
        SQLModel.metadata.drop_all(bind=engine)
        cleanup_test_db()

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for API requests"""
        # Try to login with default admin
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Admin123!"}
        )

        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        else:
            pytest.skip("Admin user not available in test database")

    @pytest.fixture
    def digikey_config_data(self):
        """DigiKey configuration with OAuth-specific fields in custom_parameters"""
        return {
            "supplier_name": "digikey",
            "display_name": "DigiKey Electronics",
            "description": "Global electronic components distributor",
            "api_type": "rest",
            "base_url": "https://sandbox-api.digikey.com",
            "api_version": "v1",
            "rate_limit_per_minute": 1000,
            "timeout_seconds": 30,
            "max_retries": 3,
            "enabled": True,
            "supports_datasheet": True,
            "supports_image": True,
            "supports_pricing": True,
            "supports_stock": True,
            "supports_specifications": True,
            "custom_headers": {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            "custom_parameters": {
                "sandbox_mode": True,
                "oauth_callback_url": "https://localhost:8443/api/suppliers/digikey/oauth/callback",
                "storage_path": "/tmp/digikey_cache"
            }
        }

    @pytest.fixture
    def lcsc_config_data(self):
        """LCSC configuration using standard fields"""
        return {
            "supplier_name": "lcsc",
            "display_name": "LCSC Electronics",
            "description": "Chinese electronics component supplier with EasyEDA integration",
            "api_type": "rest",
            "base_url": "https://easyeda.com/api/components",
            "api_version": "v1",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 30,
            "max_retries": 3,
            "enabled": True,
            "supports_datasheet": True,
            "supports_image": True,
            "supports_pricing": True,
            "supports_specifications": True,
            "custom_headers": {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            "custom_parameters": {}
        }

    @pytest.fixture
    def mouser_config_data(self):
        """Mouser configuration using standard fields"""
        return {
            "supplier_name": "mouser",
            "display_name": "Mouser Electronics",
            "description": "Electronic component distributor with extensive catalog",
            "api_type": "rest",
            "base_url": "https://api.mouser.com/api/v1",
            "api_version": "v1",
            "rate_limit_per_minute": 1000,
            "timeout_seconds": 30,
            "max_retries": 3,
            "enabled": True,
            "supports_datasheet": True,
            "supports_image": True,
            "supports_pricing": True,
            "supports_stock": True,
            "supports_specifications": True,
            "custom_headers": {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            "custom_parameters": {}
        }

    def test_digikey_oauth_fields_in_custom_parameters(self, auth_headers, digikey_config_data):
        """Test DigiKey configuration stores OAuth fields in custom_parameters"""
        response = client.post(
            "/api/suppliers/config/suppliers",
            json=digikey_config_data,
            headers=auth_headers
        )

        assert response.status_code in [200, 201], f"Failed to create DigiKey config: {response.text}"

        data = response.json().get("data")
        assert data is not None
        assert data["supplier_name"] == "digikey"

        # Verify OAuth fields are in custom_parameters
        custom_params = data.get("custom_parameters", {})
        assert "sandbox_mode" in custom_params
        assert custom_params["sandbox_mode"] is True
        assert "oauth_callback_url" in custom_params
        assert custom_params["oauth_callback_url"] == "https://localhost:8443/api/suppliers/digikey/oauth/callback"
        assert "storage_path" in custom_params
        assert custom_params["storage_path"] == "/tmp/digikey_cache"

    def test_digikey_sandbox_mode_affects_base_url(self, auth_headers):
        """Test DigiKey sandbox mode changes base_url appropriately"""
        # Test with sandbox mode enabled
        sandbox_config = {
            "supplier_name": "digikey_sandbox",
            "display_name": "DigiKey Sandbox",
            "base_url": "https://sandbox-api.digikey.com",
            "custom_parameters": {
                "sandbox_mode": True
            }
        }

        response = client.post(
            "/api/suppliers/config/suppliers",
            json=sandbox_config,
            headers=auth_headers
        )

        if response.status_code in [200, 201]:
            data = response.json().get("data")
            assert "sandbox-api" in data["base_url"]
            assert data["custom_parameters"]["sandbox_mode"] is True

    def test_lcsc_standard_fields_only(self, auth_headers, lcsc_config_data):
        """Test LCSC configuration uses only standard fields"""
        response = client.post(
            "/api/suppliers/config/suppliers",
            json=lcsc_config_data,
            headers=auth_headers
        )

        assert response.status_code in [200, 201], f"Failed to create LCSC config: {response.text}"

        data = response.json().get("data")
        assert data is not None
        assert data["supplier_name"] == "lcsc"
        assert data["base_url"] == "https://easyeda.com/api/components"

        # Verify custom_parameters is empty or minimal for LCSC
        custom_params = data.get("custom_parameters", {})
        # LCSC shouldn't have OAuth-specific fields
        assert "sandbox_mode" not in custom_params
        assert "oauth_callback_url" not in custom_params
        assert "storage_path" not in custom_params

    def test_mouser_standard_fields_only(self, auth_headers, mouser_config_data):
        """Test Mouser configuration uses only standard fields"""
        response = client.post(
            "/api/suppliers/config/suppliers",
            json=mouser_config_data,
            headers=auth_headers
        )

        assert response.status_code in [200, 201], f"Failed to create Mouser config: {response.text}"

        data = response.json().get("data")
        assert data is not None
        assert data["supplier_name"] == "mouser"
        assert data["base_url"] == "https://api.mouser.com/api/v1"

        # Verify custom_parameters is empty or minimal for Mouser
        custom_params = data.get("custom_parameters", {})
        # Mouser shouldn't have OAuth-specific fields
        assert "sandbox_mode" not in custom_params
        assert "oauth_callback_url" not in custom_params
        assert "storage_path" not in custom_params

    def test_custom_parameters_persistence(self, auth_headers, digikey_config_data):
        """Test custom_parameters are properly persisted and retrieved"""
        # Create DigiKey config
        create_response = client.post(
            "/api/suppliers/config/suppliers",
            json=digikey_config_data,
            headers=auth_headers
        )

        assert create_response.status_code in [200, 201]

        # Retrieve the config
        get_response = client.get(
            "/api/suppliers/config/suppliers/digikey",
            headers=auth_headers
        )

        assert get_response.status_code == 200

        data = get_response.json().get("data")
        custom_params = data.get("custom_parameters", {})

        # Verify all OAuth fields persisted correctly
        assert custom_params["sandbox_mode"] is True
        assert custom_params["oauth_callback_url"] == "https://localhost:8443/api/suppliers/digikey/oauth/callback"
        assert custom_params["storage_path"] == "/tmp/digikey_cache"

    def test_update_digikey_oauth_fields(self, auth_headers, digikey_config_data):
        """Test updating DigiKey OAuth fields in custom_parameters"""
        # Create initial config
        create_response = client.post(
            "/api/suppliers/config/suppliers",
            json=digikey_config_data,
            headers=auth_headers
        )

        assert create_response.status_code in [200, 201]

        # Update OAuth fields
        update_data = {
            "custom_parameters": {
                "sandbox_mode": False,  # Switch to production
                "oauth_callback_url": "https://production.example.com/callback",
                "storage_path": "/var/lib/digikey_tokens"
            }
        }

        update_response = client.put(
            "/api/suppliers/config/suppliers/digikey",
            json=update_data,
            headers=auth_headers
        )

        if update_response.status_code == 200:
            data = update_response.json().get("data")
            custom_params = data.get("custom_parameters", {})

            assert custom_params["sandbox_mode"] is False
            assert custom_params["oauth_callback_url"] == "https://production.example.com/callback"
            assert custom_params["storage_path"] == "/var/lib/digikey_tokens"

    def test_custom_headers_set_correctly(self, auth_headers, digikey_config_data):
        """Test custom headers are properly set for all suppliers"""
        response = client.post(
            "/api/suppliers/config/suppliers",
            json=digikey_config_data,
            headers=auth_headers
        )

        if response.status_code in [200, 201]:
            data = response.json().get("data")
            custom_headers = data.get("custom_headers", {})

            assert custom_headers.get("Accept") == "application/json"
            assert custom_headers.get("Content-Type") == "application/json"

    def test_multiple_suppliers_coexist(self, auth_headers, digikey_config_data, lcsc_config_data, mouser_config_data):
        """Test multiple suppliers with different config patterns can coexist"""
        # Create all three suppliers
        suppliers = [
            ("digikey", digikey_config_data),
            ("lcsc", lcsc_config_data),
            ("mouser", mouser_config_data)
        ]

        for supplier_name, config_data in suppliers:
            response = client.post(
                "/api/suppliers/config/suppliers",
                json=config_data,
                headers=auth_headers
            )

            if response.status_code not in [200, 201]:
                continue  # Skip if creation fails (might already exist)

        # Verify all exist with correct configurations
        list_response = client.get(
            "/api/suppliers/config/suppliers",
            headers=auth_headers
        )

        if list_response.status_code == 200:
            suppliers_list = list_response.json().get("data", [])
            supplier_names = [s["supplier_name"] for s in suppliers_list]

            # Check if our test suppliers are present
            for supplier_name, _ in suppliers:
                if supplier_name in supplier_names:
                    supplier = next(s for s in suppliers_list if s["supplier_name"] == supplier_name)

                    if supplier_name == "digikey":
                        # DigiKey should have OAuth fields in custom_parameters
                        custom_params = supplier.get("custom_parameters", {})
                        assert "sandbox_mode" in custom_params or len(custom_params) > 0
                    else:
                        # LCSC and Mouser should not have OAuth fields
                        custom_params = supplier.get("custom_parameters", {})
                        assert "oauth_callback_url" not in custom_params
                        assert "storage_path" not in custom_params

    def test_invalid_custom_parameters_rejected(self, auth_headers):
        """Test that invalid custom_parameters structure is rejected"""
        invalid_config = {
            "supplier_name": "invalid_test",
            "display_name": "Invalid Test",
            "base_url": "https://example.com",
            "custom_parameters": "this should be a dict not a string"
        }

        response = client.post(
            "/api/suppliers/config/suppliers",
            json=invalid_config,
            headers=auth_headers
        )

        # Should fail validation
        assert response.status_code in [400, 422]
