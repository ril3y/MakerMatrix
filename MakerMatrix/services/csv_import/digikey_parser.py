from typing import List, Dict, Any, Optional
from .base_parser import BaseCSVParser
import logging

logger = logging.getLogger(__name__)


class DigikeyParser(BaseCSVParser):
    """Parser for DigiKey order CSV files"""
    
    def __init__(self):
        super().__init__(
            parser_type="digikey",
            name="DigiKey",
            description="DigiKey order CSV files"
        )
    
    @property
    def required_columns(self) -> List[str]:
        return ["DigiKey Part #", "Manufacturer Part Number", "Description", "Quantity"]
    
    @property
    def sample_columns(self) -> List[str]:
        return [
            "Index", "DigiKey Part #", "Manufacturer Part Number", "Description", 
            "Customer Reference", "Quantity", "Backorder", "Unit Price", "Extended Price"
        ]
    
    @property
    def detection_patterns(self) -> List[str]:
        return ["DigiKey Part #", "DigiKey Part Number"]
    
    def parse_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Parse a DigiKey CSV row into standardized part data"""
        try:
            # Skip if this looks like a subtotal or empty row
            if self.should_skip_row(row):
                return None
            
            # Extract basic information
            supplier_part_number = self.clean_string(row.get('DigiKey Part #', ''))
            manufacturer_part_number = self.clean_string(row.get('Manufacturer Part Number', ''))
            description = self.clean_string(row.get('Description', ''))
            quantity = self.parse_quantity(row.get('Quantity', '0'))
            customer_reference = self.clean_string(row.get('Customer Reference', ''))
            
            # Skip if no part number
            if not supplier_part_number:
                return None
            
            # Extract pricing
            unit_price = self.parse_price(row.get('Unit Price', '0'))
            extended_price = self.parse_price(row.get('Extended Price', '0'))
            backorder = self.parse_quantity(row.get('Backorder', '0'))
            
            # Use manufacturer part number as name if available, otherwise use DigiKey part number
            part_name = manufacturer_part_number or supplier_part_number
            
            # Create standardized part data
            part_data = {
                'part_name': part_name,
                'part_number': manufacturer_part_number if manufacturer_part_number else supplier_part_number,
                'quantity': quantity,
                'supplier': 'DigiKey',
                'supplier_url': f"https://www.digikey.com/en/products/detail/{supplier_part_number}",
                'properties': {
                    'supplier_part_number': supplier_part_number,
                    'description': description,
                    'unit_price': unit_price,
                    'extended_price': extended_price,
                    'customer_reference': customer_reference,
                    'backorder': backorder,
                    'currency': 'USD',
                    'import_source': 'DigiKey CSV'
                }
            }
            
            # Add manufacturer part number to properties if different from main part number
            if manufacturer_part_number and manufacturer_part_number != part_data['part_number']:
                part_data['properties']['manufacturer_part_number'] = manufacturer_part_number
            
            return part_data
            
        except Exception as e:
            logger.error(f"Error parsing DigiKey row {row_num}: {e}")
            raise Exception(f"Failed to parse row: {str(e)}")