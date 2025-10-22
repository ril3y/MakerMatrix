"""
McMaster-Carr Supplier Implementation

This supplier supports both:
1. Official API using client certificate authentication (contact eCommerce@mcmaster.com)
2. Web scraping fallback when API credentials are not available

The web scraping fallback is provided for convenience but may break if McMaster-Carr
changes their website structure. API access is recommended for production use.
"""

from typing import List, Dict, Any, Optional
import ssl
import aiohttp
import json
import re
from datetime import datetime, timedelta
import logging

from .base import (
    BaseSupplier, FieldDefinition, FieldType, SupplierCapability,
    PartSearchResult, SupplierInfo, CapabilityRequirement
)
from .exceptions import (
    SupplierConfigurationError, SupplierAuthenticationError,
    SupplierConnectionError, SupplierRateLimitError
)

logger = logging.getLogger(__name__)

class McMasterCarrSupplier(BaseSupplier):
    """McMaster-Carr Supplier Implementation

    Supports:
    1. Official API (requires approved account and certificates)
    2. Web scraping fallback (no credentials required)

    For API access, contact eCommerce@mcmaster.com for approval.
    """

    def __init__(self):
        super().__init__()
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._scraper = None  # Lazy-loaded web scraper
    
    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="McMaster-Carr",
            display_name="McMaster-Carr",
            description="Industrial supply with official API access - requires approval",
            website_url="https://www.mcmaster.com",
            api_documentation_url="Contact eCommerce@mcmaster.com for API documentation",
            supports_oauth=False,
            rate_limit_info="API rate limits apply - contact McMaster for details"
        )

    def get_url_patterns(self) -> List[str]:
        """Return URL patterns that identify McMaster-Carr product links"""
        return [
            r'mcmaster\.com',  # Base domain
            r'www\.mcmaster\.com',  # With www
            r'mcmaster-carr\.com',  # Alternative domain
            r'mcmaster\.com/[0-9A-Za-z]+',  # Product pages
            r'mcmaster\.com/.+/[0-9A-Za-z]+/?$',  # Product pages with category path
        ]

    def get_enrichment_field_mappings(self) -> List:
        """
        Get URL patterns and field mappings for auto-enrichment from McMaster-Carr product URLs.

        Returns patterns to extract the part number from McMaster-Carr URLs like:
        - https://www.mcmaster.com/91253A194/
        - https://mcmaster.com/screws/91253A194
        """
        from .base import EnrichmentFieldMapping

        return [
            EnrichmentFieldMapping(
                field_name="supplier_part_number",
                display_name="McMaster-Carr Part Number",
                url_patterns=[
                    r'/([A-Za-z0-9]+)/?$',  # Extract part number from end of URL
                    r'/([A-Za-z0-9]+)/?(?:\?|#|$)',  # Handle query strings and fragments
                ],
                example="91253A194",
                description="The part number from the McMaster-Carr product page URL",
                required_for_enrichment=True
            )
        ]

    def get_capabilities(self) -> List[SupplierCapability]:
        # McMaster-Carr API implementation - requires approved account and certificates
        # NOTE: McMaster does NOT support datasheets - removed FETCH_DATASHEET capability
        return [
            SupplierCapability.GET_PART_DETAILS,
            # SupplierCapability.IMPORT_ORDERS
            # Note: FETCH_PRICING_STOCK not implemented yet
            # Note: FETCH_DATASHEET removed - McMaster doesn't provide datasheets
        ]

    def get_capability_requirements(self) -> Dict[SupplierCapability, CapabilityRequirement]:
        """Define what credentials each capability needs"""
        all_creds_req = ["username", "password", "client_cert_path", "client_cert_password"]
        return {
            capability: CapabilityRequirement(
                capability=capability,
                required_credentials=all_creds_req
            )
            for capability in self.get_capabilities()
        }
    
    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="username",
                label="API Username",
                field_type=FieldType.TEXT,
                required=True,
                description="McMaster-Carr approved API account username",
                help_text="Contact eCommerce@mcmaster.com for API approval"
            ),
            FieldDefinition(
                name="password",
                label="API Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="McMaster-Carr API account password",
                help_text="Your approved API account password"
            ),
            FieldDefinition(
                name="client_cert_path",
                label="Client Certificate Path",
                field_type=FieldType.TEXT,
                required=True,
                description="Path to client certificate file (.p12 or .pfx)",
                help_text="McMaster-Carr provides client certificates for API access"
            ),
            FieldDefinition(
                name="client_cert_password",
                label="Client Certificate Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Client certificate password",
                help_text="Password for your McMaster-Carr client certificate"
            )
        ]
    
    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_base_url",
                label="API Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://www.mcmaster.com/api/v1",
                description="McMaster-Carr official API endpoint",
                help_text="Official API base URL (requires approval from McMaster)"
            ),
            FieldDefinition(
                name="timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="API request timeout in seconds",
                help_text="Maximum time to wait for API responses"
            ),
            FieldDefinition(
                name="rate_limit_delay",
                label="Rate Limit Delay (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=1.0,
                description="Delay between API requests",
                help_text="Respect McMaster's API rate limits"
            ),
            FieldDefinition(
                name="max_retries",
                label="Maximum Retries",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=3,
                description="Maximum number of API request retries",
                help_text="Number of times to retry failed requests"
            )
        ]
    
    async def _setup_ssl_context(self, credentials: Dict[str, str]) -> ssl.SSLContext:
        """Setup SSL context with client certificate"""
        if self._ssl_context:
            return self._ssl_context
        
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Load client certificate
            cert_path = credentials.get("client_cert_path")
            cert_password = credentials.get("client_cert_password")
            
            if not cert_path:
                raise SupplierConfigurationError("Client certificate path is required")
            
            # Load the client certificate
            context.load_cert_chain(cert_path, password=cert_password)
            
            self._ssl_context = context
            logger.info("✅ SSL context configured with client certificate")
            return context
            
        except Exception as e:
            raise SupplierConfigurationError(f"Failed to setup SSL context: {str(e)}")
    
    async def _authenticate(self, credentials: Dict[str, str]) -> str:
        """Authenticate with McMaster-Carr API and get access token"""
        
        if self._auth_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._auth_token
        
        try:
            ssl_context = await self._setup_ssl_context(credentials)
            base_url = self._config.get("api_base_url", "https://www.mcmaster.com/api/v1")
            timeout_seconds = self._config.get("timeout_seconds", 30)
            
            # Create HTTP connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                auth_url = f"{base_url}/auth/token"
                
                auth_data = {
                    "username": credentials["username"],
                    "password": credentials["password"]
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "MakerMatrix/1.0 (API Client)"
                }
                
                logger.info("🔐 Authenticating with McMaster-Carr API...")
                
                async with session.post(auth_url, json=auth_data, headers=headers) as response:
                    if response.status == 200:
                        auth_response = await response.json()
                        
                        self._auth_token = auth_response.get("access_token")
                        expires_in = auth_response.get("expires_in", 3600)  # Default 1 hour
                        
                        # Set token expiration
                        self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 minute buffer
                        
                        logger.info("✅ Successfully authenticated with McMaster-Carr API")
                        return self._auth_token
                    
                    elif response.status == 401:
                        error_text = await response.text()
                        raise SupplierAuthenticationError(f"Invalid credentials: {error_text}")
                    
                    else:
                        error_text = await response.text()
                        raise SupplierConnectionError(f"Authentication failed with status {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during authentication: {str(e)}")
        except Exception as e:
            raise SupplierAuthenticationError(f"Authentication failed: {str(e)}")
    
    async def _make_api_request(self, endpoint: str, credentials: Dict[str, str], params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated API request to McMaster-Carr"""
        
        try:
            # Get authentication token
            auth_token = await self._authenticate(credentials)
            
            # Setup SSL and session
            ssl_context = await self._setup_ssl_context(credentials)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout_seconds", 30))
            
            base_url = self._config.get("api_base_url", "https://www.mcmaster.com/api/v1")
            url = f"{base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
                "User-Agent": "MakerMatrix/1.0 (API Client)"
            }
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                logger.info(f"🌐 Making API request to: {endpoint}")
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    
                    elif response.status == 401:
                        # Token expired, clear it and retry once
                        self._auth_token = None
                        auth_token = await self._authenticate(credentials)
                        headers["Authorization"] = f"Bearer {auth_token}"
                        
                        async with session.get(url, headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                            else:
                                error_text = await retry_response.text()
                                raise SupplierAuthenticationError(f"API request failed after retry: {error_text}")
                    
                    elif response.status == 429:
                        raise SupplierRateLimitError("API rate limit exceeded")
                    
                    else:
                        error_text = await response.text()
                        raise SupplierConnectionError(f"API request failed with status {response.status}: {error_text}")
        
        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during API request: {str(e)}")
    
    async def authenticate(self) -> bool:
        """Authenticate with McMaster-Carr API using configured credentials"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for authentication")
                return False
            
            auth_token = await self._authenticate(credentials)
            return bool(auth_token)
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    async def test_connection(self, credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """Test connection to McMaster-Carr API"""
        try:
            # Test authentication
            auth_token = await self._authenticate(credentials)
            
            # Test a simple API endpoint
            response = await self._make_api_request("/health", credentials)
            
            return {
                "success": True,
                "message": "Successfully connected to McMaster-Carr API",
                "details": {
                    "authenticated": bool(auth_token),
                    "api_version": response.get("version", "unknown"),
                    "capabilities": [cap.value for cap in self.get_capabilities()]
                }
            }
            
        except SupplierAuthenticationError as e:
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}",
                "details": {"error_type": "authentication"}
            }
        except SupplierConfigurationError as e:
            return {
                "success": False,
                "message": f"Configuration error: {str(e)}",
                "details": {"error_type": "configuration"}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"error_type": "unknown"}
            }
    
    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using McMaster-Carr API"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for search")
                return []
            
            params = {
                "q": query,
                "limit": limit,
                "offset": 0
            }
            
            response = await self._make_api_request("/parts/search", credentials, params)
            
            results = []
            for part_data in response.get("parts", []):
                result = self._parse_part_data(part_data)
                if result:
                    results.append(result)
            
            logger.info(f"✅ Found {len(results)} parts for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed for query '{query}': {str(e)}")
            return []
    
    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed part information from McMaster-Carr API or scraping"""
        try:
            credentials = self._credentials or {}

            # If no credentials, try scraping fallback
            if not credentials:
                if self.supports_scraping():
                    logger.info(f"No credentials configured - using web scraping fallback for McMaster-Carr part: {supplier_part_number}")
                    return await self.scrape_part_details(supplier_part_number)
                else:
                    logger.error("No credentials configured for part details and scraping not supported")
                    return None

            # Try API first if credentials are available
            endpoint = f"/parts/{supplier_part_number}"
            response = await self._make_api_request(endpoint, credentials)

            result = self._parse_part_data(response)
            if result:
                logger.info(f"✅ Retrieved details for part: {supplier_part_number}")
                return result
            else:
                logger.warning(f"⚠️  No details found for part: {supplier_part_number}")
                return None

        except Exception as e:
            logger.error(f"❌ Failed to get details for part '{supplier_part_number}': {str(e)}")

            # If API fails and scraping is supported, try that as fallback
            if self.supports_scraping():
                logger.info(f"API failed, trying web scraping fallback for part: {supplier_part_number}")
                try:
                    return await self.scrape_part_details(supplier_part_number)
                except Exception as scrape_error:
                    logger.error(f"Scraping also failed: {str(scrape_error)}")
                    return None

            return None
    
    def _parse_part_data(self, part_data: Dict[str, Any]) -> Optional[PartSearchResult]:
        """Parse part data from McMaster-Carr API response"""
        try:
            part_number = part_data.get("partNumber")
            if not part_number:
                return None
            
            # Extract specifications
            specifications = {}
            specs_data = part_data.get("specifications", {})
            for spec_name, spec_value in specs_data.items():
                if spec_value:
                    specifications[spec_name] = spec_value
            
            # Extract pricing
            pricing_data = part_data.get("pricing", {})
            price_text = None
            if pricing_data:
                price_value = pricing_data.get("unitPrice")
                unit_quantity = pricing_data.get("unitQuantity", 1)
                currency = pricing_data.get("currency", "USD")
                
                if price_value:
                    if unit_quantity > 1:
                        price_text = f"{currency} {price_value} per {unit_quantity}"
                    else:
                        price_text = f"{currency} {price_value} each"
            
            # Extract image URL
            image_url = part_data.get("imageUrl")
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.mcmaster.com{image_url}"
            
            # Extract datasheet URL
            datasheet_url = part_data.get("datasheetUrl")
            if datasheet_url and not datasheet_url.startswith("http"):
                datasheet_url = f"https://www.mcmaster.com{datasheet_url}"
            
            return PartSearchResult(
                supplier_part_number=part_number,
                manufacturer="McMaster-Carr",
                manufacturer_part_number=part_number,
                description=part_data.get("description", f"McMaster-Carr Part {part_number}"),
                category=part_data.get("category", "Industrial Supply"),
                datasheet_url=datasheet_url,
                image_url=image_url,
                stock_quantity=part_data.get("stockQuantity"),
                pricing=price_text,
                specifications=specifications if specifications else None,
                additional_data={
                    "source": "mcmaster_api",
                    "api_version": part_data.get("apiVersion"),
                    "last_updated": part_data.get("lastUpdated"),
                    "unit_of_measure": part_data.get("unitOfMeasure"),
                    "minimum_order_quantity": part_data.get("minimumOrderQuantity"),
                    "lead_time_days": part_data.get("leadTimeDays")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse part data: {str(e)}")
            return None
    
    async def fetch_datasheet(self, supplier_part_number: str) -> Optional[str]:
        """Fetch datasheet URL for a part"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for datasheet fetch")
                return None
            
            endpoint = f"/parts/{supplier_part_number}/datasheet"
            response = await self._make_api_request(endpoint, credentials)
            
            datasheet_url = response.get("datasheetUrl")
            if datasheet_url:
                if not datasheet_url.startswith("http"):
                    datasheet_url = f"https://www.mcmaster.com{datasheet_url}"
                
                logger.info(f"✅ Found datasheet for part: {supplier_part_number}")
                return datasheet_url
            
            logger.warning(f"⚠️  No datasheet available for part: {supplier_part_number}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch datasheet for part '{supplier_part_number}': {str(e)}")
            return None
    
    async def fetch_image(self, supplier_part_number: str) -> Optional[str]:
        """Fetch image URL for a part"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for image fetch")
                return None

            endpoint = f"/parts/{supplier_part_number}/image"
            response = await self._make_api_request(endpoint, credentials)

            image_url = response.get("imageUrl")
            if image_url:
                if not image_url.startswith("http"):
                    image_url = f"https://www.mcmaster.com{image_url}"

                logger.info(f"✅ Found image for part: {supplier_part_number}")
                return image_url

            logger.warning(f"⚠️  No image available for part: {supplier_part_number}")
            return None

        except Exception as e:
            logger.error(f"❌ Failed to fetch image for part '{supplier_part_number}': {str(e)}")
            return None

    def map_to_standard_format(self, supplier_data: Any) -> Dict[str, Any]:
        """
        Map McMaster-Carr supplier data to standard format.

        This method flattens the PartSearchResult into simple key-value pairs for clean display.
        All specifications and additional_data are expanded into flat fields.

        Args:
            supplier_data: PartSearchResult from McMaster-Carr (scraping or API)

        Returns:
            Flat dictionary with all data as simple key-value pairs
        """
        if not isinstance(supplier_data, PartSearchResult):
            return {}

        # Start with core fields
        mapped = {
            'supplier_part_number': supplier_data.supplier_part_number,
            'part_name': supplier_data.description or supplier_data.supplier_part_number,
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

        # Define fields to skip for both specifications and additional_data
        skip_fields = {
            # Internal tracking fields
            'source', 'scraped_at', 'api_version', 'last_updated', 'warning',
            # Compliance and trade regulation fields
            'u_s_mexico_canada_agreement_usmca_qualifying',
            'delivery_info',
            'dfars_compliance',
            'export_control_classification_number_eccn',
            'reach_compliance',
            'schedule_b_number',  # Trade compliance field
            'url',  # Already have product_url in main fields
        }

        # Flatten specifications into custom fields (these become top-level additional_properties)
        if supplier_data.specifications:
            for spec_key, spec_value in supplier_data.specifications.items():
                # Skip fields in blacklist (case-insensitive)
                if spec_key.lower() in skip_fields:
                    continue
                # Create readable field names
                field_name = spec_key.replace('_', ' ').title()
                mapped[field_name] = str(spec_value) if spec_value is not None else ''

        # Flatten additional_data into custom fields
        if supplier_data.additional_data:
            for key, value in supplier_data.additional_data.items():
                # Skip fields in blacklist (case-insensitive)
                if key.lower() in skip_fields:
                    continue
                # Create readable field names
                field_name = key.replace('_', ' ').title()
                if value is not None:
                    mapped[field_name] = str(value)

        return mapped

    # ========== Web Scraping Fallback Methods ==========

    def supports_scraping(self) -> bool:
        """McMaster-Carr supports web scraping as a fallback."""
        return True

    def get_scraping_config(self) -> Dict[str, Any]:
        """Get McMaster-Carr specific scraping configuration."""
        return {
            'selectors': {
                # Use simple selectors that actually work based on our testing
                'spec_table': 'tbody tr',  # All table rows in tbody - most reliable
                'price': '[class*="price"], [class*="Price"]',  # Generic price selector
                # Don't scrape part_number from page - we already have it from the URL
                'heading': 'h1',  # Primary heading - generic product type
                'subtitle': 'h3',  # Secondary heading - specific details (size, material, etc.)
                'delivery': '[class*="Delivery"], [class*="delivery"]',
                'image': 'img[alt*="Product"], img[alt*="orientation"], img[class*="_img_"]',  # Product images
            },
            'requires_js': True,  # McMaster uses React, needs JS rendering
            'rate_limit_seconds': 2.0,  # Be respectful
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'wait_for_selector': 'tbody tr'  # Wait for table rows to load
        }

    async def scrape_part_details(self, url_or_part_number: str, force_refresh: bool = False) -> Optional[PartSearchResult]:
        """
        Scrape McMaster-Carr product page for part details.

        Args:
            url_or_part_number: Either a full McMaster URL or just the part number

        Returns:
            PartSearchResult with scraped data, or None if scraping fails
        """
        scraper_created = False
        try:
            # Initialize scraper if needed
            if not self._scraper:
                from .scrapers.web_scraper import WebScraper
                self._scraper = WebScraper()
                scraper_created = True

            # Build URL if only part number provided
            if not url_or_part_number.startswith('http'):
                url = f"https://www.mcmaster.com/{url_or_part_number}/"
                part_number = url_or_part_number
            else:
                url = url_or_part_number
                # Extract part number from URL (e.g., /91253A194/)
                match = re.search(r'/(\w+)/?$', url)
                part_number = match.group(1) if match else ""

            logger.info(f"🌐 Scraping McMaster-Carr page: {url}")

            # Get scraping configuration
            config = self.get_scraping_config()

            # Scrape the page (using Playwright for JS-rendered content)
            logger.info(f"Attempting to scrape McMaster-Carr URL: {url} (force_refresh={force_refresh})")
            scraped_data = await self._scraper.scrape_with_playwright(
                url,
                config['selectors'],
                wait_for_selector=config.get('wait_for_selector'),
                force_refresh=force_refresh
            )

            logger.info(f"Scraped data: {scraped_data}")
            if not scraped_data:
                logger.error("No data scraped from McMaster-Carr page - scraper returned empty dict")
                # Try to return minimal data just to test
                logger.info("Returning minimal test data for part")
                return PartSearchResult(
                    supplier_part_number=part_number,
                    manufacturer="McMaster-Carr",
                    manufacturer_part_number=part_number,
                    description=f"McMaster-Carr Part {part_number} (scraped data unavailable)",
                    category="Industrial Supply",
                    datasheet_url=None,
                    image_url=None,
                    stock_quantity=None,
                    pricing=None,
                    specifications={"note": "Scraping failed - returning minimal data"},
                    additional_data={
                        'source': 'web_scraping_minimal',
                        'scraped_at': datetime.now().isoformat(),
                        'url': url,
                        'warning': 'Scraping failed - only part number available'
                    }
                )

            # Parse the scraped data
            result = await self._parse_scraped_data(scraped_data, part_number, url)

            if result:
                logger.info(f"✅ Successfully scraped McMaster-Carr part: {part_number}")
            else:
                logger.warning(f"⚠️  Could not parse scraped data for: {part_number}")

            return result

        except Exception as e:
            logger.error(f"❌ Error scraping McMaster-Carr: {str(e)}")
            return None
        finally:
            # Clean up the scraper session if we created it
            if scraper_created and self._scraper:
                try:
                    await self._scraper.close()
                    self._scraper = None
                except Exception as e:
                    logger.debug(f"Error closing scraper: {e}")

    async def _parse_scraped_data(self, scraped_data: Dict[str, Any], part_number: str, url: str) -> Optional[PartSearchResult]:
        """Parse scraped data into PartSearchResult format."""
        try:
            # Extract specifications from table
            specifications = {}
            if 'spec_table' in scraped_data:
                spec_data = scraped_data['spec_table']

                # The scraper should return a dict, but just use whatever we get
                if isinstance(spec_data, dict):
                    specifications = spec_data
                else:
                    # If it's not a dict (shouldn't happen with current scraper), log it
                    logger.warning(f"spec_table is not a dict, it's a {type(spec_data)}: {spec_data[:100] if isinstance(spec_data, str) else spec_data}")

            # Parse price information
            pricing = []
            if 'price' in scraped_data:
                price_info = self._scraper.parse_price(scraped_data['price']) if self._scraper else None
                if price_info:
                    pricing = [{
                        'quantity': price_info.get('quantity', 1),
                        'price': price_info.get('unit_price', price_info.get('price', 0)),
                        'currency': price_info.get('currency', 'USD'),
                        'original_text': scraped_data['price']
                    }]

            # Build complete description from H1 (generic) and H3 (specific details)
            description_parts = []
            heading = scraped_data.get('heading', '')  # H1 - generic product type
            subtitle = scraped_data.get('subtitle', '')  # H3 - specific details

            # Combine H1 and H3 for a complete, unique description
            if heading:
                description_parts.append(heading.strip())
            if subtitle:
                description_parts.append(subtitle.strip())

            # If we have both, join with a separator for clarity
            if len(description_parts) == 2:
                description = f"{description_parts[0]} - {description_parts[1]}"
            elif description_parts:
                description = description_parts[0]
            else:
                description = f"McMaster-Carr Part {part_number}"

            # Extract key specifications
            material = specifications.get('material', '')
            thread_size = specifications.get('thread_size', '')

            # Create category from specifications
            category_parts = []
            if 'fastener_head_type' in specifications:
                category_parts.append(specifications['fastener_head_type'])
            if 'drive_style' in specifications:
                category_parts.append(specifications['drive_style'] + " Drive")
            if material:
                category_parts.append(material)

            category = " ".join(category_parts) if category_parts else "Industrial Supply"

            # Extract image URL if available
            image_url = scraped_data.get('image')
            if image_url:
                # Convert relative URLs to absolute URLs
                if not image_url.startswith("http"):
                    image_url = f"https://www.mcmaster.com{image_url}"
                logger.info(f"Scraped image URL: {image_url}")

            return PartSearchResult(
                supplier_part_number=part_number,  # The actual McMaster part number like 92210A203
                manufacturer="McMaster-Carr",
                manufacturer_part_number=part_number,  # Same as supplier part number
                description=description,  # The product description like "18-8 Stainless Steel..."
                category=category,
                datasheet_url=None,  # McMaster doesn't typically provide datasheets
                image_url=image_url,  # Now extracted from scraping
                stock_quantity=None,  # Stock info not easily scraped
                pricing=pricing if pricing else None,
                specifications=specifications,
                additional_data={
                    'source': 'web_scraping',
                    'scraped_at': datetime.now().isoformat(),
                    'url': url,
                    'delivery_info': scraped_data.get('delivery', ''),
                    'material': material,
                    'thread_size': thread_size,
                    'warning': 'Data obtained via web scraping - may be incomplete or outdated'
                }
            )

        except Exception as e:
            logger.error(f"Error parsing scraped McMaster-Carr data: {str(e)}")
            return None
    

# Register the supplier
from .registry import SupplierRegistry
SupplierRegistry.register("mcmaster-carr", McMasterCarrSupplier)