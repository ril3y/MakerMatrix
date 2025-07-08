"""
Bolt Depot Supplier Implementation

Implements web scraping for BoltDepot.com using BeautifulSoup to extract
part details, pricing, and specifications from product pages.
"""

from typing import List, Dict, Any, Optional
import aiohttp
import re
from bs4 import BeautifulSoup
from decimal import Decimal
import logging

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, CapabilityRequirement
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

logger = logging.getLogger(__name__)

@register_supplier("bolt-depot")
class BoltDepotSupplier(BaseSupplier):
    """Bolt Depot supplier implementation using web scraping"""
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="bolt-depot",
            display_name="Bolt Depot",
            description="Specialty fastener supplier offering bolts, screws, nuts, washers, and threaded rod. Uses web scraping to extract product details, pricing, and specifications from product pages.",
            website_url="https://boltdepot.com",
            api_documentation_url=None,  # No official API - uses web scraping
            supports_oauth=False,
            rate_limit_info="Conservative delays to respect website resources. Recommend 2-3 second delays between requests."
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,       # Scrape individual product pages
            SupplierCapability.FETCH_PRICING_STOCK,    # Extract pricing and availability data
        ]

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Bolt Depot uses web scraping, so no credentials required for any capability"""
        return {
            capability: CapabilityRequirement(
                capability=capability,
                required_credentials=[]
            )
            for capability in self.get_capabilities()
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for public web scraping
        return []
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="base_url",
                label="Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://boltdepot.com",
                description="Bolt Depot website base URL",
                help_text="Default URL should work for most users"
            ),
            FieldDefinition(
                name="request_delay_seconds",
                label="Request Delay (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=2.0,
                description="Delay between requests to be respectful to the website",
                validation={"min": 1.0, "max": 10.0},
                help_text="Recommended: 2-3 seconds to avoid overloading the server"
            ),
            FieldDefinition(
                name="timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="HTTP request timeout in seconds",
                validation={"min": 5, "max": 120},
                help_text="How long to wait for page responses"
            ),
            FieldDefinition(
                name="user_agent",
                label="User Agent String",
                field_type=FieldType.TEXT,
                required=False,
                default_value="MakerMatrix/1.0 (Inventory Management System)",
                description="User agent string for HTTP requests",
                help_text="Identifies your application to the website"
            ),
            FieldDefinition(
                name="enable_caching",
                label="Enable Response Caching",
                field_type=FieldType.BOOLEAN,
                required=False,
                default_value=True,
                description="Cache scraped pages to reduce server load",
                help_text="Recommended to enable for better performance and server courtesy"
            )
        ]
    
    def _get_base_url(self) -> str:
        """Get base URL for Bolt Depot"""
        return self._config.get("base_url", "https://boltdepot.com")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests"""
        return {
            "User-Agent": self._config.get("user_agent", "MakerMatrix/1.0 (Inventory Management System)"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def authenticate(self) -> bool:
        """No authentication required for public web scraping"""
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Bolt Depot website"""
        if not self._configured:
            return {
                "success": False,
                "message": "Supplier not configured. Call .configure() before testing.",
                "details": {"error": "Unconfigured supplier"}
            }
        try:
            session = await self._get_session()
            headers = self._get_headers()
            
            url = self._get_base_url()
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("timeout_seconds", 30)
            )
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Check if this looks like the Bolt Depot website
                    title = soup.find('title')
                    title_text = title.get_text() if title else ""
                    
                    if "bolt depot" in title_text.lower():
                        return {
                            "success": True,
                            "message": "Connection successful",
                            "details": {
                                "base_url": url,
                                "page_title": title_text.strip(),
                                "status_code": response.status
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Website content doesn't match expected Bolt Depot format",
                            "details": {"page_title": title_text.strip()}
                        }
                else:
                    return {
                        "success": False,
                        "message": f"HTTP error: {response.status}",
                        "details": {"status_code": response.status}
                    }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """
        Search not directly supported - Bolt Depot requires browsing by category.
        This method will try to treat the query as a product number.
        """
        # Try to get part details directly if query looks like a product number
        if query.isdigit():
            part_details = await self.get_part_details(query)
            if part_details:
                return [part_details]
        
        # Could implement category browsing here in the future
        return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific Bolt Depot part"""
        try:
            if not supplier_part_number.isdigit():
                logger.warning(f"Bolt Depot part number should be numeric: {supplier_part_number}")
                return None
            
            session = await self._get_session()
            headers = self._get_headers()
            
            # Construct product URL
            base_url = self._get_base_url()
            url = f"{base_url}/Product-Details?product={supplier_part_number}"
            
            timeout = aiohttp.ClientTimeout(
                total=self._config.get("timeout_seconds", 30)
            )
            
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch product {supplier_part_number}: HTTP {response.status}")
                    return None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                return self._parse_product_page(soup, supplier_part_number, url)
        
        except Exception as e:
            logger.error(f"Error fetching part details for {supplier_part_number}: {e}")
            return None
    
    def _parse_product_page(self, soup: BeautifulSoup, part_number: str, url: str) -> Optional[PartSearchResult]:
        """Parse a Bolt Depot product page"""
        try:
            # Extract product details from the details table
            details = self._extract_product_details(soup)
            
            # Extract pricing information
            pricing = self._extract_pricing(soup, part_number)
            
            # Extract image URL
            image_url = self._extract_image_url(soup)
            
            # Get category and description from details
            category = details.get("Category", "")
            description = self._build_description(details)
            
            # Remove category from additional_data since it's redundant
            additional_data = {k: v for k, v in details.items() if k.lower() != "category"}
            
            return PartSearchResult(
                supplier_part_number=part_number,
                manufacturer="Bolt Depot",
                manufacturer_part_number=part_number,
                description=description,
                category=category,
                datasheet_url=None,  # Bolt Depot doesn't provide datasheets
                image_url=image_url,
                stock_quantity=None,  # Not available from scraping
                pricing=pricing,
                specifications=None,  # Using additional_data instead
                additional_data=additional_data
            )
        
        except Exception as e:
            logger.error(f"Error parsing product page for {part_number}: {e}")
            return None
    
    def _extract_product_details(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract product details from the product-details-table"""
        details = {}
        
        # Find the product details table
        details_table = soup.find('table', class_='product-details-table')
        if not details_table:
            logger.warning("Product details table not found")
            return details
        
        # Extract all property rows
        for row in details_table.find_all('tr'):
            property_name_cell = row.find('td', class_='property-name')
            property_value_cell = row.find('td', class_='property-value')
            
            if property_name_cell and property_value_cell:
                # Get the property name
                prop_name = property_name_cell.get_text().strip()
                
                # Get the property value (main text, excluding value-message divs)
                prop_value = ""
                for content in property_value_cell.contents:
                    if hasattr(content, 'name'):
                        # Skip value-message divs
                        if content.name == 'div' and 'value-message' in content.get('class', []):
                            continue
                        prop_value += content.get_text().strip()
                    else:
                        # Text node
                        prop_value += str(content).strip()
                
                if prop_name and prop_value:
                    details[prop_name] = prop_value
        
        return details
    
    def _extract_pricing(self, soup: BeautifulSoup, part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Extract pricing information from the product table"""
        pricing = []
        
        # Find the product table row for this part number
        product_row = soup.find('tr', id=f'p{part_number}')
        if not product_row:
            logger.warning(f"Product row not found for part {part_number}")
            return None
        
        # Extract pricing from different columns
        price_cells = product_row.find_all('td', class_='cell-price')
        if not price_cells:
            price_cells = product_row.find_all('td', class_='cell-price-single')
        
        for cell in price_cells:
            price_breaks = cell.find_all('span', class_='price-break')
            for price_break in price_breaks:
                price_text = price_break.get_text().strip()
                
                # Parse price and quantity
                # Format: "$0.25 / ea" or "$19.13 / 100" or "$168.00 / 1,000"
                match = re.search(r'\$(\d+(?:\.\d{2})?)\s*/\s*(\d+(?:,\d+)*|ea)', price_text)
                if match:
                    price_str = match.group(1)
                    qty_str = match.group(2)
                    
                    try:
                        price = float(price_str)
                        quantity = 1 if qty_str == "ea" else int(qty_str.replace(',', ''))
                        
                        pricing.append({
                            "quantity": quantity,
                            "price": price,
                            "currency": "USD"
                        })
                    except ValueError:
                        continue
        
        # Remove duplicates and sort by quantity
        unique_pricing = []
        seen_quantities = set()
        
        for price_info in pricing:
            qty = price_info["quantity"]
            if qty not in seen_quantities:
                unique_pricing.append(price_info)
                seen_quantities.add(qty)
        
        # Sort by quantity
        unique_pricing.sort(key=lambda x: x["quantity"])
        
        return unique_pricing if unique_pricing else None
    
    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image URL"""
        # Look for product images
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            # Look for catalog images first (these are the actual product images)
            if 'images/catalog/' in src:
                # Convert relative URL to absolute
                if src.startswith('/'):
                    return f"{self._get_base_url()}{src}"
                elif src.startswith('images/'):
                    return f"{self._get_base_url()}/{src}"
                elif src.startswith('http'):
                    return src
        
        # Fallback: look for any image with product-related alt text
        for img in img_tags:
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            if any(keyword in alt.lower() for keyword in ['bolt', 'screw', 'hex', 'thread']) and 'images/' in src:
                if src.startswith('/'):
                    return f"{self._get_base_url()}{src}"
                elif src.startswith('images/'):
                    return f"{self._get_base_url()}/{src}"
                elif src.startswith('http'):
                    return src
        
        return None
    
    def _build_description(self, details: Dict[str, str]) -> str:
        """Build a descriptive string from product details"""
        description_parts = []
        
        # Start with category and subcategory
        category = details.get("Category", "")
        subcategory = details.get("Subcategory", "")
        
        if subcategory and subcategory != category:
            description_parts.append(subcategory)
        elif category:
            description_parts.append(category)
        
        # Add key specifications
        material = details.get("Material", "")
        if material:
            description_parts.append(material)
        
        diameter = details.get("Diameter", "")
        length = details.get("Length", "")
        if diameter and length:
            description_parts.append(f"{diameter} x {length}")
        elif diameter:
            description_parts.append(diameter)
        elif length:
            description_parts.append(f"{length} length")
        
        # Add thread info if available
        thread_count = details.get("Thread count", "")
        if thread_count:
            description_parts.append(f"{thread_count} TPI")
        
        return ", ".join(description_parts) if description_parts else "Fastener"
    
    async def fetch_pricing(self, supplier_part_number: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch current pricing for a Bolt Depot part
        
        Returns pricing in the standard format expected by the price update task:
        List of price break dictionaries with quantity, price, and currency.
        """
        part_details = await self.get_part_details(supplier_part_number)
        if not part_details or not part_details.pricing:
            return None
        
        # Return the pricing data directly as it's already in the correct format
        # from get_part_details (list of dicts with quantity/price/currency)
        return part_details.pricing
    
    async def fetch_stock(self, supplier_part_number: str) -> Optional[int]:
        """Stock information not available from web scraping"""
        return None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a Bolt Depot part"""
        part_details = await self.get_part_details(supplier_part_number)
        return part_details.image_url if part_details else None
    
    
    def get_rate_limit_delay(self) -> float:
        """Get configured delay between requests"""
        return self._config.get("request_delay_seconds", 2.0)