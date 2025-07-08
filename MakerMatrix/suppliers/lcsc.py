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
            SupplierCapability.FETCH_PRICING_STOCK,  # Combined pricing and stock information
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
            SupplierCapability.FETCH_PRICING_STOCK: CapabilityRequirement(
                capability=SupplierCapability.FETCH_PRICING_STOCK,
                required_credentials=[],
                description="Fetch pricing and stock information from LCSC"
            )
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for LCSC/EasyEDA public API
        return []
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """
        Get configuration schema for LCSC supplier.
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
        Return configuration options for LCSC API.
        Provides different rate limiting and scraping configurations.
        """
        return [
            ConfigurationOption(
                name='standard',
                label='LCSC Rate Limiting',
                description='Configure rate limiting for responsible LCSC web scraping.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=20,
                        description="Maximum requests per minute for responsible scraping",
                        validation={"min": 1, "max": 60},
                        help_text="Lower values are more respectful to LCSC servers (recommended: 10-20)"
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
                label='LCSC Conservative Rate Limiting',
                description='Very slow rate limiting for bulk operations and maximum server respect.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=10,
                        description="Conservative rate limiting for maximum server respect",
                        validation={"min": 1, "max": 60},
                        help_text="Very conservative rate limiting - best for large batch operations"
                    )
                ],
                is_default=False,
                requirements={
                    'api_key_required': False,
                    'complexity': 'low',
                    'data_type': 'public_api',
                    'prerequisites': ['Internet access']
                }
            )
        ]
    
    def _get_easyeda_api_url(self, lcsc_id: str) -> str:
        """Get EasyEDA API URL for a specific LCSC part"""
        config = self._config or {}  # Handle case where _config might be None
        version = config.get("api_version", "6.4.19.5")  # Internal default, not user-configurable
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
            timeout = config.get("request_timeout", 30)  # Internal default, not user-configurable
            
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
                timeout = config.get("request_timeout", 30)  # Internal default, not user-configurable
                
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
        
        # Always scrape datasheet from LCSC website for accurate URLs
        # The API response often contains incorrect URLs like item.szlcsc.com
        # The correct URLs are always on the product page in format:
        # https://lcsc.com/datasheet/lcsc_datasheet_{timestamp}_{mfr_part}_{lcsc_part}.pdf
        datasheet_url = await self._scrape_lcsc_datasheet(lcsc_id)
        
        # Fallback to API response only if scraping fails
        if not datasheet_url:
            possible_datasheet_paths = [
                ['packageDetail', 'dataStr', 'head', 'c_para', 'link'],
                ['dataStr', 'head', 'c_para', 'link'],
                ['dataStr', 'head', 'c_para', 'Datasheet'],
                ['szlcsc', 'attributes', 'Datasheet'],
                ['attributes', 'Datasheet']
            ]
            
            for path in possible_datasheet_paths:
                api_datasheet_url = self._get_nested_value(result, path)
                if api_datasheet_url and api_datasheet_url.strip():
                    # Only use API URLs that look like proper datasheets
                    if 'datasheet' in api_datasheet_url.lower() or api_datasheet_url.endswith('.pdf'):
                        datasheet_url = api_datasheet_url
                        break
        
        product_url = self._get_nested_value(result, ['szlcsc', 'url'])
        
        # Extract image URL by scraping LCSC website instead of using EasyEDA symbol
        image_url = await self._scrape_lcsc_image(lcsc_id)
        
        # Extract pricing information from LCSC website
        pricing = await self._scrape_lcsc_pricing(lcsc_id)
        
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
            pricing=pricing,  # Scraped from LCSC website
            specifications=specifications if specifications else None,
            additional_data=additional_data
        )
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    
    async def fetch_pricing_stock(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch combined pricing and stock information for an LCSC part"""
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
    
    async def _scrape_lcsc_image(self, lcsc_id: str) -> Optional[str]:
        """Scrape actual part image from LCSC website with simplified, more reliable approach"""
        try:
            session = await self._get_session()
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            # Try direct image URL patterns first (more reliable than HTML scraping)
            direct_image_patterns = [
                f"https://wmsc.lcsc.com/wmsc/upload/image/c_part/{lcsc_id}.jpg",
                f"https://wmsc.lcsc.com/wmsc/upload/image/c_part/{lcsc_id}.png",
                f"https://assets.lcsc.com/images/lcsc/900x900/{lcsc_id}_front.jpg",
                f"https://assets.lcsc.com/images/lcsc/600x600/{lcsc_id}.jpg"
            ]
            
            # Test each direct URL pattern
            for image_url in direct_image_patterns:
                try:
                    async with session.head(image_url, timeout=10) as response:
                        if response.status == 200 and 'image' in response.headers.get('content-type', ''):
                            logger.debug(f"Found direct image for {lcsc_id}: {image_url}")
                            return image_url
                except:
                    continue
            
            # If direct URLs don't work, fall back to HTML scraping
            product_url = f"https://lcsc.com/product-detail/{lcsc_id}.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            async with session.get(product_url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.debug(f"Failed to load LCSC page for {lcsc_id}: status {response.status}")
                    return None
                
                html_content = await response.text()
                import re
                
                # Primary pattern: assets.lcsc.com high-res images
                assets_pattern = r'https://assets\.lcsc\.com/images/lcsc/(?:900x900|600x600)/[^"\s]*\.(?:jpg|jpeg|png)'
                matches = re.findall(assets_pattern, html_content, re.IGNORECASE)
                if matches:
                    logger.debug(f"Found assets.lcsc.com image for {lcsc_id}: {matches[0]}")
                    return matches[0]
                
                # Secondary pattern: wmsc.lcsc.com images
                wmsc_pattern = r'https://wmsc\.lcsc\.com/wmsc/upload/image/[^"\s]*\.(?:jpg|jpeg|png)'
                matches = re.findall(wmsc_pattern, html_content, re.IGNORECASE)
                if matches:
                    logger.debug(f"Found wmsc.lcsc.com image for {lcsc_id}: {matches[0]}")
                    return matches[0]
                
                # Fallback: any LCSC domain image
                lcsc_img_pattern = r'https://[^"\s]*(?:lcsc|szlcsc)[^"\s]*\.(?:jpg|jpeg|png|gif|webp)'
                matches = re.findall(lcsc_img_pattern, html_content, re.IGNORECASE)
                
                # Filter out obvious UI elements
                exclude_patterns = ['logo', 'icon', 'banner', 'header', 'footer', 'nav', 'menu', 'button']
                for img_url in matches:
                    if not any(pattern in img_url.lower() for pattern in exclude_patterns):
                        logger.debug(f"Found fallback LCSC image for {lcsc_id}: {img_url}")
                        return img_url
                
                logger.debug(f"No suitable image found for {lcsc_id}")
                return None
                
        except Exception as e:
            logger.debug(f"Error scraping image for {lcsc_id}: {str(e)}")
            return None
    
    async def _scrape_lcsc_pricing(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Scrape pricing information from LCSC website using multiple strategies"""
        try:
            session = await self._get_session()
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            product_url = f"https://lcsc.com/product-detail/{lcsc_id}.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            async with session.get(product_url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.debug(f"Failed to load LCSC page for pricing {lcsc_id}: status {response.status}")
                    return None
                
                html_content = await response.text()
                import re
                
                pricing_data = {}
                
                # Strategy 1: Extract from meta tags (most reliable)
                meta_price_pattern = r'name="og:product:price"\s+content="([0-9.]+)"'
                meta_match = re.search(meta_price_pattern, html_content)
                
                if meta_match:
                    try:
                        unit_price = float(meta_match.group(1))
                        pricing_data = {
                            "unit_price": unit_price,
                            "currency": "USD",  # LCSC meta tags typically use USD
                            "quantity_breaks": [],
                            "source": "lcsc_meta_tag"
                        }
                        logger.debug(f"Found meta tag pricing for {lcsc_id}: ${unit_price}")
                    except (ValueError, IndexError):
                        pass
                
                # Strategy 2: Extract quantity break pricing from table structure
                # Look for the pricing table with quantity tiers like "100+", "1,000+", etc.
                qty_pricing_pattern = r'aria-label="Change the quantity to(\d+(?:,\d+)*)"[^>]*>.*?<span[^>]*>\$\s*([0-9.]+)</span>'
                qty_matches = re.findall(qty_pricing_pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                if qty_matches:
                    quantity_breaks = []
                    for qty_str, price_str in qty_matches:
                        try:
                            # Remove commas from quantity (e.g., "1,000" -> "1000")
                            quantity = int(qty_str.replace(',', ''))
                            price = float(price_str)
                            quantity_breaks.append({
                                "quantity": quantity,
                                "price": price,
                                "extended_price": quantity * price
                            })
                        except (ValueError, TypeError):
                            continue
                    
                    if quantity_breaks:
                        # Sort by quantity
                        quantity_breaks.sort(key=lambda x: x["quantity"])
                        
                        if pricing_data:
                            pricing_data["quantity_breaks"] = quantity_breaks
                        else:
                            # Use the lowest quantity tier as unit price if no meta tag found
                            pricing_data = {
                                "unit_price": quantity_breaks[0]["price"],
                                "currency": "USD",
                                "quantity_breaks": quantity_breaks,
                                "source": "lcsc_quantity_table"
                            }
                        
                        logger.debug(f"Found {len(quantity_breaks)} quantity tiers for {lcsc_id}")
                
                # Strategy 3: Fallback to simple price pattern matching
                if not pricing_data:
                    price_patterns = [
                        r'\$\s*([0-9]+\.?[0-9]*)',  # Dollar prices with optional $ and spaces
                        r'Price\s*[:\s]*\$?\s*([0-9]+\.?[0-9]*)',  # Price labels
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, html_content, re.IGNORECASE)
                        if matches:
                            try:
                                # Filter out obvious non-price values (like years, part numbers)
                                valid_prices = []
                                for match in matches:
                                    price = float(match)
                                    # Reasonable price range for electronic components
                                    if 0.0001 <= price <= 10000:
                                        valid_prices.append(price)
                                
                                if valid_prices:
                                    # Use the most common price or the first reasonable one
                                    unit_price = min(valid_prices)  # Often the smallest price is the unit price
                                    pricing_data = {
                                        "unit_price": unit_price,
                                        "currency": "USD",
                                        "quantity_breaks": [],
                                        "source": "lcsc_pattern_match"
                                    }
                                    logger.debug(f"Found fallback pricing for {lcsc_id}: ${unit_price}")
                                    break
                            except (ValueError, IndexError):
                                continue
                
                return pricing_data if pricing_data else None
                
        except Exception as e:
            logger.debug(f"Error scraping pricing for {lcsc_id}: {str(e)}")
            return None
    
    async def _scrape_lcsc_datasheet(self, lcsc_id: str) -> Optional[str]:
        """Scrape datasheet URL from LCSC website"""
        try:
            session = await self._get_session()
            config = self._config or {}
            timeout = config.get("request_timeout", 30)
            
            product_url = f"https://lcsc.com/product-detail/{lcsc_id}.html"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            async with session.get(product_url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.debug(f"Failed to load LCSC page for datasheet {lcsc_id}: status {response.status}")
                    return None
                
                html_content = await response.text()
                import re
                
                # Look for datasheet PDF links in the HTML
                # Pattern: https://lcsc.com/datasheet/lcsc_datasheet_*_*_*.pdf
                datasheet_pattern = r'href="(https://lcsc\.com/datasheet/lcsc_datasheet_[^"]*\.pdf)"'
                matches = re.findall(datasheet_pattern, html_content, re.IGNORECASE)
                
                if matches:
                    # Return the first datasheet URL found
                    datasheet_url = matches[0]
                    logger.debug(f"Found datasheet URL for {lcsc_id}: {datasheet_url}")
                    return datasheet_url
                
                # Fallback: look for any PDF link that might be a datasheet
                pdf_pattern = r'href="([^"]*\.pdf)"[^>]*(?:datasheet|spec|specification)'
                pdf_matches = re.findall(pdf_pattern, html_content, re.IGNORECASE)
                
                if pdf_matches:
                    # Convert relative URLs to absolute
                    pdf_url = pdf_matches[0]
                    if pdf_url.startswith('//'):
                        pdf_url = f"https:{pdf_url}"
                    elif pdf_url.startswith('/'):
                        pdf_url = f"https://lcsc.com{pdf_url}"
                    elif not pdf_url.startswith('http'):
                        pdf_url = f"https://lcsc.com/{pdf_url}"
                    
                    logger.debug(f"Found fallback datasheet URL for {lcsc_id}: {pdf_url}")
                    return pdf_url
                
                logger.debug(f"No datasheet URL found for {lcsc_id}")
                return None
                
        except Exception as e:
            logger.debug(f"Error scraping datasheet for {lcsc_id}: {str(e)}")
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
                    # Remove dollar sign and other currency symbols for parsing
                    unit_price_str = unit_price_str.replace('$', '').replace('¥', '').replace('€', '').replace('£', '')
                    unit_price = float(unit_price_str) if unit_price_str else 0.0
                    
                    order_price_str = row.get('Order Price($)', row.get('Subtotal(USD)', '0')).strip()
                    # Remove dollar sign and other currency symbols for parsing
                    order_price_str = order_price_str.replace('$', '').replace('¥', '').replace('€', '').replace('£', '')
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
                        'supplier_part_number': part_number,  # Use dedicated supplier_part_number field for enrichment
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
                            'min_mult_order_qty': row.get('Min\\Mult Order Qty.', '').strip()
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
    
