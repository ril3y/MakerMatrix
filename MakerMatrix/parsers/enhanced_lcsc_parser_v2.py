"""
Enhanced LCSC Parser with Dependency Injection

Refactored version of the LCSC parser that separates API logic from parsing logic
using dependency injection for better testability and maintainability.
"""

import re
import logging
from typing import Dict, Any, Optional

from MakerMatrix.lib.required_input import RequiredInput
from MakerMatrix.parts.parts import Part
from MakerMatrix.parsers.enhanced_parser import EnhancedParser, EnrichmentResult
from MakerMatrix.parsers.supplier_capabilities import CapabilityType
from MakerMatrix.clients.suppliers.lcsc_client import LCSCClient
from MakerMatrix.clients.base_client import BaseAPIClient

logger = logging.getLogger(__name__)


def get_nested_value(data, keys, default=""):
    """Safely extract a value from nested dictionaries."""
    for key in keys:
        data = data.get(key, {})
        if not data:
            return default
    return data if data != default else default


class EnhancedLcscParserV2(EnhancedParser):
    """
    Enhanced LCSC Parser with dependency injection
    
    This version separates API communication from data parsing, making it
    more testable and maintainable.
    """
    
    def __init__(self, api_client: Optional[BaseAPIClient] = None):
        """
        Initialize parser with dependency injection
        
        Args:
            api_client: API client for LCSC/EasyEDA (defaults to LCSCClient)
        """
        super().__init__(pattern=re.compile(r"(\w+):([^,']+)"), supplier_name="LCSC")
        
        # Use provided client or create default
        self.api_client = api_client or LCSCClient()
        
        # Part instance will be created when needed, avoiding abstract class instantiation
        self._part_config = {
            'categories': ['electronics'],
            'part_vendor': "LCSC",
            'part_type': "electronic component",
            'supplier': "LCSC"
        }
        
        # Define required inputs
        req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")
        self.required_inputs = [req_part_type, req_part_quantity]
        
        self.logger = logging.getLogger(f"{__name__}.EnhancedLcscParserV2")
    
    def matches(self, data):
        """Check if data matches LCSC pattern"""
        try:
            match_data = self.decode_json_data(data)
            return bool(self.pattern.search(match_data))
        except Exception as e:
            self.logger.error(f"Error matching LCSC data: {e}")
            return False
    
    # Capability-based enrichment implementations with separated API logic
    
    async def _fetch_datasheet_impl(self, part_number: str) -> EnrichmentResult:
        """
        Fetch datasheet URL from LCSC/EasyEDA API
        
        This method now uses the injected API client instead of direct API calls.
        """
        try:
            self.logger.info(f"Fetching datasheet for LCSC part: {part_number}")
            
            # Use the injected API client to get component data
            if isinstance(self.api_client, LCSCClient):
                component_data = await self.api_client.get_component_info(part_number.upper())
            else:
                # Fallback for generic API clients
                response = await self.api_client.get(f"api/products/{part_number.upper()}/components")
                if not response.success:
                    raise Exception(f"API request failed: {response.error_message}")
                component_data = response.data
            
            # Parse the response to extract datasheet URL
            datasheet_url = self._extract_datasheet_url(component_data, part_number)
            
            if datasheet_url:
                return EnrichmentResult(
                    CapabilityType.FETCH_DATASHEET,
                    success=True,
                    data={
                        "url": datasheet_url,
                        "source": "EasyEDA API",
                        "part_number": part_number,
                        "supplier": "LCSC"
                    }
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_DATASHEET,
                    success=False,
                    error="No datasheet URL found in LCSC/EasyEDA data"
                )
                
        except Exception as e:
            self.logger.error(f"Error fetching LCSC datasheet for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_DATASHEET,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_pricing_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch pricing information from LCSC"""
        try:
            self.logger.info(f"Fetching pricing for LCSC part: {part_number}")
            
            # Get component data via API client
            if isinstance(self.api_client, LCSCClient):
                component_data = await self.api_client.get_component_info(part_number.upper())
            else:
                response = await self.api_client.get(f"api/products/{part_number.upper()}/components")
                if not response.success:
                    raise Exception(f"API request failed: {response.error_message}")
                component_data = response.data
            
            # Parse pricing data
            pricing_data = self._extract_pricing_data(component_data, part_number)
            
            if pricing_data:
                return EnrichmentResult(
                    CapabilityType.FETCH_PRICING,
                    success=True,
                    data=pricing_data
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_PRICING,
                    success=False,
                    error="No pricing information found"
                )
                
        except Exception as e:
            self.logger.error(f"Error fetching LCSC pricing for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_PRICING,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_stock_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch stock information from LCSC"""
        try:
            self.logger.info(f"Fetching stock for LCSC part: {part_number}")
            
            # Get component data via API client
            if isinstance(self.api_client, LCSCClient):
                component_data = await self.api_client.get_component_info(part_number.upper())
            else:
                response = await self.api_client.get(f"api/products/{part_number.upper()}/components")
                if not response.success:
                    raise Exception(f"API request failed: {response.error_message}")
                component_data = response.data
            
            # Parse stock data
            stock_info = self._extract_stock_data(component_data, part_number)
            
            return EnrichmentResult(
                CapabilityType.FETCH_STOCK,
                success=True,
                data=stock_info
            )
                
        except Exception as e:
            self.logger.error(f"Error fetching LCSC stock for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_STOCK,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_image_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch component image from LCSC/EasyEDA"""
        try:
            self.logger.info(f"Fetching image for LCSC part: {part_number}")
            
            # Get component data via API client
            if isinstance(self.api_client, LCSCClient):
                component_data = await self.api_client.get_component_info(part_number.upper())
                # Also try direct image URL method
                image_url = await self.api_client.get_component_image_url(part_number.upper())
            else:
                response = await self.api_client.get(f"api/products/{part_number.upper()}/components")
                if not response.success:
                    raise Exception(f"API request failed: {response.error_message}")
                component_data = response.data
                image_url = self._extract_image_url(component_data, part_number)
            
            if image_url:
                return EnrichmentResult(
                    CapabilityType.FETCH_IMAGE,
                    success=True,
                    data={
                        "url": image_url,
                        "source": "EasyEDA API",
                        "part_number": part_number,
                        "supplier": "LCSC"
                    }
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_IMAGE,
                    success=False,
                    error="No image URL found in LCSC/EasyEDA data"
                )
                
        except Exception as e:
            self.logger.error(f"Error fetching LCSC image for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_IMAGE,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_specifications_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch detailed specifications from LCSC/EasyEDA"""
        try:
            self.logger.info(f"Fetching specifications for LCSC part: {part_number}")
            
            # Get component data via API client
            if isinstance(self.api_client, LCSCClient):
                component_data = await self.api_client.get_component_info(part_number.upper())
            else:
                response = await self.api_client.get(f"api/products/{part_number.upper()}/components")
                if not response.success:
                    raise Exception(f"API request failed: {response.error_message}")
                component_data = response.data
            
            # Parse specifications
            specifications = self._extract_specifications(component_data, part_number)
            
            if specifications:
                return EnrichmentResult(
                    CapabilityType.FETCH_SPECIFICATIONS,
                    success=True,
                    data=specifications
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_SPECIFICATIONS,
                    success=False,
                    error="No specifications found"
                )
                
        except Exception as e:
            self.logger.error(f"Error fetching LCSC specifications for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_SPECIFICATIONS,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    # Pure parsing methods (no API calls)
    
    def _extract_datasheet_url(self, component_data: Dict[str, Any], part_number: str) -> Optional[str]:
        """
        Extract datasheet URL from component data
        
        Pure parsing method that doesn't make API calls.
        """
        if not component_data:
            return None
        
        # Try multiple paths in the response structure
        datasheet_paths = [
            ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'],
            ['result', 'datasheet'],
            ['result', 'datasheet_url'],
            ['result', 'pdf_url'],
            ['datasheet'],
            ['datasheet_url']
        ]
        
        for path in datasheet_paths:
            url = get_nested_value(component_data, path)
            if url and isinstance(url, str) and url.startswith(('http://', 'https://')):
                self.logger.debug(f"Found datasheet URL for {part_number}: {url}")
                return url
        
        self.logger.debug(f"No datasheet URL found for {part_number}")
        return None
    
    def _extract_pricing_data(self, component_data: Dict[str, Any], part_number: str) -> Dict[str, Any]:
        """Extract pricing data from component response"""
        pricing_data = {
            'part_number': part_number,
            'supplier': 'LCSC',
            'last_updated': None
        }
        
        if not component_data:
            return pricing_data
        
        # Get product info
        product_info = component_data.get('result', {})
        
        # Get pricing from szlcsc section
        szlcsc_data = product_info.get('szlcsc', {})
        if szlcsc_data:
            pricing_data['stock'] = szlcsc_data.get('stock', 0)
            pricing_data['price'] = szlcsc_data.get('price')
            pricing_data['currency'] = 'USD'  # LCSC typically shows USD prices
            pricing_data['product_url'] = szlcsc_data.get('url', '')
        
        return pricing_data
    
    def _extract_stock_data(self, component_data: Dict[str, Any], part_number: str) -> Dict[str, Any]:
        """Extract stock data from component response"""
        stock_info = {
            'part_number': part_number,
            'supplier': 'LCSC',
            'last_updated': None,
            'stock_level': 0,
            'availability': 'unknown'
        }
        
        if not component_data:
            return stock_info
        
        szlcsc_data = component_data.get('result', {}).get('szlcsc', {})
        if szlcsc_data:
            stock_level = szlcsc_data.get('stock', 0)
            stock_info['stock_level'] = stock_level
            stock_info['availability'] = 'in_stock' if stock_level > 0 else 'out_of_stock'
        
        return stock_info
    
    def _extract_image_url(self, component_data: Dict[str, Any], part_number: str) -> Optional[str]:
        """Extract component image URL from response"""
        if not component_data:
            return None
        
        # Try multiple paths for image URL
        image_paths = [
            ['result', 'image'],
            ['result', 'image_url'],
            ['result', 'photo'],
            ['result', 'picture'],
            ['image'],
            ['image_url']
        ]
        
        for path in image_paths:
            url = get_nested_value(component_data, path)
            if url and isinstance(url, str) and url.startswith(('http://', 'https://')):
                self.logger.debug(f"Found image URL for {part_number}: {url}")
                return url
        
        self.logger.debug(f"No image URL found for {part_number}")
        return None
    
    def _extract_specifications(self, component_data: Dict[str, Any], part_number: str) -> Dict[str, Any]:
        """Extract technical specifications from component response"""
        if not component_data:
            return {}
        
        specifications = {}
        
        # Extract various specification fields from the response
        result = component_data.get('result', {})
        
        # Basic component information
        if 'title' in result:
            specifications['name'] = result['title']
        
        if 'description' in result:
            specifications['description'] = result['description']
        
        # Package information
        package_detail = result.get('packageDetail', {})
        if package_detail:
            data_str = package_detail.get('dataStr', {})
            if data_str:
                head = data_str.get('head', {})
                if head:
                    specifications.update(head)
        
        # LCSC specific data
        szlcsc_data = result.get('szlcsc', {})
        if szlcsc_data:
            # Add relevant fields from LCSC data
            for field in ['brand', 'model', 'description', 'package']:
                if field in szlcsc_data:
                    specifications[field] = szlcsc_data[field]
        
        # Add metadata
        specifications['part_number'] = part_number
        specifications['supplier'] = 'LCSC'
        specifications['source'] = 'EasyEDA API'
        
        return specifications
    
    # Implementation of abstract methods from base Parser class
    
    def parse(self, fields):
        """
        Parse QR code fields using pattern matching
        
        This method is required by the base Parser class for QR code parsing.
        """
        try:
            if not fields:
                return None
            
            # Convert fields to string if necessary
            if isinstance(fields, dict):
                fields_str = str(fields)
            elif isinstance(fields, list):
                fields_str = ' '.join(str(f) for f in fields)
            else:
                fields_str = str(fields)
            
            # Check if it matches LCSC pattern
            if self.matches(fields_str):
                self.logger.debug(f"LCSC pattern matched for: {fields_str}")
                
                # Extract part information
                match = self.pattern.search(fields_str)
                if match:
                    # This is basic parsing - enrichment happens through capability methods
                    part_data = {
                        'supplier': 'LCSC',
                        'raw_data': fields_str,
                        'pattern_match': match.groups()
                    }
                    return part_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing LCSC fields: {e}")
            return None
    
    def submit(self):
        """
        Implementation for data submission specific to LCSC Parser
        
        This method is required by the base Parser class.
        """
        # In the modular architecture, submission is handled by the task system
        # This method can be used for any final processing or cleanup
        self.logger.debug("LCSC parser submit called")
        pass