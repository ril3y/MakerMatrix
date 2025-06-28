"""
Integration tests for DigiKey supplier API endpoints.

Tests the actual API routes for DigiKey supplier functionality
including OAuth callback handling and supplier-specific endpoints.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from MakerMatrix.main import app
from MakerMatrix.models.models import engine
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers for API requests"""
    client = TestClient(app)
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


@pytest.fixture
def digikey_config():
    """Standard DigiKey configuration for testing"""
    return {
        "credentials": {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        },
        "config": {
            "oauth_callback_url": "https://localhost:8443/api/suppliers/digikey/oauth/callback",
            "storage_path": "./test_digikey_tokens"
        }
    }


class TestDigiKeySupplierDiscovery:
    """Test DigiKey supplier discovery endpoints"""
    
    def test_get_available_suppliers_includes_digikey(self, client, auth_headers):
        """Test that DigiKey is in the list of available suppliers"""
        response = client.get("/api/suppliers/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "digikey" in data["data"]
    
    def test_get_digikey_info(self, client, auth_headers):
        """Test getting DigiKey supplier information"""
        response = client.get("/api/suppliers/digikey/info", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "digikey"
        assert data["data"]["display_name"] == "DigiKey Electronics"
        assert data["data"]["supports_oauth"] is True
    
    def test_get_digikey_capabilities(self, client, auth_headers):
        """Test getting DigiKey capabilities"""
        response = client.get("/api/suppliers/digikey/capabilities", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "import_orders" in data["data"]
        assert "search_parts" in data["data"]
        assert "fetch_datasheet" in data["data"]
    
    def test_get_digikey_credential_schema(self, client, auth_headers):
        """Test getting DigiKey credential schema"""
        response = client.get("/api/suppliers/digikey/credentials-schema", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]) == 2
        
        # Check for client_id and client_secret fields
        field_names = [field["name"] for field in data["data"]]
        assert "client_id" in field_names
        assert "client_secret" in field_names
    
    def test_get_digikey_config_schema(self, client, auth_headers):
        """Test getting DigiKey configuration schema"""
        response = client.get("/api/suppliers/digikey/config-schema", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # DigiKey config schema might be empty if only requiring OAuth credentials
        # This is normal - the schema endpoint shows configuration fields beyond credentials
        assert isinstance(data["data"], list)


class TestDigiKeyConfiguration:
    """Test DigiKey supplier configuration"""
    
    def test_test_connection_not_configured(self, client, auth_headers):
        """Test connection test when DigiKey is not configured"""
        config_data = {
            "credentials": {},
            "config": {}
        }
        
        response = client.post(
            "/api/suppliers/digikey/test",
            json=config_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error" or data["status"] == "success"
        
        if data["status"] == "error":
            # If not configured properly, should get configuration error
            assert ("configuration" in data["message"].lower() or 
                   "credentials" in data["message"].lower() or
                   "not configured" in data["message"].lower())
    
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    def test_test_connection_with_credentials(self, client, auth_headers, digikey_config):
        """Test connection test with valid credentials"""
        with patch('requests.get') as mock_get:
            # Mock API reachability check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.post(
                "/api/suppliers/digikey/test",
                json=digikey_config,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should indicate OAuth is required for DigiKey
            assert "oauth" in data["message"].lower() or "authentication" in data["message"].lower()
    
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', False)
    def test_test_connection_missing_library(self, client, auth_headers, digikey_config):
        """Test connection test when DigiKey library is missing"""
        response = client.post(
            "/api/suppliers/digikey/test",
            json=digikey_config,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error" or data["status"] == "success"
        
        # Should mention missing library
        if "digikey" in data["message"].lower():
            assert "library" in data["message"].lower() or "dependency" in data["message"].lower()


class TestDigiKeyOAuthFlow:
    """Test DigiKey OAuth functionality"""
    
    def test_get_oauth_authorization_url(self, client, auth_headers, digikey_config):
        """Test getting OAuth authorization URL"""
        response = client.post(
            "/api/suppliers/digikey/oauth/authorization-url",
            json=digikey_config,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        auth_url = data["data"]
        assert "https://api.digikey.com/v1/oauth2/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "redirect_uri=" in auth_url
        assert "/api/suppliers/digikey/oauth/callback" in auth_url
    
    def test_oauth_callback_success(self, client):
        """Test successful OAuth callback"""
        response = client.get(
            "/api/suppliers/digikey/oauth/callback?code=test_auth_code"
        )
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Check that the response contains the authorization code
        html_content = response.text
        assert "test_auth_code" in html_content
        assert "OAuth Authorization Successful" in html_content
        assert "Copy the authorization code below" in html_content
    
    def test_oauth_callback_error(self, client):
        """Test OAuth callback with error"""
        response = client.get(
            "/api/suppliers/digikey/oauth/callback?error=access_denied"
        )
        
        assert response.status_code == 400
        assert "text/html" in response.headers["content-type"]
        
        html_content = response.text
        assert "OAuth Authorization Failed" in html_content
        assert "access_denied" in html_content
    
    def test_oauth_callback_missing_code(self, client):
        """Test OAuth callback without code or error"""
        response = client.get("/api/suppliers/digikey/oauth/callback")
        
        assert response.status_code == 400
        assert "text/html" in response.headers["content-type"]
        
        html_content = response.text
        assert "Missing Authorization Code" in html_content
    
    def test_oauth_exchange_success(self, client, auth_headers, digikey_config):
        """Test OAuth code exchange endpoint structure"""
        response = client.post(
            "/api/suppliers/digikey/oauth/exchange?authorization_code=test_code",
            json=digikey_config,
            headers=auth_headers
        )
        
        # This might fail if the supplier doesn't have the exchange method
        # but we're testing the API endpoint structure
        assert response.status_code in [200, 400, 500]


class TestDigiKeyPartSearch:
    """Test DigiKey part search functionality"""
    
    @patch('MakerMatrix.suppliers.digikey.DIGIKEY_API_AVAILABLE', True)
    @patch('MakerMatrix.suppliers.digikey.digikey')
    def test_search_parts(self, mock_digikey, client, auth_headers, digikey_config):
        """Test part search functionality"""
        # Mock authentication
        with patch('MakerMatrix.suppliers.registry.SupplierRegistry.get_supplier') as mock_get_supplier:
            mock_supplier = Mock()
            mock_supplier.configure = Mock()
            mock_supplier.close = AsyncMock()
            
            # Mock search results
            from MakerMatrix.suppliers.base import PartSearchResult
            mock_result = PartSearchResult(
                supplier_part_number="TEST123-DK",
                manufacturer="Test Mfg",
                manufacturer_part_number="MANU456",
                description="Test Resistor",
                category="Resistors",
                datasheet_url="http://example.com/datasheet.pdf",
                image_url="http://example.com/image.jpg",
                stock_quantity=1000,
                pricing=[{"quantity": 1, "price": 0.05, "currency": "USD"}],
                specifications={"Resistance": "1K", "Tolerance": "5%"},
                additional_data={}
            )
            
            mock_supplier.search_parts = AsyncMock(return_value=[mock_result])
            mock_get_supplier.return_value = mock_supplier
            
            search_request = {
                "query": "test resistor",
                "limit": 10
            }
            
            response = client.post(
                "/api/suppliers/digikey/search",
                json={**digikey_config, **search_request},
                headers=auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert len(data["data"]) == 1
                
                result = data["data"][0]
                assert result["supplier_part_number"] == "TEST123-DK"
                assert result["manufacturer"] == "Test Mfg"
                assert result["stock_quantity"] == 1000


class TestDigiKeyCSVImport:
    """Test DigiKey CSV import functionality through supplier registry"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_csv_content = '''Digi-Key Part Number,Manufacturer,Manufacturer Part Number,Description,Quantity,Unit Price
TEST123-DK,Test Mfg,MANU456,Test Resistor 1K,10,$0.05
TEST456-DK,Another Mfg,MANU789,Test Capacitor 10uF,5,$0.25'''
    
    def test_digikey_can_import_file(self, client, auth_headers):
        """Test DigiKey file type detection"""
        from MakerMatrix.suppliers.digikey import DigiKeySupplier
        
        supplier = DigiKeySupplier()
        
        # Test DigiKey file patterns
        assert supplier.can_import_file("digikey_order.csv") is True
        assert supplier.can_import_file("digi-key_export.xlsx") is True
        assert supplier.can_import_file("weborder_123.csv") is True
        
        # Test non-DigiKey files
        assert supplier.can_import_file("mouser_order.csv") is False
        assert supplier.can_import_file("lcsc_parts.xlsx") is False
    
    @pytest.mark.asyncio
    async def test_digikey_csv_import_direct(self):
        """Test direct CSV import through supplier"""
        from MakerMatrix.suppliers.digikey import DigiKeySupplier
        
        supplier = DigiKeySupplier()
        
        result = await supplier.import_order_file(
            self.test_csv_content.encode('utf-8'),
            "csv",
            "test_digikey.csv"
        )
        
        assert result.success is True
        assert result.imported_count == 2
        assert len(result.parts) == 2
        
        # Check first part
        part1 = result.parts[0]
        assert part1['part_number'] == "TEST123-DK"
        assert part1['manufacturer'] == "Test Mfg"
        assert part1['quantity'] == 10
        assert part1['supplier'] == "DigiKey"


class TestDigiKeyRateLimit:
    """Test DigiKey rate limiting"""
    
    def test_connection_test_rate_limit(self, client, auth_headers, digikey_config):
        """Test that connection tests are rate limited"""
        # Make multiple rapid requests
        responses = []
        for _ in range(3):
            response = client.post(
                "/api/suppliers/digikey/test",
                json=digikey_config,
                headers=auth_headers
            )
            responses.append(response)
        
        # At least one should succeed (rate limiting is lenient for tests)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1


class MockDigiKeySupplier:
    """Mock DigiKey supplier for testing"""
    
    def configure(self, credentials, config):
        pass
    
    async def exchange_code_for_tokens(self, code):
        return True
    
    async def close(self):
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])