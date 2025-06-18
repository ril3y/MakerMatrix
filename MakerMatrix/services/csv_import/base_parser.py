from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import csv
import io
import logging

logger = logging.getLogger(__name__)


class BaseCSVParser(ABC):
    """Base class for CSV order file parsers"""
    
    def __init__(self, parser_type: str, name: str, description: str):
        self.parser_type = parser_type
        self.name = name
        self.description = description
    
    @property
    @abstractmethod
    def required_columns(self) -> List[str]:
        """List of required column names for this parser"""
        pass
    
    @property
    @abstractmethod
    def sample_columns(self) -> List[str]:
        """List of sample column names for documentation"""
        pass
    
    @property
    @abstractmethod
    def detection_patterns(self) -> List[str]:
        """List of column names/patterns that indicate this CSV type"""
        pass
    
    @abstractmethod
    def parse_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Parse a single CSV row into standardized part data
        
        Args:
            row: Dictionary of column_name -> value from CSV
            row_num: Row number for error reporting
            
        Returns:
            Standardized part data dictionary or None if row should be skipped
        """
        pass
    
    def can_parse(self, headers: List[str]) -> bool:
        """Check if this parser can handle a CSV with the given headers"""
        normalized_headers = [header.strip().lower() for header in headers]
        
        # Check if any detection patterns match
        for pattern in self.detection_patterns:
            if pattern.lower() in normalized_headers:
                return True
        
        return False
    
    def validate_headers(self, headers: List[str]) -> List[str]:
        """Validate that required columns are present
        
        Returns:
            List of missing required columns
        """
        normalized_headers = [header.strip().lower() for header in headers]
        missing_columns = []
        
        for required_col in self.required_columns:
            if required_col.lower() not in normalized_headers:
                missing_columns.append(required_col)
        
        return missing_columns
    
    def extract_order_info_from_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Extract order information from filename (override in subclasses)
        
        Args:
            filename: The CSV filename
            
        Returns:
            Dict with order_date, order_number, supplier if extraction successful, None otherwise
        """
        return None
    
    def get_supplier_name(self) -> str:
        """Get the supplier name for this parser type
        
        Returns:
            Supplier name with proper capitalization
        """
        # Map parser types to supplier names with proper capitalization
        supplier_name_mapping = {
            'lcsc': 'LCSC',
            'digikey': 'DigiKey', 
            'mouser': 'Mouser',
            'tme': 'TME',
            'arrow': 'Arrow',
            'avnet': 'Avnet',
            'element14': 'Element14',
            'farnell': 'Farnell',
            'newark': 'Newark',
            'rs': 'RS Components'
        }
        
        # Return mapped name or capitalize the parser type as fallback
        return supplier_name_mapping.get(self.parser_type.lower(), self.parser_type.title())
    
    def get_info(self) -> Dict[str, Any]:
        """Get parser information for API responses"""
        return {
            "type": self.parser_type,
            "name": self.name,
            "description": self.description,
            "required_columns": self.required_columns,
            "sample_columns": self.sample_columns,
            "supplier_name": self.get_supplier_name()
        }
    
    # Utility methods that subclasses can use
    def parse_quantity(self, quantity_str: str) -> int:
        """Parse quantity string to integer"""
        try:
            import re
            # Remove any non-digit characters except decimal points
            cleaned = re.sub(r'[^\d.]', '', str(quantity_str))
            if cleaned:
                return int(float(cleaned))
            return 0
        except (ValueError, TypeError):
            return 0
    
    def parse_price(self, price_str: str) -> float:
        """Parse price string to float"""
        try:
            import re
            from decimal import Decimal
            # Remove currency symbols and convert to float
            cleaned = re.sub(r'[$€£¥,]', '', str(price_str))
            if cleaned:
                # Convert through Decimal first to handle precision, then to float
                decimal_value = Decimal(cleaned)
                return float(decimal_value)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def clean_string(self, value: str) -> str:
        """Clean and normalize string value"""
        if not value:
            return ""
        return str(value).strip()
    
    def should_skip_row(self, row: Dict[str, str]) -> bool:
        """Check if a row should be skipped (subtotals, empty rows, etc.)"""
        # Check for common skip patterns
        description = str(row.get('Description', '')).lower()
        if any(skip_word in description for skip_word in ['subtotal', 'total', 'tax', 'shipping']):
            return True
        
        # Check if all important fields are empty
        important_fields = ['part number', 'part #', 'manufacturer part number', 'lcsc part number', 'mouser part #', 'digikey part #']
        has_part_number = False
        
        for field_name, field_value in row.items():
            if any(important in field_name.lower() for important in important_fields):
                if field_value and str(field_value).strip():
                    has_part_number = True
                    break
        
        return not has_part_number