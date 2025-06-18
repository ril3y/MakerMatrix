"""
DigiKey API Client

Implements DigiKey's Product Information V4 API with OAuth2 Client Credentials flow.
Provides part search, datasheet fetching, and product information retrieval.
"""

import asyncio
import aiohttp
import base64
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from ..base_client import BaseAPIClient, APIResponse, APIError
from ..exceptions import AuthenticationError, RateLimitError, APIClientError
from .base_supplier_client import BaseSupplierClient
from MakerMatrix.schemas.enrichment_schemas import (
    DatasheetEnrichmentResponse,
    ImageEnrichmentResponse,
    PricingEnrichmentResponse,
    DetailsEnrichmentResponse,
    EnrichmentSource,
    ImageInfo,
    SpecificationAttribute,
    PriceBreak
)

logger = logging.getLogger(__name__)


class DigiKeyClient(BaseAPIClient, BaseSupplierClient):
    """
    DigiKey API client using OAuth2 Client Credentials flow
    
    Supports:
    - Part search and information
    - Datasheet URL retrieval  
    - Product images
    - Pricing and availability
    - Technical specifications
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://api.digikey.com",
        api_version: str = "v4",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_per_minute: int = 1000,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize DigiKey API client
        
        Args:
            client_id: DigiKey Client ID
            client_secret: DigiKey Client Secret  
            base_url: API base URL
            api_version: API version
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit_per_minute: Rate limit per minute
            custom_headers: Additional headers
        """
        # Initialize both parent classes
        BaseAPIClient.__init__(self, base_url, timeout, max_retries)
        BaseSupplierClient.__init__(self, supplier_name="DigiKey")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_version = api_version
        self.rate_limit_per_minute = rate_limit_per_minute
        self.custom_headers = custom_headers or {}
        
        # OAuth token management
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.token_type: str = "Bearer"
        
        # API endpoints
        # DigiKey uses sandbox vs production URLs
        if "sandbox" in base_url.lower():
            self.auth_url = f"{base_url}/v1/oauth2/token"
        else:
            # Production endpoint - note this might require whitelisted redirect URIs
            self.auth_url = f"{base_url}/v1/oauth2/token"
        
        self.api_base = f"{base_url}/{api_version}"
        
        self.logger = logging.getLogger(f"{__name__}.DigiKeyClient")
        
        # Rate limiting
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window = 60  # 1 minute
        
        self.logger.info(f"DigiKey API client initialized (API v{api_version})")
    
    async def authenticate(self) -> bool:
        """
        Authenticate using OAuth2 Client Credentials flow
        
        Returns:
            True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            self.logger.info(f"Authenticating with DigiKey API using Client Credentials flow at {self.auth_url}")
            
            # Prepare authentication request
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            self.logger.debug(f"Auth request headers: {headers}")
            self.logger.debug(f"Auth request data: grant_type={auth_data['grant_type']}, client_id={self.client_id[:8]}...")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    self.auth_url,
                    data=auth_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        auth_response = await response.json()
                        
                        self.access_token = auth_response.get("access_token")
                        self.token_type = auth_response.get("token_type", "Bearer")
                        expires_in = auth_response.get("expires_in", 3600)  # Default 1 hour
                        
                        # Calculate expiration time with buffer
                        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
                        
                        self.logger.info(f"DigiKey authentication successful, token expires at {self.token_expires_at}")
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"DigiKey authentication failed: {response.status} - {error_text}")
                        raise AuthenticationError(f"DigiKey authentication failed: {response.status}")
                        
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error during DigiKey authentication: {e}")
            raise AuthenticationError(f"Network error during authentication: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during DigiKey authentication: {e}")
            raise AuthenticationError(f"Authentication error: {str(e)}")
    
    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token"""
        if not self.access_token or not self.token_expires_at:
            await self.authenticate()
        elif datetime.utcnow() >= self.token_expires_at:
            self.logger.info("Access token expired, refreshing...")
            await self.authenticate()
    
    async def get_authentication_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests
        
        Returns:
            Dictionary of headers including Authorization
        """
        await self._ensure_authenticated()
        
        headers = {
            "Authorization": f"{self.token_type} {self.access_token}",
            "X-DIGIKEY-Client-Id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add custom headers
        headers.update(self.custom_headers)
        
        return headers
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting"""
        current_time = datetime.utcnow().timestamp()
        
        # Reset counter if window has passed
        if current_time - self._last_request_time > self._rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time
        
        # Check rate limit
        if self._request_count >= self.rate_limit_per_minute:
            wait_time = self._rate_limit_window - (current_time - self._last_request_time)
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._last_request_time = datetime.utcnow().timestamp()
        
        self._request_count += 1
    
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """
        Make authenticated API request to DigiKey
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: Request body data
            params: URL parameters
            
        Returns:
            APIResponse object
            
        Raises:
            APIClientError: For various API errors
        """
        await self._enforce_rate_limit()
        
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = await self.get_authentication_headers()
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"DigiKey API request: {method} {url} (attempt {attempt + 1})")
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.request(
                        method=method,
                        url=url,
                        json=data if data else None,
                        params=params,
                        headers=headers
                    ) as response:
                        response_text = await response.text()
                        
                        # Handle successful responses
                        if 200 <= response.status < 300:
                            try:
                                response_data = json.loads(response_text) if response_text else {}
                            except json.JSONDecodeError:
                                response_data = {"raw_response": response_text}
                            
                            return APIResponse(
                                success=True,
                                status_code=response.status,
                                data=response_data,
                                headers=dict(response.headers),
                                raw_response=response_text
                            )
                        
                        # Handle authentication errors
                        elif response.status == 401:
                            self.logger.warning("DigiKey authentication failed, retrying...")
                            self.access_token = None
                            await self.authenticate()
                            headers = await self.get_authentication_headers()
                            continue
                        
                        # Handle rate limiting
                        elif response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', 60))
                            if attempt < self.max_retries:
                                self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                raise RateLimitError(f"Rate limit exceeded: {response_text}")
                        
                        # Handle other errors
                        else:
                            error_message = f"DigiKey API error {response.status}: {response_text}"
                            if attempt < self.max_retries and response.status >= 500:
                                self.logger.warning(f"{error_message}, retrying...")
                                await asyncio.sleep(2 ** attempt)
                                continue
                            else:
                                raise APIClientError(error_message)
                                
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    self.logger.warning(f"Network error on attempt {attempt + 1}: {e}, retrying...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise APIClientError(f"Network error: {str(e)}")
        
        raise APIClientError("Max retries exceeded")
    
    async def test_connection(self) -> bool:
        """
        Test DigiKey API connection
        
        Returns:
            True if connection successful
        """
        try:
            # Test authentication first
            await self.authenticate()
            
            # Make a simple API call to verify access
            response = await self.request("GET", "Search/v4/productcount", params={"keywords": "resistor"})
            
            if response.success:
                self.logger.info("DigiKey API connection test successful")
                return True
            else:
                self.logger.error(f"DigiKey API connection test failed: {response.data}")
                return False
                
        except Exception as e:
            self.logger.error(f"DigiKey API connection test failed: {e}")
            return False
    
    async def search_parts(
        self,
        keywords: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Search for parts by keywords
        
        Args:
            keywords: Search keywords
            limit: Maximum results to return
            offset: Result offset for pagination
            filters: Additional search filters
            
        Returns:
            APIResponse with search results
        """
        search_data = {
            "Keywords": keywords,
            "RecordCount": limit,
            "RecordStartPosition": offset,
            "Sort": {
                "SortOption": "SortByQuantityAvailable",
                "Direction": "Descending"
            }
        }
        
        if filters:
            search_data.update(filters)
        
        return await self.request("POST", "Search/v4/Product", data=search_data)
    
    async def get_part_details(self, part_number: str) -> APIResponse:
        """
        Get detailed information for a specific part
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            APIResponse with part details
        """
        return await self.request("GET", f"Search/v4/Product/{part_number}")
    
    async def get_part_datasheet(self, part_number: str) -> APIResponse:
        """
        Get datasheet URL for a part
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            APIResponse with datasheet information
        """
        part_response = await self.get_part_details(part_number)
        
        if part_response.success and part_response.data:
            part_data = part_response.data
            
            # Extract datasheet URL from part details
            datasheet_url = None
            if 'PrimaryDatasheet' in part_data:
                datasheet_url = part_data['PrimaryDatasheet']
            elif 'DatasheetUrl' in part_data:
                datasheet_url = part_data['DatasheetUrl']
            
            return APIResponse(
                success=True,
                status_code=200,
                data={
                    "part_number": part_number,
                    "datasheet_url": datasheet_url,
                    "has_datasheet": datasheet_url is not None
                }
            )
        
        return part_response
    
    async def get_part_pricing(self, part_number: str) -> APIResponse:
        """
        Get pricing information for a part
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            APIResponse with pricing data
        """
        part_response = await self.get_part_details(part_number)
        
        if part_response.success and part_response.data:
            part_data = part_response.data
            
            # Extract pricing information
            pricing_data = {
                "part_number": part_number,
                "unit_price": part_data.get('UnitPrice'),
                "quantity_available": part_data.get('QuantityAvailable'),
                "minimum_quantity": part_data.get('MinimumOrderQuantity'),
                "pricing_breaks": part_data.get('ProductVariations', [])
            }
            
            return APIResponse(
                success=True,
                status_code=200,
                data=pricing_data
            )
        
        return part_response
    
    async def get_part_images(self, part_number: str) -> APIResponse:
        """
        Get product images for a part
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            APIResponse with image URLs
        """
        part_response = await self.get_part_details(part_number)
        
        if part_response.success and part_response.data:
            part_data = part_response.data
            
            # Extract image URLs
            images = []
            if 'PrimaryPhoto' in part_data:
                images.append({
                    "type": "primary",
                    "url": part_data['PrimaryPhoto'],
                    "description": "Primary product image"
                })
            
            if 'Photos' in part_data:
                for i, photo_url in enumerate(part_data['Photos']):
                    images.append({
                        "type": "additional",
                        "url": photo_url,
                        "description": f"Additional product image {i + 1}"
                    })
            
            return APIResponse(
                success=True,
                status_code=200,
                data={
                    "part_number": part_number,
                    "images": images,
                    "image_count": len(images)
                }
            )
        
        return part_response
    
    def get_part_url(self, part_number: str) -> str:
        """
        Get DigiKey product page URL for a part
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            Product page URL
        """
        return f"https://www.digikey.com/en/products/detail/{part_number}"
    
    # BaseSupplierClient implementation - Required abstract methods
    
    async def enrich_part_datasheet(self, part_number: str) -> DatasheetEnrichmentResponse:
        """
        Enrich part with datasheet information using standardized schema
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            DatasheetEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching datasheet for DigiKey part: {part_number}")
            
            source = EnrichmentSource(
                supplier="DigiKey",
                api_endpoint=f"{self.api_base}/Search/v4/Product/{part_number}",
                api_version=self.api_version
            )
            
            # Get datasheet using existing method
            datasheet_response = await self.get_part_datasheet(part_number)
            
            if datasheet_response.success and datasheet_response.data:
                datasheet_data = datasheet_response.data
                datasheet_url = datasheet_data.get("datasheet_url")
                
                if datasheet_url:
                    return DatasheetEnrichmentResponse(
                        success=True,
                        status="success",
                        source=source,
                        part_number=part_number,
                        datasheet_url=datasheet_url,
                        download_verified=False
                    )
                else:
                    return DatasheetEnrichmentResponse(
                        success=False,
                        status="failed",
                        source=source,
                        part_number=part_number,
                        error_message="No datasheet URL found for this part"
                    )
            else:
                return DatasheetEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="Failed to retrieve part information"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching datasheet for {part_number}: {e}")
            return DatasheetEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="DigiKey"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_image(self, part_number: str) -> ImageEnrichmentResponse:
        """
        Enrich part with image information using standardized schema
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            ImageEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching image for DigiKey part: {part_number}")
            
            source = EnrichmentSource(
                supplier="DigiKey",
                api_endpoint=f"{self.api_base}/Search/v4/Product/{part_number}",
                api_version=self.api_version
            )
            
            # Get images using existing method
            images_response = await self.get_part_images(part_number)
            
            if images_response.success and images_response.data:
                images_data = images_response.data
                image_list = images_data.get("images", [])
                
                if image_list:
                    # Convert to standardized ImageInfo objects
                    image_infos = []
                    primary_image_url = None
                    
                    for img in image_list:
                        image_info = ImageInfo(
                            url=img["url"],
                            type=img.get("type", "product"),
                            format="jpg"  # DigiKey typically uses JPG
                        )
                        image_infos.append(image_info)
                        
                        # Set primary image (first one or specifically marked as primary)
                        if img.get("type") == "primary" or primary_image_url is None:
                            primary_image_url = img["url"]
                    
                    return ImageEnrichmentResponse(
                        success=True,
                        status="success",
                        source=source,
                        part_number=part_number,
                        images=image_infos,
                        primary_image_url=primary_image_url
                    )
                else:
                    return ImageEnrichmentResponse(
                        success=False,
                        status="failed",
                        source=source,
                        part_number=part_number,
                        error_message="No images found for this part"
                    )
            else:
                return ImageEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="Failed to retrieve part information"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching image for {part_number}: {e}")
            return ImageEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="DigiKey"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_details(self, part_number: str) -> DetailsEnrichmentResponse:
        """
        Enrich part with detailed component information using standardized schema
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            DetailsEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching details for DigiKey part: {part_number}")
            
            source = EnrichmentSource(
                supplier="DigiKey",
                api_endpoint=f"{self.api_base}/Search/v4/Product/{part_number}",
                api_version=self.api_version
            )
            
            # Get part details
            details_response = await self.get_part_details(part_number)
            
            if details_response.success and details_response.data:
                part_data = details_response.data
                
                # Extract specifications
                specifications = []
                if "Parameters" in part_data:
                    for param in part_data["Parameters"]:
                        if isinstance(param, dict) and "Parameter" in param and "Value" in param:
                            specifications.append(SpecificationAttribute(
                                name=param["Parameter"],
                                value=param["Value"],
                                unit=param.get("Unit")
                            ))
                
                return DetailsEnrichmentResponse(
                    success=True,
                    status="success",
                    source=source,
                    part_number=part_number,
                    manufacturer=part_data.get("ManufacturerName"),
                    manufacturer_part_number=part_data.get("ManufacturerPartNumber"),
                    product_description=part_data.get("ProductDescription"),
                    detailed_description=part_data.get("DetailedDescription"),
                    category=part_data.get("Category", {}).get("Name"),
                    subcategory=part_data.get("Subcategory", {}).get("Name"),
                    package_type=part_data.get("Packaging", {}).get("Name"),
                    series=part_data.get("Series"),
                    specifications=specifications,
                    rohs_compliant=part_data.get("RohsInfo") == "RoHS Compliant"
                )
            else:
                return DetailsEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="Failed to retrieve part details"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching details for {part_number}: {e}")
            return DetailsEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="DigiKey"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_pricing(self, part_number: str) -> PricingEnrichmentResponse:
        """
        Enrich part with pricing information using standardized schema
        
        Args:
            part_number: DigiKey part number
            
        Returns:
            PricingEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching pricing for DigiKey part: {part_number}")
            
            source = EnrichmentSource(
                supplier="DigiKey",
                api_endpoint=f"{self.api_base}/Search/v4/Product/{part_number}",
                api_version=self.api_version
            )
            
            # Get pricing using existing method
            pricing_response = await self.get_part_pricing(part_number)
            
            if pricing_response.success and pricing_response.data:
                pricing_data = pricing_response.data
                
                # Extract price breaks
                price_breaks = []
                if "pricing_breaks" in pricing_data:
                    for break_item in pricing_data["pricing_breaks"]:
                        if isinstance(break_item, dict):
                            qty = break_item.get("Quantity", 1)
                            price = break_item.get("UnitPrice", 0.0)
                            if price > 0:
                                price_breaks.append(PriceBreak(
                                    quantity=int(qty),
                                    unit_price=float(price),
                                    currency="USD",
                                    price_type="distributor"
                                ))
                
                # Get unit price
                unit_price = pricing_data.get("unit_price")
                if unit_price is None and price_breaks:
                    price_breaks.sort(key=lambda x: x.quantity)
                    unit_price = price_breaks[0].unit_price
                
                return PricingEnrichmentResponse(
                    success=True,
                    status="success",
                    source=source,
                    part_number=part_number,
                    unit_price=float(unit_price) if unit_price else None,
                    currency="USD",
                    price_breaks=price_breaks,
                    minimum_order_quantity=pricing_data.get("minimum_quantity", 1),
                    price_source="digikey_api"
                )
            else:
                return PricingEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="Failed to retrieve pricing information"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching pricing for {part_number}: {e}")
            return PricingEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="DigiKey"),
                part_number=part_number,
                error_message=str(e)
            )
    
    def get_supported_capabilities(self) -> List[str]:
        """
        Get list of enrichment capabilities supported by DigiKey supplier
        
        Returns:
            List of capability names that DigiKey API v4 actually supports
        """
        return [
            "fetch_datasheet",      # Via MediaLinks in product details
            "fetch_image",          # Via PrimaryPhoto/Photos in product details
            "fetch_pricing",        # Via StandardPricing/QuantityAvailable
            "fetch_stock",          # Via QuantityAvailable in product details
            "fetch_specifications", # Via Parameters in product details
            "fetch_details",        # Via complete product information
        ]
    
    def get_supplier_part_number(self, part_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract DigiKey part number from part data
        
        Args:
            part_data: Dictionary containing part information
            
        Returns:
            DigiKey part number, or None if not found
        """
        additional_properties = part_data.get('additional_properties', {})
        
        # Try different possible keys for DigiKey part number
        digikey_keys = ['digikey_part_number', 'DigiKey_part_number', 'digikey_id', 'digikey_sku']
        
        for key in digikey_keys:
            if key in additional_properties and additional_properties[key]:
                digikey_part = str(additional_properties[key]).strip()
                if digikey_part:
                    self.logger.debug(f"Found DigiKey part number: {digikey_part}")
                    return digikey_part
        
        # Fallback to manufacturer part number (DigiKey can search by manufacturer part number)
        part_number = part_data.get('part_number', '')
        if part_number:
            self.logger.debug(f"Using manufacturer part number for DigiKey: {part_number}")
            return part_number
        
        self.logger.debug("No DigiKey part number found")
        return None