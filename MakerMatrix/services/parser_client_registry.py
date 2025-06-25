"""
Parser-Client Registry

Establishes formal connections between CSV parsers and their corresponding
supplier enrichment clients. This enables automatic enrichment of imported
parts based on their source supplier.
"""

from typing import Dict, Optional, List, Tuple, Any
import logging
from datetime import datetime

from MakerMatrix.services.csv_import.parser_registry import csv_parser_registry
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.suppliers.base import BaseSupplier
from MakerMatrix.services.csv_import.base_parser import BaseCSVParser

logger = logging.getLogger(__name__)


class ParserClientRegistry:
    """
    Registry for CSV parser to supplier enrichment integration
    
    Uses direct name matching: if CSV parser is 'lcsc', looks for supplier named 'LCSC'
    This eliminates the need for hardcoded mappings and makes the system more intuitive.
    """
    
    # Enrichment capabilities that make sense for CSV import context
    DEFAULT_CSV_ENRICHMENT_CAPABILITIES = [
        'fetch_datasheet',
        'fetch_image', 
        'fetch_specifications',
        'fetch_details'
        # Note: pricing and stock may not be needed for CSV imports
        # since they often come from order files with current pricing
    ]
    
    @classmethod
    def get_enrichment_client(cls, parser_type: str) -> Optional[BaseSupplier]:
        """
        Get the enrichment supplier for a given parser type
        
        Uses direct name matching: 'lcsc' parser -> 'LCSC' supplier
        
        Args:
            parser_type: CSV parser type (e.g., 'lcsc', 'digikey')
            
        Returns:
            Supplier instance or None if supplier doesn't exist
        """
        if not parser_type:
            return None
            
        # Convert parser type to supplier name (e.g., 'lcsc' -> 'LCSC')
        supplier_name = parser_type.upper()
        
        try:
            return get_supplier(supplier_name.lower())
        except Exception as e:
            logger.debug(f"No supplier '{supplier_name}' available for parser '{parser_type}': {e}")
            return None
    
    @classmethod
    def supports_enrichment(cls, parser_type: str) -> bool:
        """
        Check if a parser type supports enrichment
        
        Simple logic: 
        1. Convert parser type to supplier name (e.g., 'lcsc' -> 'LCSC')
        2. Check if that supplier is configured and enabled in database
        
        Args:
            parser_type: CSV parser type (e.g., 'lcsc', 'digikey')
            
        Returns:
            True if corresponding supplier is configured and enabled
        """
        if not parser_type:
            return False
            
        # Convert parser type to supplier name (e.g., 'lcsc' -> 'LCSC')
        supplier_name = parser_type.upper()
        
        try:
            from MakerMatrix.services.supplier_config_service import SupplierConfigService
            supplier_service = SupplierConfigService()
            config = supplier_service.get_supplier_config(supplier_name)
            is_enabled = config.enabled
            
            if not is_enabled:
                logger.info(f"Supplier '{supplier_name}' is configured but disabled - enrichment not available for '{parser_type}' CSV")
            else:
                logger.debug(f"Supplier '{supplier_name}' is configured and enabled - enrichment available for '{parser_type}' CSV")
                
            return is_enabled
            
        except Exception as e:
            # ResourceNotFoundError or other errors mean supplier not configured
            logger.info(f"Supplier '{supplier_name}' not configured in database - enrichment not available for '{parser_type}' CSV: {e}")
            return False
    
    @classmethod
    def get_enrichment_capabilities(cls, parser_type: str) -> List[str]:
        """
        Get available enrichment capabilities for a parser type
        
        Args:
            parser_type: CSV parser type (e.g., 'lcsc', 'digikey')
            
        Returns:
            List of enrichment capability names
        """
        supplier = cls.get_enrichment_client(parser_type)
        if supplier:
            try:
                # Get capabilities from supplier instance
                capabilities = supplier.get_capabilities()
                capability_names = []
                
                # Map capabilities to string names for CSV enrichment
                for cap in capabilities:
                    cap_name = cap.name.lower()  # e.g., FETCH_DATASHEET -> fetch_datasheet
                    if cap_name in cls.DEFAULT_CSV_ENRICHMENT_CAPABILITIES:
                        capability_names.append(cap_name)
                
                return capability_names
            except Exception as e:
                logger.warning(f"Failed to get capabilities for {parser_type}: {e}")
                return []
        return []
    
    @classmethod
    def get_all_enrichment_mappings(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive information about all parser-client mappings
        
        Returns:
            Dictionary with parser info, client info, and capabilities
        """
        mappings = {}
        
        for parser_type, supplier_name in cls.PARSER_CLIENT_MAPPING.items():
            parser_info = csv_parser_registry.get_parser_info(parser_type)
            client = cls.get_enrichment_client(parser_type)
            capabilities = cls.get_enrichment_capabilities(parser_type)
            
            mappings[parser_type] = {
                'parser_type': parser_type,
                'supplier_name': supplier_name,
                'parser_info': parser_info,
                'client_available': client is not None,
                'enrichment_capabilities': capabilities,
                'supports_enrichment': len(capabilities) > 0
            }
        
        return mappings
    
    @classmethod
    def get_parsers_with_enrichment(cls) -> List[str]:
        """
        Get list of parser types that support enrichment
        
        Returns:
            List of parser type names that have enrichment clients
        """
        enrichment_parsers = []
        for parser_type in cls.PARSER_CLIENT_MAPPING.keys():
            if cls.supports_enrichment(parser_type):
                enrichment_parsers.append(parser_type)
        return enrichment_parsers
    
    @classmethod
    def validate_mapping(cls, parser_type: str) -> Dict[str, Any]:
        """
        Validate that a parser-client mapping is working correctly
        
        Args:
            parser_type: Parser type to validate
            
        Returns:
            Validation results dictionary
        """
        validation_result = {
            'parser_type': parser_type,
            'parser_exists': False,
            'client_exists': False,
            'mapping_exists': False,
            'capabilities_available': False,
            'capabilities': [],
            'errors': []
        }
        
        try:
            # Check if parser exists
            parser_class = csv_parser_registry.get_parser_class(parser_type)
            validation_result['parser_exists'] = parser_class is not None
            if not parser_class:
                validation_result['errors'].append(f"Parser '{parser_type}' not found in registry")
            
            # Check if mapping exists
            validation_result['mapping_exists'] = parser_type.lower() in cls.PARSER_CLIENT_MAPPING
            if not validation_result['mapping_exists']:
                validation_result['errors'].append(f"No enrichment mapping found for parser '{parser_type}'")
                return validation_result
            
            # Check if client exists
            client = cls.get_enrichment_client(parser_type)
            validation_result['client_exists'] = client is not None
            if not client:
                supplier_name = cls.PARSER_CLIENT_MAPPING.get(parser_type.lower())
                validation_result['errors'].append(f"Supplier client '{supplier_name}' not available")
                return validation_result
            
            # Check capabilities
            capabilities = cls.get_enrichment_capabilities(parser_type)
            validation_result['capabilities'] = capabilities
            validation_result['capabilities_available'] = len(capabilities) > 0
            if not capabilities:
                validation_result['errors'].append(f"No enrichment capabilities available for '{parser_type}'")
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    @classmethod
    def get_enrichment_part_number(cls, parser_type: str, part_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the correct supplier part number for enrichment from part data
        
        Args:
            parser_type: CSV parser type
            part_data: Part data dictionary (including additional_properties)
            
        Returns:
            Supplier-specific part number or None if not found
        """
        # For CSV imports, typically use the part_number field directly
        # since CSV parsers extract supplier-specific part numbers
        return part_data.get('part_number') or part_data.get('supplier_part_number')
    
    @classmethod
    def prepare_part_for_enrichment(cls, parser_type: str, part_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare part data for enrichment by adding minimal enrichment metadata
        
        Args:
            parser_type: CSV parser type
            part_data: Part data dictionary to enhance
            
        Returns:
            Enhanced part data with lean enrichment metadata
        """
        if cls.supports_enrichment(parser_type):
            if 'additional_properties' not in part_data:
                part_data['additional_properties'] = {}
            
            # Store only essential enrichment metadata
            part_data['additional_properties'].update({
                'needs_enrichment': True,
                'enrichment_source': parser_type,
                'enrichment_supplier': cls.PARSER_CLIENT_MAPPING.get(parser_type.lower())
                # Removed verbose fields: available_capabilities, enrichment_prepared_at, supports_enrichment
                # These create unnecessary bloat and can be determined dynamically
            })
        
        return part_data


# Global registry instance
parser_client_registry = ParserClientRegistry()


# Convenience functions for easy imports
def get_enrichment_client(parser_type: str) -> Optional[BaseSupplier]:
    """Get enrichment supplier for parser type"""
    return parser_client_registry.get_enrichment_client(parser_type)


def supports_enrichment(parser_type: str) -> bool:
    """Check if parser supports enrichment"""
    return parser_client_registry.supports_enrichment(parser_type)


def get_enrichment_capabilities(parser_type: str) -> List[str]:
    """Get enrichment capabilities for parser type"""
    return parser_client_registry.get_enrichment_capabilities(parser_type)


def get_all_enrichment_mappings() -> Dict[str, Dict[str, Any]]:
    """Get all parser-client mappings"""
    return parser_client_registry.get_all_enrichment_mappings()


def validate_mapping(parser_type: str) -> Dict[str, Any]:
    """Validate parser-client mapping"""
    return parser_client_registry.validate_mapping(parser_type)


def prepare_part_for_enrichment(parser_type: str, part_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare part data for enrichment"""
    return parser_client_registry.prepare_part_for_enrichment(parser_type, part_data)