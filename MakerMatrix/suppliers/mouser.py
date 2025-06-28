"""
Mouser Supplier Implementation

Implements the Mouser Electronics API interface using API key authentication.
Supports part search, pricing, stock, datasheets, and comprehensive part data.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import aiohttp

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

@register_supplier("mouser")
class MouserSupplier(BaseSupplier):
    """Mouser supplier implementation with API key authentication"""
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="mouser",
            display_name="Mouser Electronics",
            description="Global electronic component distributor offering instant API access with keyword/part number search, up to 50 results per call. Provides comprehensive data including availability, pricing (4 price breaks), datasheets, images, specifications, and lifecycle status.",
            website_url="https://www.mouser.com",
            api_documentation_url="https://api.mouser.com/api/docs/V1",
            supports_oauth=False,
            rate_limit_info="30 calls per minute, 1000 calls per day (free tier with instant access)",
            supported_file_types=["xls", "xlsx"]  # Mouser exports order files in Excel format
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.SEARCH_PARTS,           # Search by keyword/part number
            SupplierCapability.GET_PART_DETAILS,       # Complete part information
            SupplierCapability.FETCH_DATASHEET,        # Data Sheet URL
            SupplierCapability.FETCH_IMAGE,            # Image URL
            SupplierCapability.FETCH_PRICING,          # Pricing (up to 4 price breaks)
            SupplierCapability.FETCH_STOCK,            # Availability
            SupplierCapability.FETCH_SPECIFICATIONS,   # Product attributes, RoHS, lifecycle
            SupplierCapability.PARAMETRIC_SEARCH,      # Enhanced search capabilities
            SupplierCapability.IMPORT_ORDERS           # Import Mouser order Excel files
        ]

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Define what credentials each capability needs"""
        api_key_req = ["api_key"]
        requirements = {}
        
        # Most capabilities require API key
        for capability in self.get_capabilities():
            if capability == SupplierCapability.IMPORT_ORDERS:
                # Order import doesn't need API key
                requirements[capability] = CapabilityRequirement(
                    capability=capability,
                    required_credentials=[],
                    description="Import Mouser order history from Excel exports"
                )
            else:
                requirements[capability] = CapabilityRequirement(
                    capability=capability,
                    required_credentials=api_key_req
                )
        
        return requirements
    
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
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """
        Get configuration schema for Mouser supplier.
        Returns fields from the default configuration option for frontend compatibility.
        """
        # Get the default configuration option and return its schema fields
        config_options = self.get_configuration_options()
        default_option = next((opt for opt in config_options if opt.is_default), None)
        
        if default_option:
            return default_option.schema
        else:
            # Fallback to standard option if no default found
            standard_option = next((opt for opt in config_options if opt.name == 'standard'), None)
            return standard_option.schema if standard_option else []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """
        Return configuration options for Mouser API.
        Provides different configuration presets for various use cases.
        """
        return [
            ConfigurationOption(
                name='standard',
                label='Mouser Standard Configuration',
                description='Standard configuration for Mouser API access with optimal search settings.',
                schema=[
                    FieldDefinition(
                        name="search_option",
                        label="Search Behavior",
                        field_type=FieldType.SELECT,
                        required=False,
                        default_value="None",
                        description="How to perform part number searches",
                        options=[
                            {"value": "None", "label": "Default search (recommended)"},
                            {"value": "ManufacturerPartNumber", "label": "Exact manufacturer part number only"},
                            {"value": "KeywordSearchInclude", "label": "Include description keywords"},
                        ],
                        help_text="Default search works best for most use cases"
                    ),
                    FieldDefinition(
                        name="search_with_your_signup_language",
                        label="Use Account Language",
                        field_type=FieldType.BOOLEAN,
                        required=False,
                        default_value=False,
                        description="Use the language preference from your Mouser account",
                        help_text="Enable if you need results in your account's configured language"
                    ),
                    FieldDefinition(
                        name="request_timeout",
                        label="Request Timeout (seconds)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=30,
                        description="API request timeout in seconds",
                        validation={"min": 5, "max": 120},
                        help_text="Increase if you experience timeout errors (5-120 seconds)"
                    ),
                    FieldDefinition(
                        name="standard_info",
                        label="Configuration Info",
                        field_type=FieldType.INFO,
                        required=False,
                        description="Standard Mouser API configuration",
                        help_text="This configuration provides balanced settings for most use cases. API key required for all features except order import."
                    )
                ],
                is_default=True,
                requirements={
                    'api_key_required': True,
                    'complexity': 'low',
                    'data_type': 'live_data',
                    'prerequisites': ['Mouser account', 'API key from Mouser support']
                }
            ),
            ConfigurationOption(
                name='advanced',
                label='Mouser Advanced Configuration',
                description='Advanced configuration with custom headers and enhanced search options.',
                schema=[
                    FieldDefinition(
                        name="search_option",
                        label="Search Behavior",
                        field_type=FieldType.SELECT,
                        required=False,
                        default_value="KeywordSearchInclude",
                        description="How to perform part number searches",
                        options=[
                            {"value": "None", "label": "Default search"},
                            {"value": "ManufacturerPartNumber", "label": "Exact manufacturer part number only"},
                            {"value": "KeywordSearchInclude", "label": "Include description keywords"},
                        ],
                        help_text="Advanced search includes description keywords by default"
                    ),
                    FieldDefinition(
                        name="search_with_your_signup_language",
                        label="Use Account Language",
                        field_type=FieldType.BOOLEAN,
                        required=False,
                        default_value=True,
                        description="Use the language preference from your Mouser account",
                        help_text="Enabled by default for localized results"
                    ),
                    FieldDefinition(
                        name="request_timeout",
                        label="Request Timeout (seconds)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=60,
                        description="API request timeout in seconds",
                        validation={"min": 5, "max": 120},
                        help_text="Extended timeout for complex searches"
                    ),
                    FieldDefinition(
                        name="custom_headers",
                        label="Custom HTTP Headers",
                        field_type=FieldType.TEXT,
                        required=False,
                        description="Custom headers for API requests (one per line: Header-Name: value)",
                        help_text="Advanced users only. Format: 'Header-Name: value' (one per line)"
                    ),
                    FieldDefinition(
                        name="advanced_info",
                        label="Advanced Configuration Info",
                        field_type=FieldType.INFO,
                        required=False,
                        description="Advanced Mouser API configuration with custom options",
                        help_text="This configuration provides enhanced search capabilities and custom header support for advanced integrations."
                    )
                ],
                is_default=False,
                requirements={
                    'api_key_required': True,
                    'complexity': 'medium',
                    'data_type': 'live_data',
                    'prerequisites': ['Mouser account', 'API key from Mouser support', 'Advanced API knowledge']
                }
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get API base URL"""
        config = self._config or {}  # Handle case where _config might be None
        return config.get("base_url", "https://api.mouser.com/api/v1")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for Mouser API calls"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add custom headers from configuration
        config = self._config or {}  # Handle case where _config might be None
        custom_headers_text = config.get("custom_headers", "")
        if custom_headers_text and custom_headers_text.strip():
            for line in custom_headers_text.strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    header_name, header_value = line.split(':', 1)
                    headers[header_name.strip()] = header_value.strip()
        
        return headers
    
    async def authenticate(self) -> bool:
        """Authenticate with Mouser API using API key"""
        if not self.is_configured():
            raise SupplierConfigurationError(
                "Mouser supplier not configured. Please provide API key.", 
                supplier_name="mouser",
                details={'missing_config': ['api_key']}
            )
        
        # Validate required credentials - handle case where _credentials might be None
        credentials = self._credentials or {}
        api_key = credentials.get('api_key', '').strip()
        
        if not api_key:
            raise SupplierConfigurationError(
                "Mouser requires an API key",
                supplier_name="mouser",
                details={
                    'missing_credentials': ['api_key']
                }
            )
        
        try:
            # Test authentication with a simple API call (without calling test_connection to avoid recursion)
            session = await self._get_session()
            headers = self._get_headers()
            
            url = f"{self._get_base_url()}/search/keyword"
            params = {"apiKey": api_key}
            
            search_data = {
                "SearchByKeywordRequest": {
                    "keyword": "test",
                    "records": 1,
                    "startingRecord": 0
                }
            }
            
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            async with session.post(url, headers=headers, params=params, json=search_data, timeout=timeout) as response:
                # Any response (even error) means API key is being accepted
                return response.status in [200, 400, 401, 403]  # 401/403 means API key was processed
                
        except SupplierError:
            # Re-raise supplier errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise SupplierAuthenticationError(
                f"Mouser authentication failed: {str(e)}",
                supplier_name="mouser",
                details={
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Mouser API"""
        logger.info("🚨 MOUSER TEST_CONNECTION METHOD CALLED!")
        try:
            # Check if supplier is configured first
            if not self.is_configured():
                return {
                    "success": False,
                    "message": "Mouser not configured",
                    "details": {
                        "error": "Missing credentials: API key required",
                        "configuration_needed": True,
                        "required_fields": ["api_key"],
                        "setup_url": "https://www.mouser.com/api-signup/",
                        "instructions": "1. Sign up for Mouser API access\\n2. Contact Mouser support to request API key\\n3. Add your API key to MakerMatrix"
                    }
                }
            
            # Check for credentials - handle case where _credentials might be None
            credentials = self._credentials or {}
            api_key = credentials.get('api_key', '').strip()
            
            if not api_key:
                return {
                    "success": False,
                    "message": "Missing Mouser API key",
                    "details": {
                        "error": "API key is required",
                        "configuration_needed": True,
                        "missing_credentials": ["api_key"],
                        "setup_url": "https://www.mouser.com/api-signup/"
                    }
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
            
            config = self._config or {}  # Handle case where _config might be None
            timeout = config.get("request_timeout", 30)
            
            async with session.post(url, headers=headers, params=params, json=search_data, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    data = data or {}  # Handle case where response.json() returns None
                    search_results = data.get("SearchResults", {}) or {}  # Handle case where SearchResults is None
                    return {
                        "success": True,
                        "message": "Mouser API connection successful",
                        "details": {
                            "api_version": "v1",
                            "base_url": self._get_base_url(),
                            "test_results": f"Found {search_results.get('NumberOfResult', 0)} components",
                            "rate_limit": "30 calls per minute, 1000 calls per day",
                            "api_ready": True
                        }
                    }
                elif response.status == 429:
                    return {
                        "success": False,
                        "message": "Rate limit exceeded",
                        "details": {
                            "error": "Too many API requests",
                            "status_code": response.status,
                            "rate_limit": "30 calls per minute, 1000 calls per day",
                            "suggestion": "Wait before retrying or upgrade API plan"
                        }
                    }
                elif response.status == 401:
                    return {
                        "success": False,
                        "message": "Invalid API key",
                        "details": {
                            "error": "API key authentication failed",
                            "status_code": response.status,
                            "configuration_needed": True,
                            "setup_url": "https://www.mouser.com/api-signup/"
                        }
                    }
                elif response.status == 403:
                    return {
                        "success": False,
                        "message": "API access forbidden",
                        "details": {
                            "error": "API key may not have required permissions",
                            "status_code": response.status,
                            "suggestion": "Contact Mouser support to verify API access"
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "message": f"Mouser API error: {response.status}",
                        "details": {
                            "error": error_text,
                            "status_code": response.status,
                            "api_call_failed": True,
                            "suggestion": "Check API key and network connectivity"
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
                    "traceback": tb,
                    "unexpected_error": True
                }
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using Mouser API"""
        if not await self.authenticate():
            raise SupplierAuthenticationError("Authentication required", supplier_name="mouser")
        
        session = await self._get_session()
        headers = self._get_headers()
        credentials = self._credentials or {}
        api_key = credentials.get("api_key")
        
        url = f"{self._get_base_url()}/search/keyword"
        params = {
            "apiKey": api_key
        }
        
        config = self._config or {}  # Handle case where _config might be None
        search_data = {
            "SearchByKeywordRequest": {
                "keyword": query,
                "records": min(limit, 100),  # Mouser allows up to 100 records
                "startingRecord": 0,
                "searchOptions": config.get("search_option", "None"),
                "searchWithYourSignUpLanguage": config.get("search_with_your_signup_language", False)
            }
        }
        
        try:
            async with session.post(url, headers=headers, params=params, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    data = data or {}  # Handle case where response.json() returns None
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
        data = data or {}  # Handle case where data is None
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
        credentials = self._credentials or {}
        api_key = credentials.get("api_key")
        
        url = f"{self._get_base_url()}/search/partnumber"
        params = {
            "apiKey": api_key
        }
        
        config = self._config or {}  # Handle case where _config might be None
        search_data = {
            "SearchByPartRequest": {
                "mouserPartNumber": supplier_part_number,
                "partSearchOptions": config.get("search_option", "None")
            }
        }
        
        try:
            async with session.post(url, headers=headers, params=params, json=search_data) as response:
                if response.status == 200:
                    data = await response.json()
                    data = data or {}  # Handle case where response.json() returns None
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
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.pricing if part_details else None
        
        return await self._tracked_api_call("fetch_pricing", _impl)
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Fetch current stock level for a Mouser part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.stock_quantity if part_details else None
        
        return await self._tracked_api_call("fetch_stock", _impl)
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a Mouser part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a Mouser part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.image_url if part_details else None
        
        return await self._tracked_api_call("fetch_image", _impl)
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for a Mouser part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.specifications if part_details else None
        
        return await self._tracked_api_call("fetch_specifications", _impl)
    
    def get_rate_limit_delay(self) -> float:
        """Mouser rate limit: 30 calls per minute = 2 seconds between requests"""
        return 2.0  # Conservative delay to stay under 30 calls/minute
    
    # ========== Order Import Implementation ==========
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this is a Mouser Excel file"""
        filename_lower = filename.lower()
        
        # Check file extension - Mouser uses Excel formats
        if not filename_lower.endswith(('.xls', '.xlsx')):
            return False
        
        # Check filename patterns - if Mouser pattern found, we can handle it
        mouser_patterns = ['mouser', 'mouse', 'order', 'cart']
        if any(pattern in filename_lower for pattern in mouser_patterns):
            return True
        
        # Check content for Mouser-specific patterns
        if file_content:
            try:
                import pandas as pd
                import io
                df = pd.read_excel(io.BytesIO(file_content), nrows=10)  # Read first 10 rows
                
                # Check column headers for Mouser patterns
                if not df.empty:
                    headers = ' '.join(str(col).lower() for col in df.columns)
                    mouser_indicators = [
                        'mouser part', 'mouser p/n', 'part number', 'mouse part',
                        'manufacturer part number', 'quantity', 'unit price',
                        'extended price', 'customer part'
                    ]
                    if any(indicator in headers for indicator in mouser_indicators):
                        return True
            except Exception:
                # If we can't read the Excel file, but extension is supported, allow it
                return True
        
        # If no content provided but extension is supported, allow it for now
        return True
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import Mouser order Excel file"""
        file_type_lower = file_type.lower()
        
        if file_type_lower not in ['xls', 'xlsx']:
            return ImportResult(
                success=False,
                error_message=f"Mouser uses Excel format (.xls/.xlsx), not {file_type}. Please download your Mouser order as Excel."
            )
        
        try:
            import pandas as pd
            import io
            
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            parts = []
            errors = []
            
            # Try to detect Mouser Excel format
            columns = [col.lower() for col in df.columns]
            
            # Common Mouser column mappings
            column_mappings = {
                'part_number': ['mouser #:', 'mouser part #', 'mouser part number', 'part number', 'mouser p/n'],
                'manufacturer': ['manufacturer', 'mfr', 'mfg'],
                'manufacturer_part_number': ['mfr. #:', 'manufacturer part number', 'mfr part #', 'mfg part #', 'customer #'],
                'description': ['desc.:', 'description', 'product description'],
                'quantity': ['order qty.', 'quantity', 'qty', 'order qty'],
                'unit_price': ['price (usd)', 'unit price', 'price', 'unit cost'],
                'extended_price': ['ext. (usd)', 'extended price', 'total price', 'line total']
            }
            
            # Find actual column names
            mapped_columns = {}
            for field, possible_names in column_mappings.items():
                for possible_name in possible_names:
                    matching_cols = [col for col in df.columns if possible_name.lower() in col.lower()]
                    if matching_cols:
                        mapped_columns[field] = matching_cols[0]
                        break
            
            # Validate we have minimum required columns
            required_fields = ['part_number', 'quantity']
            missing_fields = [field for field in required_fields if field not in mapped_columns]
            
            if missing_fields:
                return ImportResult(
                    success=False,
                    error_message=f"Missing required columns: {', '.join(missing_fields)}",
                    warnings=[f"Available columns: {', '.join(df.columns)}"]
                )
            
            # Parse rows
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get(mapped_columns['part_number'], '')) or row.get(mapped_columns['part_number'], '').strip() == '':
                        continue
                    
                    # Extract pricing values
                    unit_price = 0.0
                    extended_price = 0.0
                    
                    if 'unit_price' in mapped_columns:
                        unit_price_str = str(row.get(mapped_columns['unit_price'], '0')).replace('$', '').replace(',', '').strip()
                        try:
                            unit_price = float(unit_price_str) if unit_price_str else 0.0
                        except ValueError:
                            unit_price = 0.0
                    
                    if 'extended_price' in mapped_columns:
                        extended_price_str = str(row.get(mapped_columns['extended_price'], '0')).replace('$', '').replace(',', '').strip()
                        try:
                            extended_price = float(extended_price_str) if extended_price_str else 0.0
                        except ValueError:
                            extended_price = 0.0
                    
                    # Extract quantity
                    quantity_str = str(row.get(mapped_columns['quantity'], '0')).replace(',', '').strip()
                    try:
                        quantity = int(float(quantity_str)) if quantity_str else 0
                    except ValueError:
                        quantity = 0
                    
                    part = {
                        'part_name': str(row.get(mapped_columns.get('description', ''), 
                                               row.get(mapped_columns.get('manufacturer_part_number', ''), ''))).strip(),
                        'part_number': str(row.get(mapped_columns['part_number'], '')).strip(),  # Changed from supplier_part_number to part_number
                        'manufacturer': str(row.get(mapped_columns.get('manufacturer', ''), '')).strip(),
                        'manufacturer_part_number': str(row.get(mapped_columns.get('manufacturer_part_number', ''), '')).strip(),
                        'description': str(row.get(mapped_columns.get('description', ''), '')).strip(),
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'currency': 'USD',  # Mouser pricing is typically in USD
                        'supplier': 'Mouser',
                        'additional_properties': {
                            'row_index': index + 1,
                            'extended_price': extended_price  # Move extended_price to additional_properties
                        }
                    }
                    
                    # Use manufacturer part number as part name if description is empty
                    if not part['part_name'] and part['manufacturer_part_number']:
                        part['part_name'] = part['manufacturer_part_number']
                    
                    # Only add parts with valid part numbers
                    if part['part_number']:
                        parts.append(part)
                        
                except Exception as e:
                    errors.append(f"Error parsing row {index + 1}: {str(e)}")
            
            if not parts:
                return ImportResult(
                    success=False,
                    error_message="No valid parts found in Excel file",
                    warnings=errors
                )
            
            return ImportResult(
                success=True,
                imported_count=len(parts),
                parts=parts,
                parser_type='mouser',
                warnings=errors if errors else []
            )
            
        except Exception as e:
            import traceback
            return ImportResult(
                success=False,
                error_message=f"Error importing Mouser Excel file: {str(e)}",
                warnings=[traceback.format_exc()]
            )