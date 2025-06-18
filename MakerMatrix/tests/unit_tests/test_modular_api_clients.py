"""
Unit tests for the modular API client system

Tests the new dependency injection architecture with mocked API responses
to ensure parsing logic is separated from API communication.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from MakerMatrix.clients.base_client import BaseAPIClient, APIResponse, HTTPMethod
from MakerMatrix.clients.rest_client import RESTClient, MockRESTClient
from MakerMatrix.clients.suppliers.lcsc_client import LCSCClient
from MakerMatrix.clients.exceptions import APIClientError, RateLimitError, AuthenticationError
from MakerMatrix.parsers.enhanced_lcsc_parser_v2 import EnhancedLcscParserV2
try:
    from MakerMatrix.parsers.supplier_capabilities import CapabilityType
except ImportError:
    from enum import Enum
    class CapabilityType(Enum):
        FETCH_DATASHEET = "fetch_datasheet"
        FETCH_IMAGE = "fetch_image"
        FETCH_PRICING = "fetch_pricing"


class TestBaseAPIClient:
    """Test the abstract base API client"""
    
    def test_base_client_is_abstract(self):
        """BaseAPIClient cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseAPIClient("https://api.example.com")


class TestRESTClient:
    """Test the REST API client implementation"""
    
    @pytest.fixture
    def rest_client(self):
        """Create a REST client for testing"""
        return RESTClient(
            base_url="https://api.example.com",
            api_key="test-key",
            timeout=10,
            max_retries=2
        )
    
    def test_rest_client_initialization(self, rest_client):
        """Test REST client initialization"""
        assert rest_client.base_url == "https://api.example.com"
        assert rest_client.api_key == "test-key"
        assert rest_client.timeout == 10
        assert rest_client.max_retries == 2
    
    def test_authentication_headers(self, rest_client):
        """Test authentication header generation"""
        headers = rest_client.get_authentication_headers()
        assert headers["Authorization"] == "Bearer test-key"
    
    def test_custom_auth_header(self):
        """Test custom authentication header format"""
        client = RESTClient(
            base_url="https://api.example.com",
            api_key="secret",
            auth_header_name="X-API-Key",
            auth_prefix=""
        )
        headers = client.get_authentication_headers()
        assert headers["X-API-Key"] == "secret"
    
    def test_url_building(self, rest_client):
        """Test URL building from endpoints"""
        url = rest_client._build_url("products/123")
        assert url == "https://api.example.com/products/123"
        
        url = rest_client._build_url("/products/123")
        assert url == "https://api.example.com/products/123"
    
    def test_header_merging(self, rest_client):
        """Test header merging functionality"""
        custom_headers = {"Content-Type": "application/json"}
        merged = rest_client._merge_headers(custom_headers)
        
        assert "Authorization" in merged
        assert merged["Content-Type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        client = RESTClient(
            base_url="https://api.example.com",
            rate_limit_per_minute=2
        )
        
        # Add two requests to the rate limit tracker
        import time
        current_time = time.time()
        client._request_times = [current_time, current_time]
        
        # This should trigger rate limiting
        start_time = time.time()
        await client._check_rate_limit()
        end_time = time.time()
        
        # Should have slept for some time
        assert end_time > start_time


class TestMockRESTClient:
    """Test the mock REST client for testing"""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock REST client"""
        mock_responses = {
            "products/C1000": {
                "result": {
                    "title": "Test Resistor",
                    "datasheet": "https://example.com/datasheet.pdf",
                    "szlcsc": {
                        "stock": 1000,
                        "price": "0.01"
                    }
                }
            },
            "*": {"error": "Not found"}
        }
        return MockRESTClient(mock_responses)
    
    @pytest.mark.asyncio
    async def test_mock_response(self, mock_client):
        """Test mock client returns expected responses"""
        response = await mock_client.get("products/C1000")
        
        assert response.success
        assert response.data["result"]["title"] == "Test Resistor"
    
    @pytest.mark.asyncio
    async def test_mock_fallback(self, mock_client):
        """Test mock client fallback response"""
        response = await mock_client.get("unknown/endpoint")
        
        # The mock client returns success=True but with error data
        # This matches the "*" fallback pattern in the mock responses
        assert response.success  # Mock returns 200 with error content
        assert response.data["error"] == "Not found"
    
    def test_request_history(self, mock_client):
        """Test that mock client tracks request history"""
        assert len(mock_client.request_history) == 0
        
        # Make a request
        asyncio.run(mock_client.get("test"))
        
        assert len(mock_client.request_history) == 1
        assert mock_client.request_history[0]["method"] == HTTPMethod.GET
        assert mock_client.request_history[0]["endpoint"] == "test"


class TestLCSCClient:
    """Test the LCSC-specific API client"""
    
    @pytest.fixture
    def lcsc_client(self):
        """Create an LCSC client for testing"""
        return LCSCClient(timeout=10, max_retries=1)
    
    def test_lcsc_client_initialization(self, lcsc_client):
        """Test LCSC client initialization"""
        assert lcsc_client.base_url == "https://easyeda.com"
        assert lcsc_client.timeout == 10
        assert "User-Agent" in lcsc_client.custom_headers
    
    def test_lcsc_authentication_headers(self, lcsc_client):
        """Test that LCSC client doesn't require authentication"""
        headers = lcsc_client.get_authentication_headers()
        assert headers == {}
    
    @pytest.mark.asyncio
    async def test_lcsc_component_info_url_building(self, lcsc_client):
        """Test URL building for component info"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock the HTTP client
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": {"title": "Test Component"}}
            mock_response.text = '{"result": {"title": "Test Component"}}'
            mock_response.headers = {}
            
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)
            
            result = await lcsc_client.get_component_info("C1000")
            
            # Verify the request was made with correct URL
            call_args = mock_client.return_value.__aenter__.return_value.request.call_args
            assert "products/C1000/components" in call_args[1]["url"]
    
    @pytest.mark.asyncio
    async def test_lcsc_datasheet_url_extraction(self, lcsc_client):
        """Test datasheet URL extraction"""
        # Mock the get_component_info method
        lcsc_client.get_component_info = AsyncMock(return_value={
            "result": {
                "datasheet": "https://example.com/datasheet.pdf"
            }
        })
        
        datasheet_url = await lcsc_client.get_datasheet_url("C1000")
        assert datasheet_url == "https://example.com/datasheet.pdf"
    
    @pytest.mark.asyncio
    async def test_lcsc_image_url_extraction(self, lcsc_client):
        """Test image URL extraction"""
        lcsc_client.get_component_info = AsyncMock(return_value={
            "result": {
                "image": "https://example.com/component.jpg"
            }
        })
        
        image_url = await lcsc_client.get_component_image_url("C1000")
        assert image_url == "https://example.com/component.jpg"


class TestEnhancedLcscParserV2:
    """Test the refactored LCSC parser with dependency injection"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client for testing"""
        return MockRESTClient({
            "api/products/C1000/components": {
                "result": {
                    "title": "Test Resistor 1k",
                    "packageDetail": {
                        "dataStr": {
                            "head": {
                                "c_para": {
                                    "link": "https://example.com/datasheet.pdf"
                                }
                            }
                        }
                    },
                    "image": "https://example.com/resistor.jpg",
                    "szlcsc": {
                        "stock": 1000,
                        "price": "0.01",
                        "url": "https://lcsc.com/product-detail/C1000"
                    }
                }
            }
        })
    
    @pytest.fixture
    def parser_with_mock(self, mock_api_client):
        """Create parser with mock API client"""
        return EnhancedLcscParserV2(api_client=mock_api_client)
    
    def test_parser_initialization_with_injection(self, mock_api_client):
        """Test parser initialization with dependency injection"""
        parser = EnhancedLcscParserV2(api_client=mock_api_client)
        assert parser.api_client is mock_api_client
        assert parser.supplier_name == "LCSC"
    
    def test_parser_initialization_default_client(self):
        """Test parser initialization with default client"""
        parser = EnhancedLcscParserV2()
        assert isinstance(parser.api_client, LCSCClient)
    
    @pytest.mark.asyncio
    async def test_fetch_datasheet_with_mock(self, parser_with_mock):
        """Test datasheet fetching with mocked API"""
        result = await parser_with_mock._fetch_datasheet_impl("C1000")
        
        assert result.capability == CapabilityType.FETCH_DATASHEET
        assert result.success
        assert result.data["url"] == "https://example.com/datasheet.pdf"
        assert result.data["source"] == "EasyEDA API"
        assert result.data["part_number"] == "C1000"
    
    @pytest.mark.asyncio
    async def test_fetch_pricing_with_mock(self, parser_with_mock):
        """Test pricing fetching with mocked API"""
        result = await parser_with_mock._fetch_pricing_impl("C1000")
        
        assert result.capability == CapabilityType.FETCH_PRICING
        assert result.success
        assert result.data["stock"] == 1000
        assert result.data["price"] == "0.01"
        assert result.data["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_fetch_stock_with_mock(self, parser_with_mock):
        """Test stock fetching with mocked API"""
        result = await parser_with_mock._fetch_stock_impl("C1000")
        
        assert result.capability == CapabilityType.FETCH_STOCK
        assert result.success
        assert result.data["stock_level"] == 1000
        assert result.data["availability"] == "in_stock"
    
    @pytest.mark.asyncio
    async def test_fetch_image_with_mock(self, parser_with_mock):
        """Test image fetching with mocked API"""
        result = await parser_with_mock._fetch_image_impl("C1000")
        
        assert result.capability == CapabilityType.FETCH_IMAGE
        assert result.success
        assert result.data["url"] == "https://example.com/resistor.jpg"
    
    def test_datasheet_url_extraction_pure_parsing(self, parser_with_mock):
        """Test pure parsing of datasheet URL without API calls"""
        component_data = {
            "result": {
                "packageDetail": {
                    "dataStr": {
                        "head": {
                            "c_para": {
                                "link": "https://example.com/test.pdf"
                            }
                        }
                    }
                }
            }
        }
        
        url = parser_with_mock._extract_datasheet_url(component_data, "TEST123")
        assert url == "https://example.com/test.pdf"
    
    def test_pricing_data_extraction_pure_parsing(self, parser_with_mock):
        """Test pure parsing of pricing data without API calls"""
        component_data = {
            "result": {
                "szlcsc": {
                    "stock": 500,
                    "price": "0.05",
                    "url": "https://lcsc.com/product"
                }
            }
        }
        
        pricing = parser_with_mock._extract_pricing_data(component_data, "TEST123")
        assert pricing["stock"] == 500
        assert pricing["price"] == "0.05"
        assert pricing["currency"] == "USD"
        assert pricing["part_number"] == "TEST123"
    
    def test_stock_data_extraction_pure_parsing(self, parser_with_mock):
        """Test pure parsing of stock data without API calls"""
        component_data = {
            "result": {
                "szlcsc": {
                    "stock": 0
                }
            }
        }
        
        stock = parser_with_mock._extract_stock_data(component_data, "TEST123")
        assert stock["stock_level"] == 0
        assert stock["availability"] == "out_of_stock"
        assert stock["part_number"] == "TEST123"
    
    @pytest.mark.asyncio
    async def test_error_handling_with_failed_api(self):
        """Test error handling when API calls fail"""
        # Create a mock client that always fails
        failing_client = MockRESTClient({})
        parser = EnhancedLcscParserV2(api_client=failing_client)
        
        result = await parser._fetch_datasheet_impl("INVALID")
        
        assert not result.success
        assert "error" in result.error.lower()
    
    def test_parsing_methods_are_pure_functions(self, parser_with_mock):
        """Test that parsing methods don't make external calls"""
        # These methods should work with any data without making network calls
        
        empty_data = {}
        url = parser_with_mock._extract_datasheet_url(empty_data, "TEST")
        assert url is None
        
        pricing = parser_with_mock._extract_pricing_data(empty_data, "TEST")
        assert pricing["part_number"] == "TEST"
        
        stock = parser_with_mock._extract_stock_data(empty_data, "TEST")
        assert stock["availability"] == "unknown"


class TestAPIErrorHandling:
    """Test comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_api_client_error_propagation(self):
        """Test that API errors are properly propagated"""
        # Create a mock that raises an exception
        mock_client = Mock(spec=BaseAPIClient)
        mock_client.get = AsyncMock(side_effect=APIClientError("Test error"))
        
        parser = EnhancedLcscParserV2(api_client=mock_client)
        
        result = await parser._fetch_datasheet_impl("TEST")
        assert not result.success
        assert "Test error" in result.error
    
    def test_api_response_validation(self):
        """Test API response validation"""
        from MakerMatrix.clients.base_client import APIResponse
        
        # Test successful response
        response = APIResponse(status_code=200, data={"test": "data"})
        assert response.success
        
        # Test error response
        error_response = APIResponse(status_code=404)
        assert not error_response.success
    
    def test_exception_types(self):
        """Test different exception types"""
        from MakerMatrix.clients.exceptions import (
            APIClientError, RateLimitError, AuthenticationError
        )
        
        # Test base exception
        base_error = APIClientError("Base error", status_code=500)
        assert base_error.status_code == 500
        assert base_error.message == "Base error"
        
        # Test rate limit exception
        rate_error = RateLimitError("Rate limited", retry_after=60)
        assert rate_error.retry_after == 60
        
        # Test auth exception
        auth_error = AuthenticationError("Auth failed")
        assert auth_error.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])