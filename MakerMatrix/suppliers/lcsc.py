"""
LCSC Supplier Implementation

Modernized implementation using unified supplier architecture:
- Uses SupplierHTTPClient for all HTTP operations (eliminates 100+ lines)
- Uses DataExtractor for standardized data parsing (eliminates 150+ lines)
- Implements defensive null safety patterns throughout
- No authentication required - uses public EasyEDA API
"""

import re
import json
import logging
import html
from urllib.parse import urljoin
from html.parser import HTMLParser
import pandas as pd
from typing import List, Dict, Any, Optional

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, ConfigurationOption,
    CapabilityRequirement, ImportResult
)
from MakerMatrix.models.enrichment_requirement_models import (
    EnrichmentRequirements, FieldRequirement, RequirementSeverity
)
from .registry import register_supplier
from .http_client import SupplierHTTPClient, RetryConfig
from .data_extraction import DataExtractor, extract_common_part_data
from .exceptions import (
    SupplierError, SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)
from MakerMatrix.services.data.unified_column_mapper import UnifiedColumnMapper
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper

logger = logging.getLogger(__name__)


class _LCSCProductPageTableParser(HTMLParser):
    """Lightweight HTML parser to extract key/value rows from LCSC tables."""

    def __init__(self):
        super().__init__()
        self.rows: List[Dict[str, Any]] = []
        self._current_row: List[Dict[str, Optional[str]]] = []
        self._in_td: bool = False
        self._skip_depth: int = 0
        self._current_text_parts: List[str] = []
        self._current_links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        if tag == "tr":
            self._current_row = []
        elif tag == "td":
            self._in_td = True
            self._current_text_parts = []
            self._current_links = []
        elif tag == "a" and self._in_td:
            href = dict(attrs).get("href")
            if href:
                self._current_links.append(href)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return

        if self._skip_depth > 0:
            return

        if tag == "td" and self._in_td:
            text = ''.join(self._current_text_parts)
            cleaned_text = self._clean_text(text)
            link = self._current_links[0] if self._current_links else None
            self._current_row.append({"text": cleaned_text, "link": link})
            self._in_td = False
        elif tag == "tr" and self._current_row:
            if len(self._current_row) >= 2:
                label = self._current_row[0].get("text", "").strip()
                value = self._current_row[1].get("text", "").strip()
                link = self._current_row[1].get("link")
                if label:
                    self.rows.append({
                        "label": label,
                        "value": value,
                        "link": link
                    })
            self._current_row = []

    def handle_data(self, data):
        if self._skip_depth > 0 or not self._in_td:
            return
        if data:
            self._current_text_parts.append(data)

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        unescaped = html.unescape(text)
        # Collapse whitespace while preserving hyphenated values
        return ' '.join(unescaped.split())


def _decode_js_string(value: str) -> str:
    """Decode JavaScript-style escaped string."""
    if value is None:
        return ""
    if '\\u' in value or '\\x' in value:
        try:
            return bytes(value, 'utf-8').decode('unicode_escape').strip()
        except UnicodeDecodeError:
            pass
    return value.strip()


@register_supplier("lcsc")
class LCSCSupplier(BaseSupplier):
    """
    LCSC supplier implementation using unified supplier architecture.
    
    Modernized with:
    - SupplierHTTPClient for unified HTTP operations 
    - DataExtractor for standardized parsing
    - Defensive null safety patterns
    - Consistent error handling
    """
    
    def __init__(self):
        super().__init__()
        self._http_client: Optional[SupplierHTTPClient] = None
        self._data_extractor: Optional[DataExtractor] = None
        
        # LCSC-specific data extraction configuration
        self._extraction_config = {
            "description_paths": ["title", "dataStr.head.c_para.Value", "description"],
            "image_paths": ["thumb", "image_url", "thumbnail", "photo"],
            "datasheet_paths": [
                "packageDetail.dataStr.head.c_para.link",
                "dataStr.head.c_para.link", 
                "dataStr.head.c_para.Datasheet",
                "szlcsc.attributes.Datasheet",
                "packageDetail.datasheet_pdf",
                "datasheet_pdf"
            ],
            "specifications": {
                "manufacturer": ["dataStr.head.c_para.Manufacturer"],
                "manufacturer_part": ["dataStr.head.c_para.Manufacturer Part"],
                "package": ["dataStr.head.c_para.package"],
                "value": ["dataStr.head.c_para.Value"],
                "mounting": ["SMT"]
            },
            # Note: Don't use base_url here as EasyEDA thumb paths need special handling
            "base_url": None
        }
    
    def _get_http_client(self) -> SupplierHTTPClient:
        """Get or create HTTP client with LCSC-specific configuration"""
        if not self._http_client:
            config = self._config or {}
            rate_limit = config.get("rate_limit_requests_per_minute", 20)
            
            # Calculate request delay from rate limit
            delay_seconds = 60.0 / max(rate_limit, 1)
            
            # Configure retry behavior for LCSC
            retry_config = RetryConfig(
                max_retries=2,
                base_delay=delay_seconds,
                max_delay=30.0,
                retry_on_status=[429, 500, 502, 503, 504]
            )
            
            # Standard headers for EasyEDA API
            default_headers = {
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "MakerMatrix/1.0 (easyeda2kicad compatible)"
            }
            
            # Add custom headers from configuration
            custom_headers_text = config.get("custom_headers", "")
            if custom_headers_text and custom_headers_text.strip():
                for line in custom_headers_text.strip().split('\n'):
                    line = line.strip()
                    if ':' in line:
                        header_name, header_value = line.split(':', 1)
                        default_headers[header_name.strip()] = header_value.strip()
            
            self._http_client = SupplierHTTPClient(
                supplier_name="lcsc",
                default_timeout=config.get("request_timeout", 30),
                default_headers=default_headers,
                retry_config=retry_config
            )
        
        return self._http_client
    
    def _get_data_extractor(self) -> DataExtractor:
        """Get or create data extractor"""
        if not self._data_extractor:
            self._data_extractor = DataExtractor("lcsc")
        return self._data_extractor
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="lcsc",
            display_name="LCSC Electronics",
            description="Chinese electronics component supplier with EasyEDA integration and competitive pricing. Modernized implementation with unified architecture.",
            website_url="https://www.lcsc.com",
            api_documentation_url="https://easyeda.com",
            supports_oauth=False,
            rate_limit_info="Configurable rate limiting (default: 20 requests per minute)",
            supported_file_types=["csv"]
        )
    
    def get_capabilities(self) -> List[SupplierCapability]:
        return [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_PRICING_STOCK,
            SupplierCapability.IMPORT_ORDERS
        ]
    
    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """LCSC uses public API, so no credentials required"""
        return {
            cap: CapabilityRequirement(
                capability=cap,
                required_credentials=[],  # No credentials needed
                description=f"LCSC {cap.value} using public EasyEDA API"
            )
            for cap in self.get_capabilities()
        }

    def get_enrichment_requirements(self) -> EnrichmentRequirements:
        """
        Define what part data is required for enrichment from LCSC.

        LCSC requires the supplier_part_number (LCSC part number starting with 'C')
        to look up parts in their EasyEDA API.

        Returns:
            EnrichmentRequirements with required, recommended, and optional fields
        """
        return EnrichmentRequirements(
            supplier_name="lcsc",
            display_name="LCSC Electronics",
            description="LCSC can enrich parts with detailed specifications, images, pricing, stock levels, and datasheets using the EasyEDA API",
            required_fields=[
                FieldRequirement(
                    field_name="supplier_part_number",
                    display_name="LCSC Part Number",
                    severity=RequirementSeverity.REQUIRED,
                    description="The LCSC part number (e.g., C25804) is required to look up part details from the EasyEDA API. This is the primary identifier for LCSC parts.",
                    example="C25804",
                    validation_pattern="^C\\d+$"
                )
            ],
            recommended_fields=[
                FieldRequirement(
                    field_name="manufacturer_part_number",
                    display_name="Manufacturer Part Number",
                    severity=RequirementSeverity.RECOMMENDED,
                    description="Having the manufacturer part number helps validate that the enriched data matches your intended part",
                    example="STM32F103C8T6"
                )
            ],
            optional_fields=[
                FieldRequirement(
                    field_name="description",
                    display_name="Part Description",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Existing description can help verify the enriched data is correct",
                    example="ARM Cortex-M3 microcontroller"
                ),
                FieldRequirement(
                    field_name="component_type",
                    display_name="Component Type",
                    severity=RequirementSeverity.OPTIONAL,
                    description="Component type helps organize enriched specifications",
                    example="Microcontroller"
                )
            ]
        )

    def get_credential_schema(self) -> List[FieldDefinition]:
        # No credentials required for LCSC public API
        return []
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        """Get configuration schema for LCSC supplier"""
        config_options = self.get_configuration_options()
        default_option = next((opt for opt in config_options if opt.is_default), None)
        return default_option.schema if default_option else []
    
    def get_configuration_options(self) -> List[ConfigurationOption]:
        """Configuration options for LCSC rate limiting"""
        return [
            ConfigurationOption(
                name='standard',
                label='LCSC Rate Limiting',
                description='Configure rate limiting for responsible LCSC API access.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=20,
                        description="Maximum requests per minute",
                        validation={"min": 1, "max": 60},
                        help_text="Lower values are more respectful to LCSC servers"
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
                description='Very slow rate limiting for bulk operations.',
                schema=[
                    FieldDefinition(
                        name="rate_limit_requests_per_minute",
                        label="Rate Limit (requests per minute)",
                        field_type=FieldType.NUMBER,
                        required=False,
                        default_value=10,
                        description="Conservative rate limiting",
                        validation={"min": 1, "max": 60},
                        help_text="Best for large batch operations"
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
        config = self._config or {}
        version = config.get("api_version", "6.4.19.5")
        return f"https://easyeda.com/api/products/{lcsc_id}/components?version={version}"
    
    async def authenticate(self) -> bool:
        """No authentication required for EasyEDA public API"""
        return True
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to EasyEDA API using unified HTTP client.

        LCSC uses public API and requires no configuration, so we skip
        the configuration check and test the API directly.
        """
        try:
            http_client = self._get_http_client()
            
            # Test with a known LCSC part (resistor)
            test_lcsc_id = "C25804"  # Common 10K resistor
            url = self._get_easyeda_api_url(test_lcsc_id)
            
            # Make request using unified HTTP client
            response = await http_client.get(url, endpoint_type="test_connection")
            
            if response.success and response.data.get("result"):
                config = self._config or {}
                return {
                    "success": True,
                    "message": "LCSC/EasyEDA API connection successful",
                    "details": {
                        "api_endpoint": "EasyEDA API",
                        "test_part": test_lcsc_id,
                        "rate_limit": f"{config.get('rate_limit_requests_per_minute', 20)} requests per minute",
                        "response_time_ms": response.duration_ms,
                        "api_ready": True
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"API test failed: {response.error_message or 'Invalid response'}",
                    "details": {
                        "status_code": response.status,
                        "response_data": response.data
                    }
                }
                
        except Exception as e:
            logger.error(f"LCSC connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"exception": str(e)}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """
        LCSC/EasyEDA API doesn't support search - only individual part lookup.
        If query looks like an LCSC part number, try to get part details.
        """
        # Check if query looks like an LCSC part number (e.g., C25804, c123456)
        lcsc_pattern = re.compile(r'^c\d+$', re.IGNORECASE)
        if lcsc_pattern.match(query.strip()):
            part_details = await self.get_part_details(query.strip().upper())
            return [part_details] if part_details else []
        else:
            # For non-LCSC part numbers, return empty list since we can't search
            return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed information about a specific LCSC part using unified architecture"""
        async def _impl():
            try:
                # Clean part number
                lcsc_id = supplier_part_number.strip().upper()

                # Try EasyEDA API first
                http_client = self._get_http_client()
                url = self._get_easyeda_api_url(lcsc_id)

                response = await http_client.get(url, endpoint_type="get_part_details")

                # Check if result exists and has data
                if response.success and response.data.get("result") is not None:
                    # Parse EasyEDA response (includes product page enrichment)
                    return await self._parse_easyeda_response(response.data, lcsc_id)

                # EasyEDA API failed or returned no data - try product page fallback
                logger.info(f"EasyEDA API returned no data for {lcsc_id}, attempting product page fallback")
                page_details = await self._fetch_product_page_details(lcsc_id)

                if not page_details:
                    logger.warning(f"Both EasyEDA API and product page failed for {lcsc_id}")
                    return None

                # Build PartSearchResult from product page data only
                return await self._parse_product_page_only(page_details, lcsc_id)

            except Exception as e:
                logger.error(f"Failed to get LCSC part details for {supplier_part_number}: {e}")
                return None

        return await self._tracked_api_call("get_part_details", _impl)
    
    def _preprocess_lcsc_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess LCSC data to fix protocol-relative URLs and other format issues"""
        if not isinstance(data, dict):
            return data
        
        # Create a deep copy to avoid modifying original data
        import copy
        processed_data = copy.deepcopy(data)
        
        # Fix protocol-relative URLs (starting with //)
        def fix_urls(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith("//"):
                        obj[key] = "https:" + value
                    elif isinstance(value, (dict, list)):
                        fix_urls(value)
            elif isinstance(obj, list):
                for item in obj:
                    fix_urls(item)
        
        fix_urls(processed_data)
        return processed_data

    async def _fetch_product_page_details(self, lcsc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the public LCSC product page for additional metadata."""
        try:
            http_client = self._get_http_client()
            product_url = f"https://www.lcsc.com/product-detail/{lcsc_id}.html"
            response = await http_client.get(product_url, endpoint_type="product_page")

            if not response.success or not response.raw_content:
                logger.debug(
                    "LCSC product page fetch failed for %s (status=%s)",
                    lcsc_id,
                    response.status,
                )
                return None

            return self._parse_product_page_html(response.raw_content, product_url)

        except Exception as exc:
            logger.warning(
                "Failed to fetch LCSC product page for %s: %s",
                lcsc_id,
                exc,
            )
            return None

    def _parse_product_page_html(self, html_text: str, page_url: str) -> Dict[str, Any]:
        """Parse key metadata from the LCSC product detail page HTML."""
        page_details: Dict[str, Any] = {
            "attributes": {},
            "attribute_links": {},
            "product_url": page_url,
        }

        nuxt_value_map = self._extract_nuxt_value_map(html_text)

        # Extract structured JSON-LD blocks for canonical product metadata
        try:
            script_pattern = re.compile(
                r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                re.IGNORECASE | re.DOTALL,
            )
            for match in script_pattern.finditer(html_text):
                raw_block = match.group(1).strip()
                if not raw_block:
                    continue

                try:
                    data = json.loads(raw_block)
                except json.JSONDecodeError:
                    continue

                # Some pages emit a list of JSON-LD objects
                if isinstance(data, list):
                    for item in data:
                        self._merge_json_ld_item(item, page_details)
                else:
                    self._merge_json_ld_item(data, page_details)
        except Exception as exc:
            logger.debug("Failed parsing JSON-LD for LCSC page %s: %s", page_url, exc)

        # Extract tabular key/value data (Manufacturer, Package, Key Attributes, etc.)
        table_parser = _LCSCProductPageTableParser()
        table_parser.feed(html_text)

        for row in table_parser.rows:
            label = row.get("label", "")
            value_text = row.get("value", "")
            link = row.get("link")

            if not label:
                continue

            if value_text:
                page_details.setdefault("attributes", {})[label] = value_text

            if link:
                page_details.setdefault("attribute_links", {})[label] = urljoin(page_url, link)

        datasheet_link = page_details.get("attribute_links", {}).get("Datasheet")
        if datasheet_link:
            page_details["datasheet_url"] = datasheet_link

        # Extract dynamic specification data embedded in __NUXT__ payload
        specs_from_nuxt = self._extract_nuxt_specifications(html_text, nuxt_value_map)
        for spec_name, spec_value in specs_from_nuxt.items():
            if spec_value:
                page_details.setdefault("attributes", {}).setdefault(spec_name, spec_value)

        return page_details

    def _extract_nuxt_value_map(self, html_text: str) -> Dict[str, Any]:
        """Build mapping from short parameter names to their values in __NUXT__ payload."""
        try:
            function_match = re.search(r'window.__NUXT__=\(function\((.*?)\)\{', html_text, re.DOTALL)
            call_match = re.search(r'\}\((.*)\);</script>', html_text, re.DOTALL)
            if not function_match or not call_match:
                return {}

            params = [p.strip() for p in function_match.group(1).split(',')]
            raw_args = call_match.group(1).replace('\n', '')

            args: List[str] = []
            current = ''
            brackets = 0
            quotes: Optional[str] = None
            escape = False

            for ch in raw_args:
                if escape:
                    current += ch
                    escape = False
                    continue
                if ch == '\\':
                    current += ch
                    escape = True
                    continue
                if quotes:
                    current += ch
                    if ch == quotes:
                        quotes = None
                    continue
                if ch in ('"', "'"):
                    current += ch
                    quotes = ch
                    continue
                if ch in '([{':
                    brackets += 1
                    current += ch
                    continue
                if ch in ')]}':
                    brackets -= 1
                    current += ch
                    continue
                if ch == ',' and brackets == 0:
                    args.append(current.strip())
                    current = ''
                    continue
                current += ch

            if current.strip():
                args.append(current.strip())

            value_map: Dict[str, Any] = {}
            for name, value in zip(params, args):
                parsed_value = self._convert_js_token(value)
                value_map[name] = parsed_value

            return value_map

        except Exception as exc:
            logger.debug("Failed to parse __NUXT__ value map: %s", exc)
            return {}

    def _convert_js_token(self, token: str) -> Any:
        """Convert primitive JS token to Python value."""
        if token is None:
            return None

        token = token.strip()
        if not token:
            return None

        if token.lower() in {'null', 'undefined'}:
            return None
        if token in {'true', 'True'}:
            return True
        if token in {'false', 'False'}:
            return False

        if token.startswith(('"', "'")) and token.endswith(('"', "'")):
            inner = token[1:-1]
            inner = inner.replace('\\u002F', '/')
            return _decode_js_string(inner)

        # Numeric values
        try:
            if token.startswith('.'):
                token = '0' + token
            if '.' in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        return token

    def _extract_nuxt_specifications(self, html_text: str, value_map: Dict[str, Any]) -> Dict[str, str]:
        """Extract specification list defined in __NUXT__ payload."""
        specifications: Dict[str, str] = {}

        if not value_map:
            return specifications

        try:
            pattern = re.compile(
                r'paramNameEn:"([^"]+)"[^}]*?paramValueEn:([^,}\]]+)',
                re.DOTALL
            )

            for match in pattern.finditer(html_text):
                spec_name = match.group(1).strip()
                value_token = match.group(2).strip()

                if not spec_name or spec_name.startswith('param_'):
                    continue

                resolved_value = self._resolve_nuxt_value_token(value_token, value_map)
                if resolved_value:
                    specifications[spec_name] = resolved_value

        except Exception as exc:
            logger.debug("Failed to extract __NUXT__ specifications: %s", exc)

        return specifications

    def _resolve_nuxt_value_token(self, token: str, value_map: Dict[str, Any]) -> Optional[str]:
        token = token.strip()
        if not token:
            return None

        # Remove trailing characters such as ')' from invocation wrappers
        token = token.rstrip(')')

        if token.startswith(('"', "'")) and token.endswith(('"', "'")):
            value = self._convert_js_token(token)
            return str(value) if value is not None else None

        if token in value_map:
            value = value_map[token]
            if isinstance(value, str):
                return value
            return str(value) if value is not None else None

        return None

    async def _parse_product_page_only(self, page_details: Dict[str, Any], lcsc_id: str) -> PartSearchResult:
        """
        Build PartSearchResult from product page data only (fallback when EasyEDA API fails).
        Used for parts that exist on LCSC.com but not in EasyEDA database.
        """
        attributes = page_details.get("attributes", {})

        # Extract core fields
        manufacturer = page_details.get("brand") or attributes.get("Manufacturer", "")
        manufacturer_part_number = page_details.get("mpn") or attributes.get("Mfr. Part #", "")
        description = attributes.get("Description") or page_details.get("description") or page_details.get("name", "")
        category = page_details.get("category") or attributes.get("Category", "")

        # Get datasheet URL
        datasheet_url = page_details.get("datasheet_url") or page_details.get("attribute_links", {}).get("Datasheet")

        # Get image URL
        image_url = page_details.get("image_url")

        # Build flat additional_data from all attributes
        additional_data = {
            "lcsc_part_number": lcsc_id,
            "product_url": f"https://www.lcsc.com/product-detail/{lcsc_id}.html",
            "data_source": "lcsc_product_page_only"  # Indicate this came from page scraping
        }

        # Add package info
        package = attributes.get("Package")
        if package:
            additional_data["package"] = package

        # Add key attributes
        key_attributes = attributes.get("Key Attributes")
        if key_attributes:
            additional_data["key_attributes"] = key_attributes

        # Add pricing/stock if available
        if page_details.get("price") is not None:
            additional_data["lcsc_price"] = page_details["price"]
        if page_details.get("price_currency"):
            additional_data["lcsc_price_currency"] = page_details["price_currency"]
        if page_details.get("inventory_level") is not None:
            additional_data["lcsc_inventory_level"] = page_details["inventory_level"]

        # Add remaining attributes as flat data
        for attr_name, attr_value in attributes.items():
            if not attr_value:
                continue
            if attr_name in {"Manufacturer", "Mfr. Part #", "LCSC Part #", "Package", "Key Attributes", "Description", "Category"}:
                continue
            # Convert to clean key format
            clean_key = attr_name.lower().replace(' ', '_').replace('-', '_')
            additional_data[clean_key] = attr_value

        return PartSearchResult(
            supplier_part_number=lcsc_id,
            manufacturer=manufacturer,
            manufacturer_part_number=manufacturer_part_number,
            description=description,
            category=category,
            datasheet_url=datasheet_url,
            image_url=image_url,
            stock_quantity=page_details.get("inventory_level"),
            pricing=None,  # Could be extracted from page but format varies
            specifications=None,
            additional_data=additional_data
        )

    def _merge_json_ld_item(self, item: Dict[str, Any], page_details: Dict[str, Any]) -> None:
        """Merge a parsed JSON-LD item into the page details structure."""
        if not isinstance(item, dict):
            return

        item_type = item.get("@type")

        if item_type == "ImageObject":
            image_url = item.get("contentUrl") or item.get("thumbnail")
            if image_url:
                page_details["image_url"] = image_url
            if item.get("description") and not page_details.get("description"):
                page_details["description"] = item["description"]

        elif item_type == "Product":
            # Core identifiers
            for key in ("name", "description", "mpn", "sku", "category"):
                value = item.get(key)
                if value and not page_details.get(key):
                    page_details[key] = value

            brand = item.get("brand")
            if brand:
                if isinstance(brand, dict):
                    brand_name = brand.get("name")
                else:
                    brand_name = brand
                if brand_name:
                    page_details["brand"] = brand_name

            # Offers block can contain pricing and inventory data
            offers = item.get("offers")
            if isinstance(offers, dict):
                price = offers.get("price")
                currency = offers.get("priceCurrency")
                inventory_level = offers.get("inventoryLevel")

                try:
                    if price is not None:
                        page_details["price"] = float(price)
                except (TypeError, ValueError):
                    pass

                if currency:
                    page_details["price_currency"] = currency

                try:
                    if inventory_level is not None:
                        page_details["inventory_level"] = int(inventory_level)
                except (TypeError, ValueError):
                    pass

    
    async def _parse_easyeda_response(self, data: Dict[str, Any], lcsc_id: str) -> PartSearchResult:
        """Parse EasyEDA API response using unified data extraction"""
        extractor = self._get_data_extractor()
        
        # Extract result data safely using defensive null safety
        result = extractor.safe_get(data, "result", {})
        
        # Pre-process the data to fix protocol-relative URLs before extraction
        processed_result = self._preprocess_lcsc_data(result)
        
        # Extract common part data using unified extraction config
        extracted_data = extract_common_part_data(extractor, processed_result, self._extraction_config)
        
        # Extract LCSC-specific data using safe access patterns
        manufacturer = extractor.safe_get(result, ["dataStr", "head", "c_para", "Manufacturer"])
        manufacturer_part_number = extractor.safe_get(result, ["dataStr", "head", "c_para", "Manufacturer Part"])
        value = extractor.safe_get(result, ["dataStr", "head", "c_para", "Value"])
        package = extractor.safe_get(result, ["dataStr", "head", "c_para", "package"])
        
        # Extract category from tags
        tags = result.get('tags', [])
        category = tags[0] if tags else ''
        
        # Determine part type from prefix
        prefix = extractor.safe_get(result, ["dataStr", "head", "c_para", "pre"], "")
        part_type = ""
        if prefix.startswith('C?'):
            part_type = "capacitor"
        elif prefix.startswith('R?'):
            part_type = "resistor"
        
        # Check if SMT
        is_smt = result.get('SMT', False)
        
        # Build flat additional_data instead of nested specifications
        # Store simple key-value pairs that will be flattened into additional_properties
        flat_specs = {}
        if value:
            flat_specs['value'] = value
        if package:
            flat_specs['package'] = package
        if is_smt:
            flat_specs['mounting_type'] = 'SMT'

        # Merge with extracted specifications but flatten them
        if extracted_data.get("specifications"):
            extracted_specs = extracted_data["specifications"]
            if isinstance(extracted_specs, dict):
                # Flatten any nested specifications
                for spec_key, spec_value in extracted_specs.items():
                    # Convert to lowercase with underscores for consistency
                    clean_key = spec_key.lower().replace(' ', '_').replace('-', '_')
                    flat_specs[clean_key] = spec_value
        
        # Build additional data with flat specifications merged in
        additional_data = {
            "part_type": part_type,
            "is_smt": is_smt,
            "prefix": prefix,
            "easyeda_data_available": True,
            "product_url": f"https://www.lcsc.com/product-detail/{lcsc_id}.html"
        }
        # Merge flat specifications directly into additional_data
        additional_data.update(flat_specs)

        # Base description, datasheet, pricing, and stock information from EasyEDA
        description = extracted_data.get("description") or (value or "")
        datasheet_url = extracted_data.get("datasheet_url") or extractor.safe_get(
            result, ["dataStr", "head", "c_para", "link"]
        )
        image_url = extracted_data.get("image_url")
        stock_quantity = extracted_data.get("stock_quantity")
        pricing = extracted_data.get("pricing")

        # If no image URL from extraction, try manual thumb field extraction
        if not image_url:
            thumb_value = extractor.safe_get(result, ["thumb"])
            if thumb_value:
                image_url = thumb_value

        # Handle different URL formats from EasyEDA API
        if image_url:
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            elif image_url.startswith("/component/"):
                image_url = "https://easyeda.com" + image_url
            elif not image_url.startswith("http"):
                image_url = "https://easyeda.com" + (image_url if image_url.startswith("/") else "/" + image_url)

        # Fetch and merge additional metadata from the public product page
        page_details = await self._fetch_product_page_details(lcsc_id)
        if page_details:
            attributes = page_details.get("attributes", {})
            attribute_links = page_details.get("attribute_links", {})

            # Prefer clean manufacturer and MPN values from the product page when available
            manufacturer = page_details.get("brand") or attributes.get("Manufacturer") or manufacturer
            manufacturer_part_number = page_details.get("mpn") or attributes.get("Mfr. Part #") or manufacturer_part_number

            # Rich description overrides the terse EasyEDA title
            rich_description = attributes.get("Description") or page_details.get("description")
            if rich_description and len(rich_description) > len(description):
                description = rich_description

            # Capture key attributes and structured package information as flat data
            key_attributes = attributes.get("Key Attributes")
            if key_attributes:
                additional_data['key_attributes'] = key_attributes

            package_from_page = attributes.get("Package")
            if package_from_page:
                additional_data['package'] = package_from_page

            # Datasheet link on the product page tends to be more reliable
            datasheet_link = page_details.get("datasheet_url") or attribute_links.get("Datasheet")
            if datasheet_link:
                datasheet_url = datasheet_link

            # Prefer high-resolution marketing image when present
            if page_details.get("image_url"):
                image_url = page_details["image_url"]

            # Update category from structured data if EasyEDA tags were empty
            category = page_details.get("category") or category

            # Enrich additional metadata with pricing and inventory when provided
            if page_details.get("price") is not None:
                additional_data['lcsc_price'] = page_details['price']
            if page_details.get("price_currency"):
                additional_data['lcsc_price_currency'] = page_details['price_currency']
            if page_details.get("inventory_level") is not None:
                additional_data['lcsc_inventory_level'] = page_details['inventory_level']
            if page_details.get("name"):
                additional_data['lcsc_product_name'] = page_details['name']

            # Store the resolved datasheet link for downstream consumers
            if datasheet_url:
                additional_data['lcsc_datasheet_url'] = datasheet_url

            # Capture remaining attribute rows as flat additional_data
            for attr_name, attr_value in attributes.items():
                if not attr_value:
                    continue

                normalized_attr = attr_name.strip()

                if normalized_attr in {"Manufacturer", "Mfr. Part #", "LCSC Part #", "Package", "Key Attributes", "Description"}:
                    continue

                if normalized_attr == "Category":
                    additional_data['lcsc_category'] = attr_value
                    continue

                # Convert attribute name to clean key format
                clean_attr_key = normalized_attr.lower().replace(' ', '_').replace('-', '_')
                additional_data[clean_attr_key] = attr_value

        return PartSearchResult(
            supplier_part_number=lcsc_id,
            manufacturer=manufacturer,
            manufacturer_part_number=manufacturer_part_number,
            description=description,
            category=category or (part_type.title() if part_type else ""),
            datasheet_url=datasheet_url,
            image_url=image_url,
            stock_quantity=stock_quantity,
            pricing=pricing,
            specifications=None,  # No longer using nested specifications
            additional_data=additional_data  # All data is now flat
        )
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for an LCSC part"""
        async def _impl():
            part_details = await self.get_part_details(supplier_part_number)
            return part_details.datasheet_url if part_details else None
        
        return await self._tracked_api_call("fetch_datasheet", _impl)
    
    async def fetch_pricing_stock(self, supplier_part_number: str) -> Optional[Dict[str, Any]]:
        """Fetch pricing and stock information"""
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
    
    # ========== File Import Capability ==========
    
    def can_import_file(self, filename: str, file_content: bytes = None) -> bool:
        """Check if this supplier can handle this file"""
        if not filename:
            return False
        
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        return file_ext == 'csv' and 'lcsc' in filename.lower()
    
    async def import_order_file(self, file_content: bytes, file_type: str, filename: str = None) -> ImportResult:
        """Import LCSC CSV order file using unified patterns and proper data extraction"""
        async def _impl():
            if file_type.lower() != 'csv':
                return ImportResult(
                    success=False,
                    error_message="LCSC only supports CSV file imports"
                )
            
            try:
                # Decode CSV content with defensive encoding handling
                try:
                    csv_text = file_content.decode('utf-8-sig')  # Handle BOM
                except UnicodeDecodeError:
                    csv_text = file_content.decode('utf-8', errors='ignore')
                
                # Use pandas for robust CSV parsing
                from io import StringIO
                df = pd.read_csv(StringIO(csv_text))
                
                if df.empty:
                    return ImportResult(
                        success=False,
                        error_message="CSV file contains no data rows"
                    )
                
                # Initialize column mapper with LCSC-specific mappings
                column_mapper = UnifiedColumnMapper()
                lcsc_mappings = column_mapper.get_supplier_specific_mappings('lcsc')
                
                # Map columns using flexible matching
                mapped_columns = column_mapper.map_columns(df.columns.tolist(), lcsc_mappings)
                
                # Validate required columns
                required_fields = ['part_number', 'quantity']
                if not column_mapper.validate_required_columns(mapped_columns, required_fields):
                    return ImportResult(
                        success=False,
                        error_message=f"Required columns not found. Available columns: {list(df.columns)}"
                    )
                
                parts = []
                failed_items = []
                supplier_mapper = SupplierDataMapper()
                
                # Process each row with full data extraction
                for index, row in df.iterrows():
                    try:
                        # Extract all available data using column mapping
                        extracted_data = column_mapper.extract_row_data(row, mapped_columns)
                        
                        # Skip rows without part numbers
                        if not extracted_data.get('part_number'):
                            continue
                        
                        # Parse quantity safely
                        quantity = 1
                        if extracted_data.get('quantity'):
                            try:
                                quantity = max(1, int(float(str(extracted_data['quantity']).replace(',', ''))))
                            except (ValueError, TypeError):
                                quantity = 1
                        
                        # Parse pricing safely
                        unit_price = None
                        order_price = None
                        if extracted_data.get('unit_price'):
                            try:
                                unit_price = float(str(extracted_data['unit_price']).replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                pass
                        
                        if extracted_data.get('order_price'):
                            try:
                                order_price = float(str(extracted_data['order_price']).replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                pass
                        
                        # Create smart part name from available data
                        part_name = column_mapper.create_smart_part_name(extracted_data)
                        
                        # Build comprehensive additional_properties
                        additional_properties = self._build_lcsc_additional_properties(
                            extracted_data, unit_price, order_price, index
                        )
                        
                        # Create PartSearchResult object for SupplierDataMapper
                        from .base import PartSearchResult
                        part_search_result = PartSearchResult(
                            supplier_part_number=str(extracted_data['part_number']).strip(),
                            manufacturer=extracted_data.get('manufacturer', '').strip() if extracted_data.get('manufacturer') else None,
                            manufacturer_part_number=extracted_data.get('manufacturer_part_number', '').strip() if extracted_data.get('manufacturer_part_number') else None,
                            description=extracted_data.get('description', '').strip() if extracted_data.get('description') else None,
                            additional_data=additional_properties
                        )
                        
                        # Use SupplierDataMapper for standardization
                        standardized_part = supplier_mapper.map_supplier_result_to_part_data(
                            part_search_result, 'LCSC', enrichment_capabilities=['csv_import']
                        )
                        
                        # Add import-specific fields that aren't in PartSearchResult
                        standardized_part['part_name'] = part_name
                        standardized_part['quantity'] = quantity
                        standardized_part['supplier'] = 'LCSC'
                        
                        parts.append(standardized_part)
                        
                    except Exception as e:
                        failed_items.append({
                            'line_number': index + 2,  # +2 for header and 0-based index
                            'error': str(e),
                            'data': row.to_dict()
                        })
                        logger.warning(f"Failed to process LCSC CSV row {index + 2}: {e}")
                
                return ImportResult(
                    success=True,
                    imported_count=len(parts),
                    failed_count=len(failed_items),
                    parts=parts,
                    failed_items=failed_items,
                    parser_type="lcsc"
                )
                
            except Exception as e:
                logger.error(f"Failed to parse LCSC CSV: {e}")
                return ImportResult(
                    success=False,
                    error_message=f"Failed to parse LCSC CSV: {str(e)}"
                )
        
        return await self._tracked_api_call("import_orders", _impl)
    
    def _build_lcsc_additional_properties(self, extracted_data: Dict[str, Any], unit_price: Optional[float], order_price: Optional[float], row_index: int) -> Dict[str, Any]:
        """Build flat additional_properties for LCSC parts (no nested structures)"""
        # Create flat key-value pairs instead of nested structure
        additional_properties = {
            # Supplier information as flat keys
            'supplier_name': 'LCSC',
            'supplier_part_number': extracted_data.get('part_number'),
            'row_index': row_index,
            'import_source': 'csv'
        }

        # Add customer reference if available
        if extracted_data.get('customer_reference'):
            additional_properties['customer_reference'] = extracted_data['customer_reference']

        # Add minimum order quantity if available
        if extracted_data.get('min_order_qty'):
            try:
                min_qty_str = str(extracted_data['min_order_qty'])
                # Handle format like "5\5" - take the first number
                min_qty = int(min_qty_str.split('\\')[0]) if '\\' in min_qty_str else int(min_qty_str)
                additional_properties['minimum_order_quantity'] = min_qty
            except (ValueError, TypeError):
                pass

        # Add pricing information as flat keys
        if unit_price is not None:
            additional_properties['unit_price'] = unit_price
        if order_price is not None:
            additional_properties['order_price'] = order_price

        # Add package information as flat keys
        if extracted_data.get('package'):
            package_info = str(extracted_data['package']).strip()
            additional_properties['package'] = package_info

            # Extract mounting type from package info
            if 'smd' in package_info.lower():
                additional_properties['mounting_type'] = 'SMT'
            elif 'through' in package_info.lower() or 'th' in package_info.lower():
                additional_properties['mounting_type'] = 'Through Hole'

        # Add RoHS compliance as flat keys
        if extracted_data.get('rohs'):
            rohs_value = str(extracted_data['rohs']).strip().upper()
            if rohs_value in ['YES', 'Y', 'TRUE', '1']:
                additional_properties['rohs_compliant'] = True
            elif rohs_value in ['NO', 'N', 'FALSE', '0']:
                additional_properties['rohs_compliant'] = False

        return additional_properties
    
    # ========== Cleanup ==========
    
    async def close(self):
        """Clean up resources"""
        await super().close()
        if self._http_client:
            await self._http_client.close()
