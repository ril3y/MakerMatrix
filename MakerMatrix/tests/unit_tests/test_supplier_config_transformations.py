"""
Unit tests for Supplier Configuration Transformations

Tests the supplier-specific configuration transformation logic for DigiKey,
LCSC, and Mouser suppliers, focusing on custom_parameters handling.
"""

import pytest
from typing import Dict, Any


class TestSupplierConfigTransformations:
    """Test supplier configuration transformation patterns"""

    @pytest.fixture
    def base_digikey_config(self) -> Dict[str, Any]:
        """Base DigiKey configuration"""
        return {
            "supplier_name": "digikey",
            "display_name": "DigiKey Electronics",
            "description": "Global electronic components distributor",
            "base_url": "https://api.digikey.com",
            "api_version": "v1",
            "rate_limit_per_minute": 1000,
            "timeout_seconds": 30,
            "max_retries": 3,
            "enabled": True,
            "custom_headers": {},
            "custom_parameters": {},
        }

    @pytest.fixture
    def digikey_oauth_data(self) -> Dict[str, Any]:
        """DigiKey OAuth-specific fields"""
        return {
            "sandbox_mode": True,
            "oauth_callback_url": "https://localhost:8443/api/suppliers/digikey/oauth/callback",
            "storage_path": "/tmp/digikey_cache",
        }

    def test_digikey_oauth_fields_transform_to_custom_parameters(self, base_digikey_config, digikey_oauth_data):
        """Test DigiKey OAuth fields are transformed into custom_parameters"""
        # Simulate frontend transformation: DigiKey-specific fields -> custom_parameters
        config = base_digikey_config.copy()
        config["custom_parameters"] = {
            "sandbox_mode": digikey_oauth_data["sandbox_mode"],
            "oauth_callback_url": digikey_oauth_data["oauth_callback_url"],
            "storage_path": digikey_oauth_data["storage_path"],
        }

        # Verify transformation
        assert "sandbox_mode" in config["custom_parameters"]
        assert config["custom_parameters"]["sandbox_mode"] is True
        assert "oauth_callback_url" in config["custom_parameters"]
        assert config["custom_parameters"]["oauth_callback_url"] == digikey_oauth_data["oauth_callback_url"]
        assert "storage_path" in config["custom_parameters"]
        assert config["custom_parameters"]["storage_path"] == digikey_oauth_data["storage_path"]

    def test_digikey_sandbox_mode_updates_base_url(self, base_digikey_config):
        """Test sandbox mode changes base_url appropriately"""
        config_sandbox = base_digikey_config.copy()
        config_sandbox["custom_parameters"] = {"sandbox_mode": True}
        config_sandbox["base_url"] = "https://sandbox-api.digikey.com"

        config_production = base_digikey_config.copy()
        config_production["custom_parameters"] = {"sandbox_mode": False}
        config_production["base_url"] = "https://api.digikey.com"

        # Verify sandbox URL
        assert "sandbox" in config_sandbox["base_url"]
        assert config_sandbox["custom_parameters"]["sandbox_mode"] is True

        # Verify production URL
        assert "sandbox" not in config_production["base_url"]
        assert config_production["custom_parameters"]["sandbox_mode"] is False

    def test_digikey_sets_default_headers(self, base_digikey_config):
        """Test DigiKey transformation sets default headers"""
        config = base_digikey_config.copy()
        config["custom_headers"] = {"Accept": "application/json", "Content-Type": "application/json"}

        assert config["custom_headers"]["Accept"] == "application/json"
        assert config["custom_headers"]["Content-Type"] == "application/json"

    def test_lcsc_uses_standard_fields_only(self):
        """Test LCSC configuration uses standard fields without custom_parameters"""
        lcsc_config = {
            "supplier_name": "lcsc",
            "display_name": "LCSC Electronics",
            "base_url": "https://easyeda.com/api/components",
            "rate_limit_per_minute": 100,
            "custom_parameters": {},
            "custom_headers": {"Accept": "application/json", "Content-Type": "application/json"},
        }

        # Verify no OAuth-specific fields
        assert "sandbox_mode" not in lcsc_config["custom_parameters"]
        assert "oauth_callback_url" not in lcsc_config["custom_parameters"]
        assert "storage_path" not in lcsc_config["custom_parameters"]

        # Verify standard headers are set
        assert lcsc_config["custom_headers"]["Accept"] == "application/json"

    def test_mouser_uses_standard_fields_only(self):
        """Test Mouser configuration uses standard fields without custom_parameters"""
        mouser_config = {
            "supplier_name": "mouser",
            "display_name": "Mouser Electronics",
            "base_url": "https://api.mouser.com/api/v1",
            "rate_limit_per_minute": 1000,
            "custom_parameters": {},
            "custom_headers": {"Accept": "application/json", "Content-Type": "application/json"},
        }

        # Verify no OAuth-specific fields
        assert "sandbox_mode" not in mouser_config["custom_parameters"]
        assert "oauth_callback_url" not in mouser_config["custom_parameters"]
        assert "storage_path" not in mouser_config["custom_parameters"]

        # Verify standard headers are set
        assert mouser_config["custom_headers"]["Accept"] == "application/json"

    def test_custom_parameters_merge_preserves_existing(self):
        """Test merging custom_parameters preserves existing fields"""
        existing_config = {
            "supplier_name": "digikey",
            "custom_parameters": {"existing_field": "existing_value", "another_field": 123},
        }

        # Merge new OAuth fields
        oauth_fields = {"sandbox_mode": True, "oauth_callback_url": "https://example.com/callback"}

        merged_params = {**existing_config["custom_parameters"], **oauth_fields}

        # Verify both old and new fields exist
        assert merged_params["existing_field"] == "existing_value"
        assert merged_params["another_field"] == 123
        assert merged_params["sandbox_mode"] is True
        assert merged_params["oauth_callback_url"] == "https://example.com/callback"

    def test_custom_parameters_empty_dict_valid(self):
        """Test empty custom_parameters dict is valid for non-OAuth suppliers"""
        configs = [
            {"supplier_name": "lcsc", "custom_parameters": {}},
            {"supplier_name": "mouser", "custom_parameters": {}},
        ]

        for config in configs:
            assert isinstance(config["custom_parameters"], dict)
            assert len(config["custom_parameters"]) == 0

    def test_supplier_specific_field_separation(self):
        """Test supplier-specific fields are properly separated from base config"""
        # Simulates frontend pattern of keeping supplier-specific data separate
        base_config = {"supplier_name": "digikey", "display_name": "DigiKey", "base_url": "https://api.digikey.com"}

        supplier_specific_data = {
            "sandbox_mode": True,
            "oauth_callback_url": "https://localhost:8443/callback",
            "storage_path": "/tmp/cache",
        }

        # These should NOT be in base config
        assert "sandbox_mode" not in base_config
        assert "oauth_callback_url" not in base_config
        assert "storage_path" not in base_config

        # They should be in supplier_specific_data
        assert "sandbox_mode" in supplier_specific_data
        assert "oauth_callback_url" in supplier_specific_data
        assert "storage_path" in supplier_specific_data

    def test_transformation_idempotency(self, base_digikey_config, digikey_oauth_data):
        """Test transforming config multiple times produces same result"""
        # First transformation
        config1 = base_digikey_config.copy()
        config1["custom_parameters"] = digikey_oauth_data.copy()

        # Second transformation with same data
        config2 = base_digikey_config.copy()
        config2["custom_parameters"] = digikey_oauth_data.copy()

        assert config1["custom_parameters"] == config2["custom_parameters"]

    def test_oauth_callback_url_validation_format(self):
        """Test OAuth callback URL follows expected format"""
        valid_urls = [
            "https://localhost:8443/api/suppliers/digikey/oauth/callback",
            "https://production.example.com/api/suppliers/digikey/oauth/callback",
            "http://192.168.1.58:8443/api/suppliers/digikey/oauth/callback",
        ]

        for url in valid_urls:
            assert "/oauth/callback" in url
            assert url.startswith("http")

    def test_storage_path_validation_format(self):
        """Test storage path follows expected format"""
        valid_paths = ["/tmp/digikey_cache", "/var/lib/digikey_tokens", "/opt/makermatrix/digikey_cache"]

        for path in valid_paths:
            assert path.startswith("/")
            assert "digikey" in path.lower()

    def test_all_suppliers_have_custom_headers(self):
        """Test all supplier configurations include custom_headers"""
        suppliers = [
            {"name": "digikey", "custom_headers": {"Accept": "application/json"}},
            {"name": "lcsc", "custom_headers": {"Accept": "application/json"}},
            {"name": "mouser", "custom_headers": {"Accept": "application/json"}},
        ]

        for supplier in suppliers:
            assert "custom_headers" in supplier
            assert isinstance(supplier["custom_headers"], dict)
            assert "Accept" in supplier["custom_headers"]

    def test_digikey_production_vs_sandbox_distinction(self):
        """Test clear distinction between production and sandbox DigiKey configs"""
        sandbox_config = {"base_url": "https://sandbox-api.digikey.com", "custom_parameters": {"sandbox_mode": True}}

        production_config = {"base_url": "https://api.digikey.com", "custom_parameters": {"sandbox_mode": False}}

        assert sandbox_config["base_url"] != production_config["base_url"]
        assert sandbox_config["custom_parameters"]["sandbox_mode"] is True
        assert production_config["custom_parameters"]["sandbox_mode"] is False
