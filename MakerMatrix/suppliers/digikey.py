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
import pandas as pd

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
from MakerMatrix.models.enrichment_requirement_models import (
    EnrichmentRequirements, FieldRequirement, RequirementSeverity
)
from .registry import register_supplier
from .exceptions import (
    SupplierError, SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)
from MakerMatrix.services.data.unified_column_mapper import UnifiedColumnMapper
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper

logger = logging.getLogger(__name__)

@register_supplier("digikey")
class DigiKeySupplier(BaseSupplier):
    """DigiKey supplier implementation with OAuth2 support"""
    
    # Class-level token cache to share tokens across instances
    _shared_access_token: Optional[str] = None
    _shared_token_expires_at: Optional[datetime] = None
    _shared_refresh_token: Optional[str] = None
    
    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._refresh_token: Optional[str] = None
    
    def _has_valid_cached_token(self) -> bool:
        """Check if we have a valid cached token that hasn't expired"""
        if not DigiKeySupplier._shared_access_token or not DigiKeySupplier._shared_token_expires_at:
            return False
        
        # Check if token expires within the next 30 seconds (buffer for API calls)
        from datetime import timedelta
        buffer_time = timedelta(seconds=30)
        return datetime.now() + buffer_time < DigiKeySupplier._shared_token_expires_at
    
    def _use_cached_token(self) -> None:
        """Copy cached token to instance variables"""
        self._access_token = DigiKeySupplier._shared_access_token
        self._token_expires_at = DigiKeySupplier._shared_token_expires_at
        self._refresh_token = DigiKeySupplier._shared_refresh_token
    
    def _cache_token(self, access_token: str, expires_in: int, refresh_token: Optional[str] = None) -> None:
        """Cache token at class level for reuse across instances"""
        DigiKeySupplier._shared_access_token = access_token
        DigiKeySupplier._shared_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        DigiKeySupplier._shared_refresh_token = refresh_token
        
        # Also set on instance
        self._access_token = access_token
        self._token_expires_at = DigiKeySupplier._shared_token_expires_at
        self._refresh_token = refresh_token
    
    def _normalize_url(self, url: str) -> str:
        """Normalize protocol-relative URLs to use HTTPS"""
        if not url:
            return ""
        if url.startswith("//"):
            return f"https:{url}"
        return url
        
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="digikey",
            display_name="DigiKey Electronics",
            description="Global electronic components distributor with comprehensive inventory and fast shipping",
            website_url="https://www.digikey.com",
            api_documentation_url="https://developer.digikey.com",
            supports_oauth=False,  # DigiKey uses client credentials (backend-only, no browser required)
            rate_limit_info="1000 requests per hour for authenticated users",
            supports_multiple_environments=True,  # Supports both sandbox and production modes
            supported_file_types=["csv", "xls", "xlsx"]  # DigiKey exports in CSV format but files may have Excel extensions
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        """Get capabilities that DigiKey supports (always returns full list, with fallbacks when API unavailable)"""
        return [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_PRICING_STOCK,
            SupplierCapability.IMPORT_ORDERS
        ]
    
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Define what credentials each capability needs"""
        return {
            SupplierCapability.IMPORT_ORDERS: CapabilityRequirement(
                capability=SupplierCapability.IMPORT_ORDERS,
                required_credentials=[],  # No API key needed for CSV import
                description="Import DigiKey order history from CSV exports"
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
            SupplierCapability.FETCH_PRICING_STOCK: CapabilityRequirement(
                capability=SupplierCapability.FETCH_PRICING_STOCK,
                required_credentials=["client_id", "client_secret"],
                description="Get real-time pricing and stock levels via API"
            ),
        }

    def get_enrichment_requirements(self) -> EnrichmentRequirements:
        """
        Define what part data is required for enrichment from DigiKey.

        DigiKey can search by either supplier_part_number (DigiKey part number)
        or manufacturer_part_number. Having both provides the best results.

        Returns:
            EnrichmentRequirements with required, recommended, and optional fields
        """
        return EnrichmentRequirements(
            supplier_name="digikey",
            display_name="DigiKey Electronics",
            description="DigiKey can enrich parts with detailed specifications, images, datasheets, pricing, and real-time stock levels using their comprehensive API",
            required_fields=[
                FieldRequirement(
                    field_name="supplier_part_number",
                    display_name="DigiKey Part Number",
                    severity=RequirementSeverity.REQUIRED,
                    description="The DigiKey part number (e.g., 296-1234-ND) is the most reliable way to look up parts in the DigiKey API. Either this OR manufacturer_part_number is required.",
                    example="296-1234-ND"
                )
            ],
            recommended_fields=[
                FieldRequirement(
                    field_name="manufacturer_part_number",
                    display_name="Manufacturer Part Number",
                    severity=RequirementSeverity.RECOMMENDED,
                    description="DigiKey can also search by manufacturer part number. This is recommended if you don't have the DigiKey part number, or as validation.",
                    example="STM32F103C8T6"
                ),
                FieldRequirement(
                    field_name="manufacturer",
                    display_name="Manufacturer Name",
                    severity=RequirementSeverity.RECOMMENDED,
                    description="Manufacturer name helps narrow down search results when using manufacturer part numbers",
                    example="STMicroelectronics"
                )
            ],
            optional_fields=[
                FieldRequirement(
                    field_name="description",
                    display_name="Part Description",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Existing description can help verify the enriched data matches your intended part",
                    example="ARM Cortex-M3 32-bit MCU"
                ),
                FieldRequirement(
                    field_name="component_type",
                    display_name="Component Type",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Component type helps organize enriched specifications and validate results",
                    example="Microcontroller"
                )
            ]
        )

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
        Get configuration schema for DigiKey supplier.
        Returns fields from the default configuration option for frontend compatibility.
        """
        # Get the default configuration option and return its schema fields
        config_options = self.get_configuration_options()
        default_option = next((opt for opt in config_options if opt.is_default), None)
        
        if default_option:
            return default_option.schema
        else:
            # Fallback to production option if no default found
            production_option = next((opt for opt in config_options if opt.name == 'production'), None)
            return production_option.schema if production_option else []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """
        Return production configuration for DigiKey.
        Only production mode is supported for access to live inventory data.
        """
        # Automatically detect server URL for callback
        server_url = self._get_server_url()
        callback_url = f"{server_url}/api/suppliers/digikey/oauth/callback"
        
        return [
            ConfigurationOption(
                name='production',
                label='DigiKey Production (Live Data)',
                description='OAuth2 authentication for accessing live DigiKey inventory data and APIs.',
                schema=[
                    FieldDefinition(
                        name="oauth_callback_url",
                        label="OAuth Callback URL",
                        field_type=FieldType.URL,
                        required=False,
                        default_value=callback_url,
                        description=f"OAuth redirect URI for DigiKey Production API (automatically detected: {callback_url})",
                        help_text=f"Use this EXACT URL in your DigiKey app settings: {callback_url}",
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
                        label="Setup Requirements",
                        field_type=FieldType.INFO,
                        required=False,
                        description="DigiKey production API requires OAuth2 setup",
                        help_text="You'll need to complete OAuth2 authentication flow on first use. Tokens will be stored securely for future use. Ensure your DigiKey app is configured for production use."
                    )
                ],
                is_default=True,
                requirements={
                    'oauth_setup_required': True,
                    'complexity': 'medium',
                    'data_type': 'live_data',
                    'prerequisites': ['DigiKey developer account', 'OAuth2 app registration', 'Production API access']
                }
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get base URL for DigiKey production API"""
        return "https://api.digikey.com"
    
    def _get_auth_url(self) -> str:
        """Get authorization URL for DigiKey production API"""  
        return "https://api.digikey.com/v1/oauth2/authorize"
    
    def _get_token_url(self) -> str:
        """Get token URL for DigiKey production API"""
        return "https://api.digikey.com/v1/oauth2/token"
    
    def _get_server_url(self) -> str:
        """Automatically detect the server URL for OAuth callbacks"""
        # Check if HTTPS is enabled
        https_enabled = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
        protocol = "https" if https_enabled else "http"
        
        # Get the server host and port
        # In production, you might want to use environment variables for this
        host = os.getenv("SERVER_HOST", "localhost")
        port = os.getenv("SERVER_PORT", "8443" if https_enabled else "8080")
        
        return f"{protocol}://{host}:{port}"
    
    def _get_http_client(self):
        """Get or create HTTP client with DigiKey-specific configuration"""
        if not hasattr(self, '_http_client') or not self._http_client:
            from .http_client import SupplierHTTPClient, RetryConfig
            
            config = self._config or {}
            
            # Configure for API usage with OAuth2 rate limiting
            rate_limit = config.get("rate_limit_requests_per_minute", 240)  # 4 requests per second default
            delay_seconds = 60.0 / max(rate_limit, 1)
            
            retry_config = RetryConfig(
                max_retries=3,
                base_delay=delay_seconds,
                max_delay=60.0,
                retry_on_status=[429, 500, 502, 503, 504]
            )
            
            # Set up default headers for OAuth2 API
            default_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            self._http_client = SupplierHTTPClient(
                supplier_name="digikey",
                default_headers=default_headers,
                default_timeout=config.get("request_timeout", 30),
                retry_config=retry_config
            )
        
        return self._http_client
    
    async def authenticate(self) -> bool:
        """Authenticate with DigiKey production API using cached tokens when possible"""
        # First check if we have a valid cached token
        if self._has_valid_cached_token():
            logger.debug("DigiKey: Using cached access token (valid for %s more seconds)", 
                        int((DigiKeySupplier._shared_token_expires_at - datetime.now()).total_seconds()))
            self._use_cached_token()
            return True
        
        if not self.is_configured():
            raise SupplierConfigurationError(
                "DigiKey supplier not configured. Please provide client_id and client_secret.", 
                supplier_name="digikey",
                details={'missing_config': ['client_id', 'client_secret']}
            )
        
        # Validate required credentials
        credentials = self._credentials or {}
        client_id = credentials.get('client_id', '').strip()
        client_secret = credentials.get('client_secret', '').strip()
        
        if not client_id or not client_secret:
            raise SupplierConfigurationError(
                "DigiKey requires both client_id and client_secret",
                supplier_name="digikey",
                details={
                    'missing_credentials': [
                        field for field in ['client_id', 'client_secret'] 
                        if not (self._credentials or {}).get(field, '').strip()
                    ]
                }
            )
        
        try:
            # Set environment variables for the digikey library (production mode only)
            os.environ['DIGIKEY_CLIENT_ID'] = client_id
            os.environ['DIGIKEY_CLIENT_SECRET'] = client_secret
            os.environ['DIGIKEY_CLIENT_SANDBOX'] = 'False'  # Always use production
            
            # Try client credentials flow first (backend-only, no browser required)
            print("DigiKey: Attempting client credentials authentication (backend-only)")
            if await self._authenticate_client_credentials():
                print("DigiKey: Client credentials authentication successful")
                return True
            
            # Fall back to OAuth2 if client credentials fail
            print("DigiKey: Client credentials failed, falling back to OAuth2 authentication")
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
                    'api_environment': 'production',
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )
    
    
    async def _authenticate_production(self) -> bool:
        """OAuth2 authentication for DigiKey production API"""
        try:
            if not DIGIKEY_API_AVAILABLE:
                raise SupplierConfigurationError(
                    "DigiKey API library not available. Install with: pip install digikey-api",
                    supplier_name="digikey",
                    details={
                        'missing_dependency': 'digikey-api',
                        'install_command': 'pip install digikey-api',
                        'help_url': 'https://github.com/peeter123/digikey-api'
                    }
                )
            
            # Set up OAuth2 callback URL (with auto-detection fallback)
            default_callback = f"{self._get_server_url()}/api/suppliers/digikey/oauth/callback"
            oauth_callback_url = self._config.get('oauth_callback_url', default_callback).strip()
            
            # Validate callback URL format if provided
            if oauth_callback_url and not oauth_callback_url.startswith(('http://', 'https://')):
                raise SupplierConfigurationError(
                    "oauth_callback_url must be a valid URL starting with http:// or https://",
                    supplier_name="digikey",
                    details={
                        'invalid_url': oauth_callback_url,
                        'required_format': 'https://your-domain.com/callback'
                    }
                )
            
            # Set up storage path for OAuth2 tokens
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
                        'storage_path': storage_dir,
                        'os_error': str(e),
                        'suggested_path': './digikey_tokens'
                    }
                )
            
            # Set the storage path environment variable to the directory
            abs_storage_dir = os.path.abspath(storage_dir)
            os.environ['DIGIKEY_STORAGE_PATH'] = abs_storage_dir
            
            print(f"DigiKey OAuth2 storage path: {abs_storage_dir}")
            
            # The actual OAuth2 flow will be handled by the digikey library on first API call
            return True
            
        except SupplierError:
            raise
        except Exception as e:
            raise SupplierAuthenticationError(
                f"DigiKey authentication setup failed: {str(e)}",
                supplier_name="digikey",
                details={
                    'error_type': type(e).__name__,
                    'original_error': str(e),
                    'help_url': 'https://developer.digikey.com'
                }
            )
    
    async def _authenticate_client_credentials(self) -> bool:
        """Authenticate using client credentials grant (no redirect needed)"""
        try:
            print("DEBUG: Starting client credentials authentication")
            credentials = self._credentials or {}
            client_id = credentials.get("client_id")
            client_secret = credentials.get("client_secret")
            
            print(f"DEBUG: client_id={client_id is not None}, client_secret={client_secret is not None}")
            
            if not client_id or not client_secret:
                print("DEBUG: Missing client_id or client_secret")
                return False
            
            token_url = self._get_token_url()
            print(f"DEBUG: token_url={token_url}")
            
            # Workaround: Use requests library since aiohttp has connection issues with DigiKey
            
            data = {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "MakerMatrix/1.0",
                "Accept": "*/*"
            }
            
            print(f"DEBUG: Sending POST to {token_url} using unified HTTP client")
            
            http_client = self._get_http_client()
            response = await http_client.post(token_url, endpoint_type="client_credentials", headers=headers, data=data)
            print(f"DEBUG: Response status: {response.status}")
            
            if response.success:
                token_data = response.data or {}
                access_token = token_data.get("access_token")
                self._token_type = token_data.get("token_type", "Bearer")
                
                # Calculate expiration
                expires_in = token_data.get("expires_in", 600)  # Default 10 minutes
                
                # Cache the token for reuse across instances
                self._cache_token(access_token, expires_in)
                
                print(f"✅ DigiKey client credentials successful! Token expires in {expires_in} seconds")
                print(f"✅ Access token: {access_token[:20]}...")
                return True
            else:
                error_text = response.error_message or f"HTTP {response.status}"
                print(f"❌ DigiKey client credentials failed: {response.status} - {error_text}")
                return False
            
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
        
        # Prepare basic auth header
        credentials = self._credentials or {}
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
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
            http_client = self._get_http_client()
            response = await http_client.post(self._get_token_url(), endpoint_type="refresh_token", headers=headers, data=data)
            
            if response.success:
                token_data = response.data or {}
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
        credentials = self._credentials or {}
        client_id = credentials.get("client_id")
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
        credentials = self._credentials or {}
        client_id = credentials.get("client_id")
        client_secret = credentials.get("client_secret")
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
            http_client = self._get_http_client()
            response = await http_client.post(self._get_token_url(), endpoint_type="exchange_code", headers=headers, data=data)
            
            if response.success:
                token_data = response.data or {}
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                await self._save_tokens()
                return True
            else:
                error_data = response.error_message or f"HTTP {response.status}"
                raise SupplierAuthenticationError(
                    f"Token exchange failed: {error_data}",
                    supplier_name="digikey"
                    )
        except SupplierError:
            # Re-raise supplier errors as-is
            raise
        except Exception as e:
            raise SupplierConnectionError(
                f"Connection error during token exchange: {str(e)}",
                supplier_name="digikey"
            )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to DigiKey API using the official library"""
        print("🚨 DIGIKEY TEST_CONNECTION METHOD CALLED!")
        try:
            # Check if supplier is configured first
            if not self.is_configured():
                return {
                    "success": False,
                    "message": "DigiKey not configured",
                    "details": {
                        "error": "Missing credentials: client_id and client_secret required",
                        "configuration_needed": True,
                        "required_fields": ["client_id", "client_secret"],
                        "setup_url": "https://developer.digikey.com",
                        "instructions": "1. Register at developer.digikey.com\n2. Create an OAuth2 application\n3. Add your Client ID and Client Secret to MakerMatrix"
                    }
                }
            
            if not DIGIKEY_API_AVAILABLE:
                return {
                    "success": False,
                    "message": "DigiKey API library not available",
                    "details": {
                        "error": "DigiKey API library not installed",
                        "install_command": "pip install digikey-api",
                        "dependency_missing": True
                    }
                }
            
            # Check for credentials
            credentials = self._credentials or {}
            client_id = credentials.get('client_id', '').strip()
            client_secret = credentials.get('client_secret', '').strip()
            
            if not client_id or not client_secret:
                return {
                    "success": False,
                    "message": "Missing DigiKey credentials",
                    "details": {
                        "error": "client_id and client_secret are required",
                        "configuration_needed": True,
                        "missing_credentials": [
                            field for field in ['client_id', 'client_secret'] 
                            if not (self._credentials or {}).get(field, '').strip()
                        ],
                        "setup_url": "https://developer.digikey.com"
                    }
                }
            
            # Attempt authentication setup
            try:
                print("DEBUG test_connection: About to call authenticate()")
                auth_result = await self.authenticate()
                print(f"DEBUG test_connection: authenticate() returned: {auth_result}")
                
                if auth_result:
                    # Authentication successful! Now test API subscription with a simple call
                    try:
                        # Test API subscription with a simple product search
                        headers = {
                            'Authorization': f'Bearer {self._access_token}',
                            'X-DIGIKEY-Client-Id': self._credentials.get('client_id'),
                            'Content-Type': 'application/json'
                        }
                        
                        # Try a simple API call to test subscription
                        test_url = f"{self._get_base_url()}/products/v4/search/test/productdetails"
                        http_client = self._get_http_client()
                        response = await http_client.get(test_url, endpoint_type="test_subscription", headers=headers)
                        
                        if response.status == 401 and "not subscribed to this API" in (response.raw_content or ""):
                                return {
                                    "success": False,
                                    "message": "DigiKey API subscription required",
                                    "details": {
                                        "authentication": "successful",
                                        "api_subscription": "required",
                                        "error": "Your DigiKey developer account is not subscribed to the Product Information V4 API",
                                        "action_required": "Subscribe to Product Information V4 API in DigiKey Developer Portal",
                                        "portal_url": "https://developer.digikey.com"
                                    }
                                }
                            
                        # API subscription appears to be working (we might get 404 for test part, but that's ok)
                        success_response = {
                            "success": True,
                            "message": "DigiKey authentication and API subscription verified - ready for enrichment",
                            "details": {
                                "authentication_method": "client_credentials",
                                "token_expires_in": getattr(self, '_token_expires_at', None),
                                "api_ready": True,
                                "api_subscription": "verified",
                                "no_browser_required": True
                            }
                        }
                        print(f"DEBUG test_connection: Returning success response: {success_response}")
                        return success_response
                        
                    except Exception as api_test_error:
                        # Authentication worked but API test failed
                        return {
                            "success": False,
                            "message": "DigiKey authentication successful but API test failed",
                            "details": {
                                "authentication": "successful", 
                                "api_test": "failed",
                                "error": str(api_test_error),
                                "suggestion": "Check API subscription status in DigiKey Developer Portal"
                            }
                        }
                else:
                    print("DEBUG test_connection: authenticate() returned False")
                    return {
                        "success": False,
                        "message": "Authentication setup failed",
                        "details": {"error": "Failed to set up DigiKey authentication"}
                    }
            except SupplierConfigurationError as config_error:
                return {
                    "success": False,
                    "message": "Configuration error",
                    "details": {
                        "error": str(config_error),
                        "configuration_needed": True
                    }
                }
                
        except SupplierConfigurationError as config_error:
            return {
                "success": False,
                "message": "Configuration error",
                "details": {
                    "error": str(config_error),
                    "configuration_needed": True
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {
                    "exception": str(e),
                    "unexpected_error": True
                }
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
                        datasheet_url=self._normalize_url(product.primary_datasheet or ""),
                        image_url=self._normalize_url(product.primary_photo or ""),
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
            logger.info(f"🔍 DigiKey get_part_details called with: {supplier_part_number}")
            
            auth_result = await self.authenticate()
            logger.info(f"🔍 DigiKey authentication result: {auth_result}")
            if not auth_result:
                logger.error(f"❌ DigiKey authentication failed for part: {supplier_part_number}")
                raise SupplierAuthenticationError("Authentication required", supplier_name="digikey")
            
            logger.info(f"🔍 DigiKey API available: {DIGIKEY_API_AVAILABLE}")
            if not DIGIKEY_API_AVAILABLE:
                logger.error(f"❌ DigiKey API library not available")
                raise SupplierConfigurationError("DigiKey API library not available", supplier_name="digikey")
            
            try:
                # Make direct API call using our authentication with unified HTTP client
                headers = {
                    'Authorization': f'Bearer {self._access_token}',
                    'X-DIGIKEY-Client-Id': self._credentials.get('client_id'),
                    'Content-Type': 'application/json',
                    'User-Agent': 'MakerMatrix/1.0'
                }
                
                # Try the product details endpoint (might be included in Product Information V4)
                search_url = f"{self._get_base_url()}/products/v4/search/{supplier_part_number}/productdetails"
                
                http_client = self._get_http_client()
                response = await http_client.get(search_url, endpoint_type="get_part_details", headers=headers)
                
                if response.success:
                    result_data = response.data or {}
                    # Product details endpoint returns product directly
                    product = result_data.get('Product')
                    
                    # Log successful API response retrieval
                    logger.debug(f"🔍 DigiKey API Response keys: {list(result_data.keys()) if result_data else 'None'}")
                    
                    # Log successful data retrieval  
                    if product:
                        logger.info(f"✅ DigiKey retrieved part data for {supplier_part_number}: {product.get('ManufacturerProductNumber', 'Unknown MPN')}")
                    else:
                        logger.warning(f"⚠️ DigiKey: No product found in response for {supplier_part_number}")
                    
                    if product:
                        # Extract nested data properly with null safety
                        description_data = product.get("Description", {}) or {}
                        manufacturer_data = product.get("Manufacturer", {}) or {}
                        category_data = product.get("Category", {}) or {}
                        series_data = product.get("Series", {}) or {}
                        product_status = product.get("ProductStatus", {}) or {}
                        classifications = product.get("Classifications", {}) or {}
                        
                        # Extract component type from category hierarchy
                        category_name = category_data.get("Name", "") if category_data else ""
                        component_type = self._determine_component_type_from_category(category_data)
                        
                        # Extract RoHS and lifecycle status from classifications and product status
                        rohs_status = self._extract_rohs_status(classifications)
                        lifecycle_status = self._extract_lifecycle_status(product_status, product)
                        
                        # Build rich additional_data with DigiKey-specific information
                        # but exclude pricing (goes to PartPricingHistory table)
                        additional_data = {
                            # Core fields that can be mapped to PartModel top-level fields
                            "component_type": component_type,
                            "rohs_status": rohs_status,
                            "lifecycle_status": lifecycle_status,
                            
                            # DigiKey-specific identifiers
                            "digikey_part_number": supplier_part_number,
                            "product_url": product.get("ProductUrl", ""),
                            "base_product_number": product.get("BaseProductNumber", {}).get("Name", "") if product.get("BaseProductNumber") else "",
                            
                            # Detailed descriptions
                            "detailed_description": description_data.get("DetailedDescription", ""),
                            
                            # Technical specifications from Parameters
                            "series": series_data.get("Name", "") if series_data else "",
                            "package_case": self._extract_package_from_parameters(product),
                            "mounting_type": self._extract_mounting_type_from_parameters(product),
                            "supplier_device_package": self._extract_supplier_device_package(product),
                            
                            # Manufacturing and lead times (no pricing here)
                            "manufacturer_lead_weeks": int(product.get("ManufacturerLeadWeeks", 0)) if product.get("ManufacturerLeadWeeks") else 0,
                            "factory_stock_availability": product.get("ManufacturerPublicQuantity", 0),
                            "normally_stocking": product.get("NormallyStocking", False),
                            "back_order_not_allowed": product.get("BackOrderNotAllowed", False),
                            
                            # DigiKey category hierarchy (helpful for part organization)
                            "digikey_category_id": category_data.get("CategoryId") if category_data else None,
                            "digikey_category_name": category_name,
                            "digikey_parent_category": self._extract_parent_category_name(category_data),
                            "digikey_subcategory": self._extract_subcategory_name(category_data),
                            
                            # Product status and lifecycle
                            "product_status_id": product_status.get("Id") if product_status else None,
                            "product_status_name": product_status.get("Status") if product_status else "",
                            "discontinued": product.get("Discontinued", False),
                            "end_of_life": product.get("EndOfLife", False),
                            "date_last_buy_chance": product.get("DateLastBuyChance"),
                            "ncnr": product.get("Ncnr", False),  # Non-Cancelable Non-Returnable
                            
                            # Compliance and certifications
                            "reach_status": classifications.get("ReachStatus", ""),
                            "moisture_sensitivity_level": classifications.get("MoistureSensitivityLevel", ""),
                            "export_control_class_number": classifications.get("ExportControlClassNumber", ""),
                            "htsus_code": classifications.get("HtsusCode", ""),
                            
                            # Media
                            "primary_video_url": product.get("PrimaryVideoUrl"),
                            
                            # Alternative names and identifiers
                            "other_names": product.get("OtherNames", []),
                            
                            # Data enrichment metadata
                            "enrichment_source": "digikey_api_v4",
                            "enrichment_timestamp": datetime.utcnow().isoformat(),
                            "api_response_version": "v4"
                        }
                        
                        # Remove None values and empty strings to keep additional_data clean
                        additional_data = {k: v for k, v in additional_data.items() if v is not None and v != ""}
                        
                        return PartSearchResult(
                            supplier_part_number=supplier_part_number,  # Use the requested part number
                            manufacturer=manufacturer_data.get("Name", ""),
                            manufacturer_part_number=product.get("ManufacturerProductNumber", ""),
                            description=description_data.get("ProductDescription", ""),
                            category=category_name,
                            datasheet_url=self._normalize_url(product.get("DatasheetUrl", "")),
                            image_url=self._normalize_url(product.get("PhotoUrl", "")),
                            stock_quantity=product.get("QuantityAvailable", 0),
                            pricing=self._extract_pricing_from_dict(product),
                            specifications=self._extract_specifications_from_dict(product),
                            additional_data=additional_data
                        )
                    else:
                        logger.warning(f"🔍 DigiKey: No product found in response for {supplier_part_number}")
                        return None
                else:
                    error_text = response.error_message or f"HTTP {response.status}"
                    logger.error(f"🔍 DigiKey API call failed: {response.status} - {error_text}")
                    
                    # Handle specific API subscription errors
                    if response.status == 401 and "not subscribed to this API" in error_text:
                        raise SupplierConfigurationError(
                            "DigiKey API subscription required: Your DigiKey developer account is not subscribed to the Product Information V4 API. "
                            "Please visit the DigiKey Developer Portal and subscribe to the Product Information V4 API to enable part enrichment.",
                            supplier_name="digikey",
                            details={
                                'error_type': 'api_subscription_required',
                                'api_name': 'Product Information V4',
                                'action_required': 'Subscribe to API in DigiKey Developer Portal'
                            }
                        )
                    elif response.status == 401:
                        raise SupplierAuthenticationError(
                            f"DigiKey authentication failed: {error_text}",
                            supplier_name="digikey"
                        )
                    else:
                        raise SupplierConnectionError(
                            f"DigiKey API error ({response.status}): {error_text}",
                            supplier_name="digikey"
                        )
                    
            except Exception as e:
                raise SupplierConnectionError(f"DigiKey part details failed: {str(e)}", supplier_name="digikey")
        
        return await self._tracked_api_call("get_part_details", _impl)
    
    def _extract_pricing_from_dict(self, product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract pricing information from product dictionary"""
        pricing = []
        standard_pricing = product.get("StandardPricing", [])
        
        for price_break in standard_pricing:
            pricing.append({
                "quantity": price_break.get("BreakQuantity", 1),
                "price": price_break.get("UnitPrice", 0.0),
                "currency": "USD"
            })
        
        return pricing
    
    def _extract_specifications_from_dict(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extract specifications from product dictionary"""
        specs = {}
        parameters = product.get("Parameters", [])
        
        for param in parameters:
            param_name = param.get("Parameter", "")
            param_value = param.get("Value", "")
            if param_name and param_value:
                specs[param_name] = param_value
        
        return specs
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part"""
        async def _impl():
            logger.info(f"🔍 DigiKey fetch_datasheet called with part_number: {supplier_part_number}")
            part_details = await self.get_part_details(supplier_part_number)
            logger.info(f"🔍 DigiKey get_part_details returned: {part_details is not None}")
            if part_details:
                logger.info(f"🔍 DigiKey datasheet_url: {part_details.datasheet_url}")
                return part_details.datasheet_url
            else:
                logger.warning(f"❌ DigiKey get_part_details returned None for {supplier_part_number}")
                return None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_pricing_stock(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch combined pricing and stock information for a DigiKey part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            if not part_details:
                return None
            
            result = {}
            if part_details.pricing:
                result["pricing"] = part_details.pricing
            if part_details.stock_quantity is not None:
                result["stock_quantity"] = part_details.stock_quantity
            
            return result if result else None
        
        return await self._tracked_api_call("fetch_pricing_stock", _impl)
    
    
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
            credentials = self._credentials or {}
            client_id = credentials.get('client_id', '')
            default_callback = f"{self._get_server_url()}/api/suppliers/digikey/oauth/callback"
            callback_url = self._config.get('oauth_callback_url', default_callback)
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
        
        # Check file extension - DigiKey uses CSV/Excel formats
        if not filename_lower.endswith(('.csv', '.xls', '.xlsx')):
            return False
        
        # Check filename patterns - if DigiKey pattern found, we can handle it
        digikey_patterns = ['digikey', 'digi-key', 'weborder', 'salesorder', 'dk_products']
        if any(pattern in filename_lower for pattern in digikey_patterns):
            return True
        
        # Check content for DigiKey-specific patterns only if filename doesn't match
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
                        # If we can't read the Excel file, but extension is supported, allow it
                        return True
                
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
                # If we can't check content but file extension is supported, allow it
                return True
        
        # If no content provided, only allow if filename matches DigiKey patterns
        return False
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import DigiKey order CSV or Excel file"""
        file_type_lower = file_type.lower()
        
        if file_type_lower not in ['csv', 'xls', 'xlsx']:
            return ImportResult(
                success=False,
                error_message=f"DigiKey supports CSV, XLS, and XLSX formats, not {file_type}. Please export your DigiKey order as CSV or Excel."
            )
        
        try:
            # Handle Excel files (XLS/XLSX) - try Excel first, fallback to CSV
            if file_type_lower in ['xls', 'xlsx']:
                try:
                    import pandas as pd
                    import io
                    
                    # Try to read as Excel first
                    try:
                        df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl' if file_type_lower == 'xlsx' else None)
                        logger.info(f"Successfully read {filename} as Excel format")
                        # Convert DataFrame to CSV string for uniform processing
                        content_str = df.to_csv(index=False)
                    except Exception as excel_error:
                        # If Excel reading fails, try to read as CSV (common issue - CSV files with .xls extension)
                        try:
                            content_str = file_content.decode('utf-8')
                            # Quick validation - does it look like CSV?
                            if ',' in content_str and '\n' in content_str:
                                logger.warning(f"File {filename} has .{file_type_lower} extension but appears to be CSV format, processing as CSV")
                            else:
                                raise excel_error  # Re-raise original error if it doesn't look like CSV
                        except UnicodeDecodeError:
                            return ImportResult(
                                success=False,
                                error_message=f"File appears to be neither valid Excel nor CSV format: {str(excel_error)}"
                            )
                except ImportError:
                    return ImportResult(
                        success=False,
                        error_message="pandas library not available for Excel file processing. Please install pandas or export as CSV."
                    )
            else:
                # Handle CSV files
                content_str = file_content.decode('utf-8')
            
            # Remove BOM (Byte Order Mark) if present
            if content_str.startswith('\ufeff'):
                content_str = content_str[1:]
                logger.info("Removed BOM (Byte Order Mark) from CSV file")
            
            # Use pandas for robust CSV/Excel parsing
            from io import StringIO
            import pandas as pd
            df = pd.read_csv(StringIO(content_str))
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            if df.empty:
                return ImportResult(
                    success=False,
                    error_message="File contains no data rows"
                )
            
            parts = []
            errors = []
            
            # Use unified column mapping for consistent data extraction
            column_mapper = UnifiedColumnMapper()
            digikey_mappings = column_mapper.get_supplier_specific_mappings('digikey')
            
            # Map columns using flexible matching
            mapped_columns = column_mapper.map_columns(df.columns.tolist(), digikey_mappings)
            
            # Validate required columns using unified validation
            required_fields = ['part_number', 'quantity']
            if not column_mapper.validate_required_columns(mapped_columns, required_fields):
                return ImportResult(
                    success=False,
                    error_message=f"Required columns not found. Available columns: {list(df.columns)}",
                    warnings=[f"Missing required fields: {[field for field in required_fields if field not in mapped_columns]}"]
                )
            
            # Initialize SupplierDataMapper for standardization
            supplier_mapper = SupplierDataMapper()
            
            # Parse rows using unified data extraction
            for index, row in df.iterrows():
                try:
                    # Extract all available data using column mapping
                    extracted_data = column_mapper.extract_row_data(row, mapped_columns)
                    
                    # Skip rows without part numbers
                    if not extracted_data.get('part_number'):
                        continue
                    
                    # Parse quantity safely
                    quantity = 1
                    if extracted_data.get('quantity'):
                        try:
                            quantity = max(1, int(float(str(extracted_data['quantity']).replace(',', ''))))
                        except (ValueError, TypeError):
                            quantity = 1
                    
                    # Parse pricing safely
                    unit_price = None
                    order_price = None
                    if extracted_data.get('unit_price'):
                        try:
                            unit_price = float(str(extracted_data['unit_price']).replace('$', '').replace(',', '').replace('"', ''))
                        except (ValueError, TypeError):
                            pass
                    
                    if extracted_data.get('order_price'):
                        try:
                            order_price = float(str(extracted_data['order_price']).replace('$', '').replace(',', '').replace('"', ''))
                        except (ValueError, TypeError):
                            pass
                    
                    # Create smart part name from available data
                    part_name = column_mapper.create_smart_part_name(extracted_data)
                    
                    # Build comprehensive additional_properties
                    additional_properties = self._build_digikey_additional_properties(
                        extracted_data, unit_price, order_price, index
                    )
                    
                    # Create PartSearchResult object for SupplierDataMapper
                    from .base import PartSearchResult
                    part_search_result = PartSearchResult(
                        supplier_part_number=str(extracted_data['part_number']).strip(),
                        manufacturer=extracted_data.get('manufacturer', '').strip() if extracted_data.get('manufacturer') else None,
                        manufacturer_part_number=extracted_data.get('manufacturer_part_number', '').strip() if extracted_data.get('manufacturer_part_number') else None,
                        description=extracted_data.get('description', '').strip() if extracted_data.get('description') else None,
                        additional_data=additional_properties
                    )
                    
                    # Use SupplierDataMapper for standardization
                    standardized_part = supplier_mapper.map_supplier_result_to_part_data(
                        part_search_result, 'DigiKey', enrichment_capabilities=['csv_import']
                    )
                    
                    # Add import-specific fields that aren't in PartSearchResult
                    standardized_part['part_name'] = part_name
                    standardized_part['quantity'] = quantity
                    standardized_part['supplier'] = 'DigiKey'
                    
                    parts.append(standardized_part)
                        
                except Exception as e:
                    errors.append(f"Error parsing row {index + 1}: {str(e)}")
                    logger.warning(f"Failed to process DigiKey row {index + 1}: {e}")
            
            if not parts:
                return ImportResult(
                    success=False,
                    error_message="No valid parts found in file",
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
    
    def _build_digikey_additional_properties(self, extracted_data: Dict[str, Any], unit_price: Optional[float], order_price: Optional[float], row_index: int) -> Dict[str, Any]:
        """Build comprehensive additional_properties for DigiKey parts"""
        additional_properties = {
            'supplier_data': {
                'supplier': 'DigiKey',
                'supplier_part_number': extracted_data.get('part_number'),
                'row_index': row_index + 1,
                'import_source': 'csv'
            },
            'order_info': {},
            'technical_specs': {}
        }
        
        # Add customer reference if available
        if extracted_data.get('customer_reference'):
            additional_properties['order_info']['customer_reference'] = extracted_data['customer_reference']
        
        # Add backorder information if available
        if extracted_data.get('backorder_qty'):
            try:
                backorder_qty = int(str(extracted_data['backorder_qty']).replace(',', ''))
                additional_properties['order_info']['backorder_quantity'] = backorder_qty
            except (ValueError, TypeError):
                pass
        
        # Add pricing information
        if unit_price is not None:
            additional_properties['order_info']['unit_price'] = unit_price
            additional_properties['order_info']['currency'] = 'USD'  # DigiKey pricing is typically in USD
        if order_price is not None:
            additional_properties['order_info']['extended_price'] = order_price
        
        # Add package information to technical specs if available
        if extracted_data.get('package'):
            additional_properties['technical_specs']['package'] = str(extracted_data['package']).strip()
        
        # Clean up empty sections
        additional_properties = {k: v for k, v in additional_properties.items() if v}
        
        return additional_properties
    
    # ========== DigiKey V4 API Helper Methods ==========
    
    def _determine_component_type_from_category(self, category_data: Dict[str, Any]) -> str:
        """Determine component type from DigiKey category hierarchy"""
        if not category_data:
            return ""
        
        category_name = category_data.get("Name", "").lower()
        
        # Map DigiKey categories to component types
        category_mappings = {
            "integrated circuits": "integrated_circuit",
            "resistors": "resistor", 
            "capacitors": "capacitor",
            "inductors": "inductor",
            "crystals": "crystal",
            "connectors": "connector",
            "sensors": "sensor",
            "transistors": "transistor",
            "diodes": "diode",
            "switches": "switch",
            "relays": "relay",
            "transformers": "transformer",
            "fuses": "fuse",
            "leds": "led",
            "displays": "display"
        }
        
        for key, component_type in category_mappings.items():
            if key in category_name:
                return component_type
        
        # Check parent categories if available
        child_categories = category_data.get("ChildCategories", [])
        if child_categories:
            for child in child_categories:
                child_name = child.get("Name", "").lower()
                for key, component_type in category_mappings.items():
                    if key in child_name:
                        return component_type
        
        return category_name.replace(" ", "_").lower()
    
    def _extract_rohs_status(self, classifications: Dict[str, Any]) -> str:
        """Extract RoHS status from DigiKey classifications"""
        if not classifications:
            return ""
        
        rohs_status = classifications.get("RohsStatus", "")
        
        # Standardize DigiKey RoHS status values
        if "compliant" in rohs_status.lower():
            return "Compliant"
        elif "exempt" in rohs_status.lower():
            return "Exempt"
        elif "non" in rohs_status.lower():
            return "Non-Compliant"
        
        return rohs_status
    
    def _extract_lifecycle_status(self, product_status: Dict[str, Any], product: Dict[str, Any]) -> str:
        """Extract lifecycle status from DigiKey product status and flags"""
        if product.get("Discontinued", False):
            return "Discontinued"
        elif product.get("EndOfLife", False):
            return "End of Life"
        elif product_status.get("Status", "").lower() == "active":
            return "Active"
        elif product.get("DateLastBuyChance"):
            return "Last Time Buy"
        else:
            return product_status.get("Status", "")
    
    def _extract_package_from_parameters(self, product: Dict[str, Any]) -> str:
        """Extract package/case information from DigiKey parameters"""
        parameters = product.get("Parameters", [])
        
        for param in parameters:
            param_text = param.get("ParameterText", "").lower()
            if "package" in param_text or "case" in param_text:
                return param.get("ValueText", "")
        
        return ""
    
    def _extract_mounting_type_from_parameters(self, product: Dict[str, Any]) -> str:
        """Extract mounting type from DigiKey parameters"""
        parameters = product.get("Parameters", [])
        
        for param in parameters:
            param_text = param.get("ParameterText", "").lower()
            if "mounting" in param_text:
                return param.get("ValueText", "")
        
        return ""
    
    def _extract_supplier_device_package(self, product: Dict[str, Any]) -> str:
        """Extract supplier device package from DigiKey parameters"""
        parameters = product.get("Parameters", [])
        
        for param in parameters:
            param_text = param.get("ParameterText", "").lower()
            if "supplier device package" in param_text:
                return param.get("ValueText", "")
        
        return ""
    
    def _extract_parent_category_name(self, category_data: Dict[str, Any]) -> str:
        """Extract parent category name from DigiKey category data"""
        if not category_data:
            return ""
        
        parent_id = category_data.get("ParentId", 0)
        if parent_id == 0:
            return ""  # This is a top-level category
        
        # For now, return empty - we'd need to map parent IDs to names
        # This could be enhanced with a lookup table if needed
        return ""

    async def close(self):
        """Clean up resources including HTTP client sessions"""
        # Call parent cleanup
        await super().close()

        # Close HTTP client if it exists
        if hasattr(self, '_http_client') and self._http_client:
            await self._http_client.close()
            self._http_client = None

    def _extract_subcategory_name(self, category_data: Dict[str, Any]) -> str:
        """Extract subcategory name from DigiKey category hierarchy"""
        if not category_data:
            return ""
        
        child_categories = category_data.get("ChildCategories", [])
        if child_categories:
            # Return the first subcategory name if available
            return child_categories[0].get("Name", "")
        
        return ""
    
