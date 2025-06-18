"""
API Client Exceptions

Custom exceptions for API client operations, providing detailed error context
and proper error categorization for different failure scenarios.
"""

from typing import Optional, Dict, Any


class APIClientError(Exception):
    """Base exception for all API client errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None, 
                 supplier: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        self.supplier = supplier


class RateLimitError(APIClientError):
    """Raised when API rate limits are exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(APIClientError):
    """Raised when API authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class TimeoutError(APIClientError):
    """Raised when API requests timeout"""
    
    def __init__(self, message: str = "Request timeout", 
                 timeout_duration: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.timeout_duration = timeout_duration


class InvalidResponseError(APIClientError):
    """Raised when API response is invalid or malformed"""
    
    def __init__(self, message: str = "Invalid response format", 
                 expected_format: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.expected_format = expected_format


class NetworkError(APIClientError):
    """Raised when network-level errors occur"""
    
    def __init__(self, message: str = "Network error", **kwargs):
        super().__init__(message, **kwargs)


class ServerError(APIClientError):
    """Raised when server returns 5xx errors"""
    
    def __init__(self, message: str = "Server error", **kwargs):
        super().__init__(message, **kwargs)


class ConfigurationError(APIClientError):
    """Raised when client configuration is invalid"""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, **kwargs)