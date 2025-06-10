from typing import List, Dict, Any, Optional
from .base_parser import BaseCSVParser
import logging

logger = logging.getLogger(__name__)


class LCSCParser(BaseCSVParser):
    """Parser for LCSC order CSV files"""
    
    def __init__(self):
        super().__init__(
            parser_type="lcsc",
            name="LCSC",
            description="LCSC order CSV files"
        )
    
    @property
    def required_columns(self) -> List[str]:
        return ["LCSC Part Number", "Manufacture Part Number", "Description", "Order Qty."]
    
    @property
    def sample_columns(self) -> List[str]:
        return [
            "LCSC Part Number", "Manufacture Part Number", "Manufacturer", "Customer NO.", 
            "Package", "Description", "RoHS", "Order Qty.", "Min\\Mult Order Qty.", 
            "Unit Price($)", "Order Price($)"
        ]
    
    @property
    def detection_patterns(self) -> List[str]:
        return ["LCSC Part Number", "Manufacture Part Number"]
    
    def parse_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Parse an LCSC CSV row into standardized part data"""
        try:
            # Skip if this looks like a subtotal or empty row
            if self.should_skip_row(row):
                return None
            
            # Extract basic information
            lcsc_part_number = self.clean_string(row.get('LCSC Part Number', ''))
            manufacturer_part_number = self.clean_string(row.get('Manufacture Part Number', ''))
            manufacturer = self.clean_string(row.get('Manufacturer', ''))
            description = self.clean_string(row.get('Description', ''))
            package = self.clean_string(row.get('Package', ''))
            quantity = self.parse_quantity(row.get('Order Qty.', '0'))
            customer_no = self.clean_string(row.get('Customer NO.', ''))
            rohs = self.clean_string(row.get('RoHS', ''))
            
            # Skip if no part numbers
            if not lcsc_part_number or not manufacturer_part_number:
                return None
            
            # Extract pricing
            unit_price = self.parse_price(row.get('Unit Price($)', '0'))
            order_price = self.parse_price(row.get('Order Price($)', '0'))
            min_order_qty = self.clean_string(row.get('Min\\Mult Order Qty.', ''))
            
            # Create standardized part data
            part_data = {
                'part_name': manufacturer_part_number,
                'part_number': manufacturer_part_number,
                'quantity': quantity,
                'supplier': 'LCSC',
                'supplier_url': f"https://www.lcsc.com/product-detail/{lcsc_part_number}.html",
                'properties': {
                    'lcsc_part_number': lcsc_part_number,
                    'manufacturer': manufacturer,
                    'description': description,
                    'package': package,
                    'unit_price': unit_price,
                    'order_price': order_price,
                    'customer_no': customer_no,
                    'rohs': rohs,
                    'min_order_qty': min_order_qty,
                    'currency': 'USD',
                    'import_source': 'LCSC CSV'
                }
            }
            
            # Try to extract component type and value from description
            self._extract_component_info(part_data, description, package)
            
            return part_data
            
        except Exception as e:
            logger.error(f"Error parsing LCSC row {row_num}: {e}")
            raise Exception(f"Failed to parse row: {str(e)}")
    
    def _extract_component_info(self, part_data: Dict[str, Any], description: str, package: str):
        """Extract component type and value from description"""
        if not description:
            return
        
        desc_lower = description.lower()
        
        # Try to identify component type and add categories
        categories = []
        
        if any(keyword in desc_lower for keyword in ['resistor', 'chip resistor', 'thick film resistor']):
            categories.append('Resistors')
            part_data['properties']['component_type'] = 'Resistor'
        elif any(keyword in desc_lower for keyword in ['capacitor', 'mlcc', 'ceramic capacitor', 'electrolytic']):
            categories.append('Capacitors')
            part_data['properties']['component_type'] = 'Capacitor'
        elif any(keyword in desc_lower for keyword in ['inductor', 'power inductor']):
            categories.append('Inductors')
            part_data['properties']['component_type'] = 'Inductor'
        elif any(keyword in desc_lower for keyword in ['diode', 'schottky', 'zener']):
            categories.append('Diodes')
            part_data['properties']['component_type'] = 'Diode'
        elif any(keyword in desc_lower for keyword in ['led', 'light emitting']):
            categories.append('LEDs')
            part_data['properties']['component_type'] = 'LED'
        elif any(keyword in desc_lower for keyword in ['connector', 'header', 'socket']):
            categories.append('Connectors')
            part_data['properties']['component_type'] = 'Connector'
        elif any(keyword in desc_lower for keyword in ['crystal', 'oscillator']):
            categories.append('Crystals & Oscillators')
            part_data['properties']['component_type'] = 'Crystal'
        elif any(keyword in desc_lower for keyword in ['microcontroller', 'mcu', 'processor']):
            categories.append('Microcontrollers')
            part_data['properties']['component_type'] = 'Microcontroller'
        elif any(keyword in desc_lower for keyword in ['sensor', 'temperature', 'pressure']):
            categories.append('Sensors')
            part_data['properties']['component_type'] = 'Sensor'
        elif any(keyword in desc_lower for keyword in ['module', 'wifi', 'bluetooth', 'gps']):
            categories.append('Modules')
            part_data['properties']['component_type'] = 'Module'
        
        # Add electronics as a general category
        categories.append('Electronics')
        part_data['categories'] = categories
        
        # Try to extract component value (for resistors, capacitors, etc.)
        import re
        
        # Look for value patterns like "10kΩ", "100nF", "4.7uH", etc.
        value_patterns = [
            r'(\d+\.?\d*[kKmMuUnNpP]?[FfHhΩΩ])',  # Standard component values
            r'(\d+\.?\d*[kKmMuUnNpP]?V)',           # Voltage ratings
            r'(\d+\.?\d*[kKmMuUnNpP]?A)',           # Current ratings
            r'(\d+\.?\d*MHz|KHz|Hz)',               # Frequency
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, description)
            if match:
                part_data['properties']['component_value'] = match.group(1)
                break
    
    def extract_order_info_from_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Extract order information from LCSC filename format: LCSC_Exported__YYYYMMDD_HHMMSS.csv"""
        import re
        
        # LCSC filename pattern: LCSC_Exported__20241222_232705.csv
        lcsc_match = re.match(r'LCSC_Exported__(\d{8})_(\d{6})\.csv$', filename, re.IGNORECASE)
        if lcsc_match:
            date_str, time_str = lcsc_match.groups()
            
            try:
                # Convert YYYYMMDD to YYYY-MM-DD
                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                
                # Validate the date format
                from datetime import datetime
                datetime.strptime(formatted_date, '%Y-%m-%d')
                
                return {
                    'order_date': formatted_date,
                    'order_number': time_str,  # Use the time as order number
                    'supplier': 'LCSC'
                }
            except ValueError:
                # Invalid date format
                logger.warning(f"Invalid date in LCSC filename: {date_str}")
                return None
        
        return None