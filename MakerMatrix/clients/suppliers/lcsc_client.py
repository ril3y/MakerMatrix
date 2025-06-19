"""
LCSC/EasyEDA API Client

Client for interacting with the EasyEDA API to fetch LCSC component data,
datasheets, and other enrichment information.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import re
from bs4 import BeautifulSoup

from ..base_client import BaseAPIClient, APIResponse, HTTPMethod
from ..exceptions import APIClientError, InvalidResponseError
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


class LCSCClient(BaseAPIClient, BaseSupplierClient):
    """
    LCSC API client using EasyEDA endpoints
    
    This client interfaces with EasyEDA's API to fetch component information
    for LCSC parts including datasheets, images, and technical specifications.
    Implements BaseSupplierClient for standardized enrichment interface.
    """
    
    # EasyEDA API endpoints
    COMPONENT_INFO_URL = "https://easyeda.com/api/products/{lcsc_id}/components"
    MODEL_3D_URL = "https://easyeda.com/analyzer/api/3dmodel/{uuid}"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 rate_limit_per_minute: Optional[int] = 60,  # Conservative rate limit
                 custom_headers: Optional[Dict[str, str]] = None):
        """
        Initialize LCSC client
        
        Args:
            api_key: Not required for EasyEDA API (public API)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit_per_minute: Rate limit for requests
            custom_headers: Additional headers
        """
        # Initialize both parent classes
        BaseAPIClient.__init__(
            self,
            base_url="https://easyeda.com",
            api_key=api_key,  # Not required for EasyEDA
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_per_minute=rate_limit_per_minute,
            custom_headers=custom_headers
        )
        BaseSupplierClient.__init__(self, supplier_name="LCSC")
        
        # Default headers for EasyEDA API
        self.default_headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "MakerMatrix/1.0.0 (Component Management System)",
        }
        
        # Merge with custom headers
        self.custom_headers.update(self.default_headers)
        
        self.logger = logging.getLogger(f"{__name__}.LCSCClient")
    
    async def request(self, 
                     method: HTTPMethod,
                     endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """
        Make HTTP request to EasyEDA API
        """
        await self._check_rate_limit()
        
        # For EasyEDA, we often use full URLs rather than relative endpoints
        if endpoint.startswith('http'):
            url = endpoint
        else:
            url = self._build_url(endpoint)
        
        merged_headers = self._merge_headers(headers)
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"Making {method.value} request to EasyEDA: {url}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method.value,
                        url=url,
                        params=params,
                        json=data,
                        headers=merged_headers
                    )
                    
                    return await self._process_easyeda_response(response)
                    
            except httpx.TimeoutException as e:
                last_exception = APIClientError(f"Request timeout: {e}")
                self.logger.warning(f"Request timeout on attempt {attempt + 1}")
                
            except httpx.RequestError as e:
                last_exception = APIClientError(f"Request error: {e}")
                self.logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                last_exception = APIClientError(f"Unexpected error: {e}")
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            # Retry with exponential backoff
            if attempt < self.max_retries:
                backoff_time = 1.0 * (2 ** attempt)
                await asyncio.sleep(backoff_time)
        
        if last_exception:
            raise last_exception
        raise APIClientError("All retry attempts failed")
    
    async def _process_easyeda_response(self, response: httpx.Response) -> APIResponse:
        """
        Process EasyEDA API response
        """
        try:
            response_data = response.json()
        except Exception:
            response_data = {"content": response.text}
        
        api_response = APIResponse(
            status_code=response.status_code,
            data=response_data,
            headers=dict(response.headers),
            raw_content=response.text
        )
        
        # EasyEDA API specific error handling
        if response.status_code == 200:
            # Check for EasyEDA API error format
            if isinstance(response_data, dict):
                if response_data.get("success") is False:
                    api_response.success = False
                    api_response.error_message = response_data.get("message", "EasyEDA API error")
                elif "code" in response_data and response_data.get("success") is not True:
                    api_response.success = False
                    api_response.error_message = f"EasyEDA error code: {response_data.get('code')}"
            
            return api_response
        
        # Handle HTTP errors
        elif response.status_code >= 400:
            raise APIClientError(
                f"EasyEDA API error: {response.status_code} - {response_data}",
                status_code=response.status_code,
                response_data=response_data
            )
        
        return api_response
    
    async def get_component_info(self, lcsc_id: str, version: str = "6.4.19.5") -> Dict[str, Any]:
        """
        Get component information from EasyEDA API
        
        Args:
            lcsc_id: LCSC component ID (e.g., "C1000")
            version: API version parameter
            
        Returns:
            Dictionary containing component information
            
        Raises:
            APIClientError: If the request fails
            InvalidResponseError: If response format is invalid
        """
        self.logger.info(f"Fetching component info for LCSC ID: {lcsc_id}")
        
        url = self.COMPONENT_INFO_URL.format(lcsc_id=lcsc_id.upper())
        params = {"version": version}
        
        try:
            response = await self.request(HTTPMethod.GET, url, params=params)
            
            if not response.success:
                raise APIClientError(
                    f"Failed to fetch component info: {response.error_message}",
                    response_data=response.data
                )
            
            # Validate response structure
            if not isinstance(response.data, dict):
                raise InvalidResponseError(
                    "Expected JSON object in response",
                    expected_format="JSON object"
                )
            
            self.logger.debug(f"Successfully fetched component info for {lcsc_id}")
            return response.data
            
        except Exception as e:
            self.logger.error(f"Error fetching component info for {lcsc_id}: {e}")
            raise
    
    async def get_cad_data(self, lcsc_id: str) -> Dict[str, Any]:
        """
        Get CAD data for component
        
        Args:
            lcsc_id: LCSC component ID
            
        Returns:
            Dictionary containing CAD data from the 'result' field
        """
        component_info = await self.get_component_info(lcsc_id)
        
        if not component_info:
            return {}
        
        return component_info.get("result", {})
    
    async def get_3d_model(self, uuid: str) -> Optional[str]:
        """
        Get 3D model data for component
        
        Args:
            uuid: Component UUID for 3D model
            
        Returns:
            3D model data as string, or None if not found
        """
        self.logger.info(f"Fetching 3D model for UUID: {uuid}")
        
        url = self.MODEL_3D_URL.format(uuid=uuid)
        
        try:
            response = await self.request(HTTPMethod.GET, url)
            
            if response.success and response.raw_content:
                self.logger.debug(f"Successfully fetched 3D model for {uuid}")
                return response.raw_content
            else:
                self.logger.warning(f"No 3D model found for UUID: {uuid}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching 3D model for {uuid}: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        Test connection to EasyEDA API
        """
        try:
            self.logger.info("Testing EasyEDA API connection...")
            
            # Test with known working LCSC components
            test_components = ["C25804", "C14663", "C25879"]  # Common components that should exist
            
            for test_lcsc_id in test_components:
                try:
                    self.logger.debug(f"Testing with component: {test_lcsc_id}")
                    test_response = await self.get_component_info(test_lcsc_id)
                    
                    # Check if we got a valid response structure
                    if isinstance(test_response, dict) and test_response:
                        self.logger.info("EasyEDA API connection test successful")
                        return True
                        
                except APIClientError as e:
                    # Try next component if this one fails
                    self.logger.debug(f"Component {test_lcsc_id} failed: {e}")
                    continue
            
            # If all test components failed
            self.logger.warning("EasyEDA API connection test failed - no test components found")
            return False
                
        except Exception as e:
            self.logger.warning(f"EasyEDA API connection test failed: {e}")
            return False
    
    def get_authentication_headers(self) -> Dict[str, str]:
        """
        EasyEDA API doesn't require authentication
        """
        return {}
    
    def get_supported_capabilities(self) -> List[str]:
        """
        Get list of enrichment capabilities supported by LCSC supplier
        
        Returns:
            List of capability names that LCSC actually supports
        """
        return [
            "fetch_datasheet",  # Via web scraping for PDF URL
            "fetch_image",      # Via result.thumb
            "fetch_pricing",    # Via result.lcsc pricing data
            "fetch_details",    # Via dataStr.head.c_para component parameters
            # Note: LCSC does not support stock or specifications via EasyEDA API
        ]
    
    def get_supplier_part_number(self, part_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract LCSC part number from part data
        
        Args:
            part_data: Dictionary containing part information
            
        Returns:
            LCSC part number (e.g., "C136648"), or None if not found
        """
        additional_properties = part_data.get('additional_properties', {})
        
        # Try different possible keys for LCSC part number
        lcsc_keys = ['lcsc_part_number', 'LCSC_part_number', 'lcsc_id', 'lcsc_number']
        
        for key in lcsc_keys:
            if key in additional_properties and additional_properties[key]:
                lcsc_part = str(additional_properties[key]).strip()
                if lcsc_part:
                    self.logger.debug(f"Found LCSC part number: {lcsc_part}")
                    return lcsc_part
        
        # If no LCSC part number found, check if the main part_number looks like an LCSC ID
        part_number = part_data.get('part_number', '')
        if part_number and str(part_number).upper().startswith('C') and str(part_number)[1:].isdigit():
            self.logger.debug(f"Main part number appears to be LCSC format: {part_number}")
            return part_number
        
        self.logger.debug("No LCSC part number found")
        return None
    
    # Convenience methods for common operations
    
    async def search_by_part_number(self, part_number: str) -> Dict[str, Any]:
        """
        Search for component by part number
        
        Note: This assumes the part number is an LCSC ID.
        For more complex search, additional API endpoints would be needed.
        """
        return await self.get_component_info(part_number)
    
    async def get_datasheet_url(self, lcsc_id: str) -> Optional[str]:
        """
        Extract datasheet URL from component info and get direct PDF URL from intermediate page
        
        Args:
            lcsc_id: LCSC component ID
            
        Returns:
            Direct PDF URL if available, intermediate datasheet URL otherwise, None if not found
        """
        try:
            component_info = await self.get_component_info(lcsc_id)
            
            # Navigate the nested structure to find datasheet
            result = component_info.get("result", {})
            if isinstance(result, dict):
                lcsc_info = result.get("lcsc", {})
                
                # Try to get URL from lcsc_info, if not present, construct it
                product_url = lcsc_info.get("url")
                if not product_url and "number" in lcsc_info:
                    # Use new LCSC URL format (without www, different path)
                    product_url = f"https://lcsc.com/product/{lcsc_info['number']}"
                    self.logger.debug(f"Constructed LCSC product URL: {product_url}")
                elif not product_url:
                    # Fallback: construct from the lcsc_id parameter with new format
                    product_url = f"https://lcsc.com/product/{lcsc_id}"
                    self.logger.debug(f"Fallback constructed LCSC product URL: {product_url}")
                
                if product_url:
                    # Get the intermediate datasheet URL from the product page first
                    intermediate_datasheet_url = await self._extract_intermediate_datasheet_url(product_url)
                    
                    if intermediate_datasheet_url:
                        self.logger.info(f"📄 Found intermediate datasheet URL: {intermediate_datasheet_url}")
                        
                        # Now scrape the intermediate page to get the actual PDF URL
                        pdf_url = await self._extract_pdf_from_intermediate_page(intermediate_datasheet_url)
                        if pdf_url:
                            self.logger.info(f"🎯 Successfully extracted direct PDF URL: {pdf_url}")
                            return pdf_url
                        else:
                            self.logger.warning(f"⚠️ Could not extract PDF from intermediate page, returning intermediate URL")
                            return intermediate_datasheet_url
                    
                    # Fallback: try direct PDF extraction from product page (old method)
                    pdf_url = await self._extract_datasheet_pdf_from_page(product_url)
                    if pdf_url:
                        self.logger.debug(f"Found direct PDF datasheet URL for {lcsc_id}: {pdf_url}")
                        return pdf_url

                    # Final fallback to product page URL
                    self.logger.debug(f"Returning LCSC product page URL for datasheet: {product_url}")
                    return product_url
            
            self.logger.debug(f"No datasheet URL found for {lcsc_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting datasheet URL for {lcsc_id}: {e}")
            return None
    
    async def _extract_intermediate_datasheet_url(self, product_url: str) -> Optional[str]:
        """
        Extract intermediate datasheet URL (lcsc.com/datasheet/...) from LCSC product page
        
        Args:
            product_url: LCSC product page URL
            
        Returns:
            Intermediate datasheet URL if found, None otherwise
        """
        try:
            self.logger.debug(f"Extracting intermediate datasheet URL from: {product_url}")
            
            # Fetch the product page with browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(product_url, headers=headers)
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch product page: {response.status_code}")
                    return None
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for datasheet button or link with specific patterns
                # Pattern 1: Look for "View Online" or "Datasheet" buttons/links
                datasheet_patterns = [
                    r'https?://(?:www\.)?lcsc\.com/datasheet/lcsc_datasheet_.*\.pdf',
                    r'https?://lcsc\.com/datasheet/lcsc_datasheet_.*\.pdf',
                    r'/datasheet/lcsc_datasheet_.*\.pdf'
                ]
                
                # Search in all links
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href:
                        for pattern in datasheet_patterns:
                            if re.search(pattern, href):
                                # Ensure URL is absolute
                                if href.startswith('//'):
                                    href = 'https:' + href
                                elif href.startswith('/'):
                                    href = 'https://www.lcsc.com' + href
                                
                                self.logger.debug(f"Found intermediate datasheet URL: {href}")
                                return href
                
                # Pattern 2: Look in onclick handlers or data attributes
                for element in soup.find_all(attrs={"onclick": True}):
                    onclick = element.get('onclick', '')
                    for pattern in datasheet_patterns:
                        match = re.search(pattern, onclick)
                        if match:
                            url = match.group(0)
                            if url.startswith('//'):
                                url = 'https:' + url
                            elif url.startswith('/'):
                                url = 'https://www.lcsc.com' + url
                            
                            self.logger.debug(f"Found intermediate datasheet URL in onclick: {url}")
                            return url
                
                # Pattern 3: Look for specific button text that might contain datasheet links
                datasheet_buttons = soup.find_all(text=re.compile(r'(view\s+online|datasheet|pdf)', re.IGNORECASE))
                for button_text in datasheet_buttons:
                    parent = button_text.parent
                    if parent and parent.name == 'a':
                        href = parent.get('href')
                        if href:
                            for pattern in datasheet_patterns:
                                if re.search(pattern, href):
                                    if href.startswith('//'):
                                        href = 'https:' + href
                                    elif href.startswith('/'):
                                        href = 'https://www.lcsc.com' + href
                                    
                                    self.logger.debug(f"Found intermediate datasheet URL via button text: {href}")
                                    return href
                
                self.logger.debug("No intermediate datasheet URL found on product page")
                return None
                
        except httpx.TimeoutException:
            self.logger.warning(f"Timeout while fetching product page: {product_url}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting intermediate datasheet URL: {e}")
            return None
    
    async def _extract_pdf_from_intermediate_page(self, intermediate_url: str) -> Optional[str]:
        """
        Extract actual PDF URL from intermediate datasheet page
        
        Args:
            intermediate_url: LCSC intermediate datasheet URL (e.g., https://lcsc.com/datasheet/...)
            
        Returns:
            Direct PDF URL (wmsc.lcsc.com) if found, None otherwise
        """
        try:
            self.logger.debug(f"Extracting PDF URL from intermediate page: {intermediate_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://www.lcsc.com/'
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(intermediate_url, headers=headers)
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch intermediate datasheet page: {response.status_code}")
                    # Check if the response itself contains a redirect to PDF
                    if response.status_code in [301, 302, 303, 307, 308]:
                        location = response.headers.get('location', '')
                        if 'wmsc.lcsc.com' in location and location.endswith('.pdf'):
                            self.logger.info(f"✅ Found wmsc PDF URL via redirect: {location}")
                            return location
                    return None
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for wmsc.lcsc.com PDF links with high priority
                wmsc_patterns = [
                    r'https?://wmsc\.lcsc\.com/wmsc/upload/file/pdf/v2/lcsc/.*\.pdf',
                    r'//wmsc\.lcsc\.com/wmsc/upload/file/pdf/v2/lcsc/.*\.pdf'
                ]
                
                # Search in all links first
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if href:
                        for pattern in wmsc_patterns:
                            if re.search(pattern, href):
                                if href.startswith('//'):
                                    href = 'https:' + href
                                self.logger.info(f"✅ Found wmsc PDF URL: {href}")
                                return href
                
                # Search in iframe sources (LCSC often embeds PDFs in iframes)
                for iframe in soup.find_all('iframe', src=True):
                    src = iframe.get('src')
                    if src:
                        for pattern in wmsc_patterns:
                            if re.search(pattern, src):
                                if src.startswith('//'):
                                    src = 'https:' + src
                                self.logger.info(f"✅ Found wmsc PDF URL in iframe: {src}")
                                return src
                
                # Search in button onclick handlers
                for button in soup.find_all(['button', 'a'], onclick=True):
                    onclick = button.get('onclick', '')
                    for pattern in wmsc_patterns:
                        match = re.search(pattern, onclick)
                        if match:
                            url = match.group(0)
                            if url.startswith('//'):
                                url = 'https:' + url
                            self.logger.info(f"✅ Found wmsc PDF URL in onclick: {url}")
                            return url
                
                # Search in script tags for JavaScript variables
                for script in soup.find_all('script'):
                    if script.string:
                        script_content = script.string
                        for pattern in wmsc_patterns:
                            match = re.search(pattern, script_content)
                            if match:
                                url = match.group(0)
                                if url.startswith('//'):
                                    url = 'https:' + url
                                self.logger.info(f"✅ Found wmsc PDF URL in script: {url}")
                                return url
                
                # Search for open/view buttons that might trigger PDF download
                open_buttons = soup.find_all(text=re.compile(r'(open|view|download)', re.IGNORECASE))
                for button_text in open_buttons:
                    parent = button_text.parent
                    while parent and parent.name:
                        if parent.get('href') or parent.get('onclick'):
                            target = parent.get('href') or parent.get('onclick', '')
                            for pattern in wmsc_patterns:
                                if re.search(pattern, target):
                                    url = re.search(pattern, target).group(0)
                                    if url.startswith('//'):
                                        url = 'https:' + url
                                    self.logger.info(f"✅ Found wmsc PDF URL via button: {url}")
                                    return url
                        parent = parent.parent
                        if not parent or parent.name == 'html':
                            break
                
                # Look for meta refresh or redirect
                meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
                if meta_refresh:
                    content = meta_refresh.get('content', '')
                    for pattern in wmsc_patterns:
                        match = re.search(pattern, content)
                        if match:
                            url = match.group(0)
                            if url.startswith('//'):
                                url = 'https:' + url
                            self.logger.info(f"✅ Found wmsc PDF URL in meta refresh: {url}")
                            return url
                
                self.logger.warning("No wmsc PDF URL found on intermediate datasheet page")
                return None
                
        except httpx.TimeoutException:
            self.logger.warning(f"Timeout while fetching intermediate datasheet page: {intermediate_url}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting PDF from intermediate page: {e}")
            return None
    
    async def _extract_datasheet_pdf_from_page(self, product_url: str) -> Optional[str]:
        """
        Extract direct PDF datasheet URL from LCSC product page
        
        Args:
            product_url: LCSC product page URL
            
        Returns:
            Direct PDF URL if found, None otherwise
        """
        try:
            self.logger.debug(f"Attempting to extract PDF datasheet from: {product_url}")
            
            # Fetch the product page with browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(product_url, headers=headers)
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch product page: {response.status_code}")
                    return None
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for datasheet PDF links in order of preference
                
                # 1. First try wmsc.lcsc.com URLs (the actual PDFs)
                wmsc_links = soup.find_all('a', href=re.compile(r'.*wmsc\.lcsc\.com.*\.pdf'))
                if wmsc_links:
                    pdf_url = wmsc_links[0].get('href')
                    if pdf_url:
                        if pdf_url.startswith('//'):
                            pdf_url = 'https:' + pdf_url
                        self.logger.debug(f"Found wmsc datasheet PDF URL: {pdf_url}")
                        return pdf_url
                
                # 2. Try standard LCSC datasheet URLs
                pdf_links = soup.find_all('a', href=re.compile(r'.*\.lcsc\.com/datasheet/.*\.pdf'))
                if pdf_links:
                    pdf_url = pdf_links[0].get('href')
                    if pdf_url:
                        # Ensure URL is absolute
                        if pdf_url.startswith('//'):
                            pdf_url = 'https:' + pdf_url
                        elif pdf_url.startswith('/'):
                            pdf_url = 'https://www.lcsc.com' + pdf_url
                        
                        self.logger.debug(f"Found datasheet PDF URL: {pdf_url}")
                        return pdf_url
                
                # 3. Alternative pattern - look for any link containing 'datasheet' and ending with '.pdf'
                datasheet_links = soup.find_all('a', href=re.compile(r'.*datasheet.*\.pdf', re.IGNORECASE))
                if datasheet_links:
                    pdf_url = datasheet_links[0].get('href')
                    if pdf_url:
                        if pdf_url.startswith('//'):
                            pdf_url = 'https:' + pdf_url
                        elif pdf_url.startswith('/'):
                            pdf_url = 'https://www.lcsc.com' + pdf_url
                        
                        self.logger.debug(f"Found alternative datasheet PDF URL: {pdf_url}")
                        return pdf_url
                
                self.logger.debug("No PDF datasheet link found on product page")
                return None
                
        except httpx.TimeoutException:
            self.logger.warning(f"Timeout while fetching product page: {product_url}")
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting PDF from product page: {e}")
            return None
    
    async def get_component_image_url(self, lcsc_id: str) -> Optional[str]:
        """
        Extract actual component photo from LCSC product page
        
        Args:
            lcsc_id: LCSC component ID
            
        Returns:
            Image URL if available, None otherwise
        """
        try:
            # First try to get the actual part photo from LCSC product page
            product_url = f"https://lcsc.com/product/{lcsc_id}"
            
            # Use proper async HTTP client with browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(product_url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Method 1: Look for Open Graph meta tags (most reliable)
                    og_image = soup.find('meta', attrs={'name': 'og:image', 'content': True})
                    if og_image:
                        img_url = og_image.get('content')
                        if img_url and 'assets.lcsc.com' in img_url:
                            self.logger.debug(f"Found OG image URL for {lcsc_id}: {img_url}")
                            return img_url
                    
                    # Method 2: Look for JSON-LD structured data
                    json_ld_scripts = soup.find_all('script', type='application/ld+json')
                    for script in json_ld_scripts:
                        try:
                            import json
                            data = json.loads(script.string)
                            if isinstance(data, dict):
                                # Check for image in Product schema
                                if data.get('@type') == 'Product' and 'image' in data:
                                    img_url = data['image']
                                    if img_url and 'assets.lcsc.com' in img_url:
                                        self.logger.debug(f"Found JSON-LD product image URL for {lcsc_id}: {img_url}")
                                        return img_url
                                # Check for image in ImageObject schema
                                elif data.get('@type') == 'ImageObject' and 'contentUrl' in data:
                                    img_url = data['contentUrl']
                                    if img_url and 'assets.lcsc.com' in img_url:
                                        self.logger.debug(f"Found JSON-LD image object URL for {lcsc_id}: {img_url}")
                                        return img_url
                        except (json.JSONDecodeError, AttributeError):
                            continue
                    
                    # Method 3: Look for background-image in style attributes (Vue.js rendered content)
                    elements_with_bg = soup.find_all(attrs={"style": True})
                    for element in elements_with_bg:
                        style = element.get('style', '')
                        if 'background-image: url(' in style and 'assets.lcsc.com' in style:
                            # Extract URL from background-image: url("...")
                            match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
                            if match:
                                img_url = match.group(1)
                                # Only return if it's an actual part photo (contains specific patterns)
                                if any(pattern in img_url for pattern in ['_front.jpg', '_back.jpg', '/900x900/', '/lcsc/']):
                                    if img_url.startswith("//"):
                                        img_url = "https:" + img_url
                                    self.logger.debug(f"Found background image URL for {lcsc_id}: {img_url}")
                                    return img_url
                    
                    # Method 4: Look for img tags with src attributes (fallback)
                    image_selectors = [
                        'img[src*="assets.lcsc.com"]',
                        'img[src*="lcsc.com/images"]',
                        '.product-image img',
                        'img.product-photo'
                    ]
                    
                    for selector in image_selectors:
                        img_element = soup.select_one(selector)
                        if img_element:
                            img_url = img_element.get('src')
                            if img_url and 'assets.lcsc.com' in img_url:
                                # Only return if it's an actual part photo
                                if any(pattern in img_url for pattern in ['_front.jpg', '_back.jpg', '/900x900/', '/lcsc/']):
                                    if img_url.startswith("//"):
                                        img_url = "https:" + img_url
                                    elif img_url.startswith("/"):
                                        img_url = "https://lcsc.com" + img_url
                                    self.logger.debug(f"Found img tag image URL for {lcsc_id}: {img_url}")
                                    return img_url
            
            # Fallback to EasyEDA symbol if no product photo found
            self.logger.debug(f"No product photo found, falling back to symbol for {lcsc_id}")
            component_info = await self.get_component_info(lcsc_id)
            
            result = component_info.get("result", {})
            if isinstance(result, dict):
                image_url = result.get("thumb")
                if image_url:
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                    self.logger.debug(f"Found symbol image URL for {lcsc_id}: {image_url}")
                    return image_url
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting image URL for {lcsc_id}: {e}")
            return None
            return None
    
    # BaseSupplierClient implementation - Required abstract methods
    
    async def enrich_part_datasheet(self, part_number: str) -> DatasheetEnrichmentResponse:
        """
        Enrich part with datasheet information using standardized schema
        
        Args:
            part_number: LCSC part number (e.g., "C1000")
            
        Returns:
            DatasheetEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching datasheet for LCSC part: {part_number}")
            
            source = EnrichmentSource(
                supplier="LCSC",
                api_endpoint=self.COMPONENT_INFO_URL.format(lcsc_id=part_number),
                api_version="6.4.19.5"
            )
            
            # Get datasheet URL using existing method
            datasheet_url = await self.get_datasheet_url(part_number)
            
            if datasheet_url:
                return DatasheetEnrichmentResponse(
                    success=True,
                    status="success",
                    source=source,
                    part_number=part_number,
                    datasheet_url=datasheet_url,
                    download_verified=False  # We don't verify downloads by default
                )
            else:
                return DatasheetEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="No datasheet URL found for this part"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching datasheet for {part_number}: {e}")
            return DatasheetEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="LCSC"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_image(self, part_number: str) -> ImageEnrichmentResponse:
        """
        Enrich part with image information using standardized schema
        
        Args:
            part_number: LCSC part number (e.g., "C1000")
            
        Returns:
            ImageEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching image for LCSC part: {part_number}")
            
            source = EnrichmentSource(
                supplier="LCSC",
                api_endpoint=self.COMPONENT_INFO_URL.format(lcsc_id=part_number),
                api_version="6.4.19.5"
            )
            
            # Get image URL using existing method
            image_url = await self.get_component_image_url(part_number)
            
            if image_url:
                # Create image info object
                image_info = ImageInfo(
                    url=image_url,
                    type="product",
                    format="jpg"  # LCSC typically uses JPG images
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
                
        except Exception as e:
            self.logger.error(f"Error enriching image for {part_number}: {e}")
            return ImageEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="LCSC"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_details(self, part_number: str) -> DetailsEnrichmentResponse:
        """
        Enrich part with detailed component information using standardized schema
        
        Args:
            part_number: LCSC part number (e.g., "C1000")
            
        Returns:
            DetailsEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching details for LCSC part: {part_number}")
            
            source = EnrichmentSource(
                supplier="LCSC",
                api_endpoint=self.COMPONENT_INFO_URL.format(lcsc_id=part_number),
                api_version="6.4.19.5"
            )
            
            # Get component info
            component_info = await self.get_component_info(part_number)
            result = component_info.get("result", {})
            
            if not result:
                return DetailsEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="No component details found"
                )
            
            # Extract details from LCSC response structure
            specifications = []
            
            # Look for detailed component parameters in dataStr.head.c_para
            manufacturer = None
            manufacturer_part_number = None
            package_type = None
            category = None
            
            # Extract from nested component parameters
            if "dataStr" in result and isinstance(result["dataStr"], dict):
                head = result["dataStr"].get("head", {})
                if isinstance(head, dict) and "c_para" in head:
                    c_para = head["c_para"]
                    if isinstance(c_para, dict):
                        manufacturer = c_para.get("Manufacturer")
                        manufacturer_part_number = c_para.get("Manufacturer Part")
                        package_type = c_para.get("package")
                        category = c_para.get("JLCPCB Part Class")
                        
                        # Convert c_para to specifications
                        for key, value in c_para.items():
                            if value and str(value).strip() and key not in ["pre", "name", "nameAlias"]:
                                specifications.append(SpecificationAttribute(
                                    name=str(key),
                                    value=str(value)
                                ))
            
            # Extract category from tags if available
            if not category and "tags" in result and isinstance(result["tags"], list):
                if result["tags"]:
                    category = result["tags"][0]  # Use first tag as category
            
            return DetailsEnrichmentResponse(
                success=True,
                status="success",
                source=source,
                part_number=part_number,
                manufacturer=manufacturer,
                manufacturer_part_number=manufacturer_part_number,
                product_description=result.get("title") or result.get("description"),
                detailed_description=result.get("description"),
                category=category,
                subcategory=None,
                package_type=package_type,
                series=None,
                specifications=specifications,
                rohs_compliant=None
            )
                
        except Exception as e:
            self.logger.error(f"Error enriching details for {part_number}: {e}")
            return DetailsEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="LCSC"),
                part_number=part_number,
                error_message=str(e)
            )
    
    async def enrich_part_pricing(self, part_number: str) -> PricingEnrichmentResponse:
        """
        Enrich part with pricing information using standardized schema
        
        Args:
            part_number: LCSC part number (e.g., "C1000")
            
        Returns:
            PricingEnrichmentResponse with validated structure
        """
        try:
            self.logger.info(f"Enriching pricing for LCSC part: {part_number}")
            
            source = EnrichmentSource(
                supplier="LCSC",
                api_endpoint=self.COMPONENT_INFO_URL.format(lcsc_id=part_number),
                api_version="6.4.19.5"
            )
            
            # Get component info
            component_info = await self.get_component_info(part_number)
            result = component_info.get("result", {})
            
            if not result:
                return PricingEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="No pricing information found"
                )
            
            # Extract pricing information from LCSC API structure
            price_breaks = []
            unit_price = None
            minimum_order_quantity = 1
            
            # Look for pricing in result.lcsc section
            if "lcsc" in result and isinstance(result["lcsc"], dict):
                lcsc_data = result["lcsc"]
                
                # Extract basic pricing info
                price = lcsc_data.get("price")
                min_qty = lcsc_data.get("min", 1)
                step_qty = lcsc_data.get("step", 1)
                
                if price and price > 0:
                    unit_price = float(price)
                    minimum_order_quantity = int(min_qty)
                    
                    # Create price break for minimum quantity
                    price_breaks.append(PriceBreak(
                        quantity=minimum_order_quantity,
                        unit_price=unit_price,
                        currency="USD",
                        price_type="list"
                    ))
            
            # Also check szlcsc section as backup
            if not price_breaks and "szlcsc" in result and isinstance(result["szlcsc"], dict):
                szlcsc_data = result["szlcsc"]
                
                price = szlcsc_data.get("price")
                min_qty = szlcsc_data.get("min", 1)
                
                if price and price > 0:
                    unit_price = float(price)
                    minimum_order_quantity = int(min_qty)
                    
                    price_breaks.append(PriceBreak(
                        quantity=minimum_order_quantity,
                        unit_price=unit_price,
                        currency="USD",
                        price_type="list"
                    ))
            
            if unit_price is not None or price_breaks:
                return PricingEnrichmentResponse(
                    success=True,
                    status="success",
                    source=source,
                    part_number=part_number,
                    unit_price=unit_price,
                    currency="USD",
                    price_breaks=price_breaks,
                    minimum_order_quantity=minimum_order_quantity,
                    price_source="lcsc_api"
                )
            else:
                return PricingEnrichmentResponse(
                    success=False,
                    status="failed",
                    source=source,
                    part_number=part_number,
                    error_message="No valid pricing information found"
                )
                
        except Exception as e:
            self.logger.error(f"Error enriching pricing for {part_number}: {e}")
            return PricingEnrichmentResponse(
                success=False,
                status="failed",
                source=EnrichmentSource(supplier="LCSC"),
                part_number=part_number,
                error_message=str(e)
            )