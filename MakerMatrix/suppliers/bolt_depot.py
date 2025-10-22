"""
Bolt Depot Supplier Implementation

Implements web scraping for BoltDepot.com using BeautifulSoup to extract
part details, pricing, and specifications from product pages.
"""

from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from decimal import Decimal
import logging

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, CapabilityRequirement,
    EnrichmentFieldMapping
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

logger = logging.getLogger(__name__)

@register_supplier("boltdepot")
class BoltDepotSupplier(BaseSupplier):
    """Bolt Depot supplier implementation using web scraping"""

    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="boltdepot",
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

    def supports_scraping(self) -> bool:
        """Bolt Depot supports web scraping as a fallback."""
        return True

    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for public web scraping
        return []

    def get_url_patterns(self) -> List[str]:
        """Return URL patterns that identify Bolt Depot product links"""
        return [
            r'boltdepot\.com',  # Base domain
            r'www\.boltdepot\.com',  # With www
            r'boltdepot\.com/Product-Details\.aspx',  # Product pages
        ]

    def get_enrichment_field_mappings(self) -> List[EnrichmentFieldMapping]:
        """
        Define URL patterns for extracting part numbers from Bolt Depot product URLs.

        Bolt Depot product URLs follow the pattern:
        https://boltdepot.com/Product-Details?product=15294
        """
        return [
            EnrichmentFieldMapping(
                field_name="supplier_part_number",
                display_name="Bolt Depot Product ID",
                url_patterns=[
                    r'[?&]product=([^&]+)',  # Extract from ?product=15294 or &product=15294
                    r'/Product-Details\?product=([^&]+)',  # More specific pattern
                ],
                example="15294",
                description="Product ID from Bolt Depot URL (e.g., ?product=15294)",
                required_for_enrichment=True
            )
        ]
    
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
        base_url = self._config.get("base_url", "https://boltdepot.com")
        # Ensure we always have a valid URL, never empty string
        return base_url if base_url else "https://boltdepot.com"

    def extract_part_number_from_url(self, url: str) -> Optional[str]:
        """
        Extract product number from Bolt Depot URL.

        Examples:
            https://boltdepot.com/Product-Details?product=15294 -> 15294
            https://www.boltdepot.com/Product-Details?product=15294 -> 15294
        """
        import re
        from urllib.parse import urlparse, parse_qs

        try:
            # Parse the URL
            parsed = urlparse(url)

            # Check if it's a Bolt Depot URL
            if 'boltdepot.com' not in parsed.netloc.lower():
                logger.debug(f"URL {url} is not a Bolt Depot URL")
                return None

            # Extract product parameter from query string
            query_params = parse_qs(parsed.query)
            if 'product' in query_params:
                product_id = query_params['product'][0]
                logger.debug(f"Extracted product number {product_id} from URL {url}")
                return product_id

            logger.debug(f"Could not find product parameter in URL {url}")
            return None

        except Exception as e:
            logger.warning(f"Error parsing Bolt Depot URL {url}: {e}")
            return None
    
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
    
    def _get_http_client(self):
        """Get or create HTTP client with Bolt Depot-specific configuration for web scraping"""
        if not hasattr(self, '_http_client') or not self._http_client:
            from .http_client import SupplierHTTPClient, RetryConfig
            
            config = self._config or {}
            
            # Configure for web scraping with conservative rate limiting
            request_delay = config.get("request_delay_seconds", 2.0)
            
            retry_config = RetryConfig(
                max_retries=2,
                base_delay=request_delay, 
                max_delay=10.0,
                retry_on_status=[429, 500, 502, 503, 504]
            )
            
            self._http_client = SupplierHTTPClient(
                supplier_name="bolt_depot",
                default_headers=self._get_headers(),
                default_timeout=config.get("timeout_seconds", 30),
                retry_config=retry_config
            )
        
        return self._http_client
    
    async def authenticate(self) -> bool:
        """No authentication required for public web scraping"""
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Bolt Depot website using unified HTTP client"""
        if not self._configured:
            return {
                "success": False,
                "message": "Supplier not configured. Call .configure() before testing.",
                "details": {"error": "Unconfigured supplier"}
            }
        try:
            http_client = self._get_http_client()
            url = self._get_base_url()
            
            response = await http_client.get(url, endpoint_type="test_connection")
            
            if response.success:
                soup = BeautifulSoup(response.raw_content, 'html.parser')
                
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
        """Get detailed information about a specific Bolt Depot part using unified HTTP client"""
        try:
            if not supplier_part_number.isdigit():
                logger.warning(f"Bolt Depot part number should be numeric: {supplier_part_number}")
                return None

            http_client = self._get_http_client()

            # Construct product URL
            base_url = self._get_base_url()
            url = f"{base_url}/Product-Details?product={supplier_part_number}"

            response = await http_client.get(url, endpoint_type="get_part_details")

            if not response.success:
                logger.warning(f"Failed to fetch product {supplier_part_number}: HTTP {response.status}")
                return None

            soup = BeautifulSoup(response.raw_content, 'html.parser')
            return self._parse_product_page(soup, supplier_part_number, url)

        except Exception as e:
            logger.error(f"Error fetching part details for {supplier_part_number}: {e}")
            return None

    async def scrape_part_details(self, url_or_part_number: str, force_refresh: bool = False) -> Optional[PartSearchResult]:
        """
        Scrape Bolt Depot product page for part details using Playwright.

        Args:
            url_or_part_number: Either a full Bolt Depot URL or just the product number
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            PartSearchResult with scraped data, or None if scraping fails
        """
        scraper_created = False
        try:
            # Initialize scraper if needed
            if not hasattr(self, '_scraper') or not self._scraper:
                from .scrapers.web_scraper import WebScraper
                self._scraper = WebScraper()
                scraper_created = True

            # Build URL if only part number provided
            if not url_or_part_number.startswith('http'):
                base_url = self._get_base_url()
                url = f"{base_url}/Product-Details?product={url_or_part_number}"
                part_number = url_or_part_number
            else:
                url = url_or_part_number
                # Extract part number from URL
                part_number = self.extract_part_number_from_url(url) or url_or_part_number

            logger.info(f"Scraping Bolt Depot page: {url}")

            # Define CSS selectors for data extraction
            selectors = {
                'product_table': f'tr#p{part_number}',  # Product row in table
                'details_table': 'table.product-details-table tr',  # Product details
                'price': f'tr#p{part_number} td.cell-price span.price-break, tr#p{part_number} td.cell-price-single span.price-break',  # Pricing
                'image': 'img[src*="images/catalog/"]',  # Product image
            }

            # Scrape with Playwright (handles JavaScript-rendered content)
            logger.info(f"Scraping Bolt Depot URL: {url} (force_refresh={force_refresh})")
            scraped_data = await self._scraper.scrape_with_playwright(
                url,
                selectors,
                wait_for_selector='table.product-details-table',  # Wait for details table to load
                force_refresh=force_refresh
            )

            logger.info(f"Scraped data: {scraped_data}")
            if not scraped_data:
                logger.error("No data scraped from Bolt Depot page")
                return None

            # Parse the scraped data
            result = await self._parse_scraped_data_from_scraper(scraped_data, part_number, url)

            if result:
                logger.info(f"Successfully scraped Bolt Depot part: {part_number}")
            else:
                logger.warning(f"Could not parse scraped data for: {part_number}")

            return result

        except Exception as e:
            logger.error(f"Error scraping Bolt Depot: {str(e)}")
            return None
        finally:
            # Clean up the scraper session if we created it
            if scraper_created and hasattr(self, '_scraper') and self._scraper:
                try:
                    await self._scraper.close()
                    self._scraper = None
                except Exception as e:
                    logger.debug(f"Error closing scraper: {e}")

    async def _parse_scraped_data_from_scraper(self, scraped_data: Dict[str, Any], part_number: str, url: str) -> Optional[PartSearchResult]:
        """Parse scraped data from WebScraper into PartSearchResult format."""
        try:
            from datetime import datetime

            # Extract product details from the details_table
            details = {}
            if 'details_table' in scraped_data and isinstance(scraped_data['details_table'], dict):
                details = scraped_data['details_table']

            # Build description from details
            description = self._build_description(details)

            # Extract category
            category = details.get("Category", "")

            # Extract image URL
            image_url = scraped_data.get('image')
            if image_url:
                # Convert relative URL to absolute
                if image_url.startswith('/'):
                    image_url = self._get_base_url() + image_url
                elif image_url.startswith('images/'):
                    image_url = self._get_base_url() + '/' + image_url
                elif not image_url.startswith('http'):
                    image_url = self._get_base_url() + '/' + image_url

            # Parse pricing from scraped data
            pricing = []
            if 'price' in scraped_data:
                price_text = scraped_data['price']
                # Parse multiple price breaks if available (format: "$0.25 / ea" or "$19.13 / 100")
                price_breaks = price_text.split('\n') if isinstance(price_text, str) else [price_text]
                for price_break in price_breaks:
                    match = re.search(r'\$(\d+(?:\.\d{2})?)\s*/\s*(\d+(?:,\d+)*|ea)', price_break.strip())
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
            unique_pricing.sort(key=lambda x: x["quantity"])

            # Remove category from additional_data since it's redundant
            additional_data = {k: v for k, v in details.items() if k.lower() != "category"}
            additional_data['source'] = 'web_scraping'
            additional_data['scraped_at'] = datetime.now().isoformat()
            additional_data['url'] = url

            return PartSearchResult(
                supplier_part_number=part_number,
                manufacturer="Bolt Depot",
                manufacturer_part_number=part_number,
                description=description,
                category=category,
                datasheet_url=None,
                image_url=image_url,
                stock_quantity=None,
                pricing=unique_pricing if unique_pricing else None,
                specifications=None,
                additional_data=additional_data
            )

        except Exception as e:
            logger.error(f"Error parsing scraped Bolt Depot data: {str(e)}")
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

    def map_to_standard_format(self, supplier_data: Any) -> Dict[str, Any]:
        """
        Map supplier data to standard format.

        This method flattens the PartSearchResult into simple key-value pairs for clean display.
        All specifications and additional_data are expanded into flat fields.

        Args:
            supplier_data: PartSearchResult from this supplier

        Returns:
            Flat dictionary with all data as simple key-value pairs
        """
        if not isinstance(supplier_data, PartSearchResult):
            return {}

        # Start with core fields
        mapped = {
            'supplier_part_number': supplier_data.supplier_part_number,
            'part_name': supplier_data.description or supplier_data.part_name or supplier_data.supplier_part_number,
            'manufacturer': supplier_data.manufacturer,
            'manufacturer_part_number': supplier_data.manufacturer_part_number,
            'description': supplier_data.description,
            'category': supplier_data.category,
        }

        # Add image and datasheet URLs if available
        if supplier_data.image_url:
            mapped['image_url'] = supplier_data.image_url
        if supplier_data.datasheet_url:
            mapped['datasheet_url'] = supplier_data.datasheet_url

        # Extract unit price from pricing array (first tier)
        if supplier_data.pricing and len(supplier_data.pricing) > 0:
            first_price = supplier_data.pricing[0]
            mapped['unit_price'] = first_price.get('price')
            mapped['currency'] = first_price.get('currency', 'USD')

        # Flatten specifications into custom fields
        if supplier_data.specifications:
            for spec_key, spec_value in supplier_data.specifications.items():
                # Create readable field names
                field_name = spec_key.replace('_', ' ').title()
                if spec_value is not None:
                    mapped[field_name] = str(spec_value)

        # Flatten additional_data into custom fields
        if supplier_data.additional_data:
            for key, value in supplier_data.additional_data.items():
                # Skip internal tracking fields
                if key in ['source', 'scraped_at', 'api_version', 'last_updated', 'warning', 'data_source']:
                    continue
                # Create readable field names
                field_name = key.replace('_', ' ').title()
                if value is not None:
                    mapped[field_name] = str(value)

        return mapped