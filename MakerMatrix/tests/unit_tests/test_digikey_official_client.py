"""
Unit tests for DigiKey Official API Client

Tests the official DigiKey API integration using the digikey-api library.
These tests use mocking to avoid making real API calls during testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from MakerMatrix.clients.suppliers.digikey_official_client import DigiKeyOfficialClient
from MakerMatrix.clients.base_client import APIResponse


class TestDigiKeyOfficialClient:
    """Test cases for DigiKey Official API Client"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = DigiKeyOfficialClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            sandbox=True
        )

    def test_client_initialization(self):
        """Test client initialization with credentials"""
        client = DigiKeyOfficialClient(
            client_id="test_id",
            client_secret="test_secret",
            sandbox=True
        )
        
        assert client.client_id == "test_id"
        assert client.client_secret == "test_secret"
        assert client.sandbox is True

    def test_client_initialization_from_env(self):
        """Test client initialization using environment variables"""
        with patch.dict('os.environ', {
            'DIGIKEY_CLIENT_ID': 'env_client_id',
            'DIGIKEY_CLIENT_SECRET': 'env_client_secret'
        }):
            client = DigiKeyOfficialClient(sandbox=True)
            assert client.client_id == "env_client_id"
            assert client.client_secret == "env_client_secret"

    def test_client_initialization_missing_credentials(self):
        """Test that initialization fails without credentials"""
        # Clear environment variables to test missing credentials
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="DigiKey Client ID and Client Secret are required"):
                DigiKeyOfficialClient()

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication"""
        mock_search_result = Mock()
        mock_search_result.ExactManufacturerProductsCount = 1000
        
        with patch('digikey.keyword_search') as mock_keyword_search:
            mock_keyword_search.return_value = mock_search_result
            
            result = await self.client.authenticate()
            assert result is True
            mock_keyword_search.assert_called_once_with("resistor", 1)

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test authentication failure"""
        with patch('digikey.keyword_search') as mock_keyword_search:
            mock_keyword_search.side_effect = Exception("API Error")
            
            result = await self.client.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_no_results(self):
        """Test authentication with no results"""
        with patch('digikey.keyword_search') as mock_keyword_search:
            mock_keyword_search.return_value = None
            
            result = await self.client.authenticate()
            assert result is False

    @pytest.mark.asyncio
    async def test_search_parts_success(self):
        """Test successful part search"""
        # Mock search result
        mock_result = Mock()
        mock_result.ExactManufacturerProductsCount = 100
        mock_result.Products = [
            Mock(
                DigiKeyPartNumber="STM32F405RGT6CT-ND",
                ManufacturerPartNumber="STM32F405RGT6",
                ProductDescription="IC MCU 32BIT",
                Manufacturer=Mock(Name="STMicroelectronics", Id=123),
                QuantityAvailable=50
            )
        ]
        
        with patch('digikey.keyword_search') as mock_search:
            mock_search.return_value = mock_result
            
            response = await self.client.search_parts("STM32", limit=10)
            
            assert response.success is True
            assert response.status_code == 200
            assert response.data["total_count"] == 100
            assert len(response.data["products"]) == 1
            
            product = response.data["products"][0]
            assert product["digikey_part_number"] == "STM32F405RGT6CT-ND"
            assert product["manufacturer_part_number"] == "STM32F405RGT6"

    @pytest.mark.asyncio
    async def test_search_parts_no_results(self):
        """Test part search with no results"""
        with patch('digikey.keyword_search') as mock_search:
            mock_search.return_value = None
            
            response = await self.client.search_parts("nonexistent")
            
            assert response.success is False
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_search_parts_api_error(self):
        """Test part search with API error"""
        from digikey.exceptions import DigikeyError
        
        with patch('digikey.keyword_search') as mock_search:
            mock_search.side_effect = DigikeyError("API Error")
            
            response = await self.client.search_parts("test")
            
            assert response.success is False
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_part_details_success(self):
        """Test successful part details retrieval"""
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "STM32F405RGT6CT-ND"
        mock_product.ManufacturerPartNumber = "STM32F405RGT6"
        mock_product.ProductDescription = "IC MCU 32BIT"
        mock_product.PrimaryDatasheet = "http://example.com/datasheet.pdf"
        mock_product.PrimaryPhoto = "http://example.com/image.jpg"
        mock_product.QuantityAvailable = 50
        
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = mock_product
            
            response = await self.client.get_part_details("STM32F405RGT6CT-ND")
            
            assert response.success is True
            assert response.status_code == 200
            assert response.data["digikey_part_number"] == "STM32F405RGT6CT-ND"
            assert response.data["primary_datasheet"] == "http://example.com/datasheet.pdf"

    @pytest.mark.asyncio
    async def test_get_part_details_not_found(self):
        """Test part details for non-existent part"""
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = None
            
            response = await self.client.get_part_details("INVALID-PART")
            
            assert response.success is False
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_part_datasheet(self):
        """Test datasheet URL retrieval"""
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "STM32F405RGT6CT-ND"
        mock_product.PrimaryDatasheet = "http://example.com/datasheet.pdf"
        
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = mock_product
            
            response = await self.client.get_part_datasheet("STM32F405RGT6CT-ND")
            
            assert response.success is True
            assert response.data["datasheet_url"] == "http://example.com/datasheet.pdf"
            assert response.data["has_datasheet"] is True

    @pytest.mark.asyncio
    async def test_get_part_pricing(self):
        """Test pricing information retrieval"""
        mock_pricing1 = Mock()
        mock_pricing1.BreakQuantity = 1
        mock_pricing1.UnitPrice = 10.50
        mock_pricing1.Currency = "USD"
        
        mock_pricing2 = Mock()
        mock_pricing2.BreakQuantity = 10
        mock_pricing2.UnitPrice = 9.50
        mock_pricing2.Currency = "USD"
        
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "STM32F405RGT6CT-ND"
        mock_product.QuantityAvailable = 100
        mock_product.MinimumOrderQuantity = 1
        mock_product.StandardPricing = [mock_pricing1, mock_pricing2]
        
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = mock_product
            
            response = await self.client.get_part_pricing("STM32F405RGT6CT-ND")
            
            assert response.success is True
            assert response.data["unit_price"] == 10.50
            assert response.data["quantity_available"] == 100
            assert len(response.data["pricing_breaks"]) == 2

    @pytest.mark.asyncio
    async def test_get_part_images(self):
        """Test product image retrieval"""
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "STM32F405RGT6CT-ND"
        mock_product.PrimaryPhoto = "http://example.com/image.jpg"
        
        with patch('digikey.product_details') as mock_details:
            mock_details.return_value = mock_product
            
            response = await self.client.get_part_images("STM32F405RGT6CT-ND")
            
            assert response.success is True
            assert response.data["image_count"] == 1
            assert response.data["images"][0]["url"] == "http://example.com/image.jpg"

    def test_convert_product_to_dict_complete(self):
        """Test product conversion with all fields"""
        mock_manufacturer = Mock()
        mock_manufacturer.Name = "STMicroelectronics"
        mock_manufacturer.Id = 123
        
        mock_pricing = Mock()
        mock_pricing.BreakQuantity = 1
        mock_pricing.UnitPrice = 10.50
        mock_pricing.Currency = "USD"
        
        mock_attribute = Mock()
        mock_attribute.AttributeName = "Voltage"
        mock_attribute.AttributeValue = "3.3V"
        mock_attribute.AttributeId = 789
        
        mock_category = Mock()
        mock_category.CategoryName = "Microcontrollers"
        mock_category.CategoryId = 456
        mock_category.ParentId = None
        
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "STM32F405RGT6CT-ND"
        mock_product.ManufacturerPartNumber = "STM32F405RGT6"
        mock_product.ProductDescription = "IC MCU 32BIT"
        mock_product.DetailedDescription = "Detailed description"
        mock_product.PrimaryDatasheet = "http://example.com/datasheet.pdf"
        mock_product.PrimaryPhoto = "http://example.com/image.jpg"
        mock_product.QuantityAvailable = 100
        mock_product.MinimumOrderQuantity = 1
        mock_product.Manufacturer = mock_manufacturer
        mock_product.StandardPricing = [mock_pricing]
        mock_product.ProductAttributes = [mock_attribute]
        mock_product.Categories = [mock_category]
        
        result = self.client._convert_product_to_dict(mock_product)
        
        assert result["digikey_part_number"] == "STM32F405RGT6CT-ND"
        assert result["manufacturer_part_number"] == "STM32F405RGT6"
        assert result["manufacturer"]["name"] == "STMicroelectronics"
        assert result["unit_price"] == 10.50
        assert len(result["product_attributes"]) == 1
        assert len(result["categories"]) == 1

    def test_convert_product_to_dict_minimal(self):
        """Test product conversion with minimal fields"""
        mock_product = Mock()
        mock_product.DigiKeyPartNumber = "SIMPLE-PART"
        mock_product.ManufacturerPartNumber = "SIMPLE"
        
        result = self.client._convert_product_to_dict(mock_product)
        
        assert result["digikey_part_number"] == "SIMPLE-PART"
        assert result["manufacturer_part_number"] == "SIMPLE"
        # Mock objects will have manufacturer data from the Mock
        assert "name" in result["manufacturer"]
        assert result["unit_price"] is None

    def test_convert_product_to_dict_error_handling(self):
        """Test product conversion error handling"""
        # Test with invalid product object that will cause an exception
        invalid_product = Mock()
        
        # Mock getattr to raise an exception
        with patch('builtins.getattr', side_effect=Exception("Mock error")):
            result = self.client._convert_product_to_dict(invalid_product)
            
            assert "error" in result
            assert "Failed to convert product data" in result["error"]

    def test_get_part_url(self):
        """Test DigiKey product URL generation"""
        url = self.client.get_part_url("STM32F405RGT6CT-ND")
        expected_url = "https://www.digikey.com/en/products/detail/STM32F405RGT6CT-ND"
        assert url == expected_url

    @pytest.mark.asyncio 
    async def test_test_connection_delegates_to_authenticate(self):
        """Test that test_connection calls authenticate"""
        with patch.object(self.client, 'authenticate') as mock_auth:
            mock_auth.return_value = True
            
            result = await self.client.test_connection()
            assert result is True
            mock_auth.assert_called_once()

    def test_get_authentication_headers_returns_empty(self):
        """Test that get_authentication_headers returns empty dict"""
        headers = self.client.get_authentication_headers()
        assert headers == {}

    def test_request_method_not_implemented(self):
        """Test that request method raises NotImplementedError"""
        with pytest.raises(NotImplementedError):
            asyncio.run(self.client.request("GET", "/test"))


class TestDigiKeyClientIntegration:
    """Integration tests for DigiKey client with supplier configuration service"""

    @pytest.mark.asyncio
    async def test_client_integration_with_config_service(self):
        """Test DigiKey client integration with supplier configuration"""
        from MakerMatrix.services.supplier_config_service import SupplierConfigService
        
        service = SupplierConfigService()
        
        # Mock credentials for testing
        test_credentials = {
            "api_key": "test_client_id",  # Maps to client_id
            "secret_key": "test_client_secret"  # Maps to client_secret
        }
        
        # Mock the supplier config
        mock_config = Mock()
        mock_config.supplier_name = "DigiKey"
        mock_config.base_url = "https://sandbox-api.digikey.com"
        mock_config.timeout_seconds = 30
        mock_config.max_retries = 3
        mock_config.rate_limit_per_minute = 1000
        mock_config.get_custom_headers.return_value = {}
        
        # Test client creation
        client = service._create_api_client(mock_config, test_credentials)
        
        assert isinstance(client, DigiKeyOfficialClient)
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.sandbox is True  # Should detect sandbox from URL