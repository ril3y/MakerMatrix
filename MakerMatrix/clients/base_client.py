"""
Base API Client Interface

Abstract base class defining the contract for all API clients in the MakerMatrix system.
Provides standardized methods for API communication with consistent error handling.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """Supported HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIResponse:
    """Standardized API response container"""
    status_code: int
    data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    raw_content: Optional[Union[str, bytes]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Automatically determine success based on status code"""
        if self.status_code < 200 or self.status_code >= 400:
            self.success = False


@dataclass
class APIError:
    """Structured error information"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False


class BaseAPIClient(ABC):
    """
    Abstract base class for all API clients.
    
    Defines the contract that all supplier-specific API clients must implement,
    ensuring consistent behavior across different suppliers and API types.
    """
    
    def __init__(self, 
                 base_url: str,
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit_per_minute: Optional[int] = None,
                 custom_headers: Optional[Dict[str, str]] = None):
        """
        Initialize base API client
        
        Args:
            base_url: Base URL for the API
            api_key: API key for authentication (if required)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_per_minute: Rate limit for requests per minute
            custom_headers: Additional headers to include in requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_per_minute = rate_limit_per_minute
        self.custom_headers = custom_headers or {}
        
        # Rate limiting state
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def request(self, 
                     method: HTTPMethod,
                     endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method to use
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Request body data
            headers: Additional headers
            
        Returns:
            APIResponse object containing response data
            
        Raises:
            APIClientError: For various API-related errors
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the API connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_authentication_headers(self) -> Dict[str, str]:
        """
        Get headers required for API authentication
        
        Returns:
            Dictionary of authentication headers
        """
        pass
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                  headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Convenience method for GET requests"""
        return await self.request(HTTPMethod.GET, endpoint, params=params, headers=headers)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                   params: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Convenience method for POST requests"""
        return await self.request(HTTPMethod.POST, endpoint, params=params, 
                                data=data, headers=headers)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Convenience method for PUT requests"""
        return await self.request(HTTPMethod.PUT, endpoint, params=params,
                                data=data, headers=headers)
    
    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Convenience method for DELETE requests"""
        return await self.request(HTTPMethod.DELETE, endpoint, params=params, headers=headers)
    
    async def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limiting
        
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        if not self.rate_limit_per_minute:
            return
            
        async with self._rate_limit_lock:
            import time
            current_time = time.time()
            
            # Remove requests older than 1 minute
            self._request_times = [
                req_time for req_time in self._request_times 
                if current_time - req_time < 60
            ]
            
            # Check if we're at the rate limit
            if len(self._request_times) >= self.rate_limit_per_minute:
                oldest_request = min(self._request_times)
                sleep_time = 60 - (current_time - oldest_request)
                
                if sleep_time > 0:
                    self.logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
            
            # Record this request
            self._request_times.append(current_time)
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _merge_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Merge authentication, custom, and additional headers"""
        headers = {}
        
        # Add authentication headers
        headers.update(self.get_authentication_headers())
        
        # Add custom headers
        headers.update(self.custom_headers)
        
        # Add request-specific headers
        if additional_headers:
            headers.update(additional_headers)
            
        return headers
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup if needed"""
        pass