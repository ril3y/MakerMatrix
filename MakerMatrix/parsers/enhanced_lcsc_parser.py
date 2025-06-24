"""
Enhanced LCSC Parser with capability-based enrichment and task integration.
"""

import re
import asyncio
import logging
from typing import Dict, Any, Optional

from MakerMatrix.lib.required_input import RequiredInput
from MakerMatrix.parts.parts import Part
from MakerMatrix.parsers.enhanced_parser import EnhancedParser, EnrichmentResult
from MakerMatrix.parsers.supplier_capabilities import CapabilityType
from MakerMatrix.services.easyeda_service import EasyedaApi


logger = logging.getLogger(__name__)


def get_nested_value(data, keys, default=""):
    """Safely extract a value from nested dictionaries."""
    for key in keys:
        data = data.get(key, {})
        if not data:
            return default
    return data if data != default else default


class EnhancedLcscParser(EnhancedParser):
    """Enhanced LCSC Parser with capability-based enrichment"""
    
    def __init__(self):
        super().__init__(pattern=re.compile(r"(\w+):([^,']+)"), supplier_name="LCSC")
        self.api = EasyedaApi()
        
        self.part = Part(
            categories=['electronics'],
            part_vendor="LCSC",
            part_type="electronic component",
            supplier="LCSC"
        )
        
        # Define required inputs
        req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")
        self.required_inputs = [req_part_type, req_part_quantity]
    
    def matches(self, data):
        """Check if data matches LCSC pattern"""
        try:
            match_data = self.decode_json_data(data)
            return bool(self.pattern.search(match_data))
        except Exception as e:
            logger.error(f"Error matching LCSC data: {e}")
            return False
    
    # Capability-based enrichment implementations
    
    async def _fetch_datasheet_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch datasheet URL from LCSC/EasyEDA API"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                datasheet_url = get_nested_value(
                    lcsc_data, ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link']
                )
                
                if datasheet_url:
                    return EnrichmentResult(
                        CapabilityType.FETCH_DATASHEET,
                        success=True,
                        data={
                            "url": datasheet_url,
                            "source": "EasyEDA API",
                            "part_number": part_number
                        }
                    )
                else:
                    return EnrichmentResult(
                        CapabilityType.FETCH_DATASHEET,
                        success=False,
                        error="No datasheet URL found in LCSC/EasyEDA data"
                    )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_DATASHEET,
                    success=False,
                    error="Part not found in LCSC/EasyEDA database"
                )
                
        except Exception as e:
            logger.error(f"Error fetching LCSC datasheet for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_DATASHEET,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_pricing_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch pricing information from LCSC"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                # Extract pricing data
                pricing_data = {}
                
                # Try to get pricing information from different locations in the API response
                product_info = lcsc_data.get('result', {})
                
                # Get stock and pricing from szlcsc section
                szlcsc_data = product_info.get('szlcsc', {})
                if szlcsc_data:
                    pricing_data['stock'] = szlcsc_data.get('stock', 0)
                    pricing_data['price'] = szlcsc_data.get('price')
                    pricing_data['currency'] = 'USD'  # LCSC typically shows USD prices
                
                # Get additional product URL
                pricing_data['product_url'] = szlcsc_data.get('url', '')
                
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
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_PRICING,
                    success=False,
                    error="Part not found in LCSC database"
                )
                
        except Exception as e:
            logger.error(f"Error fetching LCSC pricing for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_PRICING,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_stock_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch stock information from LCSC"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                stock_info = {}
                
                szlcsc_data = lcsc_data.get('result', {}).get('szlcsc', {})
                if szlcsc_data:
                    stock_info['stock_level'] = szlcsc_data.get('stock', 0)
                    stock_info['availability'] = 'in_stock' if stock_info['stock_level'] > 0 else 'out_of_stock'
                    stock_info['last_updated'] = None  # LCSC doesn't provide timestamp
                
                return EnrichmentResult(
                    CapabilityType.FETCH_STOCK,
                    success=True,
                    data=stock_info
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_STOCK,
                    success=False,
                    error="Part not found in LCSC database"
                )
                
        except Exception as e:
            logger.error(f"Error fetching LCSC stock for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_STOCK,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _fetch_specifications_impl(self, part_number: str) -> EnrichmentResult:
        """Fetch detailed specifications from LCSC/EasyEDA"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                result = lcsc_data.get('result', {})
                specs = {}
                
                # Extract component parameters
                c_para = get_nested_value(result, ['dataStr', 'head', 'c_para'])
                if c_para:
                    specs['value'] = c_para.get('Value', '')
                    specs['package'] = c_para.get('package', '')
                    specs['manufacturer'] = c_para.get('Manufacturer', '')
                    specs['tolerance'] = c_para.get('Tolerance', '')
                    specs['voltage_rating'] = c_para.get('Voltage', '')
                    specs['temperature_coefficient'] = c_para.get('Temperature Coefficient', '')
                
                # Determine component type from prefix
                component_prefix = c_para.get('pre', '') if c_para else ''
                if component_prefix.startswith('C?'):
                    specs['component_type'] = 'capacitor'
                elif component_prefix.startswith('R?'):
                    specs['component_type'] = 'resistor'
                elif component_prefix.startswith('L?'):
                    specs['component_type'] = 'inductor'
                elif component_prefix.startswith('D?'):
                    specs['component_type'] = 'diode'
                else:
                    specs['component_type'] = 'unknown'
                
                # Check if it's SMT
                if result.get('SMT'):
                    specs['mounting_type'] = 'SMT'
                else:
                    specs['mounting_type'] = 'through_hole'
                
                # Add LCSC specific data
                specs['lcsc_part_number'] = part_number
                specs['easyeda_available'] = True
                
                return EnrichmentResult(
                    CapabilityType.FETCH_SPECIFICATIONS,
                    success=True,
                    data=specs
                )
            else:
                return EnrichmentResult(
                    CapabilityType.FETCH_SPECIFICATIONS,
                    success=False,
                    error="Part not found in LCSC/EasyEDA database"
                )
                
        except Exception as e:
            logger.error(f"Error fetching LCSC specifications for {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.FETCH_SPECIFICATIONS,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _validate_part_number_impl(self, part_number: str) -> EnrichmentResult:
        """Validate LCSC part number"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                return EnrichmentResult(
                    CapabilityType.VALIDATE_PART_NUMBER,
                    success=True,
                    data={
                        "valid": True,
                        "part_number": part_number,
                        "supplier": "LCSC",
                        "found_in_database": True
                    }
                )
            else:
                return EnrichmentResult(
                    CapabilityType.VALIDATE_PART_NUMBER,
                    success=True,
                    data={
                        "valid": False,
                        "part_number": part_number,
                        "supplier": "LCSC",
                        "found_in_database": False
                    }
                )
                
        except Exception as e:
            logger.error(f"Error validating LCSC part number {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.VALIDATE_PART_NUMBER,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    async def _enrich_basic_info_impl(self, part_number: str) -> EnrichmentResult:
        """Perform basic enrichment for LCSC part"""
        try:
            lcsc_data = await asyncio.to_thread(
                self.api.get_info_from_easyeda_api, 
                lcsc_id=part_number.upper()
            )
            
            if lcsc_data and lcsc_data != {}:
                result = lcsc_data.get('result', {})
                basic_info = {}
                
                # Extract basic information
                c_para = get_nested_value(result, ['dataStr', 'head', 'c_para'])
                if c_para:
                    basic_info['manufacturer'] = c_para.get('Manufacturer', '')
                    basic_info['manufacturer_part_number'] = self.part.manufacturer_part_number or ''
                    basic_info['package'] = c_para.get('package', '')
                    basic_info['value'] = c_para.get('Value', '')
                
                # Create description from datasheet URL
                datasheet_url = get_nested_value(
                    result, ['packageDetail', 'dataStr', 'head', 'c_para', 'link']
                )
                if datasheet_url:
                    basic_info['description'] = datasheet_url.strip(
                        "https://lcsc.com/product-detail"
                    ).replace("-", ", ").rstrip(".html")
                    basic_info['datasheet_url'] = datasheet_url
                
                # Add LCSC URLs
                szlcsc_data = result.get('szlcsc', {})
                if szlcsc_data:
                    basic_info['product_url'] = szlcsc_data.get('url', '')
                
                # Set component categories
                basic_info['categories'] = ['electronics']
                
                # Check if SMT component
                if result.get('SMT'):
                    basic_info['categories'].append('SMT')
                
                # Determine component type
                component_prefix = c_para.get('pre', '') if c_para else ''
                if component_prefix.startswith('C?'):
                    basic_info['part_type'] = 'capacitor'
                    basic_info['categories'].append('capacitors')
                elif component_prefix.startswith('R?'):
                    basic_info['part_type'] = 'resistor'
                    basic_info['categories'].append('resistors')
                elif component_prefix.startswith('L?'):
                    basic_info['part_type'] = 'inductor'
                    basic_info['categories'].append('inductors')
                
                return EnrichmentResult(
                    CapabilityType.ENRICH_BASIC_INFO,
                    success=True,
                    data=basic_info
                )
            else:
                return EnrichmentResult(
                    CapabilityType.ENRICH_BASIC_INFO,
                    success=False,
                    error="Part not found in LCSC/EasyEDA database"
                )
                
        except Exception as e:
            logger.error(f"Error enriching basic info for LCSC part {part_number}: {e}")
            return EnrichmentResult(
                CapabilityType.ENRICH_BASIC_INFO,
                success=False,
                error=f"API error: {str(e)}"
            )
    
    # Legacy methods for backward compatibility
    
    def parse(self, json_data):
        """Legacy parse method"""
        try:
            decoded_data = self.decode_json_data(json_data)
            key_value_pairs = re.findall(r"(\w+):([^,']+)", decoded_data)
            data = {key: value for key, value in key_value_pairs}
            
            self.set_property("quantity", int(data.get('qty')))
            self.set_property('part_number', data.get('pc', '').lower())
            self.set_property('manufacturer_part_number', data.get('pm', '').lower())
            
        except Exception as e:
            logger.error(f'Error parsing LCSC data: {e}')
            return None
    
    def enrich(self):
        """Legacy enrich method - use async methods instead"""
        logger.warning("Using legacy enrich() method. Consider using async capability-based enrichment.")
        try:
            lcsc_data = self.api.get_info_from_easyeda_api(
                lcsc_id=self.part.part_number.upper()
            )
            if lcsc_data != {}:
                if lcsc_data['result']['SMT']:
                    self.part.add_category("SMT")
                
                self.set_property('part_name', f" {self.part.manufacturer_part_number}")
                
                # Set additional properties using helper function
                self.part.additional_properties['value'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Value'])
                
                self.part.additional_properties['package'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'package'])
                
                self.part.additional_properties['manufacturer'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Manufacturer'])
                
                self.part.additional_properties['datasheet_url'] = get_nested_value(
                    lcsc_data, ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'])
                
                self.part.additional_properties['url'] = get_nested_value(
                    lcsc_data, ['result', 'szlcsc', 'url'])
                
                # Determine component type and set properties
                component_prefix = get_nested_value(lcsc_data, ['result','dataStr','head','c_para','pre'])
                if component_prefix.startswith('C?'):
                    self.part_type = "capacitor"
                    self.part.additional_properties['value'] = get_nested_value(
                        lcsc_data, ['result','dataStr','head','c_para','Value']).lower()
                    self.part.additional_properties['package'] = get_nested_value(
                        lcsc_data, ['result','dataStr','head','c_para','package'])
                
                elif component_prefix.startswith('R?'):
                    self.part_type = "resistor"
                    self.part.additional_properties['value'] = get_nested_value(
                        lcsc_data, ['result','dataStr','head','c_para','Value']).lower()
                    self.part.additional_properties['package'] = get_nested_value(
                        lcsc_data, ['result','dataStr','head','c_para','package'])
                
                # Set description from datasheet URL
                if 'datasheet_url' in self.part.additional_properties and self.part.additional_properties['datasheet_url']:
                    description = self.part.additional_properties['datasheet_url'].strip(
                        "https://lcsc.com/product-detail").replace("-", ", ").rstrip(".html")
                    self.set_property('description', description)
                else:
                    self.set_property('description', "")
            else:
                # Part not found in LCSC, add required inputs
                self.add_required_input(field_name="part_type", data_type="string", 
                                      prompt="Enter the part type. IE: resistor, capacitor")
                self.add_required_input(field_name="package", data_type="string", 
                                      prompt="Enter the package type.")
                self.add_required_input(field_name="value", data_type="string", 
                                      prompt="Enter the component value.")
        
        except Exception as e:
            logger.error(f'Error enriching LCSC data: {e}')
            return None
    
    def submit(self):
        """Implementation for data submission specific to LcscParser"""
        pass


# Register the enhanced parser
from MakerMatrix.parsers.enhanced_parser import parser_registry
parser_registry.register_parser("LCSC", EnhancedLcscParser)