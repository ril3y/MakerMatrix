"""
Mouser Supplier Implementation

Implements the Mouser Electronics API interface using API key authentication.
Supports part search, pricing, stock, datasheets, and comprehensive part data.
"""

from typing import List, Dict, Any, Optional
import aiohttp
import urllib.parse

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

@register_supplier("mouser")
class MouserSupplier(BaseSupplier):
    """Mouser supplier implementation with API key authentication"""
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="mouser",
            display_name="Mouser Electronics",
            description="Electronic component distributor with comprehensive inventory and global shipping",
            website_url="https://www.mouser.com",
            api_documentation_url="https://api.mouser.com/api/docs/ui/index",
            supports_oauth=False,
            rate_limit_info="1000 requests per day for API key users"
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
            SupplierCapability.PARAMETRIC_SEARCH
        ]
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_key",
                label="API Key",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Mouser API key from your Mouser account",
                help_text="Apply for API access through Mouser support. Free for registered users."
            )
        ]
    
    def get_configuration_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="base_url",
                label="API Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://api.mouser.com/api/v1",
                description="Mouser API base URL",
                help_text="Default URL should work for most users"
            ),
            FieldDefinition(
                name="search_option",
                label="Search Option",
                field_type=FieldType.SELECT,
                required=False,
                default_value="None",
                description="Search behavior option",
                options=[
                    {"value": "None", "label": "Default search"},
                    {"value": "ManufacturerPartNumber", "label": "Manufacturer part number only"},
                    {"value": "KeywordSearchInclude", "label": "Include description keywords"},
                ]
            ),
            FieldDefinition(
                name="search_with_your_signup_language",
                label="Use Account Language",
                field_type=FieldType.BOOLEAN,
                required=False,
                default_value=False,
                description="Use language from your Mouser account",
                help_text="If enabled, results will be in your account's language preference"
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get API base URL"""
        return self._config.get("base_url", "https://api.mouser.com/api/v1")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for Mouser API calls"""
        return {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def authenticate(self) -> bool:
        """Test API key authentication"""
        if not self.is_configured():
            raise SupplierConfigurationError("Supplier not configured", supplier_name="mouser")
        
        api_key = self._credentials.get("api_key")
        if not api_key:
            return False
        
        # Test with a simple API call
        try:
            result = await self.test_connection()
            return result.get("success", False)
        except Exception:
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Mouser API"""
        try:
            api_key = self._credentials.get("api_key")
            if not api_key:
                return {
                    "success": False,
                    "message": "No API key provided",
                    "details": {"requires": "Valid Mouser API key"}
                }
            
            # Test with a lightweight search
            session = await self._get_session()
            headers = self._get_headers()
            
            url = f"{self._get_base_url()}/search/keyword"
            params = {
                "apiKey": api_key
            }
            
            search_data = {
                "SearchByKeywordRequest": {
                    "keyword": "resistor",
                    "records": 1,
                    "startingRecord": 0
                }
            }
            
            async with session.post(url, headers=headers, params=params, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    search_results = data.get("SearchResults", {})
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "details": {
                            "api_version": "v1",
                            "base_url": self._get_base_url(),
                            "test_results": f"Found {search_results.get('NumberOfResult', 0)} components"
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
                        "message": "Invalid API key",
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
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using Mouser API"""
        if not await self.authenticate():
            raise SupplierAuthenticationError("Authentication required", supplier_name="mouser")
        
        session = await self._get_session()
        headers = self._get_headers()
        api_key = self._credentials.get("api_key")
        
        url = f"{self._get_base_url()}/search/keyword"
        params = {
            "apiKey": api_key
        }
        
        search_data = {
            "SearchByKeywordRequest": {
                "keyword": query,
                "records": min(limit, 100),  # Mouser allows up to 100 records
                "startingRecord": 0,
                "searchOptions": self._config.get("search_option", "None"),
                "searchWithYourSignUpLanguage": self._config.get("search_with_your_signup_language", False)
            }
        }
        
        try:
            async with session.post(url, headers=headers, params=params, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_search_results(data)
                elif response.status == 429:
                    raise SupplierRateLimitError("Rate limit exceeded", supplier_name="mouser")
                else:
                    error_text = await response.text()
                    raise SupplierConnectionError(
                        f"Search failed: {response.status} - {error_text}",
                        supplier_name="mouser"
                    )
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(
                f"Network error during search: {str(e)}",
                supplier_name="mouser"
            )
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[PartSearchResult]:
        """Parse Mouser search response into PartSearchResult objects"""
        results = []
        search_results = data.get("SearchResults", {})
        parts = search_results.get("Parts", [])
        
        for part in parts:
            # Parse pricing
            pricing = []
            price_breaks = part.get("PriceBreaks", [])
            for price_break in price_breaks:
                pricing.append({
                    "quantity": price_break.get("Quantity", 1),
                    "price": float(price_break.get("Price", "0").replace("$", "").replace(",", "")),
                    "currency": price_break.get("Currency", "USD")
                })
            
            # Parse product attributes/specifications
            specifications = {}
            attributes = part.get("ProductAttributes", [])
            for attr in attributes:
                attr_name = attr.get("AttributeName", "")
                attr_value = attr.get("AttributeValue", "")
                if attr_name and attr_value:
                    specifications[attr_name] = attr_value
            
            # Get availability info
            availability_info = part.get("Availability", "")
            stock_qty = 0
            try:
                # Extract number from availability string like "5,234 In Stock"
                if "In Stock" in availability_info:
                    stock_str = availability_info.split(" In Stock")[0].replace(",", "")
                    stock_qty = int(stock_str)
            except:
                stock_qty = 0
            
            result = PartSearchResult(
                supplier_part_number=part.get("MouserPartNumber", ""),
                manufacturer=part.get("Manufacturer", ""),
                manufacturer_part_number=part.get("ManufacturerPartNumber", ""),
                description=part.get("Description", ""),
                category=part.get("Category", ""),
                datasheet_url=part.get("DataSheetUrl", ""),
                image_url=part.get("ImagePath", ""),
                stock_quantity=stock_qty,
                pricing=pricing if pricing else None,
                specifications=specifications if specifications else None,
                additional_data={
                    "product_detail_url": part.get("ProductDetailUrl", ""),
                    "lifecycle_status": part.get("LifecycleStatus", ""),
                    "lead_time": part.get("LeadTime", ""),
                    "min_order_qty": part.get("Min", 1),
                    "mult_order_qty": part.get("Mult", 1),
                    "rohs_status": part.get("RohsStatus", ""),
                    "packaging": part.get("SuggestedReplacement", "")
                }
            )
            results.append(result)
        
        return results
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific Mouser part"""
        if not await self.authenticate():
            raise SupplierAuthenticationError("Authentication required", supplier_name="mouser")
        
        session = await self._get_session()
        headers = self._get_headers()
        api_key = self._credentials.get("api_key")
        
        url = f"{self._get_base_url()}/search/partnumber"
        params = {
            "apiKey": api_key
        }
        
        search_data = {
            "SearchByPartRequest": {
                "mouserPartNumber": supplier_part_number,
                "partSearchOptions": self._config.get("search_option", "None")
            }
        }
        
        try:
            async with session.post(url, headers=headers, params=params, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    search_results = data.get("SearchResults", {})
                    parts = search_results.get("Parts", [])
                    if parts:
                        # Return first matching part with detailed info
                        return self._parse_search_results(data)[0]
                    return None
                else:
                    return None
        except Exception:
            return None
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a Mouser part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.pricing if part_details else None
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Fetch current stock level for a Mouser part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.stock_quantity if part_details else None
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a Mouser part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.datasheet_url if part_details else None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a Mouser part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.image_url if part_details else None
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a Mouser part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.specifications if part_details else None
    
    def get_rate_limit_delay(self) -> float:
        """Mouser rate limit: 1000 requests/day = ~86 seconds between requests for sustained use"""
        return 90.0  # Conservative delay to avoid rate limiting