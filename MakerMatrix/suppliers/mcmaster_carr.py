"""
McMaster-Carr Official API Supplier Implementation

This supplier connects to McMaster-Carr's official API using client certificate authentication.
Contact eCommerce@mcmaster.com for API approval and client certificates.

NO WEB SCRAPING - API ONLY
"""

from typing import List, Dict, Any, Optional
import ssl
import aiohttp
import json
from datetime import datetime, timedelta
import logging

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, CapabilityRequirement
)
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

logger = logging.getLogger(__name__)

class McMasterCarrSupplier(BaseSupplier):
    """McMaster-Carr Official API Implementation
    
    Requires:
    - Approved API account from McMaster-Carr
    - Client certificate (.p12 or .pfx)
    - API credentials
    
    Contact eCommerce@mcmaster.com for API approval.
    """
    
    def __init__(self):
        super().__init__()
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="McMaster-Carr",
            display_name="McMaster-Carr",
            description="Industrial supply with official API access - requires approval",
            website_url="https://www.mcmaster.com",
            api_documentation_url="Contact eCommerce@mcmaster.com for API documentation",
            supports_oauth=False,
            rate_limit_info="API rate limits apply - contact McMaster for details"
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        # McMaster-Carr API implementation - requires approved account and certificates
        return [
            SupplierCapability.SEARCH_PARTS,
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_IMAGE,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.PARAMETRIC_SEARCH
            # Note: FETCH_PRICING and FETCH_STOCK not implemented yet
        ]

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Define what credentials each capability needs"""
        all_creds_req = ["username", "password", "client_cert_path", "client_cert_password"]
        return {
            capability: CapabilityRequirement(
                capability=capability,
                required_credentials=all_creds_req
            )
            for capability in self.get_capabilities()
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="username",
                label="API Username",
                field_type=FieldType.TEXT,
                required=True,
                description="McMaster-Carr approved API account username",
                help_text="Contact eCommerce@mcmaster.com for API approval"
            ),
            FieldDefinition(
                name="password",
                label="API Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="McMaster-Carr API account password",
                help_text="Your approved API account password"
            ),
            FieldDefinition(
                name="client_cert_path",
                label="Client Certificate Path",
                field_type=FieldType.TEXT,
                required=True,
                description="Path to client certificate file (.p12 or .pfx)",
                help_text="McMaster-Carr provides client certificates for API access"
            ),
            FieldDefinition(
                name="client_cert_password",
                label="Client Certificate Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Client certificate password",
                help_text="Password for your McMaster-Carr client certificate"
            )
        ]
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_base_url",
                label="API Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://www.mcmaster.com/api/v1",
                description="McMaster-Carr official API endpoint",
                help_text="Official API base URL (requires approval from McMaster)"
            ),
            FieldDefinition(
                name="timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="API request timeout in seconds",
                help_text="Maximum time to wait for API responses"
            ),
            FieldDefinition(
                name="rate_limit_delay",
                label="Rate Limit Delay (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=1.0,
                description="Delay between API requests",
                help_text="Respect McMaster's API rate limits"
            ),
            FieldDefinition(
                name="max_retries",
                label="Maximum Retries",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=3,
                description="Maximum number of API request retries",
                help_text="Number of times to retry failed requests"
            )
        ]
    
    async def _setup_ssl_context(self, credentials: Dict[str, str]) -> ssl.SSLContext:
        """Setup SSL context with client certificate"""
        if self._ssl_context:
            return self._ssl_context
        
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Load client certificate
            cert_path = credentials.get("client_cert_path")
            cert_password = credentials.get("client_cert_password")
            
            if not cert_path:
                raise SupplierConfigurationError("Client certificate path is required")
            
            # Load the client certificate
            context.load_cert_chain(cert_path, password=cert_password)
            
            self._ssl_context = context
            logger.info("✅ SSL context configured with client certificate")
            return context
            
        except Exception as e:
            raise SupplierConfigurationError(f"Failed to setup SSL context: {str(e)}")
    
    async def _authenticate(self, credentials: Dict[str, str]) -> str:
        """Authenticate with McMaster-Carr API and get access token"""
        
        if self._auth_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._auth_token
        
        try:
            ssl_context = await self._setup_ssl_context(credentials)
            base_url = self._config.get("api_base_url", "https://www.mcmaster.com/api/v1")
            timeout_seconds = self._config.get("timeout_seconds", 30)
            
            # Create HTTP connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                auth_url = f"{base_url}/auth/token"
                
                auth_data = {
                    "username": credentials["username"],
                    "password": credentials["password"]
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "MakerMatrix/1.0 (API Client)"
                }
                
                logger.info("🔐 Authenticating with McMaster-Carr API...")
                
                async with session.post(auth_url, json=auth_data, headers=headers) as response:
                    if response.status == 200:
                        auth_response = await response.json()
                        
                        self._auth_token = auth_response.get("access_token")
                        expires_in = auth_response.get("expires_in", 3600)  # Default 1 hour
                        
                        # Set token expiration
                        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 minute buffer
                        
                        logger.info("✅ Successfully authenticated with McMaster-Carr API")
                        return self._auth_token
                    
                    elif response.status == 401:
                        error_text = await response.text()
                        raise SupplierAuthenticationError(f"Invalid credentials: {error_text}")
                    
                    else:
                        error_text = await response.text()
                        raise SupplierConnectionError(f"Authentication failed with status {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during authentication: {str(e)}")
        except Exception as e:
            raise SupplierAuthenticationError(f"Authentication failed: {str(e)}")
    
    async def _make_api_request(self, endpoint: str, credentials: Dict[str, str], params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request to McMaster-Carr"""
        
        try:
            # Get authentication token
            auth_token = await self._authenticate(credentials)
            
            # Setup SSL and session
            ssl_context = await self._setup_ssl_context(credentials)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout_seconds", 30))
            
            base_url = self._config.get("api_base_url", "https://www.mcmaster.com/api/v1")
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
                "User-Agent": "MakerMatrix/1.0 (API Client)"
            }
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                logger.info(f"🌐 Making API request to: {endpoint}")
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    
                    elif response.status == 401:
                        # Token expired, clear it and retry once
                        self._auth_token = None
                        auth_token = await self._authenticate(credentials)
                        headers["Authorization"] = f"Bearer {auth_token}"
                        
                        async with session.get(url, headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                            else:
                                error_text = await retry_response.text()
                                raise SupplierAuthenticationError(f"API request failed after retry: {error_text}")
                    
                    elif response.status == 429:
                        raise SupplierRateLimitError("API rate limit exceeded")
                    
                    else:
                        error_text = await response.text()
                        raise SupplierConnectionError(f"API request failed with status {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during API request: {str(e)}")
    
    async def authenticate(self) -> bool:
        """Authenticate with McMaster-Carr API using configured credentials"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for authentication")
                return False
            
            auth_token = await self._authenticate(credentials)
            return bool(auth_token)
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    async def test_connection(self, credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """Test connection to McMaster-Carr API"""
        try:
            # Test authentication
            auth_token = await self._authenticate(credentials)
            
            # Test a simple API endpoint
            response = await self._make_api_request("/health", credentials)
            
            return {
                "success": True,
                "message": "Successfully connected to McMaster-Carr API",
                "details": {
                    "authenticated": bool(auth_token),
                    "api_version": response.get("version", "unknown"),
                    "capabilities": [cap.value for cap in self.get_capabilities()]
                }
            }
            
        except SupplierAuthenticationError as e:
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}",
                "details": {"error_type": "authentication"}
            }
        except SupplierConfigurationError as e:
            return {
                "success": False,
                "message": f"Configuration error: {str(e)}",
                "details": {"error_type": "configuration"}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"error_type": "unknown"}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using McMaster-Carr API"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for search")
                return []
            
            params = {
                "q": query,
                "limit": limit,
                "offset": 0
            }
            
            response = await self._make_api_request("/parts/search", credentials, params)
            
            results = []
            for part_data in response.get("parts", []):
                result = self._parse_part_data(part_data)
                if result:
                    results.append(result)
            
            logger.info(f"✅ Found {len(results)} parts for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed for query '{query}': {str(e)}")
            return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed part information from McMaster-Carr API"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for part details")
                return None
            
            endpoint = f"/parts/{supplier_part_number}"
            response = await self._make_api_request(endpoint, credentials)
            
            result = self._parse_part_data(response)
            if result:
                logger.info(f"✅ Retrieved details for part: {supplier_part_number}")
                return result
            else:
                logger.warning(f"⚠️  No details found for part: {supplier_part_number}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get details for part '{supplier_part_number}': {str(e)}")
            return None
    
    def _parse_part_data(self, part_data: Dict[str, Any]) -> Optional[PartSearchResult]:
        """Parse part data from McMaster-Carr API response"""
        try:
            part_number = part_data.get("partNumber")
            if not part_number:
                return None
            
            # Extract specifications
            specifications = {}
            specs_data = part_data.get("specifications", {})
            for spec_name, spec_value in specs_data.items():
                if spec_value:
                    specifications[spec_name] = spec_value
            
            # Extract pricing
            pricing_data = part_data.get("pricing", {})
            price_text = None
            if pricing_data:
                price_value = pricing_data.get("unitPrice")
                unit_quantity = pricing_data.get("unitQuantity", 1)
                currency = pricing_data.get("currency", "USD")
                
                if price_value:
                    if unit_quantity > 1:
                        price_text = f"{currency} {price_value} per {unit_quantity}"
                    else:
                        price_text = f"{currency} {price_value} each"
            
            # Extract image URL
            image_url = part_data.get("imageUrl")
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.mcmaster.com{image_url}"
            
            # Extract datasheet URL
            datasheet_url = part_data.get("datasheetUrl")
            if datasheet_url and not datasheet_url.startswith("http"):
                datasheet_url = f"https://www.mcmaster.com{datasheet_url}"
            
            return PartSearchResult(
                supplier_part_number=part_number,
                manufacturer="McMaster-Carr",
                manufacturer_part_number=part_number,
                description=part_data.get("description", f"McMaster-Carr Part {part_number}"),
                category=part_data.get("category", "Industrial Supply"),
                datasheet_url=datasheet_url,
                image_url=image_url,
                stock_quantity=part_data.get("stockQuantity"),
                pricing=price_text,
                specifications=specifications if specifications else None,
                additional_data={
                    "source": "mcmaster_api",
                    "api_version": part_data.get("apiVersion"),
                    "last_updated": part_data.get("lastUpdated"),
                    "unit_of_measure": part_data.get("unitOfMeasure"),
                    "minimum_order_quantity": part_data.get("minimumOrderQuantity"),
                    "lead_time_days": part_data.get("leadTimeDays")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse part data: {str(e)}")
            return None
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for datasheet fetch")
                return None
            
            endpoint = f"/parts/{supplier_part_number}/datasheet"
            response = await self._make_api_request(endpoint, credentials)
            
            datasheet_url = response.get("datasheetUrl")
            if datasheet_url:
                if not datasheet_url.startswith("http"):
                    datasheet_url = f"https://www.mcmaster.com{datasheet_url}"
                
                logger.info(f"✅ Found datasheet for part: {supplier_part_number}")
                return datasheet_url
            
            logger.warning(f"⚠️  No datasheet available for part: {supplier_part_number}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch datasheet for part '{supplier_part_number}': {str(e)}")
            return None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a part"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for image fetch")
                return None
            
            endpoint = f"/parts/{supplier_part_number}/image"
            response = await self._make_api_request(endpoint, credentials)
            
            image_url = response.get("imageUrl")
            if image_url:
                if not image_url.startswith("http"):
                    image_url = f"https://www.mcmaster.com{image_url}"
                
                logger.info(f"✅ Found image for part: {supplier_part_number}")
                return image_url
            
            logger.warning(f"⚠️  No image available for part: {supplier_part_number}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch image for part '{supplier_part_number}': {str(e)}")
            return None
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch specifications for a part"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for specifications fetch")
                return None
            
            endpoint = f"/parts/{supplier_part_number}/specifications"
            response = await self._make_api_request(endpoint, credentials)
            
            specifications = response.get("specifications", {})
            if specifications:
                logger.info(f"✅ Found {len(specifications)} specifications for part: {supplier_part_number}")
                return specifications
            
            logger.warning(f"⚠️  No specifications available for part: {supplier_part_number}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch specifications for part '{supplier_part_number}': {str(e)}")
            return None

# Register the supplier
from .registry import SupplierRegistry
SupplierRegistry.register("mcmaster-carr", McMasterCarrSupplier)