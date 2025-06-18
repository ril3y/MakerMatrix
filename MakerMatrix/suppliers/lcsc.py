"""
LCSC Supplier Implementation

Implements the LCSC (EasyEDA) API interface using the public EasyEDA API.
No authentication required - uses the same API as the existing LCSC parser.
"""

from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
import re

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

@register_supplier("lcsc")
class LCSCSupplier(BaseSupplier):
    """LCSC supplier implementation using public EasyEDA API (no authentication required)"""
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="lcsc",
            display_name="LCSC Electronics",
            description="Chinese electronics component supplier with EasyEDA integration and competitive pricing",
            website_url="https://www.lcsc.com",
            api_documentation_url="https://easyeda.com",
            supports_oauth=False,
            rate_limit_info="Public API - reasonable rate limits apply"
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.FETCH_IMAGE  # Added image support
        ]
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for LCSC/EasyEDA public API
        return []
    
    def get_configuration_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_version",
                label="API Version",
                field_type=FieldType.TEXT,
                required=False,
                default_value="6.4.19.5",
                description="EasyEDA API version",
                help_text="Version parameter for EasyEDA API compatibility"
            )
        ]
    
    def _get_easyeda_api_url(self, lcsc_id: str) -> str:
        """Get EasyEDA API URL for a specific LCSC part"""
        version = self._config.get("api_version", "6.4.19.5")
        return f"https://easyeda.com/api/products/{lcsc_id}/components?version={version}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for EasyEDA API calls"""
        return {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "MakerMatrix/1.0 (easyeda2kicad compatible)"
        }
    
    async def authenticate(self) -> bool:
        """No authentication required for EasyEDA public API"""
        return True  # Always return True since no authentication is needed
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to EasyEDA API"""
        try:
            # Test with a known LCSC part (resistor)
            test_lcsc_id = "C25804"  # Common 10K resistor
            session = await self._get_session()
            headers = self._get_headers()
            
            url = self._get_easyeda_api_url(test_lcsc_id)
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "result" in data:
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "details": {
                                "api_endpoint": "EasyEDA API",
                                "test_part": test_lcsc_id,
                                "api_version": self._config.get("api_version", "6.4.19.5")
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
        try:
            # Ensure part number is uppercase and clean
            lcsc_id = supplier_part_number.strip().upper()
            
            session = await self._get_session()
            headers = self._get_headers()
            
            url = self._get_easyeda_api_url(lcsc_id)
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "result" in data and data["result"]:
                        return await self._parse_easyeda_response(data, lcsc_id)
                    return None
                else:
                    return None
        except Exception:
            return None
    
    async def _parse_easyeda_response(self, data: Dict[str, Any], lcsc_id: str) -> PartSearchResult:
        """Parse EasyEDA API response into PartSearchResult format"""
        result = data.get("result", {})
        
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
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.datasheet_url if part_details else None
    
    async def fetch_specifications(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch technical specifications for an LCSC part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.specifications if part_details else None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch component image URL for an LCSC part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.image_url if part_details else None
    
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
            
            async with session.get(product_url, headers=headers) as response:
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
        """EasyEDA API - reasonable rate limiting, 2 seconds between requests"""
        return 2.0