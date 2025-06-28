"""
Unit tests for DigiKey supplier implementation.

Tests OAuth configuration, URL generation, CSV import functionality,
and API integration without requiring actual DigiKey API calls.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.suppliers.base import SupplierCapability, ImportResult
from MakerMatrix.suppliers.exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError
)


class TestDigiKeySupplierBasics:
    """Test basic DigiKey supplier functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
    
    def test_supplier_info(self):
        """Test supplier information"""
        info = self.supplier.get_supplier_info()
        assert info.name == "digikey"
        assert info.display_name == "DigiKey Electronics"
        assert info.supports_oauth is True
        assert "csv" in info.supported_file_types
        assert "xls" in info.supported_file_types
    
    def test_capabilities(self):
        """Test supplier capabilities"""
        capabilities = self.supplier.get_capabilities()
        assert SupplierCapability.IMPORT_ORDERS in capabilities
        assert SupplierCapability.SEARCH_PARTS in capabilities
        assert SupplierCapability.FETCH_DATASHEET in capabilities
    
    def test_credential_schema(self):
        """Test credential schema definition"""
        schema = self.supplier.get_credential_schema()
        assert len(schema) == 2
        
        client_id_field = next(f for f in schema if f.name == "client_id")
        assert client_id_field.required is True
        assert client_id_field.field_type.value == "text"
        
        client_secret_field = next(f for f in schema if f.name == "client_secret")
        assert client_secret_field.required is True
        assert client_secret_field.field_type.value == "password"
    
    def test_configuration_options(self):
        """Test configuration options with auto-detection"""
        with patch.dict(os.environ, {"HTTPS_ENABLED": "true", "SERVER_HOST": "localhost", "SERVER_PORT": "8443"}):
            config_options = self.supplier.get_configuration_options()
            assert len(config_options) == 1
            
            production_config = config_options[0]
            assert production_config.name == "production"
            assert production_config.is_default is True
            
            # Check auto-detected callback URL
            oauth_field = next(f for f in production_config.schema if f.name == "oauth_callback_url")
            assert "https://localhost:8443/api/suppliers/digikey/oauth/callback" in oauth_field.default_value
    
    def test_server_url_detection_https(self):
        """Test server URL detection for HTTPS"""
        with patch.dict(os.environ, {"HTTPS_ENABLED": "true", "SERVER_HOST": "example.com", "SERVER_PORT": "443"}):
            url = self.supplier._get_server_url()
            assert url == "https://example.com:443"
    
    def test_server_url_detection_http(self):
        """Test server URL detection for HTTP"""
        with patch.dict(os.environ, {"HTTPS_ENABLED": "false", "SERVER_HOST": "localhost", "SERVER_PORT": "8080"}):
            url = self.supplier._get_server_url()
            assert url == "http://localhost:8080"
    
    def test_server_url_defaults(self):
        """Test server URL detection with defaults"""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            url = self.supplier._get_server_url()
            assert url == "http://localhost:8080"  # Default HTTP


class TestDigiKeyOAuth:
    """Test OAuth functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={"oauth_callback_url": "https://localhost:8443/api/suppliers/digikey/oauth/callback"}
        )
    
    def test_oauth_url_generation(self):
        """Test OAuth authorization URL generation"""
        auth_url = self.supplier.get_oauth_authorization_url()
        
        assert "https://api.digikey.com/v1/oauth2/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "redirect_uri=https://localhost:8443/api/suppliers/digikey/oauth/callback" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=read" in auth_url
    
    def test_generate_oauth_url_method(self):
        """Test internal OAuth URL generation method"""
        oauth_url = self.supplier._generate_oauth_url()
        
        assert "https://api.digikey.com/v1/oauth2/authorize" in oauth_url
        assert "test_client_id" in oauth_url
        # Check URL-encoded callback URL
        assert "redirect_uri=" in oauth_url
        assert "digikey%2Foauth%2Fcallback" in oauth_url
    
    @pytest.mark.asyncio
    async def test_oauth_token_exchange(self):
        """Test OAuth token exchange"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful token response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600
            })
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test token exchange
            result = await self.supplier.exchange_code_for_tokens("test_auth_code")
            
            assert result is True
            assert self.supplier._access_token == "test_access_token"
            assert self.supplier._refresh_token == "test_refresh_token"
    
    @pytest.mark.asyncio
    async def test_oauth_token_exchange_failure(self):
        """Test OAuth token exchange failure"""
        with patch.object(self.supplier, '_get_session') as mock_session:
            # Mock failed token response
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text.return_value = "Invalid authorization code"
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Test token exchange failure
            with pytest.raises(Exception):
                await self.supplier.exchange_code_for_tokens("invalid_code")


class TestDigiKeyAuthentication:
    """Test authentication functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
    
    @pytest.mark.asyncio
    async def test_authentication_missing_credentials(self):
        """Test authentication with missing credentials"""
        with pytest.raises(SupplierConfigurationError) as exc_info:
            await self.supplier.authenticate()
        
        assert "not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authentication_missing_client_id(self):
        """Test authentication with missing client ID"""
        self.supplier.configure(
            credentials={"client_secret": "test_secret"},
            config={}
        )
        
        with pytest.raises(SupplierConfigurationError) as exc_info:
            await self.supplier.authenticate()
        
        assert "client_id" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authentication_missing_client_secret(self):
        """Test authentication with missing client secret"""
        self.supplier.configure(
            credentials={"client_id": "test_client_id"},
            config={}
        )
        
        with pytest.raises(SupplierConfigurationError) as exc_info:
            await self.supplier.authenticate()
        
        assert "client_secret" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    async def test_authentication_success(self):
        """Test successful authentication setup"""
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={"storage_path": "./test_tokens"}
        )
        
        with patch('os.makedirs') as mock_makedirs:
            result = await self.supplier.authenticate()
            
            assert result is True
            mock_makedirs.assert_called_once()
            assert os.environ.get('DIGIKEY_CLIENT_ID') == "test_client_id"
            assert os.environ.get('DIGIKEY_CLIENT_SECRET') == "test_secret"
            assert os.environ.get('DIGIKEY_CLIENT_SANDBOX') == 'False'
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', False)
    async def test_authentication_missing_library(self):
        """Test authentication when DigiKey library is not available"""
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={}
        )
        
        with pytest.raises(SupplierConfigurationError) as exc_info:
            await self.supplier.authenticate()
        
        assert "digikey-api" in str(exc_info.value)


class TestDigiKeyConnectionTest:
    """Test connection testing functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
    
    @pytest.mark.asyncio
    async def test_connection_test_not_configured(self):
        """Test connection test when supplier is not configured"""
        result = await self.supplier.test_connection()
        
        assert result["success"] is False
        assert "not configured" in result["message"]
        assert result["details"]["configuration_needed"] is True
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', False)
    async def test_connection_test_missing_library(self):
        """Test connection test when DigiKey library is missing"""
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={}
        )
        
        result = await self.supplier.test_connection()
        
        assert result["success"] is False
        assert "not available" in result["message"]
        assert result["details"]["dependency_missing"] is True
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    async def test_connection_test_api_reachable(self):
        """Test connection test when API is reachable"""
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={}
        )
        
        with patch.object(self.supplier, 'authenticate', return_value=True):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response
                
                result = await self.supplier.test_connection()
                
                assert result["success"] is False  # Still false because OAuth is required
                assert "OAuth required" in result["message"]
                assert result["details"]["oauth_required"] is True
                assert result["details"]["api_reachable"] is True
                assert "oauth_url" in result["details"]


class TestDigiKeyCSVImport:
    """Test CSV/Excel import functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
    
    def test_can_import_file_digikey_csv(self):
        """Test file type detection for DigiKey CSV"""
        assert self.supplier.can_import_file("digikey_order.csv") is True
        assert self.supplier.can_import_file("digi-key_export.csv") is True
        assert self.supplier.can_import_file("weborder_123.csv") is True
    
    def test_can_import_file_digikey_excel(self):
        """Test file type detection for DigiKey Excel"""
        assert self.supplier.can_import_file("digikey_order.xls") is True
        assert self.supplier.can_import_file("digikey_order.xlsx") is True
    
    def test_can_import_file_non_digikey(self):
        """Test file type detection for non-DigiKey files"""
        assert self.supplier.can_import_file("random_file.csv") is False
        assert self.supplier.can_import_file("mouser_order.csv") is False
        assert self.supplier.can_import_file("lcsc_parts.xlsx") is False
    
    def test_can_import_file_with_content(self):
        """Test file type detection with content analysis"""
        digikey_csv_content = b'Digi-Key Part Number,Manufacturer Part Number,Description,Quantity\nTEST123,MANU456,Test Part,5'
        assert self.supplier.can_import_file("unknown.csv", digikey_csv_content) is True
        
        non_digikey_content = b'Part,Price,Stock\nABC123,1.50,100'
        assert self.supplier.can_import_file("unknown.csv", non_digikey_content) is False
    
    @pytest.mark.asyncio
    async def test_import_invalid_file_type(self):
        """Test import with invalid file type"""
        result = await self.supplier.import_order_file(b"content", "txt", "test.txt")
        
        assert result.success is False
        assert "CSV, XLS, and XLSX" in result.error_message
    
    @pytest.mark.asyncio
    async def test_import_digikey_csv_standard_format(self):
        """Test import of standard DigiKey CSV format"""
        csv_content = '''Digi-Key Part Number,Manufacturer,Manufacturer Part Number,Description,Quantity,Unit Price,Extended Price
TEST123-DK,Test Mfg,MANU456,Test Resistor 1K,10,$0.05,$0.50
TEST456-DK,Another Mfg,MANU789,Test Capacitor 10uF,5,$0.25,$1.25'''
        
        result = await self.supplier.import_order_file(csv_content.encode('utf-8'), "csv", "test.csv")
        
        assert result.success is True
        assert result.imported_count == 2
        assert len(result.parts) == 2
        
        # Check first part
        part1 = result.parts[0]
        assert part1['part_number'] == "TEST123-DK"
        assert part1['manufacturer'] == "Test Mfg"
        assert part1['manufacturer_part_number'] == "MANU456"
        assert part1['description'] == "Test Resistor 1K"
        assert part1['quantity'] == 10
        assert part1['unit_price'] == 0.05
        assert part1['supplier'] == "DigiKey"
    
    @pytest.mark.asyncio
    async def test_import_digikey_csv_alternative_format(self):
        """Test import of alternative DigiKey CSV format"""
        csv_content = '''Part Number,Manufacturer,Manufacturer Part Number,Description,Quantity,Unit Price
TEST123,Test Mfg,MANU456,Test Resistor 1K,10,$0.05'''
        
        result = await self.supplier.import_order_file(csv_content.encode('utf-8'), "csv", "test.csv")
        
        assert result.success is True
        assert result.imported_count == 1
        assert len(result.parts) == 1
        
        part = result.parts[0]
        assert part['part_number'] == "TEST123"
        assert part['part_name'] == "Test Resistor 1K"
    
    @pytest.mark.asyncio
    async def test_import_digikey_csv_unrecognized_format(self):
        """Test import of unrecognized CSV format"""
        csv_content = '''Unknown Header,Another Header,Third Header
Value1,Value2,Value3'''
        
        result = await self.supplier.import_order_file(csv_content.encode('utf-8'), "csv", "test.csv")
        
        assert result.success is False
        assert "Unrecognized DigiKey CSV format" in result.error_message
    
    @pytest.mark.asyncio
    async def test_import_digikey_csv_with_bom(self):
        """Test import of CSV with BOM (Byte Order Mark)"""
        csv_content = '\ufeffDigi-Key Part Number,Description,Quantity\nTEST123,Test Part,5'
        
        result = await self.supplier.import_order_file(csv_content.encode('utf-8'), "csv", "test.csv")
        
        assert result.success is True
        assert result.imported_count == 1
    
    @pytest.mark.asyncio
    async def test_import_empty_csv(self):
        """Test import of empty CSV"""
        csv_content = '''Digi-Key Part Number,Description,Quantity'''
        
        result = await self.supplier.import_order_file(csv_content.encode('utf-8'), "csv", "test.csv")
        
        assert result.success is False
        assert "No valid parts found" in result.error_message
    
    @pytest.mark.asyncio
    @patch('pandas.read_excel')
    async def test_import_excel_file(self, mock_read_excel):
        """Test import of Excel file"""
        # Mock pandas DataFrame
        import pandas as pd
        mock_df = pd.DataFrame({
            'Digi-Key Part Number': ['TEST123'],
            'Description': ['Test Part'],
            'Quantity': [5]
        })
        mock_read_excel.return_value = mock_df
        
        result = await self.supplier.import_order_file(b"fake_excel_content", "xlsx", "test.xlsx")
        
        assert result.success is True
        assert result.imported_count == 1


class TestDigiKeyAPIIntegration:
    """Test API integration (mocked)"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={}
        )
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    @patch('MakerMatrix.suppliers.digikey.digikey')
    async def test_search_parts(self, mock_digikey):
        """Test part search functionality"""
        # Mock successful authentication
        with patch.object(self.supplier, 'authenticate', return_value=True):
            # Mock search result
            mock_product = Mock()
            mock_product.digi_key_part_number = "TEST123-DK"
            mock_product.manufacturer.value = "Test Mfg"
            mock_product.manufacturer_part_number = "MANU456"
            mock_product.product_description = "Test Resistor"
            mock_product.category.value = "Resistors"
            mock_product.primary_datasheet = "http://example.com/datasheet.pdf"
            mock_product.primary_photo = "http://example.com/image.jpg"
            mock_product.quantity_available = 1000
            mock_product.detailed_description = "Detailed description"
            mock_product.series.value = "Test Series"
            mock_product.packaging.value = "Cut Tape"
            
            mock_result = Mock()
            mock_result.products = [mock_product]
            mock_digikey.keyword_search.return_value = mock_result
            
            # Test search
            results = await self.supplier.search_parts("test resistor", limit=10)
            
            assert len(results) == 1
            result = results[0]
            assert result.supplier_part_number == "TEST123-DK"
            assert result.manufacturer == "Test Mfg"
            assert result.manufacturer_part_number == "MANU456"
            assert result.description == "Test Resistor"
            assert result.stock_quantity == 1000
    
    @pytest.mark.asyncio
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    @patch('MakerMatrix.suppliers.digikey.digikey')
    async def test_get_part_details(self, mock_digikey):
        """Test getting part details"""
        # Mock successful authentication
        with patch.object(self.supplier, 'authenticate', return_value=True):
            with patch.object(self.supplier, '_tracked_api_call') as mock_tracked_call:
                # Mock the tracked API call to return our test result directly
                async def mock_impl():
                    mock_product = Mock()
                    mock_product.digi_key_part_number = "TEST123-DK"
                    mock_product.manufacturer.value = "Test Mfg"
                    mock_product.manufacturer_part_number = "MANU456"
                    mock_product.product_description = "Test Resistor"
                    mock_product.category.value = "Resistors"
                    mock_product.primary_datasheet = "http://example.com/datasheet.pdf"
                    mock_product.primary_photo = "http://example.com/image.jpg"
                    mock_product.quantity_available = 1000
                    mock_product.detailed_description = "Detailed description"
                    mock_product.series.value = "Test Series"
                    mock_product.packaging.value = "Cut Tape"
                    mock_product.unit_price = 0.05
                    mock_product.minimum_quantity = 1
                    mock_product.standard_package = 100
                    
                    # Mock product details result
                    from MakerMatrix.suppliers.base import PartSearchResult
                    return PartSearchResult(
                        supplier_part_number="TEST123-DK",
                        manufacturer="Test Mfg",
                        manufacturer_part_number="MANU456",
                        description="Test Resistor",
                        category="Resistors",
                        datasheet_url="http://example.com/datasheet.pdf",
                        image_url="http://example.com/image.jpg",
                        stock_quantity=1000,
                        pricing=[],
                        specifications={},
                        additional_data={}
                    )
                
                mock_tracked_call.return_value = await mock_impl()
                
                # Test get part details
                result = await self.supplier.get_part_details("TEST123-DK")
                
                assert result is not None
                assert result.supplier_part_number == "TEST123-DK"
                assert result.manufacturer == "Test Mfg"
                assert result.stock_quantity == 1000


class TestDigiKeyTokenManagement:
    """Test OAuth token storage and management"""
    
    def setup_method(self):
        """Set up test environment"""
        self.supplier = DigiKeySupplier()
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "digikey_tokens.json")
        self.supplier.configure(
            credentials={"client_id": "test_client_id", "client_secret": "test_secret"},
            config={"storage_path": self.test_file}
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_token_storage_and_loading(self):
        """Test token storage and loading"""
        # Set some test tokens
        self.supplier._access_token = "test_access_token"
        self.supplier._refresh_token = "test_refresh_token"
        self.supplier._token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Save tokens
        await self.supplier._save_tokens()
        
        # Clear tokens
        self.supplier._access_token = None
        self.supplier._refresh_token = None
        self.supplier._token_expires_at = None
        
        # Load tokens back
        result = await self.supplier._load_stored_tokens()
        
        assert result is True
        assert self.supplier._access_token == "test_access_token"
        assert self.supplier._refresh_token == "test_refresh_token"
        assert self.supplier._token_expires_at is not None
    
    @pytest.mark.asyncio
    async def test_token_validity_check(self):
        """Test token validity checking"""
        # Set expired token
        self.supplier._access_token = "test_token"
        self.supplier._token_expires_at = datetime.now() - timedelta(hours=1)
        
        assert await self.supplier._is_token_valid() is False
        
        # Set valid token
        self.supplier._token_expires_at = datetime.now() + timedelta(hours=1)
        
        assert await self.supplier._is_token_valid() is True
    
    @pytest.mark.asyncio
    async def test_token_refresh(self):
        """Test token refresh functionality"""
        self.supplier._refresh_token = "test_refresh_token"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful refresh response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "access_token": "new_access_token",
                "expires_in": 3600
            })
            
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Test token refresh
            result = await self.supplier._refresh_access_token()
            
            assert result is True
            assert self.supplier._access_token == "new_access_token"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])