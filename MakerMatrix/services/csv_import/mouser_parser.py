from typing import List, Dict, Any, Optional
from .base_parser import BaseCSVParser
import logging

logger = logging.getLogger(__name__)


class MouserParser(BaseCSVParser):
    """Parser for Mouser order CSV files"""
    
    def __init__(self):
        super().__init__(
            parser_type="mouser",
            name="Mouser",
            description="Mouser order CSV files"
        )
    
    @property
    def required_columns(self) -> List[str]:
        return ["Mouser Part #", "Manufacturer Part Number", "Description", "Quantity"]
    
    @property
    def sample_columns(self) -> List[str]:
        return [
            "Mouser Part #", "Manufacturer Part Number", "Manufacturer", 
            "Description", "Quantity", "Unit Price", "Extended Price"
        ]
    
    @property
    def detection_patterns(self) -> List[str]:
        return ["Mouser Part #", "Mouser Part Number"]
    
    def parse_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Parse a Mouser CSV row into standardized part data"""
        try:
            # Skip if this looks like a subtotal or empty row
            if self.should_skip_row(row):
                return None
            
            # Extract basic information
            mouser_part_number = self.clean_string(row.get('Mouser Part #', ''))
            manufacturer_part_number = self.clean_string(row.get('Manufacturer Part Number', ''))
            manufacturer = self.clean_string(row.get('Manufacturer', ''))
            description = self.clean_string(row.get('Description', ''))
            quantity = self.parse_quantity(row.get('Quantity', '0'))
            
            # Skip if no part numbers
            if not mouser_part_number or not manufacturer_part_number:
                return None
            
            # Extract pricing
            unit_price = self.parse_price(row.get('Unit Price', '0'))
            extended_price = self.parse_price(row.get('Extended Price', '0'))
            
            # Create standardized part data
            part_data = {
                'part_name': manufacturer_part_number,
                'part_number': manufacturer_part_number,
                'quantity': quantity,
                'supplier': 'Mouser',
                'supplier_url': f"https://www.mouser.com/ProductDetail/{mouser_part_number}",
                'properties': {
                    'mouser_part_number': mouser_part_number,
                    'manufacturer': manufacturer,
                    'description': description,
                    'unit_price': unit_price,
                    'extended_price': extended_price,
                    'currency': 'USD',
                    'import_source': 'Mouser CSV'
                }
            }
            
            # Add general electronics category
            part_data['categories'] = ['Electronics']
            
            return part_data
            
        except Exception as e:
            logger.error(f"Error parsing Mouser row {row_num}: {e}")
            raise Exception(f"Failed to parse row: {str(e)}")