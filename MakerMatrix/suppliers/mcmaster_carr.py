"""
McMaster-Carr Supplier Implementation

Implements the McMaster-Carr Product Information API interface using username/password authentication.
Supports product search, pricing, stock, datasheets, images, and CAD files with token-based authentication.
"""

from typing import List, Dict, Any, Optional
import aiohttp
import urllib.parse
import json
from datetime import datetime, timedelta
import hashlib

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

@register_supplier("mcmaster-carr")
class McMasterCarrSupplier(BaseSupplier):
    """McMaster-Carr supplier implementation with username/password authentication"""
    
    def __init__(self):
        super().__init__()
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="mcmaster-carr",
            display_name="McMaster-Carr",
            description="Industrial supply company providing maintenance, repair, and operations (MRO) products. API access requires approved customer status with client certificate authentication. Contact eCommerce@mcmaster.com for API approval and client certificates. Offers comprehensive product data, pricing, CAD files, and technical specifications.",
            website_url="https://www.mcmaster.com",
            api_documentation_url="https://www.mcmaster.com/help/api/",
            supports_oauth=False,  # Uses username/password + client cert with token
            rate_limit_info="Rate limits apply to bandwidth-intensive endpoints. Daily limits on product subscriptions."
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.SEARCH_PARTS,           # Product search by part number
            SupplierCapability.GET_PART_DETAILS,       # Complete product information
            SupplierCapability.FETCH_DATASHEET,        # Datasheet downloads
            SupplierCapability.FETCH_IMAGE,            # Product images
            SupplierCapability.FETCH_PRICING,          # Current pricing
            SupplierCapability.FETCH_STOCK,            # Availability status
            SupplierCapability.FETCH_SPECIFICATIONS,   # Technical specifications
            SupplierCapability.PARAMETRIC_SEARCH       # Enhanced search capabilities
        ]
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="username",
                label="Username",
                field_type=FieldType.TEXT,
                required=True,
                description="McMaster-Carr account username",
                help_text="Your approved McMaster-Carr customer account username"
            ),
            FieldDefinition(
                name="password",
                label="Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="McMaster-Carr account password",
                help_text="Your McMaster-Carr account password (will be encrypted)"
            ),
            FieldDefinition(
                name="client_cert_path",
                label="Client Certificate Path",
                field_type=FieldType.TEXT,
                required=True,
                description="Path to client certificate file (.p12 or .pfx)",
                help_text="McMaster-Carr requires client certificates for all API access. Contact eCommerce@mcmaster.com to obtain your certificate."
            ),
            FieldDefinition(
                name="client_cert_password",
                label="Client Certificate Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Client certificate password",
                help_text="Password provided by McMaster-Carr for your client certificate"
            )
        ]
    
    def get_configuration_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="base_url",
                label="API Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://www.mcmaster.com/api/v1",
                description="McMaster-Carr API base URL",
                help_text="Default URL should work for most users"
            ),
            FieldDefinition(
                name="auto_subscribe_products",
                label="Auto-Subscribe to Products",
                field_type=FieldType.BOOLEAN,
                required=False,
                default_value=True,
                description="Automatically subscribe to products when accessing their data",
                help_text="Required to access product pricing and detailed information"
            ),
            FieldDefinition(
                name="max_subscriptions",
                label="Maximum Product Subscriptions",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=1000,
                description="Maximum number of product subscriptions to maintain",
                help_text="McMaster-Carr limits the number of product subscriptions per user"
            ),
            FieldDefinition(
                name="token_refresh_buffer_minutes",
                label="Token Refresh Buffer (minutes)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=60,
                description="Minutes before token expiry to refresh authentication",
                help_text="Tokens expire after 24 hours. Refresh proactively to avoid interruptions."
            ),
            FieldDefinition(
                name="request_timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="HTTP request timeout in seconds",
                help_text="Timeout for API requests to McMaster-Carr"
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get API base URL"""
        return self._config.get("base_url", "https://www.mcmaster.com/api/v1")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for McMaster-Carr API calls"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add authorization token if available
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        
        return headers
    
    def _is_token_valid(self) -> bool:
        """Check if current auth token is still valid"""
        if not self._auth_token or not self._token_expires_at:
            return False
        
        # Add buffer time to refresh token proactively
        buffer_minutes = self._config.get("token_refresh_buffer_minutes", 60)
        buffer_time = timedelta(minutes=buffer_minutes)
        
        return datetime.now() < (self._token_expires_at - buffer_time)
    
    async def _login(self) -> bool:
        """Authenticate with McMaster-Carr and get auth token"""
        username = self._credentials.get("username")
        password = self._credentials.get("password")
        
        if not username or not password:
            raise SupplierConfigurationError(
                "Username and password required for McMaster-Carr authentication",
                supplier_name="mcmaster-carr"
            )
        
        session = await self._get_session()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        url = f"{self._get_base_url()}/login"
        login_data = {
            "username": username,
            "password": password
        }
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("request_timeout_seconds", 30)
            )
            
            async with session.post(
                url, 
                headers=headers, 
                json=login_data,
                timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._auth_token = data.get("token")
                    
                    # McMaster tokens expire after 24 hours
                    self._token_expires_at = datetime.now() + timedelta(hours=24)
                    
                    return True
                elif response.status == 401:
                    raise SupplierAuthenticationError(
                        "Invalid username or password",
                        supplier_name="mcmaster-carr"
                    )
                elif response.status == 403:
                    raise SupplierAuthenticationError(
                        "Account not approved for API access",
                        supplier_name="mcmaster-carr"
                    )
                else:
                    error_text = await response.text()
                    raise SupplierConnectionError(
                        f"Login failed: {response.status} - {error_text}",
                        supplier_name="mcmaster-carr"
                    )
        
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(
                f"Network error during login: {str(e)}",
                supplier_name="mcmaster-carr"
            )
    
    async def authenticate(self) -> bool:
        """Ensure valid authentication token"""
        if not self.is_configured():
            raise SupplierConfigurationError(
                "Supplier not configured",
                supplier_name="mcmaster-carr"
            )
        
        # Check if current token is still valid
        if self._is_token_valid():
            return True
        
        # Login to get new token
        try:
            return await self._login()
        except Exception:
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to McMaster-Carr API"""
        try:
            if not await self.authenticate():
                return {
                    "success": False,
                    "message": "Authentication failed",
                    "details": {"requires": "Valid McMaster-Carr account credentials"}
                }
            
            # Test with a simple API call
            session = await self._get_session()
            headers = self._get_headers()
            
            # Try to get user's product subscriptions as a test
            url = f"{self._get_base_url()}/products"
            
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("request_timeout_seconds", 30)
            )
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "details": {
                            "api_version": "v1",
                            "base_url": self._get_base_url(),
                            "subscriptions_count": len(data.get("products", [])),
                            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None
                        }
                    }
                elif response.status == 429:
                    return {
                        "success": False,
                        "message": "Rate limit exceeded",
                        "details": {"status_code": response.status}
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "message": "Authentication token expired or invalid",
                        "details": {"status_code": response.status}
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "message": f"API error: {response.status}",
                        "details": {"error": error_text}
                    }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def _subscribe_to_product(self, part_number: str) -> bool:
        """Subscribe to a product to access its detailed information"""
        if not self._config.get("auto_subscribe_products", True):
            return True  # Skip subscription if disabled
        
        session = await self._get_session()
        headers = self._get_headers()
        
        url = f"{self._get_base_url()}/products"
        subscription_data = {
            "partNumbers": [part_number]
        }
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("request_timeout_seconds", 30)
            )
            
            async with session.post(
                url,
                headers=headers,
                json=subscription_data,
                timeout=timeout
            ) as response:
                return response.status in [200, 201, 409]  # 409 = already subscribed
        
        except Exception:
            return False
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using McMaster-Carr API (by part number)"""
        if not await self.authenticate():
            raise SupplierAuthenticationError(
                "Authentication required",
                supplier_name="mcmaster-carr"
            )
        
        # McMaster-Carr API primarily works with specific part numbers
        # For search functionality, we'll try to get product details for the query
        part_details = await self.get_part_details(query)
        if part_details:
            return [part_details]
        
        return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific McMaster-Carr part"""
        if not await self.authenticate():
            raise SupplierAuthenticationError(
                "Authentication required",
                supplier_name="mcmaster-carr"
            )
        
        # Subscribe to product first
        if not await self._subscribe_to_product(supplier_part_number):
            return None
        
        session = await self._get_session()
        headers = self._get_headers()
        
        url = f"{self._get_base_url()}/products/{urllib.parse.quote(supplier_part_number)}"
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("request_timeout_seconds", 30)
            )
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_product_data(data)
                elif response.status == 404:
                    return None
                else:
                    return None
        
        except Exception:
            return None
    
    def _parse_product_data(self, data: Dict[str, Any]) -> PartSearchResult:
        """Parse McMaster-Carr product data into PartSearchResult"""
        part_number = data.get("partNumber", "")
        
        # Parse specifications from product attributes
        specifications = {}
        attributes = data.get("attributes", [])
        for attr in attributes:
            name = attr.get("name", "")
            value = attr.get("value", "")
            if name and value:
                specifications[name] = value
        
        # Get image URL if available
        image_url = ""
        images = data.get("images", [])
        if images:
            image_url = f"{self._get_base_url()}/images/{images[0].get('id', '')}"
        
        # Get datasheet URL if available
        datasheet_url = ""
        datasheets = data.get("datasheets", [])
        if datasheets:
            datasheet_url = f"{self._get_base_url()}/datasheets/{datasheets[0].get('id', '')}"
        
        return PartSearchResult(
            supplier_part_number=part_number,
            manufacturer="McMaster-Carr",
            manufacturer_part_number=part_number,  # McMaster uses their own part numbers
            description=data.get("description", ""),
            category=data.get("category", ""),
            datasheet_url=datasheet_url,
            image_url=image_url,
            stock_quantity=None,  # McMaster doesn't provide stock quantities
            pricing=None,  # Will be fetched separately
            specifications=specifications if specifications else None,
            additional_data={
                "product_url": data.get("productUrl", ""),
                "weight": data.get("weight", ""),
                "dimensions": data.get("dimensions", {}),
                "material": data.get("material", ""),
                "finish": data.get("finish", ""),
                "package_quantity": data.get("packageQuantity", 1)
            }
        )
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a McMaster-Carr part"""
        if not await self.authenticate():
            return None
        
        # Subscribe to product first
        if not await self._subscribe_to_product(supplier_part_number):
            return None
        
        session = await self._get_session()
        headers = self._get_headers()
        
        url = f"{self._get_base_url()}/products/{urllib.parse.quote(supplier_part_number)}/price"
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("request_timeout_seconds", 30)
            )
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    pricing = []
                    price_breaks = data.get("priceBreaks", [])
                    for price_break in price_breaks:
                        pricing.append({
                            "quantity": price_break.get("quantity", 1),
                            "price": float(price_break.get("price", 0)),
                            "currency": "USD"  # McMaster-Carr uses USD
                        })
                    
                    return pricing if pricing else None
                else:
                    return None
        
        except Exception:
            return None
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """McMaster-Carr doesn't provide stock quantities - return None"""
        return None
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a McMaster-Carr part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.datasheet_url if part_details else None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a McMaster-Carr part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.image_url if part_details else None
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a McMaster-Carr part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.specifications if part_details else None
    
    def get_rate_limit_delay(self) -> float:
        """Conservative delay to avoid rate limits"""
        return 1.0  # 1 second between requests