from typing import List, Dict, Any, Optional
from .base_parser import BaseCSVParser
import logging
import requests
import re
from MakerMatrix.services.easyeda_service import EasyedaApi
from MakerMatrix.parsers.enhanced_lcsc_parser_v2 import get_nested_value
from MakerMatrix.services.file_download_service import file_download_service

logger = logging.getLogger(__name__)


class LCSCParser(BaseCSVParser):
    """Parser for LCSC order CSV files with EasyEDA API enrichment"""
    
    def __init__(self, download_config=None):
        super().__init__(
            parser_type="lcsc",
            name="LCSC",
            description="LCSC order CSV files"
        )
        self.easyeda_api = EasyedaApi()
        self.download_config = download_config or {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False
        }
        self.enrich_only_mode = False  # Flag to control enrichment vs download behavior
    
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
                'supplier': self.get_supplier_name(),
                'supplier_url': f"https://www.lcsc.com/product-detail/{lcsc_part_number}.html",
                'additional_properties': {
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
                    'import_source': f'{self.get_supplier_name()} CSV'
                }
            }
            
            # Try to extract component type and value from description
            self._extract_component_info(part_data, description, package)
            
            # Store LCSC part number for later enrichment (don't do API calls during parsing)
            if lcsc_part_number:
                part_data['additional_properties']['lcsc_part_number'] = lcsc_part_number
                part_data['additional_properties']['needs_enrichment'] = True
                part_data['additional_properties']['enrichment_source'] = self.get_supplier_name()
                
                # Only do API enrichment during preview mode - NEVER during normal parsing
                if self.enrich_only_mode:
                    self._enrich_with_easyeda_data_preview_only(part_data, lcsc_part_number)
                # Note: Removed enrich_during_parsing option - enrichment is now always deferred to background
            
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
            part_data['additional_properties']['component_type'] = 'Resistor'
        elif any(keyword in desc_lower for keyword in ['capacitor', 'mlcc', 'ceramic capacitor', 'electrolytic']):
            categories.append('Capacitors')
            part_data['additional_properties']['component_type'] = 'Capacitor'
        elif any(keyword in desc_lower for keyword in ['inductor', 'power inductor']):
            categories.append('Inductors')
            part_data['additional_properties']['component_type'] = 'Inductor'
        elif any(keyword in desc_lower for keyword in ['diode', 'schottky', 'zener']):
            categories.append('Diodes')
            part_data['additional_properties']['component_type'] = 'Diode'
        elif any(keyword in desc_lower for keyword in ['led', 'light emitting']):
            categories.append('LEDs')
            part_data['additional_properties']['component_type'] = 'LED'
        elif any(keyword in desc_lower for keyword in ['connector', 'header', 'socket']):
            categories.append('Connectors')
            part_data['additional_properties']['component_type'] = 'Connector'
        elif any(keyword in desc_lower for keyword in ['crystal', 'oscillator']):
            categories.append('Crystals & Oscillators')
            part_data['additional_properties']['component_type'] = 'Crystal'
        elif any(keyword in desc_lower for keyword in ['microcontroller', 'mcu', 'processor']):
            categories.append('Microcontrollers')
            part_data['additional_properties']['component_type'] = 'Microcontroller'
        elif any(keyword in desc_lower for keyword in ['sensor', 'temperature', 'pressure']):
            categories.append('Sensors')
            part_data['additional_properties']['component_type'] = 'Sensor'
        elif any(keyword in desc_lower for keyword in ['module', 'wifi', 'bluetooth', 'gps']):
            categories.append('Modules')
            part_data['additional_properties']['component_type'] = 'Module'
        
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
                part_data['additional_properties']['component_value'] = match.group(1)
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
                    'supplier': self.get_supplier_name()
                }
            except ValueError:
                # Invalid date format
                logger.warning(f"Invalid date in LCSC filename: {date_str}")
                return None
        
        return None
    
    def _enrich_with_easyeda_data_preview_only(self, part_data: Dict[str, Any], lcsc_part_number: str):
        """Enrich part data with EasyEDA API information for preview - NO downloads"""
        try:
            logger.info(f"Preview enriching part data for LCSC part: {lcsc_part_number}")
            
            # Fetch data from EasyEDA API
            lcsc_data = self.easyeda_api.get_info_from_easyeda_api(lcsc_id=lcsc_part_number.upper())
            
            if not lcsc_data or not lcsc_data.get('result'):
                logger.warning(f"No enrichment data found for LCSC part: {lcsc_part_number}")
                return
            
            result = lcsc_data['result']
            
            # Add basic information without downloading files
            if result.get('SMT'):
                part_data['additional_properties']['mounting_type'] = 'SMT'
                if 'SMT Components' not in part_data.get('categories', []):
                    part_data.setdefault('categories', []).append('SMT Components')
            
            # Extract specifications
            if 'dataStr' in result and 'head' in result['dataStr'] and 'c_para' in result['dataStr']['head']:
                c_para = result['dataStr']['head']['c_para']
                
                # Extract parameters without downloading
                for key, value in c_para.items():
                    if value and str(value).strip():
                        snake_key = key.replace(' ', '_').replace('-', '_').lower()
                        part_data['additional_properties'][f'spec_{snake_key}'] = str(value).strip()
                
                # Component type detection
                component_prefix = c_para.get('pre', '')
                if component_prefix:
                    part_data['additional_properties']['component_prefix'] = component_prefix
            
            # Store URLs for later download during import
            datasheet_url = self._find_datasheet_url(lcsc_data, lcsc_part_number)
            if datasheet_url:
                part_data['additional_properties']['datasheet_url'] = datasheet_url
                part_data['additional_properties']['datasheet_available'] = True
            else:
                part_data['additional_properties']['datasheet_available'] = False
            
            # Add enrichment metadata for preview
            from datetime import datetime
            part_data['additional_properties']['easyeda_preview_enriched_at'] = datetime.utcnow().isoformat()
            part_data['additional_properties']['enrichment_source'] = 'EasyEDA API (Preview)'
            
        except Exception as e:
            logger.error(f"Error preview enriching part data for {lcsc_part_number}: {e}")
            part_data['additional_properties']['enrichment_error'] = str(e)
    
    def _find_datasheet_url(self, lcsc_data: Dict[str, Any], lcsc_part_number: str) -> Optional[str]:
        """Find datasheet URL without downloading"""
        try:
            result = lcsc_data.get('result', {})
            
            # Try multiple possible paths for datasheet URL
            datasheet_paths = [
                ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'],
                ['result', 'dataStr', 'head', 'c_para', 'link'],
                ['result', 'dataStr', 'head', 'c_para', 'datasheet'],
                ['result', 'dataStr', 'head', 'c_para', 'Datasheet'],
                ['result', 'dataStr', 'head', 'c_para', 'pdf'],
                ['result', 'dataStr', 'head', 'c_para', 'PDF']
            ]
            
            for path in datasheet_paths:
                potential_url = get_nested_value(lcsc_data, path)
                if potential_url and isinstance(potential_url, str) and ('http' in potential_url or 'https' in potential_url):
                    return potential_url
            
            # Check for URLs in c_para values
            if 'dataStr' in result and 'head' in result['dataStr'] and 'c_para' in result['dataStr']['head']:
                c_para = result['dataStr']['head']['c_para']
                for key, value in c_para.items():
                    if isinstance(value, str) and ('datasheet' in value.lower() or 'pdf' in value.lower()) and ('http' in value or 'https' in value):
                        return value
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding datasheet URL for {lcsc_part_number}: {e}")
            return None
    
    def _enrich_with_easyeda_data(self, part_data: Dict[str, Any], lcsc_part_number: str):
        """Enrich part data with information from EasyEDA API - dynamically extract all available parameters"""
        try:
            logger.info(f"Enriching part data for LCSC part: {lcsc_part_number}")
            
            # Fetch data from EasyEDA API
            lcsc_data = self.easyeda_api.get_info_from_easyeda_api(lcsc_id=lcsc_part_number.upper())
            
            if not lcsc_data or not lcsc_data.get('result'):
                logger.warning(f"No enrichment data found for LCSC part: {lcsc_part_number}")
                return
            
            result = lcsc_data['result']
            
            # Debug logging to understand API response structure
            logger.debug(f"API response structure for {lcsc_part_number}:")
            logger.debug(f"Top level keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Log packageDetail structure if it exists
            if 'packageDetail' in result:
                logger.debug(f"packageDetail keys: {list(result['packageDetail'].keys()) if isinstance(result['packageDetail'], dict) else 'Not a dict'}")
                if 'dataStr' in result['packageDetail']:
                    logger.debug(f"packageDetail.dataStr keys: {list(result['packageDetail']['dataStr'].keys()) if isinstance(result['packageDetail']['dataStr'], dict) else 'Not a dict'}")
            
            # Log dataStr structure at root level if it exists
            if 'dataStr' in result:
                logger.debug(f"dataStr keys: {list(result['dataStr'].keys()) if isinstance(result['dataStr'], dict) else 'Not a dict'}")
                if 'head' in result['dataStr']:
                    logger.debug(f"dataStr.head keys: {list(result['dataStr']['head'].keys()) if isinstance(result['dataStr']['head'], dict) else 'Not a dict'}")
                    if 'c_para' in result['dataStr']['head']:
                        c_para_keys = list(result['dataStr']['head']['c_para'].keys()) if isinstance(result['dataStr']['head']['c_para'], dict) else []
                        logger.debug(f"dataStr.head.c_para keys: {c_para_keys}")
                        # Log any keys that might contain URLs or datasheets
                        for key in c_para_keys:
                            if any(term in key.lower() for term in ['link', 'url', 'datasheet', 'pdf', 'doc']):
                                logger.debug(f"Potential datasheet key '{key}': {result['dataStr']['head']['c_para'][key]}")
            
            # Add SMT/SMD information if available
            if result.get('SMT'):
                part_data['additional_properties']['mounting_type'] = 'SMT'
                if 'SMT Components' not in part_data.get('categories', []):
                    part_data.setdefault('categories', []).append('SMT Components')
            
            # Dynamically extract ALL available component parameters from c_para
            if 'dataStr' in result and 'head' in result['dataStr'] and 'c_para' in result['dataStr']['head']:
                c_para = result['dataStr']['head']['c_para']
                
                # Extract all parameters dynamically, converting keys to snake_case
                for key, value in c_para.items():
                    if value and str(value).strip():  # Only add non-empty values
                        # Convert parameter names to snake_case and add prefix to avoid conflicts
                        snake_key = key.replace(' ', '_').replace('-', '_').lower()
                        part_data['additional_properties'][f'spec_{snake_key}'] = str(value).strip()
                
                # Special handling for component type detection
                component_prefix = c_para.get('pre', '')
                if component_prefix:
                    part_data['additional_properties']['component_prefix'] = component_prefix
                    
                    # Basic categorization based on prefix
                    if component_prefix.startswith('C'):
                        part_data['additional_properties']['component_type'] = 'Capacitor'
                        part_data.setdefault('categories', []).extend(['Electronics', 'Capacitors'])
                    elif component_prefix.startswith('R'):
                        part_data['additional_properties']['component_type'] = 'Resistor'
                        part_data.setdefault('categories', []).extend(['Electronics', 'Resistors'])
                    elif component_prefix.startswith('L'):
                        part_data['additional_properties']['component_type'] = 'Inductor'
                        part_data.setdefault('categories', []).extend(['Electronics', 'Inductors'])
                    elif component_prefix.startswith('D'):
                        part_data['additional_properties']['component_type'] = 'Diode'
                        part_data.setdefault('categories', []).extend(['Electronics', 'Diodes'])
            
            # Add URLs and documentation
            # Try multiple possible paths for datasheet URL
            datasheet_url = None
            datasheet_paths = [
                ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'],
                ['result', 'dataStr', 'head', 'c_para', 'link'],
                ['result', 'dataStr', 'head', 'c_para', 'datasheet'],
                ['result', 'dataStr', 'head', 'c_para', 'Datasheet'],
                ['result', 'dataStr', 'head', 'c_para', 'pdf'],
                ['result', 'dataStr', 'head', 'c_para', 'PDF']
            ]
            
            for path in datasheet_paths:
                potential_url = get_nested_value(lcsc_data, path)
                if potential_url and isinstance(potential_url, str) and ('http' in potential_url or 'https' in potential_url):
                    datasheet_url = potential_url
                    logger.debug(f"Found datasheet URL at path {' -> '.join(path)}: {datasheet_url}")
                    break
            
            # If we still don't have a datasheet URL, check all c_para values for URL-like strings
            if not datasheet_url and 'dataStr' in result and 'head' in result['dataStr'] and 'c_para' in result['dataStr']['head']:
                c_para = result['dataStr']['head']['c_para']
                for key, value in c_para.items():
                    if isinstance(value, str) and ('datasheet' in value.lower() or 'pdf' in value.lower()) and ('http' in value or 'https' in value):
                        datasheet_url = value
                        logger.debug(f"Found datasheet URL in c_para['{key}']: {datasheet_url}")
                        break
            
            # Also check packageDetail if we haven't found it yet
            if not datasheet_url and 'packageDetail' in result and 'dataStr' in result['packageDetail']:
                if 'head' in result['packageDetail']['dataStr'] and 'c_para' in result['packageDetail']['dataStr']['head']:
                    pkg_c_para = result['packageDetail']['dataStr']['head']['c_para']
                    for key, value in pkg_c_para.items():
                        if isinstance(value, str) and ('datasheet' in value.lower() or 'pdf' in value.lower()) and ('http' in value or 'https' in value):
                            datasheet_url = value
                            logger.debug(f"Found datasheet URL in packageDetail c_para['{key}']: {datasheet_url}")
                            break
            
            # If we found what looks like an LCSC product page URL, try to scrape the actual datasheet URL
            if datasheet_url and ('lcsc.com' in datasheet_url or 'szlcsc.com' in datasheet_url):
                scraped_datasheet_url = self._scrape_datasheet_from_lcsc_page(datasheet_url, lcsc_part_number)
                if scraped_datasheet_url:
                    part_data['additional_properties']['lcsc_product_page'] = datasheet_url
                    datasheet_url = scraped_datasheet_url
                    logger.debug(f"Scraped actual datasheet URL: {datasheet_url}")
                else:
                    # If scraping failed, don't use the product page URL as datasheet URL
                    logger.warning(f"Failed to scrape datasheet from LCSC page, not using product URL as datasheet")
                    datasheet_url = None
            
            if datasheet_url:
                part_data['additional_properties']['datasheet_url'] = datasheet_url
                
                # Download datasheet if enabled - temporarily disabled to fix blocking issue
                if self.download_config.get('download_datasheets', False):  # Changed to False
                    try:
                        self._download_datasheet(part_data, datasheet_url, lcsc_part_number)
                    except Exception as e:
                        logger.warning(f"Datasheet download failed for {lcsc_part_number}: {e}")
                        part_data['additional_properties']['datasheet_download_error'] = str(e)
            else:
                logger.warning(f"No datasheet URL found for LCSC part: {lcsc_part_number}")
                part_data['additional_properties']['datasheet_url_not_found'] = True
            
            lcsc_url = get_nested_value(lcsc_data, ['result', 'szlcsc', 'url'])
            if lcsc_url:
                part_data['additional_properties']['lcsc_product_url'] = lcsc_url
            
            # Look for component image if enabled - temporarily disabled to fix blocking issue
            if self.download_config.get('download_images', False):  # Changed to False
                try:
                    self._download_component_image(part_data, lcsc_data, lcsc_part_number)
                except Exception as e:
                    logger.warning(f"Image download failed for {lcsc_part_number}: {e}")
                    part_data['additional_properties']['image_download_error'] = str(e)
            
            # Apply component-specific intelligent extraction
            self._apply_component_specific_extraction(part_data, c_para)
            
            # Add enrichment metadata
            from datetime import datetime
            part_data['additional_properties']['easyeda_enriched_at'] = datetime.utcnow().isoformat()
            part_data['additional_properties']['enrichment_source'] = 'EasyEDA API'
            
            # Count non-empty properties added
            enriched_count = len([k for k, v in part_data['additional_properties'].items() if k.startswith('spec_') and v])
            logger.info(f"Successfully enriched part {lcsc_part_number} with {enriched_count} specifications")
            
        except Exception as e:
            logger.error(f"Error enriching part data for {lcsc_part_number}: {e}")
            # Don't fail the import if enrichment fails, just log the error
            part_data['additional_properties']['enrichment_error'] = str(e)
            from datetime import datetime
            part_data['additional_properties']['enrichment_attempted_at'] = datetime.utcnow().isoformat()
    
    def _apply_component_specific_extraction(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Apply intelligent extraction based on component type"""
        component_type = part_data['additional_properties'].get('component_type', '').lower()
        
        # Resistor-specific extraction
        if component_type == 'resistor':
            self._extract_resistor_properties(part_data, c_para)
        
        # Capacitor-specific extraction  
        elif component_type == 'capacitor':
            self._extract_capacitor_properties(part_data, c_para)
        
        # Inductor-specific extraction
        elif component_type == 'inductor':
            self._extract_inductor_properties(part_data, c_para)
        
        # Diode-specific extraction
        elif component_type == 'diode':
            self._extract_diode_properties(part_data, c_para)
        
        # IC/Microcontroller-specific extraction
        elif any(term in component_type for term in ['microcontroller', 'processor', 'ic']):
            self._extract_ic_properties(part_data, c_para)
        
        # Apply AI-powered suggestions for additional categorization
        self._apply_ai_suggestions(part_data, c_para)
    
    def _extract_resistor_properties(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Extract resistor-specific properties with intelligent mapping"""
        resistor_mappings = {
            'resistance': ['Resistance', 'Value', 'Ohm', 'Ω'],
            'power_rating': ['Power', 'Power Rating', 'Wattage', 'Max Power'],
            'tolerance': ['Tolerance', 'Precision'],
            'temperature_coefficient': ['Temperature Coefficient', 'Temp Coeff', 'TCR'],
            'package_type': ['Package', 'Case', 'Footprint'],
            'composition': ['Composition', 'Type', 'Technology'],
            'voltage_rating': ['Voltage', 'Max Voltage', 'Working Voltage']
        }
        
        self._apply_property_mappings(part_data, c_para, resistor_mappings, 'resistor')
        
        # Additional resistor categories
        resistance_value = part_data['additional_properties'].get('resistance', '')
        if 'precision' in str(part_data['additional_properties'].get('tolerance', '')).lower():
            part_data.setdefault('categories', []).append('Precision Resistors')
        if any(term in resistance_value.lower() for term in ['meg', 'mω', 'gω']):
            part_data.setdefault('categories', []).append('High Value Resistors')
    
    def _extract_capacitor_properties(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Extract capacitor-specific properties"""
        capacitor_mappings = {
            'capacitance': ['Capacitance', 'Value', 'Cap', 'F'],
            'voltage_rating': ['Voltage Rating', 'Voltage', 'Working Voltage', 'Max Voltage'],
            'tolerance': ['Tolerance', 'Precision'],
            'temperature_coefficient': ['Temperature Coefficient', 'Temp Coeff', 'TC'],
            'dielectric': ['Dielectric', 'Material', 'Type'],
            'package_type': ['Package', 'Case', 'Footprint'],
            'esr': ['ESR', 'Equivalent Series Resistance'],
            'ripple_current': ['Ripple Current', 'Max Ripple'],
            'operating_temperature': ['Operating Temperature', 'Temp Range']
        }
        
        self._apply_property_mappings(part_data, c_para, capacitor_mappings, 'capacitor')
        
        # Specialized capacitor categories
        dielectric = str(part_data['additional_properties'].get('dielectric', '')).upper()
        if 'X7R' in dielectric or 'X5R' in dielectric:
            part_data.setdefault('categories', []).append('MLCC')
        elif 'TANT' in dielectric or 'TANTALUM' in dielectric:
            part_data.setdefault('categories', []).append('Tantalum Capacitors')
        elif 'ELECT' in dielectric:
            part_data.setdefault('categories', []).append('Electrolytic Capacitors')
    
    def _extract_inductor_properties(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Extract inductor-specific properties"""
        inductor_mappings = {
            'inductance': ['Inductance', 'Value', 'L', 'H'],
            'current_rating': ['Current Rating', 'Current', 'Max Current', 'IDC'],
            'dc_resistance': ['DC Resistance', 'DCR', 'Resistance'],
            'saturation_current': ['Saturation Current', 'Isat'],
            'tolerance': ['Tolerance', 'Precision'],
            'package_type': ['Package', 'Case', 'Footprint'],
            'shielding': ['Shielding', 'Shielded', 'Unshielded']
        }
        
        self._apply_property_mappings(part_data, c_para, inductor_mappings, 'inductor')
    
    def _extract_diode_properties(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Extract diode-specific properties"""
        diode_mappings = {
            'forward_voltage': ['Forward Voltage', 'Vf', 'Voltage Drop'],
            'current_rating': ['Current Rating', 'Current', 'Max Current', 'If'],
            'reverse_voltage': ['Reverse Voltage', 'PIV', 'Breakdown Voltage'],
            'package_type': ['Package', 'Case', 'Footprint'],
            'diode_type': ['Type', 'Diode Type'],
            'recovery_time': ['Recovery Time', 'Trr'],
            'capacitance': ['Capacitance', 'Junction Capacitance']
        }
        
        self._apply_property_mappings(part_data, c_para, diode_mappings, 'diode')
    
    def _extract_ic_properties(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Extract IC/microcontroller-specific properties"""
        ic_mappings = {
            'supply_voltage': ['Supply Voltage', 'VCC', 'VDD', 'Operating Voltage'],
            'current_consumption': ['Current Consumption', 'Supply Current', 'ICC'],
            'package_type': ['Package', 'Case', 'Footprint'],
            'pin_count': ['Pin Count', 'Pins'],
            'operating_temperature': ['Operating Temperature', 'Temp Range'],
            'processor_core': ['Core', 'Processor Core', 'Architecture'],
            'flash_memory': ['Flash', 'Flash Memory', 'Program Memory'],
            'ram_memory': ['RAM', 'SRAM', 'Data Memory'],
            'clock_speed': ['Clock Speed', 'Max Frequency', 'Clock']
        }
        
        self._apply_property_mappings(part_data, c_para, ic_mappings, 'ic')
    
    def _apply_property_mappings(self, part_data: Dict[str, Any], c_para: Dict[str, Any], mappings: Dict[str, List[str]], component_type: str):
        """Apply property mappings with fuzzy matching"""
        for std_property, possible_keys in mappings.items():
            for key in possible_keys:
                # Try exact match first
                if key in c_para and c_para[key]:
                    part_data['additional_properties'][f'{component_type}_{std_property}'] = str(c_para[key]).strip()
                    break
                
                # Try case-insensitive match
                for c_key, c_value in c_para.items():
                    if key.lower() in c_key.lower() and c_value:
                        part_data['additional_properties'][f'{component_type}_{std_property}'] = str(c_value).strip()
                        break
    
    def _apply_ai_suggestions(self, part_data: Dict[str, Any], c_para: Dict[str, Any]):
        """Use AI to suggest additional categorization and properties"""
        try:
            # Prepare context for AI
            component_info = {
                'part_name': part_data.get('part_name', ''),
                'description': part_data.get('description', ''),
                'manufacturer': part_data['additional_properties'].get('spec_manufacturer', ''),
                'component_type': part_data['additional_properties'].get('component_type', ''),
                'key_specs': {k: v for k, v in c_para.items() if v and len(str(v).strip()) > 0}
            }
            
            # Create AI prompt for suggestions
            ai_prompt = f"""
            Analyze this electronic component and suggest additional categories and insights:
            
            Component: {component_info['part_name']}
            Type: {component_info['component_type']}
            Manufacturer: {component_info['manufacturer']}
            Description: {component_info['description']}
            
            Key Specifications:
            {'; '.join([f'{k}: {v}' for k, v in component_info['key_specs'].items()])}
            
            Please suggest:
            1. Additional specific categories (e.g., "High Frequency", "Automotive Grade", "Low ESR")
            2. Application areas (e.g., "Power Supply", "RF Applications", "Audio")
            3. Any notable characteristics based on the specs
            
            Respond with a JSON object containing 'categories' and 'applications' arrays, and 'characteristics' string.
            """
            
            # Store AI suggestion request for potential future processing
            part_data['additional_properties']['ai_suggestion_prompt'] = ai_prompt
            part_data['additional_properties']['ai_suggestion_needed'] = True
            
            # TODO: Integrate with actual AI service when ready
            # For now, apply some rule-based intelligence
            self._apply_rule_based_intelligence(part_data, component_info)
            
        except Exception as e:
            logger.warning(f"Error applying AI suggestions: {e}")
    
    def _apply_rule_based_intelligence(self, part_data: Dict[str, Any], component_info: Dict[str, Any]):
        """Apply rule-based intelligence as fallback for AI suggestions"""
        specs = component_info['key_specs']
        
        # High frequency components
        if any('mhz' in str(v).lower() or 'ghz' in str(v).lower() for v in specs.values()):
            part_data.setdefault('categories', []).append('High Frequency')
        
        # Automotive grade detection
        if any('automotive' in str(v).lower() or 'aec' in str(v).lower() for v in specs.values()):
            part_data.setdefault('categories', []).append('Automotive Grade')
        
        # Low power detection
        if any('low power' in str(v).lower() or 'ultra low' in str(v).lower() for v in specs.values()):
            part_data.setdefault('categories', []).append('Low Power')
        
        # High precision detection
        if any('precision' in str(v).lower() or '0.1%' in str(v) or '±0.' in str(v) for v in specs.values()):
            part_data.setdefault('categories', []).append('High Precision')
        
        # Surface mount vs through-hole
        if any(term in str(specs).lower() for term in ['smd', 'smt', 'surface mount']):
            part_data.setdefault('categories', []).append('Surface Mount')
        elif any(term in str(specs).lower() for term in ['through hole', 'th', 'dip']):
            part_data.setdefault('categories', []).append('Through Hole')
    
    def _scrape_image_from_lcsc_page(self, lcsc_part_number: str) -> Optional[str]:
        """Scrape the actual image URL from the LCSC product page"""
        try:
            # Construct LCSC product page URL
            lcsc_page_url = f"https://www.lcsc.com/product-detail/{lcsc_part_number}.html"
            
            logger.debug(f"Scraping image from LCSC page: {lcsc_page_url}")
            
            response = requests.get(lcsc_page_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()
            
            # Look for image URLs in the HTML
            # Common patterns for LCSC product images
            image_patterns = [
                r'<img[^>]+src=["\']([^"\']*product[^"\']*\.(?:jpg|jpeg|png|gif))["\']',
                r'<img[^>]+data-src=["\']([^"\']*product[^"\']*\.(?:jpg|jpeg|png|gif))["\']',
                r'<img[^>]+data-original=["\']([^"\']*product[^"\']*\.(?:jpg|jpeg|png|gif))["\']',
                r'"image":\s*"([^"]*\.(?:jpg|jpeg|png|gif))"',
                r'"productImage":\s*"([^"]*\.(?:jpg|jpeg|png|gif))"',
                # Look for LCSC-specific image domains
                r'["\']([^"\']*(?:wmsc|static|atta)\.(?:lcsc|szlcsc)\.com[^"\']*\.(?:jpg|jpeg|png|gif))["\']'
            ]
            
            for pattern in image_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for match in matches:
                    # Clean up the URL
                    image_url = match.strip()
                    
                    # Make sure it's a complete URL
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = 'https://www.lcsc.com' + image_url
                    elif not image_url.startswith('http'):
                        continue
                    
                    # Avoid thumbnails and small images, prefer product images
                    if any(term in image_url.lower() for term in ['thumb', 'small', 'mini', 'icon']) and 'product' not in image_url.lower():
                        continue
                    
                    logger.debug(f"Found potential image URL: {image_url}")
                    return image_url
            
            logger.warning(f"No image URLs found in LCSC page for {lcsc_part_number}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to scrape image from LCSC page for {lcsc_part_number}: {e}")
            return None

    def _scrape_datasheet_from_lcsc_page(self, lcsc_page_url: str, lcsc_part_number: str) -> Optional[str]:
        """Scrape the actual datasheet PDF URL from an LCSC product page"""
        try:
            logger.debug(f"Scraping datasheet URL from LCSC page: {lcsc_page_url}")
            
            # Set up headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Fetch the LCSC product page
            response = requests.get(lcsc_page_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            html_content = response.text
            
            # Look for datasheet URLs in the HTML
            # Pattern 1: Direct PDF links
            pdf_patterns = [
                r'href="([^"]*\.pdf[^"]*)"',  # Any href with .pdf
                r"href='([^']*\.pdf[^']*)'",  # Single quotes version
                r'https://[^"\s]*\.pdf[^"\s]*',  # Direct PDF URLs
                r'https://static\.lcsc\.com/[^"\s]*\.pdf[^"\s]*',  # LCSC static PDF URLs
            ]
            
            datasheet_urls = []
            for pattern in pdf_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, str) and match not in datasheet_urls:
                        datasheet_urls.append(match)
            
            # Pattern 2: Look for the specific pattern mentioned in the user's HTML snippet
            # <a target="_blank" href="https://www.lcsc.com/datasheet/..." title="..." class="v2-a d-inline-flex"
            datasheet_link_pattern = r'<a[^>]*href="(https://www\.lcsc\.com/datasheet/[^"]*\.pdf[^"]*)"[^>]*title="[^"]*[Dd]atasheet[^"]*"'
            datasheet_matches = re.findall(datasheet_link_pattern, html_content, re.IGNORECASE)
            for match in datasheet_matches:
                if match not in datasheet_urls:
                    datasheet_urls.append(match)
            
            # Pattern 3: Look for any LCSC datasheet URLs
            lcsc_datasheet_pattern = r'https://www\.lcsc\.com/datasheet/[^"\s]*\.pdf[^"\s]*'
            lcsc_matches = re.findall(lcsc_datasheet_pattern, html_content, re.IGNORECASE)
            for match in lcsc_matches:
                if match not in datasheet_urls:
                    datasheet_urls.append(match)
            
            # Pattern 4: Look for static.lcsc.com URLs
            static_pattern = r'https://static\.lcsc\.com/[^"\s]*\.pdf[^"\s]*'
            static_matches = re.findall(static_pattern, html_content, re.IGNORECASE)
            for match in static_matches:
                if match not in datasheet_urls:
                    datasheet_urls.append(match)
            
            # Filter out common false positives and clean URLs
            valid_datasheet_urls = []
            for url in datasheet_urls:
                # Clean up the URL (remove HTML entities, etc.)
                url = url.strip().rstrip('",')
                
                # Decode HTML entities
                import html
                url = html.unescape(url)
                
                # Skip if it's not actually a PDF URL
                if not url.lower().endswith('.pdf') and '.pdf' not in url.lower():
                    continue
                
                # Skip if it's a generic/template URL
                if any(template in url.lower() for template in ['example', 'template', 'placeholder']):
                    continue
                
                # Ensure it's a proper HTTP/HTTPS URL
                if not url.startswith(('http://', 'https://')):
                    continue
                
                valid_datasheet_urls.append(url)
            
            if valid_datasheet_urls:
                # Return the first valid datasheet URL
                datasheet_url = valid_datasheet_urls[0]
                logger.info(f"Found datasheet URL for {lcsc_part_number}: {datasheet_url}")
                return datasheet_url
            else:
                logger.warning(f"No datasheet URL found in LCSC page for {lcsc_part_number}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching LCSC page for {lcsc_part_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping datasheet URL for {lcsc_part_number}: {e}")
            return None
    
    def _download_datasheet(self, part_data: Dict[str, Any], datasheet_url: str, lcsc_part_number: str):
        """Download datasheet and add file info to part data for database storage"""
        try:
            import uuid
            from MakerMatrix.services.file_download_service import FileDownloadService
            part_number = part_data.get('part_number', lcsc_part_number)
            
            # Generate UUID for the datasheet file
            file_uuid = str(uuid.uuid4())
            
            # Create file download service with current config
            download_service = FileDownloadService(download_config=self.download_config)
            
            # Download datasheet
            download_result = download_service.download_datasheet(
                url=datasheet_url,
                part_number=part_number,
                supplier=self.get_supplier_name(),
                file_uuid=file_uuid
            )
            
            if download_result:
                # Create datasheet information for the database
                datasheet_info = {
                    'file_uuid': download_result['file_uuid'],
                    'original_filename': download_result['original_filename'],
                    'file_extension': download_result['extension'],
                    'file_size': download_result['size'],
                    'source_url': datasheet_url,
                    'supplier': self.get_supplier_name(),
                    'manufacturer': part_data['additional_properties'].get('manufacturer', ''),
                    'title': f"Datasheet for {part_number}",
                    'description': f"Datasheet downloaded from LCSC for part {lcsc_part_number}",
                    'is_downloaded': True,
                    'download_error': None
                }
                
                # Store datasheet info in part data for later database insertion
                if 'datasheets' not in part_data:
                    part_data['datasheets'] = []
                part_data['datasheets'].append(datasheet_info)
                
                # Also add to additional properties for backward compatibility
                part_data['additional_properties']['datasheet_filename'] = download_result['filename']
                part_data['additional_properties']['datasheet_file_uuid'] = download_result['file_uuid']
                part_data['additional_properties']['datasheet_file_path'] = download_result['file_path']
                part_data['additional_properties']['datasheet_file_size'] = download_result['size']
                part_data['additional_properties']['datasheet_downloaded'] = True
                part_data['additional_properties']['datasheet_exists'] = download_result['exists']
                
                # Generate URL for serving the file
                datasheet_local_url = download_service.get_datasheet_url(download_result['filename'])
                part_data['additional_properties']['datasheet_local_url'] = datasheet_local_url
                
                logger.info(f"Datasheet download completed for {part_number}: {download_result['filename']} (UUID: {file_uuid})")
            else:
                # Store failed download attempt
                datasheet_info = {
                    'file_uuid': file_uuid,
                    'original_filename': None,
                    'file_extension': '.pdf',
                    'file_size': None,
                    'source_url': datasheet_url,
                    'supplier': self.get_supplier_name(),
                    'manufacturer': part_data['additional_properties'].get('manufacturer', ''),
                    'title': f"Datasheet for {part_number}",
                    'description': f"Failed to download datasheet from LCSC for part {lcsc_part_number}",
                    'is_downloaded': False,
                    'download_error': 'Download failed'
                }
                
                if 'datasheets' not in part_data:
                    part_data['datasheets'] = []
                part_data['datasheets'].append(datasheet_info)
                
                part_data['additional_properties']['datasheet_downloaded'] = False
                part_data['additional_properties']['datasheet_error'] = 'Download failed'
                
        except Exception as e:
            logger.error(f"Error downloading datasheet for {lcsc_part_number}: {e}")
            # Store error information
            try:
                import uuid
                file_uuid = str(uuid.uuid4())
                datasheet_info = {
                    'file_uuid': file_uuid,
                    'original_filename': None,
                    'file_extension': '.pdf',
                    'file_size': None,
                    'source_url': datasheet_url,
                    'supplier': self.get_supplier_name(),
                    'manufacturer': part_data['additional_properties'].get('manufacturer', ''),
                    'title': f"Datasheet for {part_data.get('part_number', lcsc_part_number)}",
                    'description': f"Error downloading datasheet from LCSC for part {lcsc_part_number}",
                    'is_downloaded': False,
                    'download_error': str(e)
                }
                
                if 'datasheets' not in part_data:
                    part_data['datasheets'] = []
                part_data['datasheets'].append(datasheet_info)
            except:
                pass  # If we can't even create the error record, just continue
                
            part_data['additional_properties']['datasheet_downloaded'] = False
            part_data['additional_properties']['datasheet_error'] = str(e)
    
    def _download_component_image(self, part_data: Dict[str, Any], lcsc_data: Dict[str, Any], lcsc_part_number: str):
        """Download component image and add file info to part data"""
        try:
            from MakerMatrix.services.file_download_service import FileDownloadService
            part_number = part_data.get('part_number', lcsc_part_number)
            
            # Create file download service with current config
            download_service = FileDownloadService(download_config=self.download_config)
            
            # Look for image URLs in the EasyEDA data
            image_urls = []
            
            # Try different locations where images might be stored
            if 'result' in lcsc_data:
                result = lcsc_data['result']
                
                # More comprehensive image URL extraction from EasyEDA API response
                def extract_image_urls_recursively(data, path=""):
                    """Recursively search for image URLs in nested data"""
                    found_urls = []
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            current_path = f"{path}.{key}" if path else key
                            
                            # Check if key suggests an image field
                            if any(term in key.lower() for term in ['image', 'photo', 'picture', 'img', 'pic', 'thumb', 'icon']):
                                if isinstance(value, str) and any(proto in value for proto in ['http://', 'https://']):
                                    found_urls.append(value)
                                    logger.debug(f"Found image URL at {current_path}: {value}")
                            
                            # Recursively search nested objects (limit depth to avoid infinite loops)
                            if isinstance(value, (dict, list)) and path.count('.') < 5:
                                found_urls.extend(extract_image_urls_recursively(value, current_path))
                    
                    elif isinstance(data, list):
                        for i, item in enumerate(data):
                            current_path = f"{path}[{i}]" if path else f"[{i}]"
                            if isinstance(item, (dict, list)) and path.count('.') < 5:
                                found_urls.extend(extract_image_urls_recursively(item, current_path))
                    
                    return found_urls
                
                # Extract image URLs from the entire API response
                extracted_urls = extract_image_urls_recursively(result, "result")
                image_urls.extend(extracted_urls)
                
                # Also check common specific locations
                # Check packageDetail for images
                if 'packageDetail' in result and 'dataStr' in result['packageDetail']:
                    package_data = result['packageDetail']['dataStr']
                    if 'head' in package_data and 'c_para' in package_data['head']:
                        c_para = package_data['head']['c_para']
                        
                        # Look for image-related fields
                        for key, value in c_para.items():
                            if 'image' in key.lower() or 'photo' in key.lower() or 'picture' in key.lower():
                                if isinstance(value, str) and ('http' in value or 'https' in value):
                                    if value not in image_urls:  # Avoid duplicates
                                        image_urls.append(value)
                
                # Check szlcsc section for product images
                if 'szlcsc' in result:
                    szlcsc_data = result['szlcsc']
                    for key, value in szlcsc_data.items():
                        if 'image' in key.lower() or 'photo' in key.lower():
                            if isinstance(value, str) and ('http' in value or 'https' in value):
                                if value not in image_urls:  # Avoid duplicates
                                    image_urls.append(value)
                
                # Try multiple LCSC image URL patterns
                # Note: Many of these URLs may not exist, but we try multiple patterns
                
                # Primary patterns that sometimes work
                image_patterns = [
                    f"https://wmsc.lcsc.com/ftpfile/product/{lcsc_part_number}.jpg",
                    f"https://wmsc.lcsc.com/ftpfile/product/pic/{lcsc_part_number}.jpg",
                    f"https://static.lcsc.com/ftpfile/product/{lcsc_part_number}.jpg",
                    f"https://wmsc.lcsc.com/ftpfile/product/{lcsc_part_number}.png",
                    f"https://wmsc.lcsc.com/ftpfile/product/images/{lcsc_part_number}.jpg",
                    f"https://atta.szlcsc.com/upload/public/pic/{lcsc_part_number[:2]}/{lcsc_part_number}.jpg"
                ]
                
                # Try to scrape image URL from LCSC product page if no URLs found in API
                if not image_urls:
                    logger.debug(f"No actual image URLs found in API data for {lcsc_part_number}, trying to scrape product page")
                    scraped_image_url = self._scrape_image_from_lcsc_page(lcsc_part_number)
                    if scraped_image_url:
                        image_urls.append(scraped_image_url)
                        logger.info(f"Scraped image URL from LCSC page for {lcsc_part_number}: {scraped_image_url}")
                
                # Add constructed URL patterns as final fallback
                if not image_urls:
                    image_urls.extend(image_patterns)
                    logger.debug(f"No image URLs found in API or scraped, trying constructed patterns for {lcsc_part_number}")
                else:
                    logger.debug(f"Found {len(image_urls)} image URLs for {lcsc_part_number}")
            
            # Log what we found
            if image_urls:
                logger.info(f"Found {len(image_urls)} image URL(s) to try for {lcsc_part_number}")
                for i, url in enumerate(image_urls):
                    logger.debug(f"  {i+1}. {url}")
            else:
                logger.warning(f"No image URLs found for {lcsc_part_number}")
                return
            
            # Try to download the first working image
            for i, image_url in enumerate(image_urls):
                logger.info(f"Attempting to download image {i+1}/{len(image_urls)} for {part_number} from {image_url}")
                
                download_result = download_service.download_image(
                    url=image_url,
                    part_number=part_number,
                    supplier='LCSC'
                )
                
                if download_result:
                    # Add file information to part data
                    part_data['additional_properties']['image_filename'] = download_result['filename']
                    part_data['additional_properties']['image_file_path'] = download_result['file_path']
                    part_data['additional_properties']['image_file_size'] = download_result['size']
                    part_data['additional_properties']['image_downloaded'] = True
                    part_data['additional_properties']['image_exists'] = download_result['exists']
                    part_data['additional_properties']['image_source_url'] = image_url
                    
                    # Generate URL for serving the file and update the part's image_url
                    image_local_url = download_service.get_image_url(download_result['image_uuid'])
                    part_data['additional_properties']['image_local_url'] = image_local_url
                    part_data['image_url'] = image_local_url  # Update the main image_url field
                    
                    logger.info(f"Successfully downloaded image for {part_number}: {download_result['filename']} from URL: {image_url}")
                    break  # Stop after first successful download
                else:
                    logger.debug(f"Failed to download from {image_url}, trying next URL...")
            else:
                # No image could be downloaded
                part_data['additional_properties']['image_downloaded'] = False
                part_data['additional_properties']['image_error'] = 'No working image URLs found'
                part_data['additional_properties']['image_urls_tried'] = image_urls
                logger.warning(f"Failed to download any images for part {part_number} from LCSC after trying {len(image_urls)} URLs")
                
        except Exception as e:
            logger.error(f"Error downloading image for {lcsc_part_number}: {e}")
            part_data['additional_properties']['image_downloaded'] = False
            part_data['additional_properties']['image_error'] = str(e)