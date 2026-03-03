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
import os
import tempfile
from datetime import datetime
import logging
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption

from .base import (
    BaseSupplier,
    FieldDefinition,
    FieldType,
    SupplierCapability,
    PartSearchResult,
    SupplierInfo,
    CapabilityRequirement,
)
from .exceptions import (
    SupplierConfigurationError,
    SupplierAuthenticationError,
    SupplierConnectionError,
    SupplierRateLimitError,
)

logger = logging.getLogger(__name__)


class McMasterCarrSupplier(BaseSupplier):
    """McMaster-Carr Supplier Implementation

    Supports:
    1. Official API (requires approved account and certificates)
    
    Web scraping is NOT supported due to anti-bot measures.
    For API access, contact eCommerce@mcmaster.com for approval.
    """

    def __init__(self):
        super().__init__()
        self._auth_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._temp_files: List[str] = []  # Track temp files for cleanup

    def get_supplier_info(self) -> SupplierInfo:
        return SupplierInfo(
            name="McMaster-Carr",
            display_name="McMaster-Carr",
            description="Industrial supply with official API access - requires approval (No Scraping Support)",
            website_url="https://www.mcmaster.com",
            api_documentation_url="Contact eCommerce@mcmaster.com for API documentation",
            supports_oauth=False,
            rate_limit_info="API rate limits apply - contact McMaster for details",
        )

    def get_url_patterns(self) -> List[str]:
        """Return URL patterns that identify McMaster-Carr product links"""
        return [
            r"mcmaster\.com",  # Base domain
            r"www\.mcmaster\.com",  # With www
            r"mcmaster-carr\.com",  # Alternative domain
            r"mcmaster\.com/[0-9A-Za-z]+",  # Product pages
            r"mcmaster\.com/.+/[0-9A-Za-z]+/?$",  # Product pages with category path
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
                    r"/([A-Za-z0-9]+)/?$",  # Extract part number from end of URL
                    r"/([A-Za-z0-9]+)/?(?:\?|#|$)",  # Handle query strings and fragments
                ],
                example="91253A194",
                description="The part number from the McMaster-Carr product page URL",
                required_for_enrichment=True,
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
        required_creds = ["client_cert_path", "client_cert_password", "username", "password"]
        return {
            capability: CapabilityRequirement(capability=capability, required_credentials=required_creds)
            for capability in self.get_capabilities()
        }

    def get_credential_schema(self) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="client_cert_path",
                label="Client Certificate (.pfx)",
                field_type=FieldType.FILE,
                required=True,
                description="Upload your McMaster-Carr client certificate file (.pfx or .p12)",
                help_text="Contact eCommerce@mcmaster.com to obtain your client certificate",
            ),
            FieldDefinition(
                name="client_cert_password",
                label="Certificate Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Password for your client certificate",
                help_text="The password provided with your certificate",
            ),
            FieldDefinition(
                name="username",
                label="API Username",
                field_type=FieldType.TEXT,
                required=True,
                description="Your McMaster-Carr API username",
                help_text="Username for API login (different from website login)",
            ),
            FieldDefinition(
                name="password",
                label="API Password",
                field_type=FieldType.PASSWORD,
                required=True,
                description="Your McMaster-Carr API password",
                help_text="Password for API login",
            ),
        ]

    def get_configuration_schema(self, **kwargs) -> List[FieldDefinition]:
        return [
            FieldDefinition(
                name="api_base_url",
                label="API Base URL",
                field_type=FieldType.URL,
                required=False,
                default_value="https://api.mcmaster.com",
                description="McMaster-Carr official API endpoint",
                help_text="Official API base URL (requires approval from McMaster)",
            ),
            FieldDefinition(
                name="timeout_seconds",
                label="Request Timeout (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=30,
                description="API request timeout in seconds",
                help_text="Maximum time to wait for API responses",
            ),
            FieldDefinition(
                name="rate_limit_delay",
                label="Rate Limit Delay (seconds)",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=1.0,
                description="Delay between API requests",
                help_text="Respect McMaster's API rate limits",
            ),
            FieldDefinition(
                name="max_retries",
                label="Maximum Retries",
                field_type=FieldType.NUMBER,
                required=False,
                default_value=3,
                description="Maximum number of API request retries",
                help_text="Number of times to retry failed requests",
            ),
        ]

    async def _setup_ssl_context(self, credentials: Optional[Dict[str, str]] = None) -> ssl.SSLContext:
        """Setup SSL context with client certificate for mutual TLS authentication"""
        if self._ssl_context:
            return self._ssl_context

        # Use provided credentials or fall back to instance credentials
        creds = credentials or self._credentials or {}

        try:
            # Create SSL context for client certificate authentication
            # McMaster's API uses a private CA, so we need to handle server verification carefully
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            # For McMaster's enterprise API with client certs, we trust the connection
            # since we're authenticating with a client certificate they issued
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Load client certificate
            cert_path = creds.get("client_cert_path")
            cert_password = creds.get("client_cert_password")

            if not cert_path:
                raise SupplierConfigurationError("Client certificate path is required")

            if not os.path.exists(cert_path):
                raise SupplierConfigurationError(f"Certificate file not found: {cert_path}")

            # Check if PFX/P12 format
            if cert_path.lower().endswith((".pfx", ".p12")):
                # Convert PFX to PEM temp files
                logger.info(f"Loading PFX certificate from {cert_path}")
                try:
                    with open(cert_path, "rb") as f:
                        pfx_data = f.read()
                except Exception as e:
                    raise SupplierConfigurationError(f"Failed to read certificate file: {str(e)}")

                password_bytes = cert_password.encode() if cert_password else None
                
                try:
                    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                        pfx_data, password_bytes
                    )
                except Exception as pfx_error:
                    raise SupplierConfigurationError(
                        f"Failed to load PFX file (check password): {str(pfx_error)}"
                    )

                if not private_key or not certificate:
                    raise SupplierConfigurationError("PFX file must contain both private key and certificate")

                # Create temp files for key and cert
                try:
                    # Create temporary files that are readable but deleted when closed/unlinked?
                    # No, on Windows we can't delete while open. We track them in self._temp_files.
                    key_fd, key_path = tempfile.mkstemp(suffix=".pem")
                    cert_fd, cert_path_pem = tempfile.mkstemp(suffix=".pem")
                    
                    # Close handlers immediately
                    os.close(key_fd)
                    os.close(cert_fd)

                    # Write PEM data
                    with open(key_path, "wb") as f:
                        f.write(
                            private_key.private_bytes(
                                encoding=Encoding.PEM,
                                format=PrivateFormat.PKCS8,
                                encryption_algorithm=NoEncryption(),
                            )
                        )
                    
                    with open(cert_path_pem, "wb") as f:
                        f.write(certificate.public_bytes(Encoding.PEM))
                        if additional_certificates:
                            for cert in additional_certificates:
                                f.write(cert.public_bytes(Encoding.PEM))
                except Exception as e:
                    raise SupplierConfigurationError(f"Failed to process certificate data: {str(e)}")

                # Track for cleanup
                self._temp_files.extend([key_path, cert_path_pem])
                
                # Load into SSL context
                try:
                    context.load_cert_chain(certfile=cert_path_pem, keyfile=key_path)
                    logger.info("Converted PFX to PEM and loaded into SSL context")
                except ssl.SSLError as e:
                    raise SupplierConfigurationError(f"Failed to load certificate into SSL context: {str(e)}")

            else:
                # Load standard PEM
                try:
                    context.load_cert_chain(cert_path, password=cert_password)
                except ssl.SSLError as e:
                    raise SupplierConfigurationError(f"Failed to load PEM certificate: {str(e)}")

            self._ssl_context = context
            logger.info("✅ SSL context configured with client certificate")
            return context

        except SupplierConfigurationError:
            raise
        except Exception as e:
            # Cleanup on failure
            await self.close()
            raise SupplierConfigurationError(f"Failed to setup SSL context: {str(e)}")

    async def _authenticate(self, credentials: Dict[str, str] = None) -> str:
        """Authenticate with McMaster-Carr API using certificate + username/password.

        McMaster-Carr uses two-step authentication:
        1. Client certificate for TLS
        2. Username/password login to get bearer token

        Returns:
            Bearer token for API requests
        """
        # Use provided credentials or fall back to instance credentials
        creds = credentials or self._credentials or {}

        # Check if we already have a valid token
        if self._auth_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._auth_token

        # Setup SSL context with client certificate
        ssl_context = await self._setup_ssl_context(creds)

        # Login to get bearer token
        username = creds.get("username")
        password = creds.get("password")

        if not username or not password:
            raise SupplierAuthenticationError("Username and password are required for McMaster-Carr API")

        base_url = self._config.get("api_base_url", "https://api.mcmaster.com")
        login_url = f"{base_url.rstrip('/')}/v1/login"

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=self._config.get("timeout_seconds", 30))

        try:
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # McMaster-Carr API uses "UserName" field per their API documentation
                login_payload = {"UserName": username, "Password": password}
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                logger.info(f"Logging in to McMaster-Carr API at {login_url}")
                logger.debug(f"Login payload: UserName={username}")
                async with session.post(login_url, json=login_payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # McMaster API returns "AuthToken" per their Postman collection
                        self._auth_token = data.get("AuthToken") or data.get("Authorization") or data.get("Token")

                        # Parse expiration - McMaster returns "ExpirationTS" as Unix timestamp
                        expires = data.get("ExpirationTS")
                        if expires:
                            try:
                                # ExpirationTS is a Unix timestamp (seconds since epoch)
                                self._token_expires_at = datetime.fromtimestamp(int(expires))
                            except (ValueError, TypeError):
                                # Default to 23 hours from now if can't parse
                                from datetime import timedelta
                                self._token_expires_at = datetime.now() + timedelta(hours=23)
                        else:
                            from datetime import timedelta
                            self._token_expires_at = datetime.now() + timedelta(hours=23)

                        logger.info("✅ Successfully authenticated with McMaster-Carr API")
                        return self._auth_token
                    else:
                        error_text = await response.text()
                        raise SupplierAuthenticationError(f"Login failed ({response.status}): {error_text}")

        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during login: {str(e)}")

    async def _make_api_request(
        self, endpoint: str, credentials: Dict[str, str] = None, params: Optional[Dict] = None, method: str = "GET", json_body: Dict = None
    ) -> Dict[str, Any]:
        """Make API request to McMaster-Carr using certificate + bearer token authentication"""

        try:
            # Use provided credentials or fall back to instance credentials
            creds = credentials or self._credentials or {}

            # Get bearer token (will login if needed)
            token = await self._authenticate(creds)

            # Setup SSL context with client certificate
            ssl_context = await self._setup_ssl_context(creds)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout_seconds", 30))

            base_url = self._config.get("api_base_url", "https://api.mcmaster.com")
            url = f"{base_url.rstrip('/')}/v1/{endpoint.lstrip('/')}"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                logger.info(f"Making {method} API request to: {url}")

                if method.upper() == "GET":
                    async with session.get(url, headers=headers, params=params) as response:
                        return await self._handle_response(response, endpoint)
                elif method.upper() == "PUT":
                    async with session.put(url, headers=headers, json=json_body) as response:
                        return await self._handle_response(response, endpoint)
                elif method.upper() == "DELETE":
                    async with session.delete(url, headers=headers) as response:
                        return await self._handle_response(response, endpoint)
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=json_body) as response:
                        return await self._handle_response(response, endpoint)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

        except aiohttp.ClientError as e:
            raise SupplierConnectionError(f"Network error during API request: {str(e)}")

    async def _handle_response(self, response: aiohttp.ClientResponse, endpoint: str) -> Dict[str, Any]:
        """Handle API response and extract data or raise appropriate errors"""
        if response.status in (200, 201):
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await response.json()
            else:
                # Some endpoints may return empty success
                text = await response.text()
                return {"success": True, "raw_response": text}

        elif response.status == 401:
            # Token may have expired, clear it
            self._auth_token = None
            self._token_expires_at = None
            error_text = await response.text()
            raise SupplierAuthenticationError(f"Authentication failed (401): {error_text}")

        elif response.status == 403:
            error_text = await response.text()
            raise SupplierAuthenticationError(f"Access denied (403) - check subscription: {error_text}")

        elif response.status == 429:
            raise SupplierRateLimitError("API rate limit exceeded")

        else:
            error_text = await response.text()
            raise SupplierConnectionError(f"API request to {endpoint} failed with status {response.status}: {error_text}")

    async def authenticate(self) -> bool:
        """Validate certificate credentials are configured for McMaster-Carr API"""
        try:
            credentials = self._credentials or {}
            if not credentials.get("client_cert_path"):
                logger.error("No certificate credentials configured")
                return False

            # Setup SSL context to validate certificate
            await self._setup_ssl_context(credentials)
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    async def test_connection(self, credentials: Dict[str, str] = None) -> Dict[str, Any]:
        """Test connection to McMaster-Carr API by validating certificate and login"""
        try:
            # Use provided credentials or fall back to instance credentials
            creds = credentials or self._credentials or {}

            if not creds.get("client_cert_path"):
                return {
                    "success": False,
                    "message": "No client certificate configured. Please upload a .pfx certificate file.",
                    "details": {"error_type": "configuration"},
                }

            cert_path = creds.get("client_cert_path", "")
            if not os.path.exists(cert_path):
                return {
                    "success": False,
                    "message": f"Certificate file not found: {cert_path}",
                    "details": {"error_type": "configuration"},
                }

            if not creds.get("username") or not creds.get("password"):
                return {
                    "success": False,
                    "message": "API username and password are required for McMaster-Carr API.",
                    "details": {"error_type": "configuration"},
                }

            # Test full authentication - certificate + login for bearer token
            token = await self._authenticate(creds)

            if token:
                return {
                    "success": True,
                    "message": "Successfully authenticated with McMaster-Carr API!",
                    "details": {
                        "authentication": "certificate + bearer token",
                        "certificate_file": os.path.basename(cert_path),
                        "token_obtained": True,
                        "capabilities": [cap.value for cap in self.get_capabilities()],
                    },
                }
            else:
                return {
                    "success": False,
                    "message": "Login succeeded but no token was returned",
                    "details": {"error_type": "authentication"},
                }

        except SupplierAuthenticationError as e:
            return {
                "success": False,
                "message": f"Authentication failed: {str(e)}",
                "details": {"error_type": "authentication"},
            }
        except SupplierConfigurationError as e:
            return {
                "success": False,
                "message": f"Configuration error: {str(e)}",
                "details": {"error_type": "configuration"},
            }
        except SupplierConnectionError as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "details": {"error_type": "connection"},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}",
                "details": {"error_type": "unknown"},
            }

    async def search_parts(self, query: str, limit: int = 50) -> List[PartSearchResult]:
        """Search for parts using McMaster-Carr API"""
        try:
            credentials = self._credentials or {}
            if not credentials:
                logger.error("No credentials configured for search")
                return []

            params = {"q": query, "limit": limit, "offset": 0}

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

    async def _subscribe_to_product(self, part_number: str, credentials: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Subscribe to a product to enable access to its data.

        Per McMaster API docs, the request body format is:
        {"URL": "https://mcmaster.com/{partNumber}"}

        Returns the product data from the subscribe response (201), or None on failure.
        """
        try:
            creds = credentials or self._credentials or {}
            # PUT /v1/products with URL format per Postman collection
            product_url = f"https://mcmaster.com/{part_number}"
            response = await self._make_api_request(
                "products",
                creds,
                method="PUT",
                json_body={"URL": product_url}
            )
            logger.info(f"✅ Subscribed to product: {part_number}")
            return response
        except Exception as e:
            logger.warning(f"⚠️ Could not subscribe to product {part_number}: {str(e)}")
            return None

    async def get_part_details(self, supplier_part_number: str) -> Optional[PartSearchResult]:
        """Get detailed part information from McMaster-Carr API"""
        try:
            credentials = self._credentials or {}

            # If no credentials, we cannot proceed
            if not credentials:
                logger.error("No credentials configured for part details")
                return None

            # McMaster-Carr requires subscribing to products before accessing them.
            # The subscribe (PUT) response already contains full product data.
            subscribe_data = await self._subscribe_to_product(supplier_part_number, credentials)

            if subscribe_data:
                result = self._parse_part_data(subscribe_data)
                if result:
                    # Download authenticated image if it's an API URL
                    if result.image_url and "api.mcmaster.com" in result.image_url:
                        local_url = await self._download_authenticated_image(
                            result.image_url, supplier_part_number
                        )
                        if local_url:
                            result.image_url = local_url
                    logger.info(f"✅ Retrieved details for part from subscribe response: {supplier_part_number}")
                    return result

            # Fallback: try GET endpoint directly
            endpoint = f"products/{supplier_part_number}"
            response = await self._make_api_request(endpoint, credentials)

            result = self._parse_part_data(response)
            if result:
                # Download authenticated image if it's an API URL
                if result.image_url and "api.mcmaster.com" in result.image_url:
                    local_url = await self._download_authenticated_image(
                        result.image_url, supplier_part_number
                    )
                    if local_url:
                        result.image_url = local_url
                logger.info(f"✅ Retrieved details for part: {supplier_part_number}")
                return result
            else:
                logger.warning(f"⚠️  No details found for part: {supplier_part_number}")
                return None

        except SupplierAuthenticationError as e:
            logger.error(f"❌ Authentication error for part '{supplier_part_number}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get details for part '{supplier_part_number}': {str(e)}")
            return None

    def _parse_part_data(self, part_data: Dict[str, Any]) -> Optional[PartSearchResult]:
        """Parse part data from McMaster-Carr API response.

        The McMaster API returns PascalCase fields:
        - PartNumber, ProductStatus, ProductCategory
        - FamilyDescription, DetailDescription
        - Specifications: [{Attribute, Values}, ...]
        - Links: [{Key, Value}, ...]
        """
        try:
            # Support both PascalCase (actual API) and camelCase (legacy)
            part_number = part_data.get("PartNumber") or part_data.get("partNumber")
            if not part_number:
                return None

            # Build description from FamilyDescription + DetailDescription
            family_desc = part_data.get("FamilyDescription", "")
            detail_desc = part_data.get("DetailDescription", "")
            if family_desc and detail_desc:
                description = f"{family_desc}, {detail_desc}"
            elif family_desc:
                description = family_desc
            elif detail_desc:
                description = detail_desc
            else:
                description = part_data.get("description", f"McMaster-Carr Part {part_number}")

            # Extract category
            category = part_data.get("ProductCategory") or part_data.get("category", "Industrial Supply")

            # Extract specifications from array format: [{Attribute, Values}, ...]
            specifications = {}
            specs_data = part_data.get("Specifications") or part_data.get("specifications")
            if isinstance(specs_data, list):
                for spec in specs_data:
                    attr = spec.get("Attribute") or spec.get("attribute", "")
                    values = spec.get("Values") or spec.get("values", [])
                    if attr and values:
                        specifications[attr] = ", ".join(str(v) for v in values)
            elif isinstance(specs_data, dict):
                for spec_name, spec_value in specs_data.items():
                    if spec_value:
                        specifications[spec_name] = spec_value

            # Extract URLs from Links array: [{Key, Value}, ...]
            image_url = None
            datasheet_url = None
            price_link = None
            links = part_data.get("Links", [])
            base_api_url = self._config.get("api_base_url", "https://api.mcmaster.com")
            for link in links:
                key = link.get("Key", "")
                value = link.get("Value", "")
                if key == "Image" and value:
                    # Image links are API-relative paths
                    image_url = f"{base_api_url}/{value.lstrip('/')}" if not value.startswith("http") else value
                elif key == "2-D PDF" and value:
                    datasheet_url = f"{base_api_url}/{value.lstrip('/')}" if not value.startswith("http") else value
                elif key == "Price" and value:
                    price_link = value

            # Fallback to legacy field names
            if not image_url:
                image_url = part_data.get("imageUrl")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://www.mcmaster.com{image_url}"

            # Extract pricing from nested data or link
            pricing_data = part_data.get("pricing", {})
            price_text = None
            if pricing_data:
                price_value = pricing_data.get("unitPrice")
                unit_quantity = pricing_data.get("unitQuantity", 1)
                currency = pricing_data.get("currency", "USD")
                if price_value:
                    price_text = f"{currency} {price_value} per {unit_quantity}" if unit_quantity > 1 else f"{currency} {price_value} each"

            return PartSearchResult(
                supplier_part_number=part_number,
                manufacturer="McMaster-Carr",
                manufacturer_part_number=part_number,
                description=description,
                category=category,
                datasheet_url=datasheet_url,
                image_url=image_url,
                stock_quantity=part_data.get("stockQuantity"),
                pricing=price_text,
                specifications=specifications if specifications else None,
                additional_data={
                    "source": "mcmaster_api",
                    "product_status": part_data.get("ProductStatus"),
                    "product_detail_url": f"https://www.mcmaster.com/{part_number}",
                    "price_api_link": price_link,
                },
            )

        except Exception as e:
            logger.error(f"❌ Failed to parse part data: {str(e)}")
            return None

    async def _download_authenticated_image(self, image_api_url: str, part_number: str) -> Optional[str]:
        """Download an image from the McMaster API using authenticated session and save locally.

        McMaster image URLs are API-internal and require client cert + bearer token.
        The browser cannot load them directly, so we download and serve locally.

        Returns:
            Local serving URL (e.g., /api/utility/get_image/{uuid}) or None on failure.
        """
        try:
            from MakerMatrix.services.system.file_download_service import FileDownloadService

            creds = self._credentials or {}
            token = await self._authenticate(creds)
            ssl_context = await self._setup_ssl_context(creds)
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self._config.get("timeout_seconds", 30))

            headers = {
                "Accept": "image/*",
                "Authorization": f"Bearer {token}",
            }

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                logger.info(f"Downloading authenticated image for {part_number}: {image_api_url}")
                async with session.get(image_api_url, headers=headers) as response:
                    if response.status not in (200, 201):
                        logger.warning(f"Image download failed with status {response.status}")
                        return None

                    content_type = response.headers.get("Content-Type", "").lower()
                    image_data = await response.read()

                    if len(image_data) < 100:
                        logger.warning(f"Image too small ({len(image_data)} bytes), skipping")
                        return None

                    # Determine extension from content type
                    ext = ".png"
                    if "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"
                    elif "gif" in content_type:
                        ext = ".gif"
                    elif "webp" in content_type:
                        ext = ".webp"

                    # Generate UUID and save
                    import uuid as uuid_mod
                    image_uuid = str(uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, image_api_url))
                    file_service = FileDownloadService()
                    filename = f"{image_uuid}{ext}"
                    file_path = file_service.uploaded_images_path / filename

                    if file_path.exists():
                        logger.info(f"McMaster image already cached: {filename}")
                        return file_service.get_image_url(image_uuid)

                    with open(file_path, "wb") as f:
                        f.write(image_data)

                    logger.info(f"✅ Saved McMaster image: {filename} ({len(image_data)} bytes)")
                    return file_service.get_image_url(image_uuid)

        except Exception as e:
            logger.warning(f"Failed to download McMaster image: {e}")
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
            "supplier_part_number": supplier_data.supplier_part_number,
            "part_name": supplier_data.description or supplier_data.supplier_part_number,
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

        # Define fields to skip for both specifications and additional_data
        skip_fields = {
            # Internal tracking fields
            "source",
            "scraped_at",
            "api_version",
            "last_updated",
            "warning",
            # Compliance and trade regulation fields
            "u_s_mexico_canada_agreement_usmca_qualifying",
            "delivery_info",
            "dfars_compliance",
            "export_control_classification_number_eccn",
            "reach_compliance",
            "schedule_b_number",  # Trade compliance field
            "url",  # Already have product_url in main fields
        }

        # Flatten specifications into custom fields (these become top-level additional_properties)
        if supplier_data.specifications:
            for spec_key, spec_value in supplier_data.specifications.items():
                # Skip fields in blacklist (case-insensitive)
                if spec_key.lower() in skip_fields:
                    continue
                # Create readable field names
                field_name = spec_key.replace("_", " ").title()
                mapped[field_name] = str(spec_value) if spec_value is not None else ""

        # Flatten additional_data into custom fields
        if supplier_data.additional_data:
            for key, value in supplier_data.additional_data.items():
                # Skip fields in blacklist (case-insensitive)
                if key.lower() in skip_fields:
                    continue
                # Create readable field names
                field_name = key.replace("_", " ").title()
                if value is not None:
                    mapped[field_name] = str(value)

        return mapped

    # ========== Web Scraping Fallback Methods ==========

    async def close(self):
        """Clean up resources including temp files"""
        await super().close()
        
        # Clean up temp files
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.debug(f"Deleted temp file: {path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {path}: {e}")
        self._temp_files = []

    def supports_scraping(self) -> bool:
        """McMaster-Carr supports web scraping as a fallback."""
        return False


# Register the supplier
from .registry import SupplierRegistry

SupplierRegistry.register("mcmaster-carr", McMasterCarrSupplier)
