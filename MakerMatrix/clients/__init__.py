"""
API Client Layer for MakerMatrix

This module provides a clean separation between API communication and data parsing.
It includes base interfaces, REST/GraphQL clients, and supplier-specific implementations.
"""

from .base_client import BaseAPIClient, APIResponse, APIError
from .rest_client import RESTClient
from .exceptions import (
    APIClientError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    InvalidResponseError
)

__all__ = [
    "BaseAPIClient",
    "APIResponse", 
    "APIError",
    "RESTClient",
    "APIClientError",
    "RateLimitError",
    "AuthenticationError", 
    "TimeoutError",
    "InvalidResponseError"
]