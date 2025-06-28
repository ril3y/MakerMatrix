"""
LCSC Supplier Implementation

Implements the LCSC (EasyEDA) API interface using the public EasyEDA API.
No authentication required - uses the same API as the existing LCSC parser.
"""

import re
import logging
from typing import List, Dict, Any, Optional

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


@register_supplier("lcsc")
class LCSCSupplier(BaseSupplier):
    """LCSC supplier implementation using public EasyEDA API (no authentication required)"""
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="lcsc",
            display_name="LCSC Electronics",
            description="Chinese electronics component supplier with EasyEDA integration and competitive pricing. Uses web scraping with configurable rate limiting for responsible data access.",
            website_url="https://www.lcsc.com",
            api_documentation_url="https://easyeda.com",
            supports_oauth=False,
            rate_limit_info="Web scraping - configurable rate limiting (default: 20 requests per minute)",
            supported_file_types=["csv"]
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.FETCH_IMAGE,  # Added image support
            SupplierCapability.IMPORT_ORDERS  # Can import CSV order files
        ]
    
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """LCSC uses public API, so no credentials required for any capability"""
        return {
            SupplierCapability.IMPORT_ORDERS: CapabilityRequirement(
                capability=SupplierCapability.IMPORT_ORDERS,
                required_credentials=[],  # No credentials needed
                description="Import LCSC order history from CSV files"
            ),
            SupplierCapability.GET_PART_DETAILS: CapabilityRequirement(
                capability=SupplierCapability.GET_PART_DETAILS,
                required_credentials=[],
                description="Get part details using public EasyEDA API"
            ),
            SupplierCapability.FETCH_DATASHEET: CapabilityRequirement(
                capability=SupplierCapability.FETCH_DATASHEET,
                required_credentials=[],
                description="Fetch datasheet URLs from EasyEDA"
            ),
            SupplierCapability.FETCH_SPECIFICATIONS: CapabilityRequirement(
                capability=SupplierCapability.FETCH_SPECIFICATIONS,
                required_credentials=[],
                description="Fetch part specifications from EasyEDA"
            ),
            SupplierCapability.FETCH_IMAGE: CapabilityRequirement(
                capability=SupplierCapability.FETCH_IMAGE,
                required_credentials=[],
                description="Fetch part images from EasyEDA"
            )
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for LCSC/EasyEDA public API
        return []
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """
        Default configuration schema - returns empty list since we use get_configuration_options() instead.
        This method is kept for abstract class compliance.
        """
        return []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """
        Return configuration options for LCSC API.
        Provides different rate limiting and scraping configurations.
        """
        return [
            ConfigurationOption(
                name='standard',
                label='LCSC Standard Configuration',
                description='Standard configuration for LCSC/EasyEDA API access with moderate rate limiting.',
                schema=[
                    FieldDefinition(
                        name="api_version",
                        label="EasyEDA API Version",
                        field_type=FieldType.TEXT,
                        required=False,
                        default_value="6.4.19.5",
                        description="EasyEDA API version parameter",
                        help_text="Version parameter for EasyEDA API compatibility"
                    ),
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=20,
                        description="Maximum requests per minute for responsible scraping",
                        validation={"min": 1, "max": 60},
                        help_text="Lower values are more respectful to LCSC servers (recommended: 10-20)"
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
                        description="Standard LCSC configuration with moderate rate limiting",
                        help_text="This configuration provides balanced settings for general use. No API key required - uses public EasyEDA API."
                    )
                ],
                is_default=True,
                requirements={
                    'api_key_required': False,
                    'complexity': 'low',
                    'data_type': 'public_api',
                    'prerequisites': ['Internet access']
                }
            ),
            ConfigurationOption(
                name='conservative',
                label='LCSC Conservative Configuration',
                description='Conservative configuration with slower rate limiting for maximum server respect.',
                schema=[
                    FieldDefinition(
                        name="api_version",
                        label="EasyEDA API Version",
                        field_type=FieldType.TEXT,
                        required=False,
                        default_value="6.4.19.5",
                        description="EasyEDA API version parameter",
                        help_text="Version parameter for EasyEDA API compatibility"
                    ),
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=10,
                        description="Conservative rate limiting for maximum server respect",
                        validation={"min": 1, "max": 60},
                        help_text="Very conservative rate limiting - best for large batch operations"
                    ),
                    FieldDefinition(
                        name="request_timeout",
                        label="Request Timeout (seconds)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=45,
                        description="Extended timeout for slower connections",
                        validation={"min": 5, "max": 120},
                        help_text="Extended timeout for reliable operation"
                    ),
                    FieldDefinition(
                        name="custom_headers",
                        label="Custom HTTP Headers",
                        field_type=FieldType.TEXTAREA,
                        required=False,
                        default_value="User-Agent: Mozilla/5.0 (compatible; MakerMatrix/1.0)\nAccept-Language: en-US,en;q=0.9",
                        description="Additional HTTP headers (one per line, format: Header-Name: value)",
                        help_text="Browser-like headers for better compatibility with LCSC servers"
                    ),
                    FieldDefinition(
                        name="conservative_info",
                        label="Conservative Configuration Info",
                        field_type=FieldType.INFO,
                        required=False,
                        description="Conservative LCSC configuration with slower rate limiting",
                        help_text="This configuration prioritizes server respect and reliability over speed. Ideal for bulk operations or automated processes."
                    )
                ],
                is_default=False,
                requirements={
                    'api_key_required': False,
                    'complexity': 'medium',
                    'data_type': 'public_api',
                    'prerequisites': ['Internet access', 'Patience for slower operations']
                }
            )
        ]
    
    def _get_easyeda_api_url(self, lcsc_id: str) -> str:
        """Get EasyEDA API URL for a specific LCSC part"""
        config = self._config or {}  # Handle case where _config might be None
        version = config.get("api_version", "6.4.19.5")
        return f"https://easyeda.com/api/products/{lcsc_id}/components?version={version}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for EasyEDA API calls"""
        headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "MakerMatrix/1.0 (easyeda2kicad compatible)"
        }
        
        # Add custom headers from configuration - handle case where _config might be None
        config = self._config or {}
        custom_headers_text = config.get("custom_headers", "")
        if custom_headers_text and custom_headers_text.strip():
            for line in custom_headers_text.strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    header_name, header_value = line.split(':', 1)
                    headers[header_name.strip()] = header_value.strip()
        
        return headers
    
    async def authenticate(self) -> bool:
        """No authentication required for EasyEDA public API"""
        return True  # Always return True since no authentication is needed
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to EasyEDA API"""
        if not self._configured:
            return {
                "success": False,
                "message": "Supplier not configured. Call .configure() before testing.",
                "details": {"error": "Unconfigured supplier"}
            }
        try:
            # Test with a known LCSC part (resistor)
            test_lcsc_id = "C25804"  # Common 10K resistor
            session = await self._get_session()
            headers = self._get_headers()
            
            url = self._get_easyeda_api_url(test_lcsc_id)
            
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json() or {}  # Defensive null safety
                    if data and "result" in data:
                        return {
                            "success": True,
                            "message": "LCSC/EasyEDA API connection successful",
                            "details": {
                                "api_endpoint": "EasyEDA API",
                                "test_part": test_lcsc_id,
                                "api_version": config.get("api_version", "6.4.19.5"),
                                "rate_limit": f"{config.get('rate_limit_requests_per_minute', 20)} requests per minute",
                                "api_ready": True
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": "API returned empty response",
                            "details": {"response": data}
                        }
                elif response.status == 429:
                    return {
                        "success": False,
                        "message": "Rate limit exceeded",
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
        """
        LCSC/EasyEDA API doesn't support search - only individual part lookup.
        If query looks like an LCSC part number (C followed by digits), try to get part details.
        """
        # Check if query looks like an LCSC part number (e.g., C25804, c123456)
        lcsc_pattern = re.compile(r'^c\d+$', re.IGNORECASE)
        if lcsc_pattern.match(query.strip()):
            part_details = await self.get_part_details(query.strip().upper())
            return [part_details] if part_details else []
        else:
            # For non-LCSC part numbers, return empty list since we can't search
            return []
    
    def _get_nested_value(self, data: Dict[str, Any], keys: List[str], default: Any = "") -> Any:
        """Safely extract a value from nested dictionaries"""
        for key in keys:
            data = data.get(key, {})
            if not data:
                return default
        return data if data != default else default
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific LCSC part using EasyEDA API"""
        async def _impl():
            try:
                # Ensure part number is uppercase and clean
                lcsc_id = supplier_part_number.strip().upper()
                
                session = await self._get_session()
                headers = self._get_headers()
                
                url = self._get_easyeda_api_url(lcsc_id)
                
                config = self._config or {}
                timeout = config.get("request_timeout", 30)
                
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json() or {}  # Defensive null safety
                        if data and "result" in data and data["result"]:
                            return await self._parse_easyeda_response(data, lcsc_id)
                        return None
                    else:
                        return None
            except Exception:
                return None
        
        return await self._tracked_api_call("get_part_details", _impl)
    
    async def _parse_easyeda_response(self, data: Dict[str, Any], lcsc_id: str) -> PartSearchResult:
        """Parse EasyEDA API response into PartSearchResult format"""
        data = data or {}  # Defensive null safety
        result = data.get("result", {}) or {}  # Handle case where result is None
        
        # Extract basic component info using the same paths as the original parser
        manufacturer = self._get_nested_value(result, ['dataStr', 'head', 'c_para', 'Manufacturer'])
        manufacturer_part_number = self._get_nested_value(result, ['dataStr', 'head', 'c_para', 'Manufacturer Part'])
        package = self._get_nested_value(result, ['dataStr', 'head', 'c_para', 'package'])
        value = self._get_nested_value(result, ['dataStr', 'head', 'c_para', 'Value'])
        datasheet_url = self._get_nested_value(result, ['packageDetail', 'dataStr', 'head', 'c_para', 'link'])
        product_url = self._get_nested_value(result, ['szlcsc', 'url'])
        
        # Extract image URL by scraping LCSC website instead of using EasyEDA symbol
        image_url = await self._scrape_lcsc_image(lcsc_id)
        
        # Extract categories from tags
        tags = result.get('tags', [])
        category = tags[0] if tags else ''
        
        # Determine part type and description based on component prefix
        part_type = ""
        prefix = self._get_nested_value(result, ['dataStr', 'head', 'c_para', 'pre'])
        if prefix.startswith('C?'):
            part_type = "capacitor"
        elif prefix.startswith('R?'):
            part_type = "resistor"
        
        # Build description from datasheet URL if available
        description = ""
        if datasheet_url:
            description = datasheet_url.strip("https://lcsc.com/product-detail").replace("-", ", ").rstrip(".html")
        
        # Check if this is SMT
        is_smt = result.get('SMT', False)
        
        # Build specifications dict
        specifications = {}
        if value:
            specifications['Value'] = value
        if package:
            specifications['Package'] = package
        if manufacturer:
            specifications['Manufacturer'] = manufacturer
        if is_smt:
            specifications['Mounting'] = 'SMT'
        
        # Build additional data
        additional_data = {
            "part_type": part_type,
            "is_smt": is_smt,
            "prefix": prefix,
            "easyeda_data_available": True
        }
        
        if product_url:
            additional_data["product_url"] = product_url
        else:
            additional_data["product_url"] = f"https://lcsc.com/product-detail/{lcsc_id}.html"
        
        return PartSearchResult(
            supplier_part_number=lcsc_id,
            manufacturer=manufacturer,
            manufacturer_part_number=manufacturer_part_number,
            description=description,
            category=category or (part_type.title() if part_type else ""),
            datasheet_url=datasheet_url,
            image_url=image_url,
            stock_quantity=None,  # Not available in EasyEDA API response
            pricing=None,  # Not available in EasyEDA API response
            specifications=specifications if specifications else None,
            additional_data=additional_data
        )
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.specifications if part_details else None
        
        return await self._tracked_api_call("fetch_specifications", _impl)
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch component image URL for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.image_url if part_details else None
        
        return await self._tracked_api_call("fetch_image", _impl)
    
    async def _scrape_lcsc_image(self, lcsc_id: str) -> Optional[str]:
        """Scrape actual part image from LCSC website instead of using EasyEDA symbol"""
        try:
            # LCSC product page URL
            product_url = f"https://lcsc.com/product-detail/{lcsc_id}.html"
            
            session = await self._get_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            async with session.get(product_url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Parse HTML to find the product image
                    # LCSC typically has product images in specific div classes or img tags
                    import re
                    
                    # Look for product image patterns in LCSC HTML
                    # Pattern 1: Look for assets.lcsc.com image URLs (user's example pattern)
                    # Example: https://assets.lcsc.com/images/lcsc/900x900/20230121_FOJAN-FRC0603J103-TS_C2930027_front.jpg
                    assets_pattern = r'https://assets\.lcsc\.com/images/lcsc/900x900/[^"\']*\.jpg'
                    matches = re.findall(assets_pattern, html_content, re.IGNORECASE)
                    
                    if matches:
                        return matches[0]  # Return the first assets.lcsc.com image found
                    
                    # Pattern 2: Look for image in v-image component (Vue.js pattern from user's example)
                    vue_image_pattern = r'background-image:\s*url\(["\']?(https://assets\.lcsc\.com/images/[^"\']*)["\']?\)'
                    matches = re.findall(vue_image_pattern, html_content, re.IGNORECASE)
                    
                    if matches:
                        return matches[0]
                    
                    # Pattern 3: LCSC image viewer links (based on user's example)
                    # Example: https://www.lcsc.com/product-detail/image/FRC0603J103-TS_C2930027.html
                    image_link_pattern = r'href="[^"]*product-detail/image/[^"]*\.html"[^>]*>'
                    matches = re.findall(image_link_pattern, html_content, re.IGNORECASE)
                    
                    if matches:
                        # Extract the image link and convert to direct image URL
                        link_match = re.search(r'href="([^"]*product-detail/image/[^"]*\.html)"', matches[0])
                        if link_match:
                            image_page_url = link_match.group(1)
                            if image_page_url.startswith('/'):
                                image_page_url = 'https://lcsc.com' + image_page_url
                            
                            # Extract the part number from the image URL to construct direct image URL
                            # Pattern: /image/PART-NAME_CXXXXXX.html -> should map to actual image
                            part_match = re.search(r'/image/[^_]*_([^\.]+)\.html', image_page_url)
                            if part_match:
                                part_id = part_match.group(1)
                                # Try common LCSC image URL patterns based on user's example
                                possible_image_urls = [
                                    f"https://assets.lcsc.com/images/lcsc/900x900/*_{part_id}_front.jpg",
                                    f"https://wmsc.lcsc.com/wmsc/upload/image/c_part/{part_id}.jpg",
                                    f"https://wmsc.lcsc.com/wmsc/upload/image/c_part/{part_id}.png"
                                ]
                                return possible_image_urls[1]  # Return wmsc pattern since assets pattern needs date prefix
                    
                    # Pattern 2: Direct image tags with product in class or data attributes
                    img_pattern = r'<img[^>]*(?:class="[^"]*product[^"]*"|data-[^=]*="[^"]*product[^"]*")[^>]*src="([^"]+)"'
                    matches = re.findall(img_pattern, html_content, re.IGNORECASE)
                    
                    if matches:
                        img_url = matches[0]
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif img_url.startswith('/'):
                            img_url = 'https://lcsc.com' + img_url
                        return img_url
                    
                    # Pattern 3: Look for images in LCSC's typical image containers
                    lcsc_img_pattern = r'<img[^>]*src="(https?://[^"]*(?:lcsc|szlcsc)[^"]*\.(?:jpg|jpeg|png|gif|webp))"'
                    matches = re.findall(lcsc_img_pattern, html_content, re.IGNORECASE)
                    
                    if matches:
                        # Filter out obvious non-product images
                        for img_url in matches:
                            if not any(pattern in img_url.lower() for pattern in ['logo', 'icon', 'banner', 'header']):
                                return img_url
                    
                    # Pattern 4: General fallback - look for any reasonable product images
                    general_img_pattern = r'<img[^>]*src="(https?://[^"]*\.(?:jpg|jpeg|png|gif|webp))"'
                    all_images = re.findall(general_img_pattern, html_content, re.IGNORECASE)
                    
                    # Filter out common non-product images
                    exclude_patterns = ['logo', 'icon', 'banner', 'header', 'footer', 'nav', 'ads']
                    
                    for img_url in all_images:
                        if not any(pattern in img_url.lower() for pattern in exclude_patterns):
                            # Likely a product image
                            return img_url
                    
            return None
            
        except Exception as e:
            # Don't log as error since this is optional functionality
            return None
    
    def get_rate_limit_delay(self) -> float:
        """LCSC rate limiting based on configuration - default 20 requests per minute"""
        config = self._config or {}
        requests_per_minute = config.get("rate_limit_requests_per_minute", 20)
        # Convert requests per minute to seconds between requests
        # e.g., 20 requests/minute = 60/20 = 3 seconds between requests
        delay = 60.0 / max(requests_per_minute, 1)  # Prevent division by zero
        return delay
    
    # ========== Order Import Implementation ==========
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this supplier can handle this file"""
        # Check if file is CSV
        if not filename.lower().endswith('.csv'):
            return False
        
        # Check filename for LCSC patterns
        lcsc_patterns = ['lcsc', 'bom_szlcsc', 'order_history']
        if any(pattern in filename.lower() for pattern in lcsc_patterns):
            return True
        
        # Check content for LCSC-specific patterns if provided
        if file_content:
            try:
                content_str = file_content.decode('utf-8', errors='ignore')[:1000]  # Check first 1KB
                # Look for LCSC-specific headers or patterns
                lcsc_indicators = [
                    'LCSC Part Number',
                    'Customer NO.',
                    'Product Remark',
                    'Order NO.',
                    'szlcsc.com'
                ]
                return any(indicator in content_str for indicator in lcsc_indicators)
            except:
                pass
        
        return False
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import LCSC order CSV file"""
        if file_type.lower() != 'csv':
            return ImportResult(
                success=False,
                error_message=f"LCSC only supports CSV files, not {file_type}"
            )
        
        try:
            import csv
            import io
            
            # Convert bytes to string
            csv_content = file_content.decode('utf-8')
            
            # Parse CSV using built-in csv module
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            if not rows:
                return ImportResult(
                    success=False,
                    error_message="No data found in CSV file"
                )
            
            # Extract order info from filename if available
            order_info = None
            if filename:
                # LCSC filenames often contain date like LCSC_Exported__20241222_232708.csv
                import re
                date_match = re.search(r'(\d{8})_(\d{6})', filename)
                if date_match:
                    date_str = date_match.group(1)
                    time_str = date_match.group(2)
                    order_info = {
                        'supplier': 'LCSC',
                        'export_date': f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
                        'export_time': f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                    }
            
            # Convert CSV rows to standard format
            import_parts = []
            warnings = []
            
            for idx, row in enumerate(rows):
                try:
                    # Skip rows with empty part numbers
                    part_number = row.get('LCSC Part Number', '').strip()
                    if not part_number:
                        continue
                    
                    # Parse quantity (remove any minimum/multiple order info)
                    qty_str = row.get('Order Qty.', '0').strip()
                    quantity = int(float(qty_str)) if qty_str else 0
                    
                    # Parse prices - LCSC uses Unit Price($) and Order Price($)
                    unit_price_str = row.get('Unit Price($)', row.get('Unit Price(USD)', '0')).strip()
                    unit_price = float(unit_price_str) if unit_price_str else 0.0
                    
                    order_price_str = row.get('Order Price($)', row.get('Subtotal(USD)', '0')).strip()
                    extended_price = float(order_price_str) if order_price_str else (unit_price * quantity)
                    
                    # Extract part name with fallback logic
                    part_name = row.get('Part Name', '').strip()
                    description = row.get('Description', '').strip()
                    manufacturer_part_number = row.get('Manufacture Part Number', row.get('MFR.Part Number', '')).strip()
                    
                    # Use fallback if part name is empty
                    if not part_name:
                        if manufacturer_part_number:
                            part_name = manufacturer_part_number
                        elif description:
                            part_name = description
                        else:
                            part_name = part_number  # Use LCSC part number as last resort
                    
                    # Map LCSC CSV fields to standard part format
                    import_part = {
                        'part_name': part_name,
                        'supplier_part_number': part_number,
                        'manufacturer': row.get('Manufacturer', '').strip(),
                        'manufacturer_part_number': manufacturer_part_number,
                        'description': description,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'extended_price': extended_price,
                        'supplier': 'LCSC',
                        'additional_properties': {
                            'customer_no': row.get('Customer NO.', '').strip(),
                            'package': row.get('Package', '').strip(),
                            'rohs': row.get('RoHS', '').strip(),
                            'min_mult_order_qty': row.get('Min\Mult Order Qty.', '').strip()
                        }
                    }
                    import_parts.append(import_part)
                except (ValueError, TypeError) as e:
                    warnings.append(f"Row {idx + 2}: Error parsing data - {str(e)}")  # +2 for header and 0-index
            
            return ImportResult(
                success=True,
                imported_count=len(import_parts),
                parts=import_parts,
                order_info=order_info,
                parser_type='lcsc',
                warnings=warnings
            )
            
        except Exception as e:
            import traceback
            return ImportResult(
                success=False,
                error_message=f"Error importing LCSC CSV: {str(e)}",
                warnings=[traceback.format_exc()]
            )
    
