"""
Mouser Electronics API Client

Implements Mouser's Search API with API key authentication.
Provides part search, datasheet fetching, pricing, and product information retrieval.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..base_client import BaseAPIClient, APIResponse, HTTPMethod
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


class MouserClient(BaseAPIClient, BaseSupplierClient):
    """
    Mouser API client using API key authentication
    
    Supports:
    - Part search and information
    - Datasheet URL retrieval  
    - Product images
    - Pricing and availability
    - Technical specifications
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.mouser.com/api/v1",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_per_minute: int = 20,  # Conservative rate limit
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Mouser API client
        
        Args:
            api_key: Mouser API Key
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit_per_minute: Rate limit per minute
            custom_headers: Additional headers
        """
        # Initialize both parent classes
        BaseAPIClient.__init__(self, base_url, timeout, max_retries)
        BaseSupplierClient.__init__(self, supplier_name="Mouser")
        
        self.api_key = api_key
        self.rate_limit_per_minute = rate_limit_per_minute
        self.custom_headers = custom_headers or {}
        
        # Default headers for Mouser API
        self.default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MakerMatrix/1.0.0 (Component Management System)",
        }
        
        # Merge with custom headers
        self.custom_headers.update(self.default_headers)
        
        self.logger = logging.getLogger(f"{__name__}.MouserClient")
        
        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_window = 60.0  # 1 minute
        
        self.logger.info(f"Mouser API client initialized")
    
    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting for Mouser API"""
        current_time = datetime.utcnow().timestamp()
        
        # Initialize if needed
        if not hasattr(self, '_last_request_time') or self._last_request_time is None:
            self._last_request_time = 0.0
        if not hasattr(self, '_request_count') or self._request_count is None:
            self._request_count = 0
        
        # Ensure types are correct
        self._last_request_time = float(self._last_request_time)
        self._request_count = int(self._request_count)
        rate_limit_per_minute = int(self.rate_limit_per_minute)
        rate_limit_window = float(self._rate_limit_window)
        
        # Reset counter if window has passed
        if current_time - self._last_request_time > rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time
        
        # Check rate limit
        if self._request_count >= rate_limit_per_minute:
            wait_time = rate_limit_window - (current_time - self._last_request_time)
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._last_request_time = datetime.utcnow().timestamp()
        
        self._request_count += 1
    
    async def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """
        Make API request to Mouser
        
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
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._merge_headers()
        
        # Add API key to params
        if not params:
            params = {}
        params["apiKey"] = self.api_key
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Mouser API request: {method.value} {url} (attempt {attempt + 1})")
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.request(
                        method=method.value,
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
                                raw_content=response_text
                            )
                        
                        # Handle rate limiting
                        elif response.status == 429:
                            retry_after = int(response.headers.get('Retry-After', 60))
                            if attempt < self.max_retries:
                                self.logger.warning(f"Rate limited, waiting {retry_after} seconds")
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                raise RateLimitError(f"Rate limit exceeded: {response_text}")
                        
                        # Handle authentication errors
                        elif response.status == 401:
                            raise AuthenticationError(f"Mouser authentication failed: {response_text}")
                        
                        # Handle other errors
                        else:
                            error_message = f"Mouser API error {response.status}: {response_text}"
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
        Test Mouser API connection
        
        Returns:
            True if connection successful
        """
        try:
            # Test with a simple search
            search_data = {
                "SearchByKeywordRequest": {
                    "keyword": "resistor",
                    "records": 1,
                    "startingRecord": 0
                }
            }
            
            response = await self.request(HTTPMethod.POST, "search/keyword", data=search_data)
            
            if response.success:
                self.logger.info("Mouser API connection test successful")
                return True
            else:
                self.logger.error(f"Mouser API connection test failed: {response.data}")
                return False
                
        except Exception as e:
            self.logger.error(f"Mouser API connection test failed: {e}")
            return False
    
    async def search_parts(
        self,
        keyword: str,
        limit: int = 50,
        offset: int = 0
    ) -> APIResponse:
        """
        Search for parts by keyword
        
        Args:
            keyword: Search keyword
            limit: Maximum results to return
            offset: Result offset for pagination
            
        Returns:
            APIResponse with search results
        """
        search_data = {
            "SearchByKeywordRequest": {
                "keyword": keyword,
                "records": min(limit, 100),  # Mouser allows up to 100 records
                "startingRecord": offset,
                "searchOptions": "None"
            }
        }
        
        return await self.request(HTTPMethod.POST, "search/keyword", data=search_data)
    
    async def get_part_details(self, part_number: str) -> APIResponse:
        """
        Get detailed information for a specific part
        
        Args:
            part_number: Mouser part number
            
        Returns:
            APIResponse with part details
        """
        search_data = {
            "SearchByPartRequest": {
                "mouserPartNumber": part_number,
                "partSearchOptions": "None"
            }
        }
        
        return await self.request(HTTPMethod.POST, "search/partnumber", data=search_data)
    
    def get_authentication_headers(self) -> Dict[str, str]:
        """
        Mouser uses API key in URL params, not headers
        """
        return {}
    
    # BaseSupplierClient implementation - Required abstract methods
    
    async def enrich_part_datasheet(self, part_number: str) -> DatasheetEnrichmentResponse:
        """
        Enrich part with datasheet information using standardized schema
        
        Args:
            part_number: Mouser part number
            
        Returns:
            DatasheetEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching datasheet for Mouser part: {part_number}")
            
            source = EnrichmentSource(
                supplier="Mouser",
                api_endpoint=f"{self.base_url}/search/partnumber",
                api_version="v1"
            )
            
            # Get part details
            details_response = await self.get_part_details(part_number)
            
            if details_response.success and details_response.data:
                search_results = details_response.data.get("SearchResults", {})
                parts = search_results.get("Parts", [])
                
                if parts:
                    part_data = parts[0]
                    datasheet_url = part_data.get("DataSheetUrl")
                    
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
                        error_message="Part not found"
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
                source=EnrichmentSource(supplier="Mouser"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_image(self, part_number: str) -> ImageEnrichmentResponse:
        """
        Enrich part with image information using standardized schema
        
        Args:
            part_number: Mouser part number
            
        Returns:
            ImageEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching image for Mouser part: {part_number}")
            
            source = EnrichmentSource(
                supplier="Mouser",
                api_endpoint=f"{self.base_url}/search/partnumber",
                api_version="v1"
            )
            
            # Get part details
            details_response = await self.get_part_details(part_number)
            
            if details_response.success and details_response.data:
                search_results = details_response.data.get("SearchResults", {})
                parts = search_results.get("Parts", [])
                
                if parts:
                    part_data = parts[0]
                    image_url = part_data.get("ImagePath")
                    
                    if image_url:
                        # Create image info object
                        image_info = ImageInfo(
                            url=image_url,
                            type="product",
                            format="jpg"  # Mouser typically uses JPG images
                        )
                        
                        return ImageEnrichmentResponse(
                            success=True,
                            status="success",
                            source=source,
                            part_number=part_number,
                            images=[image_info],
                            primary_image_url=image_url
                        )
                    else:
                        return ImageEnrichmentResponse(
                            success=False,
                            status="failed",
                            source=source,
                            part_number=part_number,
                            error_message="No image URL found for this part"
                        )
                else:
                    return ImageEnrichmentResponse(
                        success=False,
                        status="failed",
                        source=source,
                        part_number=part_number,
                        error_message="Part not found"
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
                source=EnrichmentSource(supplier="Mouser"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_details(self, part_number: str) -> DetailsEnrichmentResponse:
        """
        Enrich part with detailed component information using standardized schema
        
        Args:
            part_number: Mouser part number
            
        Returns:
            DetailsEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching details for Mouser part: {part_number}")
            
            source = EnrichmentSource(
                supplier="Mouser",
                api_endpoint=f"{self.base_url}/search/partnumber",
                api_version="v1"
            )
            
            # Get part details
            details_response = await self.get_part_details(part_number)
            
            if details_response.success and details_response.data:
                search_results = details_response.data.get("SearchResults", {})
                parts = search_results.get("Parts", [])
                
                if parts:
                    part_data = parts[0]
                    
                    # Extract specifications
                    specifications = []
                    attributes = part_data.get("ProductAttributes", [])
                    for attr in attributes:
                        attr_name = attr.get("AttributeName", "")
                        attr_value = attr.get("AttributeValue", "")
                        if attr_name and attr_value:
                            specifications.append(SpecificationAttribute(
                                name=attr_name,
                                value=attr_value
                            ))
                    
                    return DetailsEnrichmentResponse(
                        success=True,
                        status="success",
                        source=source,
                        part_number=part_number,
                        manufacturer=part_data.get("Manufacturer"),
                        manufacturer_part_number=part_data.get("ManufacturerPartNumber"),
                        product_description=part_data.get("Description"),
                        detailed_description=part_data.get("DetailedDescription"),
                        category=part_data.get("Category"),
                        subcategory=part_data.get("Subcategory"),
                        package_type=None,  # Not directly available in Mouser API
                        series=None,  # Not directly available in Mouser API
                        specifications=specifications,
                        rohs_compliant=part_data.get("RohsStatus") == "RoHS Compliant"
                    )
                else:
                    return DetailsEnrichmentResponse(
                        success=False,
                        status="failed",
                        source=source,
                        part_number=part_number,
                        error_message="Part not found"
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
                source=EnrichmentSource(supplier="Mouser"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_pricing(self, part_number: str) -> PricingEnrichmentResponse:
        """
        Enrich part with pricing information using standardized schema
        
        Args:
            part_number: Mouser part number
            
        Returns:
            PricingEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching pricing for Mouser part: {part_number}")
            
            source = EnrichmentSource(
                supplier="Mouser",
                api_endpoint=f"{self.base_url}/search/partnumber",
                api_version="v1"
            )
            
            # Get part details
            details_response = await self.get_part_details(part_number)
            
            if details_response.success and details_response.data:
                search_results = details_response.data.get("SearchResults", {})
                parts = search_results.get("Parts", [])
                
                if parts:
                    part_data = parts[0]
                    
                    # Extract price breaks
                    price_breaks = []
                    price_break_data = part_data.get("PriceBreaks", [])
                    for price_break in price_break_data:
                        qty = price_break.get("Quantity", 1)
                        price_str = price_break.get("Price", "0")
                        # Remove currency symbols and commas
                        try:
                            price = float(price_str.replace("$", "").replace(",", ""))
                            if price > 0:
                                price_breaks.append(PriceBreak(
                                    quantity=int(qty),
                                    unit_price=price,
                                    currency=price_break.get("Currency", "USD"),
                                    price_type="distributor"
                                ))
                        except (ValueError, TypeError):
                            continue
                    
                    # Get unit price (lowest quantity price)
                    unit_price = None
                    if price_breaks:
                        price_breaks.sort(key=lambda x: x.quantity)
                        unit_price = price_breaks[0].unit_price
                    
                    return PricingEnrichmentResponse(
                        success=True,
                        status="success",
                        source=source,
                        part_number=part_number,
                        unit_price=unit_price,
                        currency="USD",
                        price_breaks=price_breaks,
                        minimum_order_quantity=part_data.get("Min", 1),
                        price_source="mouser_api"
                    )
                else:
                    return PricingEnrichmentResponse(
                        success=False,
                        status="failed",
                        source=source,
                        part_number=part_number,
                        error_message="Part not found"
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
                source=EnrichmentSource(supplier="Mouser"),
                part_number=part_number,
                error_message=str(e)
            )
    
    def get_supported_capabilities(self) -> List[str]:
        """
        Get list of enrichment capabilities supported by Mouser supplier
        
        Returns:
            List of capability names that Mouser Search API actually supports
        """
        return [
            "fetch_datasheet",      # Via DataSheetUrl in part search results
            "fetch_image",          # Via ImagePath in part search results
            "fetch_pricing",        # Via PriceBreaks in part search results
            "fetch_stock",          # Via Availability in part search results
            "fetch_specifications", # Via ProductAttributes in search results
            "fetch_details",        # Via complete part information from search
        ]
    
    def get_supplier_part_number(self, part_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract Mouser part number from part data
        
        Args:
            part_data: Dictionary containing part information
            
        Returns:
            Mouser part number, or None if not found
        """
        additional_properties = part_data.get('additional_properties', {})
        
        # Try different possible keys for Mouser part number
        mouser_keys = ['mouser_part_number', 'Mouser_part_number', 'mouser_id', 'mouser_sku']
        
        for key in mouser_keys:
            if key in additional_properties and additional_properties[key]:
                mouser_part = str(additional_properties[key]).strip()
                if mouser_part:
                    self.logger.debug(f"Found Mouser part number: {mouser_part}")
                    return mouser_part
        
        # Fallback to manufacturer part number (Mouser can search by manufacturer part number)
        part_number = part_data.get('part_number', '')
        if part_number:
            self.logger.debug(f"Using manufacturer part number for Mouser: {part_number}")
            return part_number
        
        self.logger.debug("No Mouser part number found")
        return None