"""
DigiKey Supplier Implementation

Implements the DigiKey API interface using OAuth2 authentication.
Supports part search, pricing, stock, datasheets, and images.
"""

import os
import json
import base64
import logging
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
    PartSearchResult, SupplierInfo, ConfigurationOption,
    CapabilityRequirement, ImportResult
)
from .registry import register_supplier
from .exceptions import (
    SupplierError, SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

logger = logging.getLogger(__name__)

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
            supports_oauth=True,  # DigiKey requires OAuth for production API access
            rate_limit_info="1000 requests per hour for authenticated users",
            supports_multiple_environments=True,  # Supports both sandbox and production modes
            supported_file_types=["csv", "xls", "xlsx"]  # DigiKey supports CSV and Excel order exports
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        """Get capabilities that DigiKey API supports"""
        base_capabilities = [
            SupplierCapability.SEARCH_PARTS,
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_IMAGE,
            SupplierCapability.FETCH_PRICING,
            SupplierCapability.FETCH_STOCK,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.IMPORT_ORDERS  # CSV order import doesn't need API
        ]
        
        # Only return API capabilities if the digikey-api library is available
        if DIGIKEY_API_AVAILABLE:
            return base_capabilities
        else:
            # If the library is not available, we can still import CSVs
            return [SupplierCapability.IMPORT_ORDERS]
    
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Define what credentials each capability needs"""
        return {
            SupplierCapability.IMPORT_ORDERS: CapabilityRequirement(
                capability=SupplierCapability.IMPORT_ORDERS,
                required_credentials=[],  # No API key needed for CSV import
                description="Import DigiKey order history from CSV exports"
            ),
            SupplierCapability.SEARCH_PARTS: CapabilityRequirement(
                capability=SupplierCapability.SEARCH_PARTS,
                required_credentials=["client_id", "client_secret"],
                description="Search DigiKey catalog using API"
            ),
            SupplierCapability.GET_PART_DETAILS: CapabilityRequirement(
                capability=SupplierCapability.GET_PART_DETAILS,
                required_credentials=["client_id", "client_secret"],
                description="Get detailed part information from API"
            ),
            SupplierCapability.FETCH_DATASHEET: CapabilityRequirement(
                capability=SupplierCapability.FETCH_DATASHEET,
                required_credentials=["client_id", "client_secret"],
                description="Download datasheets via API"
            ),
            SupplierCapability.FETCH_IMAGE: CapabilityRequirement(
                capability=SupplierCapability.FETCH_IMAGE,
                required_credentials=["client_id", "client_secret"],
                description="Get product images via API"
            ),
            SupplierCapability.FETCH_PRICING: CapabilityRequirement(
                capability=SupplierCapability.FETCH_PRICING,
                required_credentials=["client_id", "client_secret"],
                description="Get real-time pricing via API"
            ),
            SupplierCapability.FETCH_STOCK: CapabilityRequirement(
                capability=SupplierCapability.FETCH_STOCK,
                required_credentials=["client_id", "client_secret"],
                description="Get real-time stock levels via API"
            ),
            SupplierCapability.FETCH_SPECIFICATIONS: CapabilityRequirement(
                capability=SupplierCapability.FETCH_SPECIFICATIONS,
                required_credentials=["client_id", "client_secret"],
                description="Get technical specifications via API"
            )
        }
    
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
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """
        Default configuration schema - returns empty list since we use get_configuration_options() instead.
        This method is kept for abstract class compliance.
        """
        return []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """
        Return both sandbox and production configuration options for DigiKey.
        Frontend will show both options and let user choose.
        """
        return [
            ConfigurationOption(
                name='sandbox',
                label='DigiKey Sandbox (Test Data)',
                description='Simple API key authentication for testing with sample data. No OAuth2 setup required.',
                schema=[
                    FieldDefinition(
                        name="api_environment",
                        label="API Environment",
                        field_type=FieldType.HIDDEN,
                        required=True,
                        default_value="sandbox",
                        description="Set to sandbox mode"
                    ),
                    FieldDefinition(
                        name="sandbox_info",
                        label="Sandbox Information",
                        field_type=FieldType.INFO,
                        required=False,
                        description="Sandbox mode uses simple authentication",
                        help_text="Your DigiKey sandbox app credentials will be used directly as API keys. No OAuth2 flow required."
                    )
                ],
                is_default=True,  # Sandbox is easier to set up, so make it default
                requirements={
                    'oauth_setup_required': False,
                    'complexity': 'low',
                    'data_type': 'test_data'
                }
            ),
            ConfigurationOption(
                name='production',
                label='DigiKey Production (Live Data)',
                description='OAuth2 authentication for accessing live inventory data. Requires OAuth2 app setup.',
                schema=[
                    FieldDefinition(
                        name="api_environment",
                        label="API Environment", 
                        field_type=FieldType.HIDDEN,
                        required=True,
                        default_value="production",
                        description="Set to production mode"
                    ),
                    FieldDefinition(
                        name="oauth_callback_url",
                        label="OAuth Callback URL",
                        field_type=FieldType.URL,
                        required=True,
                        default_value="https://localhost:8139/digikey_callback",
                        description="OAuth redirect URI for DigiKey Production API",
                        help_text="Use this EXACT URL in your DigiKey app settings: https://localhost:8139/digikey_callback",
                        validation={'pattern': r'^https?://.*'}
                    ),
                    FieldDefinition(
                        name="storage_path",
                        label="Token Storage Directory",
                        field_type=FieldType.TEXT,
                        required=False,
                        default_value="./digikey_tokens",
                        description="Directory to store OAuth tokens",
                        help_text="Directory path where access/refresh tokens will be stored (must be a directory, not a file)",
                        validation={'min_length': 1}
                    ),
                    FieldDefinition(
                        name="production_info",
                        label="Production Requirements",
                        field_type=FieldType.INFO,
                        required=False,
                        description="Production mode requires OAuth2 setup",
                        help_text="You'll need to complete OAuth2 authentication flow on first use. Tokens will be stored securely for future use."
                    )
                ],
                is_default=False,
                requirements={
                    'oauth_setup_required': True,
                    'complexity': 'high',
                    'data_type': 'live_data',
                    'prerequisites': ['DigiKey developer account', 'OAuth2 app registration']
                }
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
        """Authenticate based on configured environment (sandbox vs production)"""
        if not self.is_configured():
            raise SupplierConfigurationError(
                "DigiKey supplier not configured. Please provide client_id and client_secret.", 
                supplier_name="digikey",
                details={'missing_config': ['client_id', 'client_secret']}
            )
        
        # Validate required credentials
        client_id = self._credentials.get('client_id', '').strip()
        client_secret = self._credentials.get('client_secret', '').strip()
        
        if not client_id or not client_secret:
            raise SupplierConfigurationError(
                "DigiKey requires both client_id and client_secret",
                supplier_name="digikey",
                details={
                    'missing_credentials': [
                        field for field in ['client_id', 'client_secret'] 
                        if not self._credentials.get(field, '').strip()
                    ]
                }
            )
        
        api_environment = self._config.get('api_environment', 'sandbox')
        
        try:
            # Set basic environment variables that the digikey library expects
            os.environ['DIGIKEY_CLIENT_ID'] = client_id
            os.environ['DIGIKEY_CLIENT_SECRET'] = client_secret
            os.environ['DIGIKEY_CLIENT_SANDBOX'] = str(api_environment == 'sandbox')
            
            if api_environment == 'sandbox':
                # Sandbox mode: Simple API key authentication, no OAuth2 required
                print("DigiKey: Using sandbox mode with simple API key authentication")
                return await self._authenticate_sandbox()
            else:
                # Production mode: Full OAuth2 flow required
                print("DigiKey: Using production mode with OAuth2 authentication")
                return await self._authenticate_production()
                
        except SupplierError:
            # Re-raise supplier errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise SupplierAuthenticationError(
                f"DigiKey authentication failed: {str(e)}",
                supplier_name="digikey",
                details={
                    'api_environment': api_environment,
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )
    
    async def _authenticate_sandbox(self) -> bool:
        """Simple authentication for sandbox environment"""
        try:
            # For sandbox, we just need to verify credentials are provided
            client_id = self._credentials.get('client_id', '').strip()
            client_secret = self._credentials.get('client_secret', '').strip()
            
            if not client_id or not client_secret:
                raise SupplierAuthenticationError(
                    "DigiKey sandbox requires both client_id and client_secret. "
                    "Get these from your DigiKey sandbox app in the developer portal.",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'sandbox',
                        'required_fields': ['client_id', 'client_secret'],
                        'help_url': 'https://developer.digikey.com'
                    }
                )
            
            # Validate credential format (basic sanity check)
            if len(client_id) < 8 or len(client_secret) < 16:
                raise SupplierAuthenticationError(
                    "DigiKey credentials appear to be invalid (too short). "
                    "Please verify your client_id and client_secret from the DigiKey developer portal.",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'sandbox',
                        'client_id_length': len(client_id),
                        'client_secret_length': len(client_secret),
                        'help_url': 'https://developer.digikey.com'
                    }
                )
            
            # No additional setup needed for sandbox - credentials are used directly as API keys
            print("DigiKey sandbox authentication configured successfully")
            return True
            
        except SupplierError:
            raise
        except Exception as e:
            raise SupplierAuthenticationError(
                f"DigiKey sandbox authentication setup failed: {str(e)}",
                supplier_name="digikey",
                details={
                    'api_environment': 'sandbox',
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )
    
    async def _authenticate_production(self) -> bool:
        """OAuth2 authentication for production environment"""
        try:
            if not DIGIKEY_API_AVAILABLE:
                raise SupplierConfigurationError(
                    "DigiKey API library not available for production mode. "
                    "Install with: pip install digikey-api",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'production',
                        'missing_dependency': 'digikey-api',
                        'install_command': 'pip install digikey-api',
                        'help_url': 'https://github.com/peeter123/digikey-api'
                    }
                )
            
            # Validate production-specific configuration
            oauth_callback_url = self._config.get('oauth_callback_url', '').strip()
            if not oauth_callback_url:
                raise SupplierConfigurationError(
                    "DigiKey production mode requires oauth_callback_url. "
                    "This must match the redirect URI in your DigiKey app settings.",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'production',
                        'missing_config': ['oauth_callback_url'],
                        'default_value': 'https://localhost:8139/digikey_callback',
                        'help_url': 'https://developer.digikey.com'
                    }
                )
            
            # Validate callback URL format
            if not oauth_callback_url.startswith(('http://', 'https://')):
                raise SupplierConfigurationError(
                    "oauth_callback_url must be a valid URL starting with http:// or https://",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'production',
                        'invalid_url': oauth_callback_url,
                        'required_format': 'https://your-domain.com/callback'
                    }
                )
            
            # Ensure storage path exists as a directory for OAuth2 tokens
            storage_path = self._config.get('storage_path', './digikey_tokens')
            
            # If it ends with .json, treat it as a file and use its directory
            if storage_path.endswith('.json'):
                storage_dir = os.path.dirname(storage_path) or '.'
            else:
                storage_dir = storage_path
            
            # Create the directory if it doesn't exist
            try:
                os.makedirs(storage_dir, exist_ok=True)
            except OSError as e:
                raise SupplierConfigurationError(
                    f"Cannot create token storage directory: {storage_dir}",
                    supplier_name="digikey",
                    details={
                        'api_environment': 'production',
                        'storage_path': storage_dir,
                        'os_error': str(e),
                        'suggested_path': './digikey_tokens'
                    }
                )
            
            # Set the storage path environment variable to the directory
            abs_storage_dir = os.path.abspath(storage_dir)
            os.environ['DIGIKEY_STORAGE_PATH'] = abs_storage_dir
            
            print(f"DigiKey production OAuth2 storage path: {abs_storage_dir}")
            
            # The actual OAuth2 flow will be handled by the digikey library on first API call
            return True
            
        except SupplierError:
            raise
        except Exception as e:
            raise SupplierAuthenticationError(
                f"DigiKey production authentication setup failed: {str(e)}",
                supplier_name="digikey",
                details={
                    'api_environment': 'production',
                    'error_type': type(e).__name__,
                    'original_error': str(e),
                    'help_url': 'https://developer.digikey.com'
                }
            )
    
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
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific part using DigiKey API"""
        async def _impl():
            if not await self.authenticate():
                raise SupplierAuthenticationError("Authentication required", supplier_name="digikey")
            
            if not DIGIKEY_API_AVAILABLE:
                raise SupplierConfigurationError("DigiKey API library not available", supplier_name="digikey")
            
            try:
                from digikey.v3.productinformation import ProductDetailsRequest
                
                # Get detailed product information
                details_request = ProductDetailsRequest(part=supplier_part_number)
                result = digikey.product_details(body=details_request)
                
                if result and result.product:
                    product = result.product
                    return PartSearchResult(
                        supplier_part_number=product.digi_key_part_number or "",
                        manufacturer=product.manufacturer.value if product.manufacturer else "",
                        manufacturer_part_number=product.manufacturer_part_number or "",
                        description=product.product_description or "",
                        category=product.category.value if product.category else "",
                        datasheet_url=product.primary_datasheet or "",
                        image_url=product.primary_photo or "",
                        stock_quantity=product.quantity_available or 0,
                        pricing=self._extract_pricing(product),
                        specifications=self._extract_specifications(product),
                        additional_data={
                            "detailed_description": product.detailed_description,
                            "series": product.series.value if product.series else "",
                            "packaging": product.packaging.value if product.packaging else "",
                            "unit_price": product.unit_price,
                            "minimum_quantity": product.minimum_quantity,
                            "standard_package": product.standard_package
                        }
                    )
                else:
                    return None
                    
            except Exception as e:
                raise SupplierConnectionError(f"DigiKey part details failed: {str(e)}", supplier_name="digikey")
        
        return await self._tracked_api_call("get_part_details", _impl)
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.image_url if part_details else None
        
        return await self._tracked_api_call("fetch_image", _impl)
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.pricing if part_details else None
        
        return await self._tracked_api_call("fetch_pricing", _impl)
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Fetch current stock level for a part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.stock_quantity if part_details else None
        
        return await self._tracked_api_call("fetch_stock", _impl)
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.specifications if part_details else None
        
        return await self._tracked_api_call("fetch_specifications", _impl)
    
    def _extract_pricing(self, product) -> List[Dict[str, Any]]:
        """Extract pricing information from DigiKey product data"""
        pricing = []
        if hasattr(product, 'standard_pricing') and product.standard_pricing:
            for price_break in product.standard_pricing:
                pricing.append({
                    "quantity": price_break.break_quantity,
                    "price": float(price_break.unit_price),
                    "currency": "USD"  # DigiKey typically uses USD
                })
        return pricing
    
    def _extract_specifications(self, product) -> Dict[str, Any]:
        """Extract specifications from DigiKey product data"""
        specs = {}
        if hasattr(product, 'parameters') and product.parameters:
            for param in product.parameters:
                if param.parameter and param.value:
                    specs[param.parameter] = param.value
        return specs
    
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
    
    # ========== Order Import Implementation ==========
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this is a DigiKey CSV or Excel file"""
        filename_lower = filename.lower()
        
        # Check file extension
        supported_extensions = ['.csv', '.xls', '.xlsx']
        if not any(filename_lower.endswith(ext) for ext in supported_extensions):
            return False
        
        # Check filename patterns
        digikey_patterns = ['digikey', 'digi-key', 'weborder', 'salesorder', 'dk_products']
        if any(pattern in filename_lower for pattern in digikey_patterns):
            return True
        
        # Check content for DigiKey-specific patterns
        if file_content:
            try:
                # For Excel files, try to read first sheet
                if filename_lower.endswith(('.xls', '.xlsx')):
                    try:
                        import pandas as pd
                        import io
                        df = pd.read_excel(io.BytesIO(file_content), nrows=5)  # Read first 5 rows
                        
                        # Check column headers for DigiKey patterns
                        if not df.empty:
                            headers = ' '.join(str(col).lower() for col in df.columns)
                            digikey_indicators = [
                                'digi-key part number', 'digikey part', 'customer reference',
                                'manufacturer part number', 'part number', 'quantity'
                            ]
                            if any(indicator in headers for indicator in digikey_indicators):
                                return True
                    except Exception as e:
                        logger.debug(f"Error reading Excel file for DigiKey detection: {e}")
                
                # For CSV files, check text content
                else:
                    content_str = file_content.decode('utf-8', errors='ignore')[:2000]  # Check first 2KB
                    # Look for DigiKey-specific headers
                    digikey_indicators = [
                        'Digi-Key Part Number',
                        'Manufacturer Part Number',
                        'Customer Reference',
                        'DigiKey Part #',
                        'Index,Quantity,Part Number,Manufacturer Part Number'
                    ]
                    return any(indicator in content_str for indicator in digikey_indicators)
            except Exception as e:
                logger.debug(f"Error checking DigiKey file content: {e}")
        
        return False
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import DigiKey order CSV or Excel file"""
        file_type_lower = file_type.lower()
        
        if file_type_lower not in ['csv', 'xls', 'xlsx']:
            return ImportResult(
                success=False,
                error_message=f"DigiKey supports CSV and Excel files, not {file_type}"
            )
        
        try:
            # Convert Excel files to CSV format for processing
            if file_type_lower in ['xls', 'xlsx']:
                try:
                    import pandas as pd
                    import io
                    
                    # Read Excel file
                    df = pd.read_excel(io.BytesIO(file_content))
                    
                    # Convert to CSV string
                    csv_content = df.to_csv(index=False)
                    content_str = csv_content
                    
                except Exception as e:
                    return ImportResult(
                        success=False,
                        error_message=f"Failed to read Excel file: {str(e)}"
                    )
            else:
                # Handle CSV files
                content_str = file_content.decode('utf-8')
            
            # Parse CSV content
            import csv
            import io
            
            csv_reader = csv.DictReader(io.StringIO(content_str))
            
            parts = []
            errors = []
            
            # Try to detect CSV format
            headers = csv_reader.fieldnames or []
            
            # Format 1: Standard DigiKey export
            if 'Digi-Key Part Number' in headers:
                for row in csv_reader:
                    try:
                        part = {
                            'part_name': row.get('Description', row.get('Manufacturer Part Number', '')).strip(),
                            'supplier_part_number': row.get('Digi-Key Part Number', '').strip(),
                            'manufacturer': row.get('Manufacturer', '').strip(),
                            'manufacturer_part_number': row.get('Manufacturer Part Number', '').strip(),
                            'description': row.get('Description', '').strip(),
                            'quantity': int(row.get('Quantity', 0)),
                            'unit_price': float(row.get('Unit Price', '0').replace('$', '').replace(',', '')),
                            'extended_price': float(row.get('Extended Price', '0').replace('$', '').replace(',', '')),
                            'supplier': 'DigiKey',
                            'additional_properties': {
                                'customer_reference': row.get('Customer Reference', ''),
                                'backorder': row.get('Backorder', ''),
                                'index': row.get('Index', '')
                            }
                        }
                        if part['supplier_part_number']:
                            parts.append(part)
                    except Exception as e:
                        errors.append(f"Error parsing row: {str(e)}")
            
            # Format 2: Alternative format
            elif 'Part Number' in headers and 'Manufacturer Part Number' in headers:
                for row in csv_reader:
                    try:
                        part = {
                            'part_name': row.get('Description', row.get('Manufacturer Part Number', '')).strip(),
                            'supplier_part_number': row.get('Part Number', '').strip(),
                            'manufacturer': row.get('Manufacturer', '').strip(),
                            'manufacturer_part_number': row.get('Manufacturer Part Number', '').strip(),
                            'description': row.get('Description', '').strip(),
                            'quantity': int(row.get('Quantity', 0)),
                            'unit_price': float(row.get('Unit Price', '0').replace('$', '').replace(',', '')),
                            'extended_price': float(row.get('Extended Price', '0').replace('$', '').replace(',', '')),
                            'supplier': 'DigiKey',
                            'additional_properties': {
                                'customer_reference': row.get('Customer Reference', '')
                            }
                        }
                        if part['supplier_part_number']:
                            parts.append(part)
                    except Exception as e:
                        errors.append(f"Error parsing row: {str(e)}")
            else:
                return ImportResult(
                    success=False,
                    error_message="Unrecognized DigiKey CSV format",
                    warnings=[f"Headers found: {', '.join(headers[:10])}"]
                )
            
            if not parts:
                return ImportResult(
                    success=False,
                    error_message="No valid parts found in CSV",
                    warnings=errors
                )
            
            return ImportResult(
                success=True,
                imported_count=len(parts),
                parts=parts,
                parser_type='digikey',
                warnings=errors if errors else []
            )
            
        except Exception as e:
            import traceback
            return ImportResult(
                success=False,
                error_message=f"Error importing DigiKey CSV: {str(e)}",
                warnings=[traceback.format_exc()]
            )
    
    def get_import_file_preview(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """Get preview of DigiKey CSV import"""
        try:
            import csv
            import io
            
            content_str = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content_str))
            
            headers = csv_reader.fieldnames or []
            preview_rows = []
            
            # Get first 5 rows for preview
            for i, row in enumerate(csv_reader):
                if i >= 5:
                    break
                preview_rows.append(dict(row))
            
            # Count total rows
            total_rows = len(preview_rows)
            for _ in csv_reader:
                total_rows += 1
            
            return {
                "headers": headers,
                "preview_rows": preview_rows,
                "total_rows": total_rows,
                "detected_supplier": "digikey",
                "is_supported": True
            }
            
        except Exception as e:
            return {
                "headers": [],
                "preview_rows": [],
                "total_rows": 0,
                "detected_supplier": "digikey",
                "is_supported": False,
                "error": str(e)
            }