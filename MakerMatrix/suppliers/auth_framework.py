"""
Common Authentication Framework for Suppliers

Provides standardized authentication patterns across all supplier implementations:
- OAuth2 client credentials flow
- API key authentication
- Token management and refresh
- Authentication state tracking
- Consistent error handling
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import base64
import json

from .http_client import SupplierHTTPClient, HTTPResponse

logger = logging.getLogger(__name__)


@dataclass
class AuthToken:
    """Represents an authentication token"""
    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired (with optional buffer)"""
        if not self.expires_at:
            return False  # No expiry means never expires
        
        return datetime.utcnow() + timedelta(seconds=buffer_seconds) >= self.expires_at
    
    def to_header_value(self) -> str:
        """Get token value for Authorization header"""
        return f"{self.token_type} {self.access_token}"


@dataclass
class AuthResult:
    """Result of an authentication attempt"""
    success: bool
    token: Optional[AuthToken] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class BaseAuthenticator(ABC):
    """Abstract base class for authentication methods"""
    
    def __init__(self, supplier_name: str, http_client: SupplierHTTPClient):
        self.supplier_name = supplier_name
        self.http_client = http_client
        self._current_token: Optional[AuthToken] = None
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Perform authentication with given credentials"""
        pass
    
    @abstractmethod
    async def refresh_token(self) -> AuthResult:
        """Refresh the current token if possible"""
        pass
    
    def get_current_token(self) -> Optional[AuthToken]:
        """Get current authentication token"""
        return self._current_token
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated with valid token"""
        if not self._current_token:
            return False
        return not self._current_token.is_expired()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests"""
        if not self._current_token:
            return {}
        return {"Authorization": self._current_token.to_header_value()}


class APIKeyAuthenticator(BaseAuthenticator):
    """Simple API key authentication"""
    
    def __init__(self, supplier_name: str, http_client: SupplierHTTPClient, header_name: str = "X-API-Key"):
        super().__init__(supplier_name, http_client)
        self.header_name = header_name
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Authenticate using API key"""
        api_key = credentials.get("api_key")
        if not api_key:
            return AuthResult(
                success=False,
                error_message="API key is required"
            )
        
        # Create a simple token for API key
        self._current_token = AuthToken(
            access_token=api_key,
            token_type="ApiKey"
        )
        
        return AuthResult(
            success=True,
            token=self._current_token
        )
    
    async def refresh_token(self) -> AuthResult:
        """API keys don't need refresh"""
        if self._current_token:
            return AuthResult(success=True, token=self._current_token)
        return AuthResult(success=False, error_message="No token to refresh")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for API key authentication"""
        if not self._current_token:
            return {}
        return {self.header_name: self._current_token.access_token}


class OAuth2ClientCredentialsAuthenticator(BaseAuthenticator):
    """OAuth2 client credentials flow authentication"""
    
    def __init__(
        self,
        supplier_name: str,
        http_client: SupplierHTTPClient,
        token_url: str,
        scope: Optional[str] = None
    ):
        super().__init__(supplier_name, http_client)
        self.token_url = token_url
        self.scope = scope
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Authenticate using OAuth2 client credentials"""
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
        
        if not client_id or not client_secret:
            return AuthResult(
                success=False,
                error_message="Client ID and client secret are required"
            )
        
        self._client_id = client_id
        self._client_secret = client_secret
        
        return await self._request_token()
    
    async def refresh_token(self) -> AuthResult:
        """Refresh token using client credentials"""
        if not self._client_id or not self._client_secret:
            return AuthResult(
                success=False,
                error_message="Client credentials not available for refresh"
            )
        
        return await self._request_token()
    
    async def _request_token(self) -> AuthResult:
        """Request new token from OAuth2 server"""
        try:
            # Prepare OAuth2 client credentials request
            auth_header = base64.b64encode(
                f"{self._client_id}:{self._client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "client_credentials"
            }
            
            if self.scope:
                data["scope"] = self.scope
            
            # Make token request
            response = await self.http_client.post(
                self.token_url,
                endpoint_type="oauth_token",
                headers=headers,
                data=data
            )
            
            if not response.success:
                return AuthResult(
                    success=False,
                    error_message=f"Token request failed: {response.error_message or 'Unknown error'}",
                    status_code=response.status
                )
            
            # Parse token response
            token_data = response.data
            access_token = token_data.get("access_token")
            
            if not access_token:
                return AuthResult(
                    success=False,
                    error_message="No access token in response",
                    status_code=response.status
                )
            
            # Calculate expiry time
            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
            
            # Create token
            self._current_token = AuthToken(
                access_token=access_token,
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope")
            )
            
            logger.info(f"OAuth2 authentication successful for {self.supplier_name}")
            
            return AuthResult(
                success=True,
                token=self._current_token,
                additional_data={
                    "expires_in": expires_in,
                    "scope": self._current_token.scope
                }
            )
            
        except Exception as e:
            logger.error(f"OAuth2 authentication failed for {self.supplier_name}: {e}")
            return AuthResult(
                success=False,
                error_message=f"Authentication error: {str(e)}"
            )


class BearerTokenAuthenticator(BaseAuthenticator):
    """Simple Bearer token authentication"""
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """Authenticate using bearer token"""
        bearer_token = credentials.get("bearer_token")
        if not bearer_token:
            return AuthResult(
                success=False,
                error_message="Bearer token is required"
            )
        
        self._current_token = AuthToken(
            access_token=bearer_token,
            token_type="Bearer"
        )
        
        return AuthResult(
            success=True,
            token=self._current_token
        )
    
    async def refresh_token(self) -> AuthResult:
        """Bearer tokens typically don't refresh"""
        if self._current_token:
            return AuthResult(success=True, token=self._current_token)
        return AuthResult(success=False, error_message="No token to refresh")


class AuthenticationManager:
    """
    Manager class for handling different authentication methods.
    
    Provides a unified interface for authentication across suppliers.
    """
    
    def __init__(self, supplier_name: str, http_client: SupplierHTTPClient):
        self.supplier_name = supplier_name
        self.http_client = http_client
        self._authenticators: Dict[str, BaseAuthenticator] = {}
        self._current_authenticator: Optional[BaseAuthenticator] = None
    
    def register_api_key_auth(self, header_name: str = "X-API-Key") -> APIKeyAuthenticator:
        """Register API key authentication method"""
        auth = APIKeyAuthenticator(self.supplier_name, self.http_client, header_name)
        self._authenticators["api_key"] = auth
        return auth
    
    def register_oauth2_client_credentials(
        self,
        token_url: str,
        scope: Optional[str] = None
    ) -> OAuth2ClientCredentialsAuthenticator:
        """Register OAuth2 client credentials authentication method"""
        auth = OAuth2ClientCredentialsAuthenticator(
            self.supplier_name, self.http_client, token_url, scope
        )
        self._authenticators["oauth2_client_credentials"] = auth
        return auth
    
    def register_bearer_token_auth(self) -> BearerTokenAuthenticator:
        """Register Bearer token authentication method"""
        auth = BearerTokenAuthenticator(self.supplier_name, self.http_client)
        self._authenticators["bearer_token"] = auth
        return auth
    
    async def authenticate(self, auth_method: str, credentials: Dict[str, Any]) -> AuthResult:
        """Authenticate using specified method"""
        if auth_method not in self._authenticators:
            return AuthResult(
                success=False,
                error_message=f"Unknown authentication method: {auth_method}"
            )
        
        authenticator = self._authenticators[auth_method]
        result = await authenticator.authenticate(credentials)
        
        if result.success:
            self._current_authenticator = authenticator
            logger.info(f"Authentication successful for {self.supplier_name} using {auth_method}")
        else:
            logger.error(f"Authentication failed for {self.supplier_name} using {auth_method}: {result.error_message}")
        
        return result
    
    async def ensure_authenticated(self) -> bool:
        """Ensure current authentication is valid, refresh if necessary"""
        if not self._current_authenticator:
            return False
        
        if self._current_authenticator.is_authenticated():
            return True
        
        # Try to refresh token
        logger.info(f"Token expired for {self.supplier_name}, attempting refresh")
        refresh_result = await self._current_authenticator.refresh_token()
        
        if refresh_result.success:
            logger.info(f"Token refresh successful for {self.supplier_name}")
            return True
        else:
            logger.error(f"Token refresh failed for {self.supplier_name}: {refresh_result.error_message}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests"""
        if not self._current_authenticator:
            return {}
        return self._current_authenticator.get_auth_headers()
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        if not self._current_authenticator:
            return False
        return self._current_authenticator.is_authenticated()
    
    def get_current_token(self) -> Optional[AuthToken]:
        """Get current authentication token"""
        if not self._current_authenticator:
            return None
        return self._current_authenticator.get_current_token()


# ========== Common Authentication Patterns ==========

async def test_connection_with_auth(
    http_client: SupplierHTTPClient,
    auth_manager: AuthenticationManager,
    test_url: str,
    expected_indicators: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Common pattern for testing API connection with authentication.
    
    Args:
        http_client: HTTP client instance
        auth_manager: Authentication manager
        test_url: URL to test connection against
        expected_indicators: List of strings that should be in successful response
        
    Returns:
        Dictionary with success status, message, and details
    """
    try:
        # Ensure we're authenticated
        if not await auth_manager.ensure_authenticated():
            return {
                "success": False,
                "message": "Authentication required but failed",
                "details": {"error": "Authentication failed"}
            }
        
        # Get auth headers
        auth_headers = auth_manager.get_auth_headers()
        
        # Make test request
        response = await http_client.get(
            test_url,
            endpoint_type="test_connection",
            headers=auth_headers
        )
        
        if not response.success:
            return {
                "success": False,
                "message": f"Connection test failed with status {response.status}",
                "details": {
                    "status_code": response.status,
                    "error": response.error_message,
                    "url": test_url
                }
            }
        
        # Check for expected indicators in response
        if expected_indicators:
            response_text = json.dumps(response.data).lower()
            found_indicators = [
                indicator for indicator in expected_indicators
                if indicator.lower() in response_text
            ]
            
            if found_indicators:
                return {
                    "success": True,
                    "message": f"Connection successful. Found indicators: {', '.join(found_indicators)}",
                    "details": {
                        "status_code": response.status,
                        "indicators_found": found_indicators,
                        "response_data": response.data
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection succeeded but expected indicators not found: {', '.join(expected_indicators)}",
                    "details": {
                        "status_code": response.status,
                        "expected_indicators": expected_indicators,
                        "response_data": response.data
                    }
                }
        
        # No specific indicators to check for
        return {
            "success": True,
            "message": f"Connection test successful (HTTP {response.status})",
            "details": {
                "status_code": response.status,
                "response_data": response.data
            }
        }
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {
            "success": False,
            "message": f"Connection test error: {str(e)}",
            "details": {"error": str(e), "exception_type": type(e).__name__}
        }


async def make_authenticated_request(
    http_client: SupplierHTTPClient,
    auth_manager: AuthenticationManager,
    method: str,
    url: str,
    endpoint_type: str = "api_call",
    **kwargs
) -> HTTPResponse:
    """
    Common pattern for making authenticated HTTP requests.
    
    Ensures authentication is valid before making the request.
    """
    # Ensure authentication
    if not await auth_manager.ensure_authenticated():
        from ..suppliers.exceptions import SupplierAuthenticationError
        raise SupplierAuthenticationError(
            f"Authentication required for {http_client.supplier_name}",
            supplier_name=http_client.supplier_name
        )
    
    # Add auth headers
    auth_headers = auth_manager.get_auth_headers()
    existing_headers = kwargs.get("headers", {})
    kwargs["headers"] = {**existing_headers, **auth_headers}
    
    # Make request using appropriate method
    if method.upper() == "GET":
        return await http_client.get(url, endpoint_type, **kwargs)
    elif method.upper() == "POST":
        return await http_client.post(url, endpoint_type, **kwargs)
    elif method.upper() == "PUT":
        return await http_client.put(url, endpoint_type, **kwargs)
    elif method.upper() == "DELETE":
        return await http_client.delete(url, endpoint_type, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")