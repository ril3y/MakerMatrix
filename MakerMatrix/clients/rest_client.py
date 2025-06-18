"""
REST API Client Implementation

Concrete implementation of BaseAPIClient for REST APIs with comprehensive
error handling, retry logic, and rate limiting.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
import httpx
import logging

from .base_client import BaseAPIClient, APIResponse, HTTPMethod
from .exceptions import (
    APIClientError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    InvalidResponseError,
    NetworkError,
    ServerError,
    ConfigurationError
)

logger = logging.getLogger(__name__)


class RESTClient(BaseAPIClient):
    """
    REST API client with comprehensive error handling and retry logic
    """
    
    def __init__(self, 
                 base_url: str,
                 api_key: Optional[str] = None,
                 auth_header_name: str = "Authorization",
                 auth_prefix: str = "Bearer",
                 timeout: int = 30,
                 max_retries: int = 3,
                 retry_backoff: float = 1.0,
                 rate_limit_per_minute: Optional[int] = None,
                 custom_headers: Optional[Dict[str, str]] = None,
                 verify_ssl: bool = True):
        """
        Initialize REST API client
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication
            auth_header_name: Name of authentication header (default: Authorization)
            auth_prefix: Prefix for auth header value (default: Bearer)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff: Base backoff time for retries (exponential backoff)
            rate_limit_per_minute: Rate limit for requests per minute
            custom_headers: Additional headers to include in requests
            verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_per_minute=rate_limit_per_minute,
            custom_headers=custom_headers
        )
        
        self.auth_header_name = auth_header_name
        self.auth_prefix = auth_prefix
        self.retry_backoff = retry_backoff
        self.verify_ssl = verify_ssl
        
        # HTTP client configuration
        self.client_config = {
            "timeout": httpx.Timeout(timeout),
            "verify": verify_ssl,
            "follow_redirects": True
        }
        
        self.logger = logging.getLogger(f"{__name__}.RESTClient")
    
    async def request(self, 
                     method: HTTPMethod,
                     endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """
        Make an HTTP request with retry logic and error handling
        """
        # Check rate limits
        await self._check_rate_limit()
        
        # Build request parameters
        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)
        
        # Prepare request data
        json_data = None
        if data:
            json_data = data
            merged_headers.setdefault("Content-Type", "application/json")
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method.value} request to {url} (attempt {attempt + 1})")
                
                async with httpx.AsyncClient(**self.client_config) as client:
                    response = await client.request(
                        method=method.value,
                        url=url,
                        params=params,
                        json=json_data,
                        headers=merged_headers
                    )
                    
                    return await self._process_response(response)
                    
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(
                    f"Request timeout after {self.timeout} seconds",
                    timeout_duration=self.timeout
                )
                self.logger.warning(f"Request timeout on attempt {attempt + 1}: {e}")
                
            except httpx.NetworkError as e:
                last_exception = NetworkError(f"Network error: {str(e)}")
                self.logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                last_exception = APIClientError(f"Unexpected error: {str(e)}")
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            # Don't retry on the last attempt
            if attempt < self.max_retries:
                backoff_time = self.retry_backoff * (2 ** attempt)
                self.logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        else:
            raise APIClientError("Request failed after all retries")
    
    async def _process_response(self, response: httpx.Response) -> APIResponse:
        """
        Process HTTP response and handle errors
        """
        # Extract response data
        try:
            # Try to parse as JSON first
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
            else:
                response_data = {"content": response.text}
        except json.JSONDecodeError:
            response_data = {"content": response.text}
        
        # Create APIResponse
        api_response = APIResponse(
            status_code=response.status_code,
            data=response_data,
            headers=dict(response.headers),
            raw_content=response.text
        )
        
        # Handle different response codes
        if response.status_code == 200 or response.status_code == 201:
            self.logger.debug(f"Successful response: {response.status_code}")
            return api_response
            
        elif response.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {response_data.get('message', 'Unauthorized')}",
                status_code=response.status_code,
                response_data=response_data
            )
            
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            
            raise RateLimitError(
                f"Rate limit exceeded: {response_data.get('message', 'Too many requests')}",
                status_code=response.status_code,
                retry_after=retry_after_int,
                response_data=response_data
            )
            
        elif 400 <= response.status_code < 500:
            raise APIClientError(
                f"Client error: {response_data.get('message', 'Bad request')}",
                status_code=response.status_code,
                response_data=response_data
            )
            
        elif 500 <= response.status_code < 600:
            raise ServerError(
                f"Server error: {response_data.get('message', 'Internal server error')}",
                status_code=response.status_code,
                response_data=response_data
            )
            
        else:
            # Unexpected status code, but not necessarily an error
            api_response.success = False
            api_response.error_message = f"Unexpected status code: {response.status_code}"
            return api_response
    
    async def test_connection(self) -> bool:
        """
        Test API connection with a simple request
        """
        try:
            self.logger.info("Testing API connection...")
            
            # Try a simple GET request to root or health endpoint
            test_endpoints = ["", "health", "status", "ping"]
            
            for endpoint in test_endpoints:
                try:
                    response = await self.get(endpoint)
                    if response.success or response.status_code in [200, 404]:
                        # 404 is okay for test - it means we can reach the server
                        self.logger.info(f"Connection test successful via endpoint: {endpoint}")
                        return True
                except Exception as e:
                    self.logger.debug(f"Test endpoint '{endpoint}' failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}")
            return False
    
    def get_authentication_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for requests
        """
        headers = {}
        
        if self.api_key:
            if self.auth_prefix:
                headers[self.auth_header_name] = f"{self.auth_prefix} {self.api_key}"
            else:
                headers[self.auth_header_name] = self.api_key
        
        return headers
    
    def validate_configuration(self) -> None:
        """
        Validate client configuration
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.base_url:
            raise ConfigurationError("Base URL is required")
        
        if not self.base_url.startswith(("http://", "https://")):
            raise ConfigurationError("Base URL must start with http:// or https://")
        
        if self.timeout <= 0:
            raise ConfigurationError("Timeout must be positive")
        
        if self.max_retries < 0:
            raise ConfigurationError("Max retries cannot be negative")
        
        if self.rate_limit_per_minute is not None and self.rate_limit_per_minute <= 0:
            raise ConfigurationError("Rate limit must be positive")
    
    async def __aenter__(self):
        """Async context manager entry with configuration validation"""
        self.validate_configuration()
        return await super().__aenter__()


class MockRESTClient(RESTClient):
    """
    Mock REST client for testing purposes
    """
    
    def __init__(self, mock_responses: Dict[str, Any], **kwargs):
        """
        Initialize mock client with predefined responses
        
        Args:
            mock_responses: Dictionary mapping endpoint patterns to response data
        """
        super().__init__(base_url="https://mock.api", **kwargs)
        self.mock_responses = mock_responses
        self.request_history = []
    
    async def request(self, method: HTTPMethod, endpoint: str, **kwargs) -> APIResponse:
        """Return mock response based on endpoint"""
        # Record request for testing
        self.request_history.append({
            "method": method,
            "endpoint": endpoint,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Find matching mock response
        for pattern, response_data in self.mock_responses.items():
            if pattern in endpoint or pattern == "*":
                return APIResponse(
                    status_code=200,
                    data=response_data,
                    success=True
                )
        
        # Default 404 response
        return APIResponse(
            status_code=404,
            data={"error": "Mock endpoint not found"},
            success=False,
            error_message="Mock endpoint not found"
        )
    
    async def test_connection(self) -> bool:
        """Always return True for mock client"""
        return True