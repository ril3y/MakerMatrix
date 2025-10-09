"""
Seeed Studio Supplier Implementation

Implements web scraping for SeeedStudio.com using BeautifulSoup to extract
part details, pricing, specifications, and images from product pages.

Focuses on Grove system components and maker hardware with comprehensive
specification extraction.
"""

from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from decimal import Decimal
import logging
from urllib.parse import urlparse

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

@register_supplier("seeedstudio")
class SeeedStudioSupplier(BaseSupplier):
    """Seeed Studio supplier implementation using web scraping

    Scrapes Seeed Studio product pages for Grove system and maker hardware,
    with comprehensive specification extraction.
    """

    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="seeedstudio",
            display_name="Seeed Studio",
            description="Open-source hardware supplier specializing in Grove system components and maker-focused products. Uses web scraping to extract product details, pricing, specifications, and images from product pages.",
            website_url="https://www.seeedstudio.com",
            api_documentation_url=None,  # No official API - uses web scraping
            supports_oauth=False,
            rate_limit_info="Conservative delays to respect website resources. Recommend 2-3 second delays between requests."
        )

    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,       # Scrape individual product pages
            SupplierCapability.FETCH_PRICING_STOCK,    # Extract pricing and stock data
        ]

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Seeed Studio uses web scraping, so no credentials required for any capability"""
        return {
            capability: CapabilityRequirement(
                capability=capability,
                required_credentials=[]
            )
            for capability in self.get_capabilities()
        }

    def get_enrichment_field_mappings(self) -> List[EnrichmentFieldMapping]:
        """
        Define URL patterns for extracting part identifiers from Seeed Studio product URLs.

        Seeed Studio product URLs follow the pattern:
        https://www.seeedstudio.com/Grove-Laser-PM2-5-Sensor-HM3301.html
        https://www.seeedstudio.com/Grove-Gas-Sensor-MQ9.html
        """
        return [
            EnrichmentFieldMapping(
                field_name="supplier_part_number",
                display_name="Seeed Studio Product Slug",
                url_patterns=[
                    r'/([^/]+)\.html$',  # Extract product slug before .html
                    r'seeedstudio\.com/([^/]+)\.html',  # More specific pattern
                ],
                example="Grove-Laser-PM2-5-Sensor-HM3301",
                description="Product identifier from Seeed Studio URL (e.g., Grove-Laser-PM2-5-Sensor-HM3301)",
                required_for_enrichment=True
            )
        ]

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
                default_value="https://www.seeedstudio.com",
                description="Seeed Studio website base URL",
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
        """Get base URL for Seeed Studio"""
        base_url = self._config.get("base_url", "https://www.seeedstudio.com")
        # Ensure we always have a valid URL, never empty string
        return base_url if base_url else "https://www.seeedstudio.com"

    def extract_part_number_from_url(self, url: str) -> Optional[str]:
        """
        Extract product slug from Seeed Studio URL.

        Examples:
            https://www.seeedstudio.com/Grove-Laser-PM2-5-Sensor-HM3301.html -> Grove-Laser-PM2-5-Sensor-HM3301
            https://www.seeedstudio.com/Grove-Gas-Sensor-MQ9.html -> Grove-Gas-Sensor-MQ9
        """
        try:
            # Parse the URL
            parsed = urlparse(url)

            # Check if it's a Seeed Studio URL
            if 'seeedstudio.com' not in parsed.netloc.lower():
                logger.debug(f"URL {url} is not a Seeed Studio URL")
                return None

            # Extract product slug from path (everything between last / and .html)
            path = parsed.path
            if path.endswith('.html'):
                # Get the last segment of the path before .html
                slug = path.rstrip('.html').split('/')[-1]
                if slug:
                    logger.debug(f"Extracted product slug {slug} from URL {url}")
                    return slug

            logger.debug(f"Could not find product slug in URL {url}")
            return None

        except Exception as e:
            logger.warning(f"Error parsing Seeed Studio URL {url}: {e}")
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
        """Get or create HTTP client with Seeed Studio-specific configuration for web scraping"""
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
                supplier_name="seeedstudio",
                default_headers=self._get_headers(),
                default_timeout=config.get("timeout_seconds", 30),
                retry_config=retry_config
            )

        return self._http_client

    async def authenticate(self) -> bool:
        """No authentication required for public web scraping"""
        return True

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Seeed Studio website using unified HTTP client"""
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

                # Check if this looks like the Seeed Studio website
                title = soup.find('title')
                title_text = title.get_text() if title else ""

                if "seeed" in title_text.lower():
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
                        "message": "Website content doesn't match expected Seeed Studio format",
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
        Search not directly supported - Seeed Studio requires browsing by category.
        This method will try to treat the query as a product slug.
        """
        # Try to get part details directly if query looks like a product slug
        part_details = await self.get_part_details(query)
        if part_details:
            return [part_details]

        # Could implement category browsing/search here in the future
        return []

    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific Seeed Studio part using unified HTTP client"""
        try:
            http_client = self._get_http_client()

            # Construct product URL
            base_url = self._get_base_url()
            # Product slug should already include the product name
            url = f"{base_url}/{supplier_part_number}.html"

            response = await http_client.get(url, endpoint_type="get_part_details")

            if not response.success:
                logger.warning(f"Failed to fetch product {supplier_part_number}: HTTP {response.status}")
                return None

            soup = BeautifulSoup(response.raw_content, 'html.parser')
            return self._parse_product_page(soup, supplier_part_number, url)

        except Exception as e:
            logger.error(f"Error fetching part details for {supplier_part_number}: {e}")
            return None

    def _parse_product_page(self, soup: BeautifulSoup, part_slug: str, url: str) -> Optional[PartSearchResult]:
        """Parse a Seeed Studio product page"""
        try:
            # Extract product details
            title = self._extract_product_title(soup)
            description = self._extract_description(soup)
            image_url = self._extract_image_url(soup)
            pricing = self._extract_pricing(soup)
            stock_quantity = self._extract_stock(soup)
            specifications = self._extract_specifications(soup)
            sku = self._extract_sku(soup)

            # Build additional_data from specifications for backward compatibility
            additional_data = dict(specifications) if specifications else {}

            # Add price to additional_data if available
            if pricing and pricing:
                additional_data['price'] = f"${pricing[0]['price']:.2f}"
                additional_data['currency'] = pricing[0].get('currency', 'USD')

            return PartSearchResult(
                supplier_part_number=part_slug,
                part_name=title,
                manufacturer="Seeed Studio",
                manufacturer_part_number=sku or part_slug,
                description=description,
                category=None,  # Could be extracted from breadcrumbs
                datasheet_url=None,  # Not commonly available on Seeed pages
                image_url=image_url,
                stock_quantity=stock_quantity,
                pricing=pricing if pricing else None,
                specifications=specifications,
                additional_data=additional_data if additional_data else None
            )

        except Exception as e:
            logger.error(f"Error parsing product page for {part_slug}: {e}")
            return None

    def _extract_product_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from page"""
        try:
            # Try common title patterns
            title_tag = (
                soup.find('h1', class_=re.compile(r'product.*title', re.I)) or
                soup.find('h1', class_='ais_p_title') or
                soup.find('h1', class_='product-name') or
                soup.find('h1')
            )

            if title_tag:
                return title_tag.get_text().strip()

            # Fallback to meta title
            meta_title = soup.find('meta', attrs={'property': 'og:title'})
            if meta_title:
                return meta_title.get('content', '').strip()

            return "Unknown Product"

        except Exception as e:
            logger.warning(f"Error extracting product title: {e}")
            return "Unknown Product"

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract product description from page"""
        try:
            # Try various description patterns - Seeed Studio uses 'short_description'
            desc_tag = (
                soup.find('div', class_='product attribute short_description') or
                soup.find('div', class_=re.compile(r'short.*desc', re.I)) or
                soup.find('div', class_='ais_p_desc') or
                soup.find('div', class_=re.compile(r'product.*desc', re.I)) or
                soup.find('div', class_='description') or
                soup.find('div', class_='product-overview')
            )

            if desc_tag:
                # Extract text from the value div if it exists
                value_div = desc_tag.find('div', class_='value')
                if value_div:
                    return value_div.get_text().strip()
                return desc_tag.get_text().strip()

            # Fallback to meta description
            meta_desc = (
                soup.find('meta', attrs={'name': 'description'}) or
                soup.find('meta', attrs={'property': 'og:description'})
            )
            if meta_desc:
                return meta_desc.get('content', '').strip()

            return ""

        except Exception as e:
            logger.warning(f"Error extracting description: {e}")
            return ""

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract primary product image URL"""
        try:
            # Try to find image in Splide slider
            main_slider = soup.find('div', id='main-slider') or soup.find('div', class_='splide-container')
            if main_slider:
                img_tag = main_slider.find('img')
                if img_tag:
                    # Try src, data-src, or other common attributes
                    img_url = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy')
                    if img_url:
                        # Handle protocol-relative URLs
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif not img_url.startswith('http'):
                            img_url = 'https://www.seeedstudio.com' + img_url
                        return img_url

            # Fallback to meta image
            meta_img = soup.find('meta', attrs={'property': 'og:image'})
            if meta_img:
                img_url = meta_img.get('content', '')
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                return img_url if img_url else None

            return None

        except Exception as e:
            logger.warning(f"Error extracting image URL: {e}")
            return None

    def _extract_pricing(self, soup: BeautifulSoup) -> Optional[List[Dict[str, Any]]]:
        """Extract pricing information"""
        try:
            # Try various price patterns
            price_tag = (
                soup.find('span', class_='ais_p_price') or
                soup.find('span', class_=re.compile(r'price', re.I)) or
                soup.find('div', class_=re.compile(r'price', re.I))
            )

            if price_tag:
                price_text = price_tag.get_text()
                # Extract numeric price
                price_match = re.search(r'\$?([\d.]+)', price_text)
                if price_match:
                    try:
                        price = float(price_match.group(1))
                        return [{
                            "quantity": 1,
                            "price": price,
                            "currency": "USD"
                        }]
                    except ValueError:
                        pass

            return None

        except Exception as e:
            logger.warning(f"Error extracting pricing: {e}")
            return None

    def _extract_stock(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract stock/availability information"""
        try:
            # Look for stock indicators
            stock_tag = (
                soup.find('div', class_=re.compile(r'stock|availability', re.I)) or
                soup.find('span', class_=re.compile(r'stock|availability', re.I))
            )

            if stock_tag:
                stock_text = stock_tag.get_text().lower()
                if 'in stock' in stock_text or 'available' in stock_text:
                    return 999  # Unknown quantity but in stock
                elif 'out of stock' in stock_text or 'unavailable' in stock_text:
                    return 0

            return None

        except Exception as e:
            logger.warning(f"Error extracting stock: {e}")
            return None

    def _extract_sku(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract SKU/product code if available"""
        try:
            # Look for SKU in various places
            sku_tag = (
                soup.find('span', class_=re.compile(r'sku|product.*code', re.I)) or
                soup.find('div', class_=re.compile(r'sku|product.*code', re.I))
            )

            if sku_tag:
                sku_text = sku_tag.get_text()
                # Extract SKU from text like "SKU: 123456"
                sku_match = re.search(r'SKU[:\s]*([A-Z0-9-]+)', sku_text, re.I)
                if sku_match:
                    return sku_match.group(1)
                # Or just use the text if it looks like a SKU
                sku_clean = sku_text.strip()
                if re.match(r'^[A-Z0-9-]+$', sku_clean):
                    return sku_clean

            return None

        except Exception as e:
            logger.warning(f"Error extracting SKU: {e}")
            return None

    def _extract_specifications(self, soup: BeautifulSoup) -> Optional[Dict[str, str]]:
        """
        Extract specifications from various HTML formats.

        Handles:
        1. HTML tables (most common) - including Seeed Studio's p_2981_table format
        2. Definition lists (<dl>)
        3. Div-based key-value pairs

        Returns dict of specification name -> value
        """
        specifications = {}

        try:
            # Strategy 1: Look for specification tables
            # Seeed Studio uses class="p_2981_table" specifically
            spec_table = (
                soup.find('table', class_='p_2981_table') or  # Seeed Studio specific
                soup.find('table', class_=re.compile(r'spec|technical|parameter', re.I)) or
                soup.find('table', id=re.compile(r'spec|technical|parameter', re.I))
            )

            if spec_table:
                logger.debug("Found specification table")
                rows = spec_table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        # Extract text directly from cells (handles p, span, or plain text)
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)

                        # Skip empty keys/values and header rows
                        if key and value and key.lower() not in ['symbol', 'sysmbol']:
                            specifications[key] = value
                            logger.debug(f"Extracted spec: {key} = {value}")

            # Strategy 2: Look for definition lists
            if not specifications:
                spec_dl = (
                    soup.find('dl', class_=re.compile(r'spec|technical|parameter', re.I)) or
                    soup.find('dl', id=re.compile(r'spec|technical|parameter', re.I))
                )

                if spec_dl:
                    logger.debug("Found specification definition list")
                    dts = spec_dl.find_all('dt')
                    dds = spec_dl.find_all('dd')
                    for dt, dd in zip(dts, dds):
                        key = dt.get_text().strip()
                        value = dd.get_text().strip()
                        if key and value:
                            specifications[key] = value

            # Strategy 3: Look for div-based specifications
            if not specifications:
                spec_section = (
                    soup.find('div', class_=re.compile(r'spec|technical|parameter', re.I)) or
                    soup.find('section', class_=re.compile(r'spec|technical|parameter', re.I))
                )

                if spec_section:
                    logger.debug("Found specification div/section")
                    # Look for key-value pairs within divs
                    spec_items = spec_section.find_all('div', class_=re.compile(r'spec.*item|param.*item', re.I))
                    for item in spec_items:
                        # Try to find label and value
                        label = item.find(['span', 'strong', 'b'], class_=re.compile(r'label|key|name', re.I))
                        value = item.find(['span', 'div'], class_=re.compile(r'value|data', re.I))

                        if label and value:
                            key = label.get_text().strip().rstrip(':')
                            val = value.get_text().strip()
                            if key and val:
                                specifications[key] = val

            # If we found specifications, log success
            if specifications:
                logger.info(f"Extracted {len(specifications)} specifications")
            else:
                logger.debug("No specifications found on page")

            return specifications if specifications else None

        except Exception as e:
            logger.warning(f"Error extracting specifications: {e}")
            return None
