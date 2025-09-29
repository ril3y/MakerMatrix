"""
Unified HTTP Client Service for Suppliers

Provides consistent HTTP operations across all supplier implementations:
- Session management with automatic cleanup
- Defensive null safety for JSON responses
- Retry logic and timeout handling
- Rate limiting integration
- Common error handling patterns
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
import json

logger = logging.getLogger(__name__)


@dataclass
class HTTPResponse:
    """Standardized HTTP response wrapper"""
    status: int
    data: Dict[str, Any]
    headers: Dict[str, str]
    url: str
    duration_ms: int
    success: bool = True
    error_message: Optional[str] = None
    raw_content: Optional[str] = None  # For HTML/text content
    
    @classmethod
    def from_aiohttp_response(cls, response: aiohttp.ClientResponse, data: Dict[str, Any], duration_ms: int, raw_content: Optional[str] = None):
        """Create HTTPResponse from aiohttp response"""
        return cls(
            status=response.status,
            data=data,
            headers=dict(response.headers),
            url=str(response.url),
            duration_ms=duration_ms,
            success=200 <= response.status < 300,
            raw_content=raw_content
        )
    
    @classmethod
    def error_response(cls, url: str, error_message: str, status: int = 500):
        """Create error response"""
        return cls(
            status=status,
            data={},
            headers={},
            url=url,
            duration_ms=0,
            success=False,
            error_message=error_message
        )


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    retry_on_status: List[int] = None  # HTTP status codes to retry on
    
    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 500, 502, 503, 504]


class SupplierHTTPClient:
    """
    Unified HTTP client for all supplier operations.
    
    Features:
    - Automatic session management
    - Defensive null safety for JSON responses  
    - Built-in retry logic with exponential backoff
    - Rate limiting integration
    - Consistent error handling
    - Request/response logging
    """
    
    def __init__(
        self,
        supplier_name: str,
        default_timeout: int = 30,
        default_headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[RetryConfig] = None
    ):
        self.supplier_name = supplier_name
        self.default_timeout = default_timeout
        self.default_headers = default_headers or {}
        self.retry_config = retry_config or RetryConfig()
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_service = None  # Lazy loaded
        
        logger.info(f"Initialized HTTP client for supplier: {supplier_name}")
    
    def _get_rate_limit_service(self):
        """Lazy load rate limit service to avoid circular imports"""
        if self._rate_limit_service is None:
            try:
                from MakerMatrix.services.rate_limit_service import RateLimitService
                from MakerMatrix.models.models import engine
                self._rate_limit_service = RateLimitService(engine)
            except ImportError as e:
                logger.warning(f"Could not import RateLimitService: {e}")
                self._rate_limit_service = None
        return self._rate_limit_service
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with proper configuration"""
        if not self._session or self._session.closed:
            import ssl
            timeout = aiohttp.ClientTimeout(total=self.default_timeout, sock_connect=10)

            # Create permissive SSL context for external API calls
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ssl=ssl_context,  # Use permissive SSL context
                enable_cleanup_closed=True  # Enable cleanup of closed connections
            )

            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.default_headers
            )
            
        return self._session
    
    def _safe_json_parse(self, response_text: str) -> Dict[str, Any]:
        """
        Safely parse JSON response with defensive null handling.
        
        This addresses the common pattern found across suppliers:
        data = await response.json() or {}
        """
        try:
            if not response_text:
                return {}
            
            parsed = json.loads(response_text)
            
            # Handle case where JSON parsing returns None
            if parsed is None:
                return {}
            
            # Ensure we return a dictionary
            if isinstance(parsed, dict):
                return parsed
            elif isinstance(parsed, list):
                return {"items": parsed}  # Wrap lists in a dict
            else:
                return {"value": parsed}  # Wrap primitives in a dict
                
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response for {self.supplier_name}: {e}")
            return {}
    
    def _safe_nested_get(self, data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
        """
        Safely get nested dictionary values with null protection.
        
        Example: _safe_nested_get(data, ["results", "items", 0, "name"], "unknown")
        """
        current = data
        
        for key in keys:
            if current is None:
                return default
            
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return default
        
        return current if current is not None else default
    
    async def _check_rate_limits(self, endpoint_type: str) -> bool:
        """Check rate limits before making request"""
        rate_service = self._get_rate_limit_service()
        if not rate_service:
            return True  # No rate limiting if service unavailable
        
        try:
            rate_status = await rate_service.check_rate_limit(self.supplier_name, endpoint_type)
            return rate_status.get("allowed", True)
        except Exception as e:
            logger.warning(f"Rate limit check failed for {self.supplier_name}: {e}")
            return True  # Allow request if check fails
    
    async def _record_request(
        self,
        endpoint_type: str,
        success: bool,
        duration_ms: int,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record request for rate limiting and usage tracking"""
        rate_service = self._get_rate_limit_service()
        if not rate_service:
            return
        
        try:
            await rate_service.record_request(
                supplier_name=self.supplier_name,
                endpoint_type=endpoint_type,
                success=success,
                response_time_ms=duration_ms,
                error_message=error_message,
                request_metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to record request for {self.supplier_name}: {e}")
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        endpoint_type: str,
        **kwargs
    ) -> HTTPResponse:
        """Make HTTP request with retry logic and rate limiting"""
        
        # Check rate limits
        if not await self._check_rate_limits(endpoint_type):
            from ..suppliers.exceptions import SupplierRateLimitError
            raise SupplierRateLimitError(
                f"Rate limit exceeded for {self.supplier_name}",
                supplier_name=self.supplier_name
            )
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            start_time = time.time()
            duration_ms = 0
            
            try:
                session = await self._get_session()
                
                # Make the request
                async with session.request(method, url, **kwargs) as response:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Read response text
                    response_text = await response.text()
                    
                    # Parse JSON with defensive null safety
                    data = self._safe_json_parse(response_text)
                    
                    # Create response object with raw content for HTML/text responses
                    http_response = HTTPResponse.from_aiohttp_response(response, data, duration_ms, raw_content=response_text)
                    
                    # Record successful request
                    await self._record_request(
                        endpoint_type=endpoint_type,
                        success=http_response.success,
                        duration_ms=duration_ms,
                        metadata={
                            "method": method,
                            "url": url,
                            "status": response.status,
                            "attempt": attempt + 1
                        }
                    )
                    
                    # Check if we should retry on this status code
                    if not http_response.success and response.status in self.retry_config.retry_on_status:
                        if attempt < self.retry_config.max_retries:
                            delay = min(
                                self.retry_config.base_delay * (self.retry_config.backoff_factor ** attempt),
                                self.retry_config.max_delay
                            )
                            logger.warning(
                                f"Request failed for {self.supplier_name} (status {response.status}), "
                                f"retrying in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_retries + 1})"
                            )
                            await asyncio.sleep(delay)
                            continue
                    
                    return http_response
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                last_exception = e
                
                # Record failed request
                await self._record_request(
                    endpoint_type=endpoint_type,
                    success=False,
                    duration_ms=duration_ms,
                    error_message=str(e),
                    metadata={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "exception_type": type(e).__name__
                    }
                )
                
                # Retry on network errors
                if attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.backoff_factor ** attempt),
                        self.retry_config.max_delay
                    )
                    logger.warning(
                        f"Request failed for {self.supplier_name} ({str(e)}), "
                        f"retrying in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # Max retries exceeded
                break
        
        # All retries failed
        error_msg = f"Request failed after {self.retry_config.max_retries + 1} attempts: {str(last_exception)}"
        logger.error(f"HTTP request failed for {self.supplier_name}: {error_msg}")
        
        return HTTPResponse.error_response(url, error_msg)
    
    # ========== Public API Methods ==========
    
    async def get(
        self,
        url: str,
        endpoint_type: str = "api_call",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> HTTPResponse:
        """Make GET request with unified error handling"""
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        return await self._make_request_with_retry(
            "GET", url, endpoint_type,
            headers=request_headers,
            params=params,
            **kwargs
        )
    
    async def post(
        self,
        url: str,
        endpoint_type: str = "api_call",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> HTTPResponse:
        """Make POST request with unified error handling"""
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        return await self._make_request_with_retry(
            "POST", url, endpoint_type,
            headers=request_headers,
            data=data,
            json=json_data,
            **kwargs
        )
    
    async def put(
        self,
        url: str,
        endpoint_type: str = "api_call",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> HTTPResponse:
        """Make PUT request with unified error handling"""
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        return await self._make_request_with_retry(
            "PUT", url, endpoint_type,
            headers=request_headers,
            data=data,
            json=json_data,
            **kwargs
        )
    
    async def delete(
        self,
        url: str,
        endpoint_type: str = "api_call",
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> HTTPResponse:
        """Make DELETE request with unified error handling"""
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        return await self._make_request_with_retry(
            "DELETE", url, endpoint_type,
            headers=request_headers,
            **kwargs
        )
    
    def safe_get(self, data: Dict[str, Any], keys: Union[str, List[str]], default: Any = None) -> Any:
        """
        Convenience method for safe nested data access.
        
        Usage:
            # Simple key access
            name = client.safe_get(data, "name", "unknown")
            
            # Nested key access
            price = client.safe_get(data, ["pricing", "breaks", 0, "price"], 0.0)
        """
        if isinstance(keys, str):
            keys = [keys]
        
        return self._safe_nested_get(data, keys, default)
    
    # ========== Cleanup ==========
    
    async def close(self):
        """Close HTTP session and cleanup resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info(f"Closed HTTP session for supplier: {self.supplier_name}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()