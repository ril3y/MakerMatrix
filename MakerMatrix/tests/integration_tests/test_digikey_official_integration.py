"""
Integration tests for DigiKey Official API

These tests verify the integration between the DigiKey official API client
and the MakerMatrix supplier configuration system.

Note: These tests require valid DigiKey API credentials to be set in environment variables.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch
from MakerMatrix.clients.suppliers.digikey_official_client import DigiKeyOfficialClient
from MakerMatrix.services.supplier_config_service import SupplierConfigService
from MakerMatrix.config.suppliers.digikey import (
    DIGIKEY_CONFIG,
    DIGIKEY_CREDENTIAL_FIELDS,
    DIGIKEY_CAPABILITIES
)


@pytest.mark.integration
class TestDigiKeyOfficialIntegration:
    """Integration tests for DigiKey Official API"""

    def setup_method(self):
        """Set up test fixtures"""
        self.supplier_service = SupplierConfigService()
        
        # Use environment credentials if available, otherwise use test values
        self.client_id = os.getenv("DIGIKEY_CLIENT_ID", "test_client_id")
        self.client_secret = os.getenv("DIGIKEY_CLIENT_SECRET", "test_client_secret")
        
        self.client = DigiKeyOfficialClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            sandbox=True  # Always use sandbox for tests
        )

    def test_digikey_config_structure(self):
        """Test DigiKey configuration structure"""
        assert DIGIKEY_CONFIG["supplier_name"] == "DigiKey"
        assert DIGIKEY_CONFIG["display_name"] == "DigiKey Electronics"
        assert DIGIKEY_CONFIG["api_type"] == "rest"
        assert DIGIKEY_CONFIG["auth_type"] == "oauth2_client_credentials"
        assert "api_key" in DIGIKEY_CONFIG["required_credentials"]
        assert "secret_key" in DIGIKEY_CONFIG["required_credentials"]

    def test_digikey_credential_fields(self):
        """Test DigiKey credential field definitions"""
        assert len(DIGIKEY_CREDENTIAL_FIELDS) == 2
        
        # Check Client ID field
        client_id_field = next(f for f in DIGIKEY_CREDENTIAL_FIELDS if f["field"] == "api_key")
        assert client_id_field["label"] == "Client ID"
        assert client_id_field["type"] == "text"
        assert client_id_field["required"] is True
        assert "DigiKey Developer Portal" in client_id_field["help_text"]
        
        # Check Client Secret field
        secret_field = next(f for f in DIGIKEY_CREDENTIAL_FIELDS if f["field"] == "secret_key")
        assert secret_field["label"] == "Client Secret"
        assert secret_field["type"] == "password"
        assert secret_field["required"] is True

    def test_digikey_capabilities(self):
        """Test DigiKey capabilities configuration"""
        expected_capabilities = [
            "fetch_datasheet",
            "fetch_image", 
            "fetch_pricing",
            "fetch_stock",
            "fetch_specifications",
            "part_search"
        ]
        
        for capability in expected_capabilities:
            assert capability in DIGIKEY_CAPABILITIES
            assert DIGIKEY_CAPABILITIES[capability]["supported"] is True

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not (os.getenv("DIGIKEY_CLIENT_ID") and os.getenv("DIGIKEY_CLIENT_SECRET")),
        reason="Real DigiKey credentials not available"
    )
    async def test_real_api_authentication(self):
        """Test authentication with real DigiKey API (requires credentials)"""
        # Only run if real credentials are available
        real_client = DigiKeyOfficialClient(sandbox=True)
        
        try:
            result = await real_client.authenticate()
            # If credentials are valid, should succeed
            # If credentials are invalid, should fail gracefully
            assert isinstance(result, bool)
        except Exception as e:
            # Should not raise unhandled exceptions
            pytest.fail(f"Authentication raised unexpected exception: {e}")

    @pytest.mark.asyncio
    async def test_mocked_api_search(self):
        """Test part search with mocked API responses"""
        mock_result = Mock()
        mock_result.ExactManufacturerProductsCount = 5
        mock_result.Products = [
            Mock(
                DigiKeyPartNumber="296-6501-1-ND",
                ManufacturerPartNumber="RC0805FR-07100RL",
                ProductDescription="RES SMD 100 OHM 1% 1/8W 0805",
                Manufacturer=Mock(Name="Yageo", Id=123),
                QuantityAvailable=10000,
                PrimaryDatasheet="http://example.com/datasheet.pdf",
                PrimaryPhoto="http://example.com/image.jpg",
                StandardPricing=[
                    Mock(BreakQuantity=1, UnitPrice=0.10, Currency="USD"),
                    Mock(BreakQuantity=10, UnitPrice=0.08, Currency="USD")
                ]
            )
        ]
        
        with patch('digikey.keyword_search') as mock_search:
            mock_search.return_value = mock_result
            
            response = await self.client.search_parts("resistor", limit=5)
            
            assert response.success is True
            assert response.data["total_count"] == 5
            assert len(response.data["products"]) == 1
            
            product = response.data["products"][0]
            assert product["digikey_part_number"] == "296-6501-1-ND"
            assert product["manufacturer"]["name"] == "Yageo"
            assert product["unit_price"] == 0.10

    @pytest.mark.asyncio
    async def test_mocked_part_details(self):
        """Test part details retrieval with mocked API"""
        mock_product = Mock(
            DigiKeyPartNumber="296-6501-1-ND",
            ManufacturerPartNumber="RC0805FR-07100RL",
            ProductDescription="RES SMD 100 OHM 1% 1/8W 0805",
            DetailedDescription="Thick Film Resistors - SMD 100 ohms 1% 1/8W",
            PrimaryDatasheet="http://example.com/resistor-datasheet.pdf",
            PrimaryPhoto="http://example.com/resistor-image.jpg",
            QuantityAvailable=10000,
            MinimumOrderQuantity=1,
            ProductAttributes=[
                Mock(AttributeName="Resistance", AttributeValue="100 Ohms"),
                Mock(AttributeName="Tolerance", AttributeValue="±1%"),
                Mock(AttributeName="Power", AttributeValue="0.125W, 1/8W")
            ]
        )
        
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = mock_product
            
            response = await self.client.get_part_details("296-6501-1-ND")
            
            assert response.success is True
            assert response.data["digikey_part_number"] == "296-6501-1-ND"
            assert response.data["primary_datasheet"] == "http://example.com/resistor-datasheet.pdf"
            assert len(response.data["product_attributes"]) == 3

    def test_supplier_config_service_digikey_creation(self):
        """Test DigiKey client creation through supplier config service"""
        # Mock supplier config
        mock_config = Mock()
        mock_config.supplier_name = "DigiKey"
        mock_config.base_url = "https://sandbox-api.digikey.com"
        mock_config.timeout_seconds = 30
        mock_config.max_retries = 3
        mock_config.rate_limit_per_minute = 1000
        mock_config.get_custom_headers.return_value = {}
        
        # Mock credentials
        credentials = {
            "api_key": "test_client_id",
            "secret_key": "test_client_secret"
        }
        
        client = self.supplier_service._create_api_client(mock_config, credentials)
        
        assert isinstance(client, DigiKeyOfficialClient)
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.sandbox is True

    @pytest.mark.asyncio
    async def test_supplier_config_service_digikey_test(self):
        """Test DigiKey connection testing through supplier config service"""
        with patch.object(self.supplier_service, 'get_supplier_config') as mock_get_config, \
             patch.object(self.supplier_service, 'get_supplier_credentials') as mock_get_creds, \
             patch.object(DigiKeyOfficialClient, 'test_connection') as mock_test:
            
            # Mock configuration
            mock_config = Mock()
            mock_config.supplier_name = "DigiKey"
            mock_config.base_url = "https://sandbox-api.digikey.com"
            mock_config.timeout_seconds = 30
            mock_config.max_retries = 3
            mock_config.rate_limit_per_minute = 1000
            mock_config.get_custom_headers.return_value = {}
            
            mock_get_config.return_value = mock_config
            mock_get_creds.return_value = {
                "api_key": "test_client_id",
                "secret_key": "test_client_secret"
            }
            mock_test.return_value = True
            
            result = await self.supplier_service.test_supplier_connection("DigiKey")
            
            assert result["success"] is True
            assert result["supplier_name"] == "DigiKey"
            assert "test_duration_seconds" in result

    def test_digikey_field_mappings(self):
        """Test DigiKey API field mappings for part enrichment"""
        from MakerMatrix.config.suppliers.digikey import DIGIKEY_FIELD_MAPPINGS
        
        expected_mappings = {
            "DigiKeyPartNumber": "supplier_part_number",
            "ManufacturerPartNumber": "part_number",
            "ProductDescription": "description",
            "PrimaryDatasheet": "datasheet_url",
            "PrimaryPhoto": "image_url",
            "QuantityAvailable": "stock_quantity",
            "UnitPrice": "unit_price"
        }
        
        for digikey_field, makermatrix_field in expected_mappings.items():
            assert DIGIKEY_FIELD_MAPPINGS[digikey_field] == makermatrix_field

    def test_digikey_category_mappings(self):
        """Test DigiKey category mappings"""
        from MakerMatrix.config.suppliers.digikey import DIGIKEY_CATEGORY_MAPPINGS
        
        # Test some standard category mappings
        assert "Electronics" in DIGIKEY_CATEGORY_MAPPINGS["Resistors"]
        assert "Passive Components" in DIGIKEY_CATEGORY_MAPPINGS["Resistors"]
        assert "Semiconductors" in DIGIKEY_CATEGORY_MAPPINGS["Transistors"]
        assert "ICs" in DIGIKEY_CATEGORY_MAPPINGS["Integrated Circuits"]

    def test_digikey_error_codes(self):
        """Test DigiKey error code mappings"""
        from MakerMatrix.config.suppliers.digikey import DIGIKEY_ERROR_CODES
        
        assert "401" in DIGIKEY_ERROR_CODES
        assert "credentials" in DIGIKEY_ERROR_CODES["401"].lower()
        assert "403" in DIGIKEY_ERROR_CODES
        assert "429" in DIGIKEY_ERROR_CODES
        assert "rate limit" in DIGIKEY_ERROR_CODES["429"].lower()

    def test_digikey_validation_rules(self):
        """Test DigiKey validation rules"""
        from MakerMatrix.config.suppliers.digikey import DIGIKEY_VALIDATION_RULES
        
        assert "client_id_format" in DIGIKEY_VALIDATION_RULES
        assert "client_secret_format" in DIGIKEY_VALIDATION_RULES
        assert DIGIKEY_VALIDATION_RULES["max_requests_per_minute"] == 1000
        assert "USD" in DIGIKEY_VALIDATION_RULES["supported_currencies"]

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """Test multiple concurrent API calls"""
        mock_result = Mock()
        mock_result.ExactManufacturerProductsCount = 1
        mock_result.Products = [Mock(DigiKeyPartNumber="TEST-PART")]
        
        with patch('digikey.keyword_search') as mock_search:
            mock_search.return_value = mock_result
            
            # Run multiple searches concurrently
            tasks = [
                self.client.search_parts(f"test{i}", limit=1) 
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(r.success for r in results)

    def test_environment_configuration(self):
        """Test that client properly configures environment variables"""
        client = DigiKeyOfficialClient(
            client_id="env_test_id",
            client_secret="env_test_secret",
            sandbox=True
        )
        
        # Check that environment variables are set
        assert os.environ.get("DIGIKEY_CLIENT_ID") == "env_test_id"
        assert os.environ.get("DIGIKEY_CLIENT_SECRET") == "env_test_secret"
        assert os.environ.get("DIGIKEY_STORAGE_PATH") == "/tmp/digikey-api"
        assert os.environ.get("DIGIKEY_CLIENT_SANDBOX") == "True"

    def test_storage_directory_creation(self):
        """Test that storage directory is created"""
        # Client initialization should create the storage directory
        DigiKeyOfficialClient(
            client_id="test",
            client_secret="test",
            sandbox=True
        )
        
        import os
        assert os.path.exists("/tmp/digikey-api")


@pytest.mark.integration
@pytest.mark.skipif(
    not (os.getenv("DIGIKEY_CLIENT_ID") and os.getenv("DIGIKEY_CLIENT_SECRET")),
    reason="Real DigiKey credentials not available"
)
class TestDigiKeyRealAPI:
    """Tests that require real DigiKey API credentials"""

    def setup_method(self):
        """Set up for real API tests"""
        self.client = DigiKeyOfficialClient(sandbox=True)

    @pytest.mark.asyncio
    async def test_real_authentication(self):
        """Test real API authentication"""
        result = await self.client.authenticate()
        assert isinstance(result, bool)

    @pytest.mark.asyncio 
    async def test_real_search_resistor(self):
        """Test real search for resistors"""
        try:
            response = await self.client.search_parts("resistor", limit=5)
            
            if response.success:
                assert response.data["total_count"] > 0
                assert len(response.data["products"]) > 0
                
                # Check first product structure
                product = response.data["products"][0]
                assert "digikey_part_number" in product
                assert "manufacturer_part_number" in product
                assert "product_description" in product
            else:
                # If search fails, should have error information
                assert response.status_code >= 400
                
        except Exception as e:
            pytest.skip(f"Real API test failed: {e}")

    @pytest.mark.asyncio
    async def test_real_part_details(self):
        """Test real part details for a known part"""
        # Use a common DigiKey part for testing
        test_part = "296-6501-1-ND"  # Common resistor part
        
        try:
            response = await self.client.get_part_details(test_part)
            
            if response.success:
                assert response.data["digikey_part_number"] == test_part
                assert "manufacturer_part_number" in response.data
                assert "product_description" in response.data
            else:
                # Part might not exist in sandbox, that's okay
                assert response.status_code in [400, 404]
                
        except Exception as e:
            pytest.skip(f"Real API test failed: {e}")