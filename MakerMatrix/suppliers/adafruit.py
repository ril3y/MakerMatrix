"""
Adafruit Supplier Implementation

Implements web scraping for Adafruit.com using BeautifulSoup to extract
part details, pricing, specifications, and order data from product pages and invoices.

Uses JSON-LD structured data for reliable product information extraction.
"""

from typing import List, Dict, Any, Optional
import re
import json
import html
from bs4 import BeautifulSoup
from decimal import Decimal
import logging

from .base import (
    BaseSupplier,
    FieldDefinition,
    FieldType,
    SupplierCapability,
    PartSearchResult,
    SupplierInfo,
    CapabilityRequirement,
    ImportResult,
    EnrichmentFieldMapping,
)
from .registry import register_supplier
from .exceptions import (
    SupplierConfigurationError,
    SupplierAuthenticationError,
    SupplierConnectionError,
    SupplierRateLimitError,
)

logger = logging.getLogger(__name__)


@register_supplier("adafruit")
class AdafruitSupplier(BaseSupplier):
    """Adafruit supplier implementation using web scraping

    Scrapes Adafruit.com for product details using JSON-LD structured data
    and parses invoice HTML for order imports.
    """

    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="adafruit",
            display_name="Adafruit Industries",
            description="Open-source hardware and electronics supplier with extensive maker-focused products. Uses web scraping to extract product details, pricing, and specifications from product pages and invoice HTML.",
            website_url="https://www.adafruit.com",
            api_documentation_url=None,  # No official API - uses web scraping
            supports_oauth=False,
            rate_limit_info="Conservative delays to respect website resources. Recommend 2-3 second delays between requests.",
            supported_file_types=["html"],  # Invoice HTML import
        )

    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,  # Scrape individual product pages
            SupplierCapability.FETCH_DATASHEET,  # Extract datasheet URLs
            SupplierCapability.FETCH_PRICING_STOCK,  # Extract pricing and stock data
            SupplierCapability.IMPORT_ORDERS,  # Import from invoice HTML
        ]

    def is_configured(self) -> bool:
        """
        Adafruit uses public web scraping which doesn't require credentials.
        Always return True since the website is publicly accessible.
        """
        return True

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Adafruit uses web scraping, so no credentials required for any capability"""
        return {
            capability: CapabilityRequirement(capability=capability, required_credentials=[])
            for capability in self.get_capabilities()
        }

    def get_url_patterns(self) -> List[str]:
        """Return URL patterns that identify Adafruit product links"""
        return [
            r"adafruit\.com",  # Base domain
            r"www\.adafruit\.com",  # With www
            r"adafruit\.com/product/\d+",  # Product pages with numeric ID
            r"adafruit\.com/products/\d+",  # Alternative product URL format
        ]

    def get_enrichment_field_mappings(self) -> List[EnrichmentFieldMapping]:
        """Define how to extract part fields from Adafruit product URLs"""
        return [
            EnrichmentFieldMapping(
                field_name="supplier_part_number",
                display_name="Adafruit Product ID",
                url_patterns=[
                    r"/product/(\d+)",  # Primary: https://www.adafruit.com/product/4759
                    r"/products/(\d+)",  # Alternative: https://www.adafruit.com/products/4759
                ],
                example="4759",
                description="The numeric product ID from the Adafruit product page URL",
                required_for_enrichment=True,
            )
        ]

    def get_enrichment_requirements(self):
        """
        Define what part data is required for enrichment from Adafruit.

        Adafruit requires the supplier_part_number (numeric product ID)
        to look up parts via web scraping.

        Returns:
            EnrichmentRequirements with required, recommended, and optional fields
        """
        from MakerMatrix.models.enrichment_requirement_models import (
            EnrichmentRequirements,
            FieldRequirement,
            RequirementSeverity,
        )

        return EnrichmentRequirements(
            supplier_name="adafruit",
            display_name="Adafruit Industries",
            description="Adafruit can enrich parts with detailed descriptions, images, pricing, and stock levels using web scraping from product pages",
            required_fields=[
                FieldRequirement(
                    field_name="supplier_part_number",
                    display_name="Adafruit Product ID",
                    severity=RequirementSeverity.REQUIRED,
                    description="The numeric product ID (e.g., 3571) is required to look up part details from the Adafruit website. This is the primary identifier for Adafruit products.",
                    example="3571",
                    validation_pattern="^\\d+$",
                )
            ],
            recommended_fields=[
                FieldRequirement(
                    field_name="description",
                    display_name="Part Description",
                    severity=RequirementSeverity.RECOMMENDED,
                    description="Having a description helps validate that the enriched data matches your intended product",
                    example="ARM Cortex-M0+ JTAG/SWD Debugger",
                )
            ],
            optional_fields=[
                FieldRequirement(
                    field_name="manufacturer_part_number",
                    display_name="Manufacturer Part Number",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Manufacturer part number can help verify the enriched data",
                    example="ATSAMD21G18",
                ),
                FieldRequirement(
                    field_name="component_type",
                    display_name="Component Type",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Component type helps organize enriched specifications",
                    example="Development Board",
                ),
            ],
        )

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
                default_value="https://www.adafruit.com",
                description="Adafruit website base URL",
                help_text="Default URL should work for most users",
            ),
            FieldDefinition(
                name="request_delay_seconds",
                label="Request Delay (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=2.0,
                description="Delay between requests to be respectful to the website",
                validation={"min": 1.0, "max": 10.0},
                help_text="Recommended: 2-3 seconds to avoid overloading the server",
            ),
            FieldDefinition(
                name="timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="HTTP request timeout in seconds",
                validation={"min": 5, "max": 120},
                help_text="How long to wait for page responses",
            ),
            FieldDefinition(
                name="user_agent",
                label="User Agent String",
                field_type=FieldType.TEXT,
                required=False,
                default_value="MakerMatrix/1.0 (Inventory Management System)",
                description="User agent string for HTTP requests",
                help_text="Identifies your application to the website",
            ),
            FieldDefinition(
                name="enable_caching",
                label="Enable Response Caching",
                field_type=FieldType.BOOLEAN,
                required=False,
                default_value=True,
                description="Cache scraped pages to reduce server load",
                help_text="Recommended to enable for better performance and server courtesy",
            ),
        ]

    def _get_base_url(self) -> str:
        """Get base URL for Adafruit"""
        return self._config.get("base_url", "https://www.adafruit.com")

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
        """Get or create HTTP client with Adafruit-specific configuration for web scraping"""
        if not hasattr(self, "_http_client") or not self._http_client:
            from .http_client import SupplierHTTPClient, RetryConfig

            config = self._config or {}

            # Configure for web scraping with conservative rate limiting
            request_delay = config.get("request_delay_seconds", 2.0)

            retry_config = RetryConfig(
                max_retries=2, base_delay=request_delay, max_delay=10.0, retry_on_status=[429, 500, 502, 503, 504]
            )

            self._http_client = SupplierHTTPClient(
                supplier_name="adafruit",
                default_headers=self._get_headers(),
                default_timeout=config.get("timeout_seconds", 30),
                retry_config=retry_config,
            )

        return self._http_client

    async def authenticate(self) -> bool:
        """No authentication required for public web scraping"""
        return True

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Adafruit website using unified HTTP client"""
        if not self._configured:
            return {
                "success": False,
                "message": "Supplier not configured. Call .configure() before testing.",
                "details": {"error": "Unconfigured supplier"},
            }
        try:
            http_client = self._get_http_client()
            url = self._get_base_url()

            response = await http_client.get(url, endpoint_type="test_connection")

            if response.success:
                soup = BeautifulSoup(response.raw_content, "html.parser")

                # Check if this looks like the Adafruit website
                title = soup.find("title")
                title_text = title.get_text() if title else ""

                if "adafruit" in title_text.lower():
                    return {
                        "success": True,
                        "message": "Connection successful",
                        "details": {"base_url": url, "page_title": title_text.strip(), "status_code": response.status},
                    }
                else:
                    return {
                        "success": False,
                        "message": "Website content doesn't match expected Adafruit format",
                        "details": {"page_title": title_text.strip()},
                    }
            else:
                return {
                    "success": False,
                    "message": f"HTTP error: {response.status}",
                    "details": {"status_code": response.status},
                }

        except Exception as e:
            return {"success": False, "message": f"Connection test failed: {str(e)}", "details": {"exception": str(e)}}

    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """
        Search not directly supported - Adafruit search requires browsing.
        This method will try to treat the query as a product ID.
        """
        # Try to get part details directly if query looks like a product number
        if query.isdigit():
            part_details = await self.get_part_details(query)
            if part_details:
                return [part_details]

        # Could implement search page scraping here in the future
        return []

    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific Adafruit product using unified HTTP client"""
        try:
            if not supplier_part_number.isdigit():
                logger.warning(f"Adafruit product ID should be numeric: {supplier_part_number}")
                return None

            http_client = self._get_http_client()

            # Construct product URL
            base_url = self._get_base_url()
            url = f"{base_url}/product/{supplier_part_number}"

            response = await http_client.get(url, endpoint_type="get_part_details")

            if not response.success:
                logger.warning(f"Failed to fetch product {supplier_part_number}: HTTP {response.status}")
                return None

            soup = BeautifulSoup(response.raw_content, "html.parser")
            return self._parse_product_page(soup, supplier_part_number, url)

        except Exception as e:
            logger.error(f"Error fetching part details for {supplier_part_number}: {e}")
            return None

    def _parse_product_page(self, soup: BeautifulSoup, product_id: str, url: str) -> Optional[PartSearchResult]:
        """Parse an Adafruit product page

        Uses JSON-LD structured data when available, falls back to HTML parsing.
        """
        try:
            # Extract product dimensions from HTML (applies to both JSON-LD and HTML parsing)
            dimensions = self._extract_dimensions(soup)

            # Try to extract JSON-LD structured data first
            json_ld_data = self._extract_json_ld(soup)

            if json_ld_data:
                result = self._parse_from_json_ld(json_ld_data, product_id, url)
            else:
                # Fallback to HTML parsing
                result = self._parse_from_html(soup, product_id, url)

            # Add dimensions to additional_data if found
            if result and dimensions:
                if not result.additional_data:
                    result.additional_data = {}
                result.additional_data["dimensions"] = dimensions

            return result

        except Exception as e:
            logger.error(f"Error parsing product page for {product_id}: {e}")
            return None

    def _extract_dimensions(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product dimensions from HTML

        Looks for patterns like:
        <p>Product Dimensions: 52.2mm x 22.8mm x 7.2mm / 2.1" x 0.9" x 0.3"</p>
        """
        try:
            # Look for paragraphs containing "dimensions" (case insensitive)
            for p_tag in soup.find_all("p"):
                text = p_tag.get_text(strip=True)
                if "dimensions" in text.lower() and ":" in text:
                    # Extract everything after "Product Dimensions:" or similar
                    parts = text.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()

            return None
        except Exception as e:
            logger.warning(f"Error extracting dimensions: {e}")
            return None

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD structured data from page"""
        try:
            # Find all JSON-LD script tags
            json_ld_scripts = soup.find_all("script", type="application/ld+json")

            for script in json_ld_scripts:
                if script.string:
                    data = json.loads(script.string)
                    # Look for Product schema
                    if isinstance(data, dict) and data.get("@type") == "Product":
                        return data
                    # Handle arrays of schemas
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("@type") == "Product":
                                return item

            return None
        except Exception as e:
            logger.warning(f"Error extracting JSON-LD: {e}")
            return None

    def _parse_from_json_ld(self, json_ld: Dict[str, Any], product_id: str, url: str) -> Optional[PartSearchResult]:
        """Parse product information from JSON-LD structured data"""
        try:
            # Extract basic product info and decode HTML entities
            name = html.unescape(json_ld.get("name", ""))
            description = html.unescape(json_ld.get("description", ""))
            sku = str(json_ld.get("sku", product_id))

            # Extract image - fix double slashes
            image_url = None
            if "image" in json_ld:
                image_data = json_ld["image"]
                if isinstance(image_data, str):
                    image_url = image_data
                elif isinstance(image_data, list) and image_data:
                    image_url = image_data[0] if isinstance(image_data[0], str) else image_data[0].get("url")
                elif isinstance(image_data, dict):
                    image_url = image_data.get("url")

            # Fix double slashes in image URL (e.g., cdn-shop.adafruit.com//970x728/)
            if image_url:
                # Handle URLs with or without protocol
                if "://" in image_url:
                    # Split protocol from rest, fix double slashes only in path
                    protocol, rest = image_url.split("://", 1)
                    rest = rest.replace("//", "/")  # Fix all double slashes in path
                    image_url = f"{protocol}://{rest}"
                else:
                    # No protocol - fix slashes and add https://
                    image_url = image_url.replace("//", "/")
                    if not image_url.startswith("http"):
                        image_url = f"https://{image_url}"

            # Extract price and stock
            pricing = []
            stock_quantity = None

            if "offers" in json_ld:
                offers = json_ld["offers"]
                if isinstance(offers, dict):
                    offers = [offers]

                for offer in offers:
                    price = offer.get("price")
                    currency = offer.get("priceCurrency", "USD")
                    availability = offer.get("availability", "")

                    if price:
                        try:
                            pricing.append({"quantity": 1, "price": float(price), "currency": currency})
                        except (ValueError, TypeError):
                            pass

                    # Check stock availability
                    if "instock" in availability.lower():
                        stock_quantity = 999  # Unknown quantity but in stock
                    elif "outofstock" in availability.lower():
                        stock_quantity = 0

            # Extract additional properties
            additional_data = {}

            # Add price to additional_data
            if pricing:
                additional_data["price"] = f"${pricing[0]['price']:.2f}"
                additional_data["currency"] = pricing[0]["currency"]

            # Brand
            if "brand" in json_ld:
                brand = json_ld["brand"]
                if isinstance(brand, dict):
                    additional_data["brand"] = brand.get("name", "Adafruit")
                else:
                    additional_data["brand"] = str(brand)

            # Category
            category = None
            if "category" in json_ld:
                category = json_ld["category"]

            # Weight and dimensions
            if "weight" in json_ld:
                weight = json_ld["weight"]
                if isinstance(weight, dict):
                    additional_data["weight"] = f"{weight.get('value', '')} {weight.get('unitCode', '')}"
                else:
                    additional_data["weight"] = str(weight)

            # Additional product properties
            if "additionalProperty" in json_ld:
                for prop in json_ld["additionalProperty"]:
                    if isinstance(prop, dict):
                        prop_name = prop.get("name", "")
                        prop_value = prop.get("value", "")
                        if prop_name and prop_value:
                            additional_data[prop_name] = prop_value

            return PartSearchResult(
                supplier_part_number=str(product_id),
                part_name=name,  # Use JSON-LD name for part_name
                manufacturer="Adafruit Industries",
                manufacturer_part_number=sku,
                description=description,  # Use JSON-LD description
                category=category,
                datasheet_url=None,  # Will be extracted from HTML if available
                image_url=image_url,
                stock_quantity=stock_quantity,
                pricing=pricing if pricing else None,
                specifications=None,
                additional_data=additional_data if additional_data else None,
            )

        except Exception as e:
            logger.error(f"Error parsing JSON-LD for product {product_id}: {e}")
            return None

    def _parse_from_html(self, soup: BeautifulSoup, product_id: str, url: str) -> Optional[PartSearchResult]:
        """Fallback HTML parsing when JSON-LD is not available"""
        try:
            # Extract title
            title_tag = soup.find("h1")
            name = title_tag.get_text().strip() if title_tag else f"Adafruit Product {product_id}"

            # Extract description from meta tags and decode HTML entities
            description = ""
            desc_meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if desc_meta:
                description = html.unescape(desc_meta.get("content", ""))

            # Extract image from meta tags
            image_url = None
            img_meta = soup.find("meta", attrs={"property": "og:image"})
            if img_meta:
                image_url = img_meta.get("content")

            # Try to extract price
            pricing = []
            price_tag = soup.find("span", class_=re.compile(r"price", re.I))
            if price_tag:
                price_text = price_tag.get_text()
                price_match = re.search(r"\$?([\d.]+)", price_text)
                if price_match:
                    try:
                        pricing.append({"quantity": 1, "price": float(price_match.group(1)), "currency": "USD"})
                    except ValueError:
                        pass

            return PartSearchResult(
                supplier_part_number=product_id,
                manufacturer="Adafruit Industries",
                manufacturer_part_number=product_id,
                description=description or name,
                category=None,
                datasheet_url=None,
                image_url=image_url,
                stock_quantity=None,
                pricing=pricing if pricing else None,
                specifications=None,
                additional_data=None,
            )

        except Exception as e:
            logger.error(f"Error parsing HTML for product {product_id}: {e}")
            return None

    async def import_order_file(self, file_content: bytes, file_type: str = "html") -> ImportResult:
        """Import Adafruit order from invoice HTML

        Args:
            file_content: Invoice HTML file content
            file_type: File type (should be 'html')

        Returns:
            ImportResult with parsed parts and order info
        """
        try:
            if file_type.lower() != "html":
                return ImportResult(
                    success=False, error_message=f"Unsupported file type: {file_type}. Expected HTML invoice file."
                )

            # Decode HTML content
            html_content = file_content.decode("utf-8")
            soup = BeautifulSoup(html_content, "html.parser")

            # Parse order metadata
            order_info = self._extract_order_info(soup)

            # Parse products from invoice
            parts = self._parse_invoice_products(soup)

            if not parts:
                return ImportResult(success=False, error_message="No products found in invoice HTML")

            return ImportResult(
                success=True,
                imported_count=len(parts),
                failed_count=0,
                parts=parts,
                failed_items=[],
                warnings=[],
                order_info=order_info,
                parser_type="adafruit_invoice_html",
            )

        except Exception as e:
            logger.error(f"Error importing Adafruit order: {e}")
            return ImportResult(success=False, error_message=f"Failed to parse invoice HTML: {str(e)}")

    def _extract_order_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract order metadata from invoice HTML"""
        order_info = {"supplier": "Adafruit Industries"}

        try:
            # Extract invoice number
            invoice_div = soup.find("div", class_="innovoice_header_oid")
            if invoice_div:
                invoice_text = invoice_div.get_text().strip()
                # Format: "2390595-7211307394"
                if "-" in invoice_text:
                    order_info["order_number"] = invoice_text.split("-")[0]
                else:
                    order_info["order_number"] = invoice_text

            # Extract order date
            date_span = soup.find("span", class_="innovoice_8 bold", string=re.compile(r"DATE ORDERED:"))
            if date_span and date_span.find_next_sibling():
                date_text = date_span.find_next_sibling().get_text().strip()
                order_info["order_date"] = date_text

            # Extract totals
            totals_table = soup.find("table", class_="totals_table")
            if totals_table:
                # Extract subtotal
                subtotal_row = totals_table.find("span", string=re.compile(r"Sub-Total:"))
                if subtotal_row:
                    subtotal_cell = subtotal_row.find_parent("tr").find_all("td")[-1]
                    subtotal_text = subtotal_cell.get_text().strip()
                    order_info["subtotal"] = subtotal_text

                # Extract total
                total_row = totals_table.find("span", string=re.compile(r"^Total:$"))
                if total_row:
                    total_cell = total_row.find_parent("tr").find_all("td")[-1]
                    total_text = total_cell.get_text().strip()
                    order_info["total"] = total_text

        except Exception as e:
            logger.warning(f"Error extracting order info: {e}")

        return order_info

    def _parse_invoice_products(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse product list from invoice HTML"""
        parts = []

        try:
            # Find the products table
            products_table = soup.find("table", class_="innovoice_products_table")
            if not products_table:
                logger.warning("Products table not found in invoice")
                return parts

            # Find all product rows (rows with main_image_holder)
            product_rows = products_table.find_all("div", class_="main_image_holder")

            for img_div in product_rows:
                try:
                    # Get the row containing this product
                    row = img_div.find_parent("tr")
                    if not row:
                        continue

                    # Extract image
                    img_tag = img_div.find("img", class_="main_image")
                    image_url = img_tag.get("src") if img_tag else None

                    # Extract product name and quantity
                    text_holder = row.find("div", class_="main_text_holder")
                    if not text_holder:
                        continue

                    # Quantity is in span with class "innovoice_24 bold blue"
                    qty_span = text_holder.find("span", class_="innovoice_24")
                    quantity = 1
                    if qty_span:
                        qty_text = qty_span.get_text().strip("()")
                        try:
                            quantity = int(qty_text)
                        except ValueError:
                            pass

                    # Product name is in span with class "innovoice_8"
                    name_span = text_holder.find("span", class_="innovoice_8")
                    name = name_span.get_text().strip() if name_span else ""

                    # Extract PID (Product ID)
                    pid_cell = row.find_all("td")[1]  # Second column
                    pid_span = pid_cell.find("span", class_="blue")
                    pid = pid_span.get_text().strip() if pid_span else ""

                    # Extract prices from third and fourth columns
                    price_cells = row.find_all("td", class_="right")
                    unit_price = None
                    total_price = None

                    if len(price_cells) >= 2:
                        # Unit price
                        unit_price_text = price_cells[0].get_text().strip()
                        unit_price_match = re.search(r"\$?([\d.]+)", unit_price_text)
                        if unit_price_match:
                            try:
                                unit_price = float(unit_price_match.group(1))
                            except ValueError:
                                pass

                        # Total price
                        total_price_text = price_cells[1].get_text().strip()
                        total_price_match = re.search(r"\$?([\d.]+)", total_price_text)
                        if total_price_match:
                            try:
                                total_price = float(total_price_match.group(1))
                            except ValueError:
                                pass

                    # Create part data
                    if pid and name:
                        part_data = {
                            "supplier_part_number": pid,
                            "part_number": pid,
                            "name": name,
                            "description": name,
                            "manufacturer": "Adafruit Industries",
                            "quantity": quantity,
                            "supplier": "Adafruit Industries",
                            "image_url": image_url,
                        }

                        if unit_price is not None:
                            part_data["unit_price"] = unit_price

                        if total_price is not None:
                            part_data["total_price"] = total_price

                        parts.append(part_data)

                except Exception as e:
                    logger.warning(f"Error parsing product row: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing invoice products: {e}")

        return parts

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
            "supplier_part_number": supplier_data.supplier_part_number,
            "part_name": supplier_data.part_name or supplier_data.description or supplier_data.supplier_part_number,
            "manufacturer": supplier_data.manufacturer,
            "manufacturer_part_number": supplier_data.manufacturer_part_number,
            "description": supplier_data.description,
            "category": supplier_data.category,
        }

        # Add image and datasheet URLs if available
        if supplier_data.image_url:
            mapped["image_url"] = supplier_data.image_url
        if supplier_data.datasheet_url:
            mapped["datasheet_url"] = supplier_data.datasheet_url

        # Extract unit price from pricing array (first tier)
        if supplier_data.pricing and len(supplier_data.pricing) > 0:
            first_price = supplier_data.pricing[0]
            mapped["unit_price"] = first_price.get("price")
            mapped["currency"] = first_price.get("currency", "USD")

        # Flatten specifications into custom fields
        if supplier_data.specifications:
            for spec_key, spec_value in supplier_data.specifications.items():
                # Create readable field names
                field_name = spec_key.replace("_", " ").title()
                if spec_value is not None:
                    mapped[field_name] = str(spec_value)

        # Flatten additional_data into custom fields
        if supplier_data.additional_data:
            for key, value in supplier_data.additional_data.items():
                # Skip internal tracking fields
                if key in ["source", "scraped_at", "api_version", "last_updated", "warning", "data_source"]:
                    continue
                # Create readable field names
                field_name = key.replace("_", " ").title()
                if value is not None:
                    mapped[field_name] = str(value)

        return mapped
