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
from MakerMatrix.clients.suppliers.supplier_registry import supplier_registry
from MakerMatrix.clients.suppliers.base_supplier_client import BaseSupplierClient
from MakerMatrix.services.csv_import.base_parser import BaseCSVParser

logger = logging.getLogger(__name__)


class ParserClientRegistry:
    """
    Registry that maps CSV parsers to their corresponding enrichment clients
    """
    
    # Formal mapping between parser types and supplier client names
    PARSER_CLIENT_MAPPING = {
        # CSV Parser Type -> Supplier Client Name
        'lcsc': 'LCSC',
        'digikey': 'DIGIKEY', 
        'mouser': 'MOUSER'
        # Add new mappings here as parsers/clients are added
    }
    
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
    def get_enrichment_client(cls, parser_type: str) -> Optional[BaseSupplierClient]:
        """
        Get the enrichment client for a given parser type
        
        Args:
            parser_type: CSV parser type (e.g., 'lcsc', 'digikey')
            
        Returns:
            Supplier client instance or None if no mapping exists
        """
        supplier_name = cls.PARSER_CLIENT_MAPPING.get(parser_type.lower())
        if supplier_name:
            try:
                return supplier_registry.create_supplier_client(supplier_name)
            except Exception as e:
                logger.warning(f"Failed to create supplier client {supplier_name} for parser {parser_type}: {e}")
                return None
        return None
    
    @classmethod
    def supports_enrichment(cls, parser_type: str) -> bool:
        """
        Check if a parser type supports enrichment
        
        Args:
            parser_type: CSV parser type
            
        Returns:
            True if enrichment is supported
        """
        if not parser_type:
            return False
        return parser_type.lower() in cls.PARSER_CLIENT_MAPPING
    
    @classmethod
    def get_enrichment_capabilities(cls, parser_type: str) -> List[str]:
        """
        Get available enrichment capabilities for a parser type
        
        Args:
            parser_type: CSV parser type
            
        Returns:
            List of enrichment capability names
        """
        client = cls.get_enrichment_client(parser_type)
        if client:
            try:
                client_capabilities = client.get_supported_capabilities()
                # Return intersection of client capabilities and CSV-relevant capabilities
                return [cap for cap in client_capabilities if cap in cls.DEFAULT_CSV_ENRICHMENT_CAPABILITIES]
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
        client = cls.get_enrichment_client(parser_type)
        if client and hasattr(client, 'get_supplier_part_number'):
            try:
                return client.get_supplier_part_number(part_data)
            except Exception as e:
                logger.warning(f"Failed to extract part number for {parser_type}: {e}")
        return None
    
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
def get_enrichment_client(parser_type: str) -> Optional[BaseSupplierClient]:
    """Get enrichment client for parser type"""
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