"""
DigiKey Supplier Implementation

Implements the DigiKey API interface using OAuth2 authentication.
Supports part search, pricing, stock, datasheets, and images.
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp

# Import the official DigiKey API library
try:
    import digikey
    DIGIKEY_API_AVAILABLE = True
except ImportError:
    digikey = None
    DIGIKEY_API_AVAILABLE = False
    print("Warning: digikey-api package not available. Install with: pip install digikey-api")

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability, 
    PartSearchResult, SupplierInfo
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

@register_supplier("digikey")
class DigiKeySupplier(BaseSupplier):
    """DigiKey supplier implementation with OAuth2 support"""
    
    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token: Optional[str] = None
        
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="digikey",
            display_name="DigiKey Electronics",
            description="Global electronic components distributor with comprehensive inventory and fast shipping",
            website_url="https://www.digikey.com",
            api_documentation_url="https://developer.digikey.com",
            supports_oauth=True,  # DigiKey requires OAuth for all API access
            rate_limit_info="1000 requests per hour for authenticated users"
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.SEARCH_PARTS,
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_IMAGE,
            SupplierCapability.FETCH_PRICING,
            SupplierCapability.FETCH_STOCK,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.BULK_SEARCH,
            SupplierCapability.PARAMETRIC_SEARCH
        ]
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="client_id",
                label="Client ID",
                field_type=FieldType.TEXT,
                required=True,
                description="OAuth2 Client ID from DigiKey developer portal",
                help_text="Get this from https://developer.digikey.com after registering your application"
            ),
            FieldDefinition(
                name="client_secret",
                label="Client Secret",
                field_type=FieldType.PASSWORD,
                required=True,
                description="OAuth2 Client Secret from DigiKey developer portal",
                help_text="Keep this secret secure - never share it publicly"
            )
        ]
    
    def get_configuration_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_environment",
                label="API Environment",
                field_type=FieldType.SELECT,
                required=True,
                default_value="production",
                description="Choose DigiKey API environment",
                help_text="Production: Real data, live inventory. Sandbox: Test data for development.",
                options=[
                    {"value": "production", "label": "Production (Live Data)"},
                    {"value": "sandbox", "label": "Sandbox (Test Data)"}
                ]
            ),
            FieldDefinition(
                name="oauth_callback_url",
                label="OAuth Callback URL",
                field_type=FieldType.URL,
                required=True,
                default_value="https://localhost:8139/digikey_callback",
                description="OAuth redirect URI for DigiKey",
                help_text="Use this EXACT URL in your DigiKey app settings: https://localhost:8139/digikey_callback"
            ),
            FieldDefinition(
                name="storage_path",
                label="Token Storage Directory",
                field_type=FieldType.TEXT,
                required=False,
                default_value="./digikey_tokens",
                description="Directory to store OAuth tokens",
                help_text="Directory path where access/refresh tokens will be stored (must be a directory, not a file)"
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get base URL based on API environment"""
        api_environment = self._config.get("api_environment", "production")
        if api_environment == "sandbox":
            return "https://sandbox-api.digikey.com"
        else:
            return "https://api.digikey.com"
    
    def _get_auth_url(self) -> str:
        """Get authorization URL based on API environment"""  
        api_environment = self._config.get("api_environment", "production")
        if api_environment == "sandbox":
            return "https://sandbox-api.digikey.com/v1/oauth2/authorize"
        else:
            return "https://api.digikey.com/v1/oauth2/authorize"
    
    def _get_token_url(self) -> str:
        """Get token URL based on API environment"""
        api_environment = self._config.get("api_environment", "production")
        if api_environment == "sandbox":
            return "https://sandbox-api.digikey.com/v1/oauth2/token"
        else:
            return "https://api.digikey.com/v1/oauth2/token"
    
    async def authenticate(self) -> bool:
        """Authenticate using the official DigiKey API library"""
        if not self.is_configured():
            raise SupplierConfigurationError("Supplier not configured", supplier_name="digikey")
        
        if not DIGIKEY_API_AVAILABLE:
            raise SupplierConfigurationError("DigiKey API library not available", supplier_name="digikey")
        
        try:
            # Set environment variables that the digikey library expects
            os.environ['DIGIKEY_CLIENT_ID'] = self._credentials.get('client_id', '')
            os.environ['DIGIKEY_CLIENT_SECRET'] = self._credentials.get('client_secret', '')
            
            # Convert api_environment to boolean for DIGIKEY_CLIENT_SANDBOX
            api_environment = self._config.get('api_environment', 'production')
            os.environ['DIGIKEY_CLIENT_SANDBOX'] = str(api_environment == 'sandbox')
            
            # Ensure storage path exists as a directory
            storage_path = self._config.get('storage_path', './digikey_tokens')
            
            # If it ends with .json, treat it as a file and use its directory
            if storage_path.endswith('.json'):
                storage_dir = os.path.dirname(storage_path) or '.'
            else:
                storage_dir = storage_path
            
            # Create the directory if it doesn't exist
            os.makedirs(storage_dir, exist_ok=True)
            
            # Set the storage path environment variable to the directory
            os.environ['DIGIKEY_STORAGE_PATH'] = os.path.abspath(storage_dir)
            
            print(f"DigiKey storage path set to: {os.environ['DIGIKEY_STORAGE_PATH']}")
            
            # Test authentication by making a simple API call
            # The digikey library will handle OAuth flow automatically
            return True  # We'll test the actual connection in test_connection
            
        except Exception as e:
            print(f"DigiKey authentication setup failed: {e}")
            return False
    
    async def _authenticate_client_credentials(self) -> bool:
        """Authenticate using client credentials grant (no redirect needed)"""
        try:
            client_id = self._credentials.get("client_id")
            client_secret = self._credentials.get("client_secret")
            
            if not client_id or not client_secret:
                return False
            
            token_url = self._get_token_url()
            
            # Client credentials flow
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = await self._session.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            self._token_type = token_data.get("token_type", "Bearer")
            
            # Store token
            await self._store_tokens(token_data)
            
            return bool(self._access_token)
            
        except Exception as e:
            print(f"Client credentials authentication failed: {e}")
            # If this is an HTTP error, log more details
            if hasattr(e, 'response'):
                try:
                    error_details = e.response.json()
                    print(f"DigiKey API error details: {error_details}")
                except:
                    print(f"DigiKey API error status: {e.response.status_code}")
                    print(f"DigiKey API error text: {e.response.text}")
            return False
    
    async def _authenticate_oauth(self) -> bool:
        """Authenticate using OAuth2 authorization code flow"""
        # Try to load existing tokens first
        if await self._load_stored_tokens():
            if await self._is_token_valid():
                return True
            elif self._refresh_token:
                return await self._refresh_access_token()
        
        # If no valid tokens, need to start OAuth flow
        # This would typically be handled by a separate OAuth flow endpoint
        return False
    
    async def _load_stored_tokens(self) -> bool:
        """Load stored OAuth tokens from file"""
        storage_path = self._config.get("storage_path", "./digikey_tokens.json")
        try:
            if os.path.exists(storage_path):
                with open(storage_path, 'r') as f:
                    tokens = json.load(f)
                    self._access_token = tokens.get("access_token")
                    self._refresh_token = tokens.get("refresh_token")
                    expires_at_str = tokens.get("expires_at")
                    if expires_at_str:
                        self._token_expires_at = datetime.fromisoformat(expires_at_str)
                    return True
        except Exception:
            pass
        return False
    
    async def _save_tokens(self):
        """Save OAuth tokens to file"""
        storage_path = self._config.get("storage_path", "./digikey_tokens.json")
        try:
            tokens = {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None
            }
            with open(storage_path, 'w') as f:
                json.dump(tokens, f)
        except Exception:
            pass
    
    async def _is_token_valid(self) -> bool:
        """Check if current access token is valid"""
        if not self._access_token or not self._token_expires_at:
            return False
        return datetime.now() < self._token_expires_at
    
    async def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self._refresh_token:
            return False
        
        session = await self._get_session()
        
        # Prepare basic auth header
        client_id = self._credentials.get("client_id")
        client_secret = self._credentials.get("client_secret")
        auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token
        }
        
        try:
            async with session.post(self._get_token_url(), headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    await self._save_tokens()
                    return True
                else:
                    return False
        except Exception:
            return False
    
    def get_oauth_authorization_url(self) -> str:
        """Get OAuth authorization URL for initial setup"""
        client_id = self._credentials.get("client_id")
        callback_url = self._config.get("oauth_callback_url")
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": callback_url,
            "scope": "read"
        }
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self._get_auth_url()}?{param_string}"
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> bool:
        """Exchange authorization code for access/refresh tokens"""
        session = await self._get_session()
        
        client_id = self._credentials.get("client_id")
        client_secret = self._credentials.get("client_secret")
        callback_url = self._config.get("oauth_callback_url")
        
        # Prepare basic auth header
        auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": callback_url
        }
        
        try:
            async with session.post(self._get_token_url(), headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._access_token = token_data.get("access_token")
                    self._refresh_token = token_data.get("refresh_token")
                    expires_in = token_data.get("expires_in", 3600)
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    await self._save_tokens()
                    return True
                else:
                    error_data = await response.text()
                    raise SupplierAuthenticationError(
                        f"Token exchange failed: {error_data}",
                        supplier_name="digikey"
                    )
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(
                f"Connection error during token exchange: {str(e)}",
                supplier_name="digikey"
            )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to DigiKey API using the official library"""
        try:            
            if not await self.authenticate():
                return {
                    "success": False,
                    "message": "Authentication setup failed",
                    "details": {"error": "Failed to set up DigiKey authentication"}
                }
            
            if not DIGIKEY_API_AVAILABLE:
                return {
                    "success": False,
                    "message": "DigiKey API library not available",
                    "details": {"error": "Install digikey-api package"}
                }
            
            # Test the DigiKey API using the official library
            try:
                # Try a simple keyword search to test authentication
                from digikey.v3.productinformation import KeywordSearchRequest
                
                search_request = KeywordSearchRequest(keywords='capacitor', record_count=1)
                result = digikey.keyword_search(body=search_request)
                
                return {
                    "success": True,
                    "message": "Connection successful",
                    "details": {
                        "api_library": "digikey-api",
                        "api_environment": self._config.get("api_environment", "production"),
                        "products_found": len(result.products) if result and result.products else 0,
                        "test_search": "capacitor"
                    }
                }
                
            except Exception as api_error:
                # Check if this is a browser/display related error (headless environment)
                error_str = str(api_error).lower()
                if "xdg-settings" in error_str or "no such device" in error_str or "display" in error_str:
                    # Generate manual OAuth URL for headless environments
                    oauth_url = self._generate_oauth_url()
                    return {
                        "success": False,
                        "message": "Manual OAuth required - No browser available",
                        "details": {
                            "error": "Running in headless environment (WSL2/server)",
                            "oauth_url": oauth_url,
                            "instructions": "1. Open the OAuth URL above in your browser\n2. Complete the authorization\n3. Copy the authorization code from the callback URL\n4. Use the code to complete authentication"
                        }
                    }
                elif "oauth" in error_str or "authentication" in error_str or "authorize" in error_str:
                    return {
                        "success": False,
                        "message": "OAuth authentication required",
                        "details": {
                            "error": str(api_error),
                            "oauth_url": self._generate_oauth_url(),
                            "instructions": "Complete OAuth authentication using the URL above"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"API call failed: {str(api_error)}",
                        "details": {"error": str(api_error)}
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using DigiKey API"""
        if not await self.authenticate():
            raise SupplierAuthenticationError("Authentication required", supplier_name="digikey")
        
        if not DIGIKEY_API_AVAILABLE:
            raise SupplierConfigurationError("DigiKey API library not available", supplier_name="digikey")
        
        try:
            from digikey.v3.productinformation import KeywordSearchRequest
            
            # Use the official DigiKey API library
            search_request = KeywordSearchRequest(
                keywords=query,
                record_count=min(limit, 50),  # DigiKey max is 50
                record_start_position=0,
                sort={
                    "SortOption": "SortByQuantityAvailable",
                    "Direction": "Descending"
                }
            )
            
            result = digikey.keyword_search(body=search_request)
            
            # Convert DigiKey results to our standard format
            parts = []
            if result and result.products:
                for product in result.products:
                    part = PartSearchResult(
                        supplier_part_number=product.digi_key_part_number or "",
                        manufacturer=product.manufacturer.value if product.manufacturer else "",
                        manufacturer_part_number=product.manufacturer_part_number or "",
                        description=product.product_description or "",
                        category=product.category.value if product.category else "",
                        datasheet_url=product.primary_datasheet or "",
                        image_url=product.primary_photo or "",
                        stock_quantity=product.quantity_available or 0,
                        pricing=[],  # We'll fetch pricing separately if needed
                        specifications={},  # We'll fetch specs separately if needed
                        additional_data={
                            "detailed_description": product.detailed_description,
                            "series": product.series.value if product.series else "",
                            "packaging": product.packaging.value if product.packaging else ""
                        }
                    )
                    parts.append(part)
            
            return parts
            
        except Exception as e:
            raise SupplierConnectionError(f"DigiKey search failed: {str(e)}", supplier_name="digikey")
    
    def _generate_oauth_url(self) -> str:
        """Generate OAuth authorization URL for manual authentication"""
        try:
            client_id = self._credentials.get('client_id', '')
            callback_url = self._config.get('oauth_callback_url', 'https://localhost:8139/digikey_callback')
            api_environment = self._config.get('api_environment', 'production')
            
            if api_environment == "sandbox":
                auth_base = "https://sandbox-api.digikey.com/v1/oauth2/authorize"
            else:
                auth_base = "https://api.digikey.com/v1/oauth2/authorize"
            
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': callback_url,
                'scope': 'read'
            }
            
            from urllib.parse import urlencode
            return f"{auth_base}?{urlencode(params)}"
            
        except Exception as e:
            return f"Error generating OAuth URL: {str(e)}"
    
    def get_rate_limit_delay(self) -> float:
        """DigiKey rate limit: ~1000 requests/hour = ~3.6 seconds between requests"""
        return 4.0