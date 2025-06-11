from typing import List, Dict, Any, Optional
from .base_parser import BaseCSVParser
import logging
import re

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
                'additional_properties': {
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
            
            # Add manufacturer part number to additional_properties if different from main part number
            if manufacturer_part_number and manufacturer_part_number != part_data['part_number']:
                part_data['additional_properties']['manufacturer_part_number'] = manufacturer_part_number
            
            # Apply DigiKey-specific enrichment
            self._enrich_digikey_part(part_data, description, supplier_part_number)
            
            return part_data
            
        except Exception as e:
            logger.error(f"Error parsing DigiKey row {row_num}: {e}")
            raise Exception(f"Failed to parse row: {str(e)}")
    
    def _enrich_digikey_part(self, part_data: Dict[str, Any], description: str, supplier_part_number: str):
        """Enrich DigiKey part data using description parsing and intelligent extraction"""
        try:
            logger.info(f"Enriching DigiKey part: {supplier_part_number}")
            
            # Extract component information from description
            self._extract_component_info_from_description(part_data, description)
            
            # Apply component-specific intelligent extraction
            self._apply_component_specific_extraction(part_data, description)
            
            # Add DigiKey-specific metadata
            from datetime import datetime
            part_data['additional_properties']['digikey_enriched_at'] = datetime.utcnow().isoformat()
            part_data['additional_properties']['enrichment_source'] = 'DigiKey Description Parsing'
            
            # Prepare for future DigiKey API integration
            part_data['additional_properties']['digikey_api_needed'] = True
            part_data['additional_properties']['digikey_part_number'] = supplier_part_number
            
            logger.info(f"Successfully enriched DigiKey part {supplier_part_number}")
            
        except Exception as e:
            logger.error(f"Error enriching DigiKey part {supplier_part_number}: {e}")
            part_data['additional_properties']['enrichment_error'] = str(e)
            from datetime import datetime
            part_data['additional_properties']['enrichment_attempted_at'] = datetime.utcnow().isoformat()
    
    def _extract_component_info_from_description(self, part_data: Dict[str, Any], description: str):
        """Extract component information from DigiKey description"""
        if not description:
            return
            
        desc_lower = description.lower()
        
        # Component type detection and categorization
        component_mappings = {
            'resistor': ['resistor', 'thick film', 'thin film', 'metal film', 'carbon film'],
            'capacitor': ['capacitor', 'cap', 'mlcc', 'ceramic', 'electrolytic', 'tantalum'],
            'inductor': ['inductor', 'choke', 'ferrite bead', 'power inductor'],
            'diode': ['diode', 'schottky', 'zener', 'tvs', 'rectifier'],
            'led': ['led', 'light emitting', 'indicator'],
            'transistor': ['transistor', 'mosfet', 'fet', 'bjt', 'igbt'],
            'connector': ['connector', 'header', 'socket', 'terminal', 'jack', 'plug'],
            'crystal': ['crystal', 'oscillator', 'resonator', 'xtal'],
            'ic': ['ic', 'microcontroller', 'processor', 'amplifier', 'regulator', 'driver'],
            'sensor': ['sensor', 'temperature', 'pressure', 'accelerometer', 'gyroscope'],
            'switch': ['switch', 'button', 'tactile', 'toggle', 'rocker'],
            'relay': ['relay', 'reed relay', 'solid state'],
            'fuse': ['fuse', 'ptc', 'circuit breaker'],
            'module': ['module', 'breakout', 'development board', 'eval board']
        }
        
        # Detect component type
        for component_type, keywords in component_mappings.items():
            if any(keyword in desc_lower for keyword in keywords):
                part_data['additional_properties']['component_type'] = component_type.title()
                part_data.setdefault('categories', []).extend(['Electronics', f'{component_type.title()}s'])
                break
        
        # Extract technical specifications using regex patterns
        self._extract_technical_specs(part_data, description)
        
        # Extract package information
        self._extract_package_info(part_data, description)
        
        # Extract manufacturer information
        self._extract_manufacturer_info(part_data, description)
    
    def _extract_technical_specs(self, part_data: Dict[str, Any], description: str):
        """Extract technical specifications from description using regex patterns"""
        
        # Common technical specification patterns
        spec_patterns = {
            'voltage': [
                r'(\d+\.?\d*)\s*v(?:olt)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*kv',
                r'(\d+\.?\d*)\s*mv'
            ],
            'current': [
                r'(\d+\.?\d*)\s*ma(?:mp)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*[aμ]a?(?:mp)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*ka(?:mp)?s?(?:\s|$)'
            ],
            'resistance': [
                r'(\d+\.?\d*)\s*[kkmgμ]?[ωΩ](?:hm)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*[kkmg]?ohm?s?(?:\s|$)'
            ],
            'capacitance': [
                r'(\d+\.?\d*)\s*[μnpkm]?f(?:arad)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*uf(?:\s|$)',
                r'(\d+\.?\d*)\s*pf(?:\s|$)'
            ],
            'inductance': [
                r'(\d+\.?\d*)\s*[μnmk]?h(?:enry)?(?:\s|$)',
                r'(\d+\.?\d*)\s*uh(?:\s|$)',
                r'(\d+\.?\d*)\s*nh(?:\s|$)'
            ],
            'frequency': [
                r'(\d+\.?\d*)\s*mhz(?:\s|$)',
                r'(\d+\.?\d*)\s*khz(?:\s|$)',
                r'(\d+\.?\d*)\s*ghz(?:\s|$)',
                r'(\d+\.?\d*)\s*hz(?:\s|$)'
            ],
            'power': [
                r'(\d+\.?\d*)\s*[mkμn]?w(?:att)?s?(?:\s|$)',
                r'(\d+\.?\d*)\s*mw(?:\s|$)',
                r'(\d+\.?\d*)\s*kw(?:\s|$)'
            ],
            'tolerance': [
                r'±\s*(\d+\.?\d*)\s*%',
                r'(\d+\.?\d*)\s*%\s*tol',
                r'tol\s*(\d+\.?\d*)\s*%'
            ],
            'temperature': [
                r'(-?\d+\.?\d*)\s*°?c(?:\s|$)',
                r'(-?\d+\.?\d*)\s*°?f(?:\s|$)',
                r'(-?\d+\.?\d*)\s*to\s*(-?\d+\.?\d*)\s*°?c'
            ]
        }
        
        desc_lower = description.lower()
        
        for spec_type, patterns in spec_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, desc_lower)
                if matches:
                    # Take the first match, handle tuple results from temperature ranges
                    value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    part_data['additional_properties'][f'spec_{spec_type}'] = value
                    break
    
    def _extract_package_info(self, part_data: Dict[str, Any], description: str):
        """Extract package/footprint information"""
        
        # Common package patterns
        package_patterns = [
            r'\b(sot-\d+)\b',
            r'\b(soic-?\d+)\b',
            r'\b(qfn-?\d+)\b',
            r'\b(bga-?\d+)\b',
            r'\b(dip-?\d+)\b',
            r'\b(smd)\b',
            r'\b(through\s+hole)\b',
            r'\b(\d{4})\b',  # 0603, 0805, etc.
            r'\b(to-\d+)\b',
            r'\b(tssop-?\d+)\b',
            r'\b(lqfp-?\d+)\b'
        ]
        
        desc_lower = description.lower()
        
        for pattern in package_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                package = match.group(1)
                part_data['additional_properties']['package'] = package.upper()
                
                # Add mounting type based on package
                if any(smd_term in package.lower() for smd_term in ['smd', 'sot', 'soic', 'qfn', 'bga', 'tssop', 'lqfp']) or package.isdigit():
                    part_data['additional_properties']['mounting_type'] = 'SMT'
                    part_data.setdefault('categories', []).append('Surface Mount')
                elif any(th_term in package.lower() for th_term in ['dip', 'through hole', 'to-']):
                    part_data['additional_properties']['mounting_type'] = 'Through Hole'
                    part_data.setdefault('categories', []).append('Through Hole')
                break
    
    def _extract_manufacturer_info(self, part_data: Dict[str, Any], description: str):
        """Extract manufacturer information from description"""
        
        # Common manufacturer names that might appear in descriptions
        manufacturers = [
            'texas instruments', 'ti', 'analog devices', 'adi', 'maxim', 'infineon',
            'stmicroelectronics', 'st micro', 'microchip', 'atmel', 'nxp', 'freescale',
            'linear technology', 'ltc', 'intersil', 'onsemi', 'vishay', 'murata',
            'tdk', 'samsung', 'yageo', 'panasonic', 'nichicon', 'kemet', 'avx',
            'bourns', 'coilcraft', 'würth', 'ferrite', 'johanson', 'epcos'
        ]
        
        desc_lower = description.lower()
        
        for manufacturer in manufacturers:
            if manufacturer in desc_lower:
                part_data['additional_properties']['detected_manufacturer'] = manufacturer.title()
                break
    
    def _apply_component_specific_extraction(self, part_data: Dict[str, Any], description: str):
        """Apply component-specific extraction rules"""
        component_type = part_data['additional_properties'].get('component_type', '').lower()
        desc_lower = description.lower()
        
        # Resistor-specific extraction
        if component_type == 'resistor':
            if 'precision' in desc_lower or 'low tol' in desc_lower:
                part_data.setdefault('categories', []).append('Precision Resistors')
            if 'high power' in desc_lower or 'power' in desc_lower:
                part_data.setdefault('categories', []).append('Power Resistors')
            if 'current sense' in desc_lower or 'sense' in desc_lower:
                part_data.setdefault('categories', []).append('Current Sense Resistors')
        
        # Capacitor-specific extraction
        elif component_type == 'capacitor':
            if 'low esr' in desc_lower:
                part_data.setdefault('categories', []).append('Low ESR Capacitors')
            if 'ceramic' in desc_lower or 'mlcc' in desc_lower:
                part_data.setdefault('categories', []).append('MLCC')
            elif 'electrolytic' in desc_lower:
                part_data.setdefault('categories', []).append('Electrolytic Capacitors')
            elif 'tantalum' in desc_lower:
                part_data.setdefault('categories', []).append('Tantalum Capacitors')
        
        # IC-specific extraction
        elif component_type == 'ic':
            if any(term in desc_lower for term in ['regulator', 'ldo', 'switching']):
                part_data.setdefault('categories', []).append('Voltage Regulators')
            elif any(term in desc_lower for term in ['amplifier', 'op amp', 'opamp']):
                part_data.setdefault('categories', []).append('Amplifiers')
            elif any(term in desc_lower for term in ['microcontroller', 'mcu', 'processor']):
                part_data.setdefault('categories', []).append('Microcontrollers')
        
        # Add general quality/grade indicators
        if any(term in desc_lower for term in ['automotive', 'aec-q', 'aec']):
            part_data.setdefault('categories', []).append('Automotive Grade')
        if any(term in desc_lower for term in ['military', 'mil-spec', 'mil']):
            part_data.setdefault('categories', []).append('Military Grade')
        if any(term in desc_lower for term in ['industrial', 'extended temp']):
            part_data.setdefault('categories', []).append('Industrial Grade')