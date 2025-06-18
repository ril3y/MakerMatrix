"""
Pytest tests for Parser-Client Registry System

Tests the integration between CSV parsers and supplier enrichment clients,
ensuring proper mapping, capability discovery, and validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from MakerMatrix.services.parser_client_registry import (
    ParserClientRegistry, 
    get_enrichment_client,
    supports_enrichment,
    get_enrichment_capabilities,
    get_all_enrichment_mappings,
    validate_mapping,
    prepare_part_for_enrichment
)
from MakerMatrix.clients.suppliers.base_supplier_client import BaseSupplierClient


class TestParserClientRegistry:
    """Test suite for Parser-Client Registry functionality"""
    
    def test_parser_client_mapping_structure(self):
        """Test that the parser-client mapping has the expected structure"""
        mapping = ParserClientRegistry.PARSER_CLIENT_MAPPING
        
        # Verify mapping exists and has expected entries
        assert isinstance(mapping, dict)
        assert 'lcsc' in mapping
        assert 'digikey' in mapping  
        assert 'mouser' in mapping
        
        # Verify mapping values are uppercase supplier names
        assert mapping['lcsc'] == 'LCSC'
        assert mapping['digikey'] == 'DIGIKEY'
        assert mapping['mouser'] == 'MOUSER'
    
    def test_supports_enrichment_valid_parsers(self):
        """Test enrichment support detection for valid parsers"""
        assert supports_enrichment('lcsc') == True
        assert supports_enrichment('digikey') == True
        assert supports_enrichment('mouser') == True
        
        # Test case insensitivity
        assert supports_enrichment('LCSC') == True
        assert supports_enrichment('DigiKey') == True
    
    def test_supports_enrichment_invalid_parsers(self):
        """Test enrichment support detection for invalid parsers"""
        assert supports_enrichment('unknown') == False
        assert supports_enrichment('invalid') == False
        assert supports_enrichment('') == False
        assert supports_enrichment(None) == False
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_client_success(self, mock_supplier_registry):
        """Test successful enrichment client creation"""
        # Mock supplier registry to return a client
        mock_client = Mock(spec=BaseSupplierClient)
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        client = get_enrichment_client('lcsc')
        
        assert client is not None
        assert client == mock_client
        mock_supplier_registry.create_supplier_client.assert_called_once_with('LCSC')
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_client_failure(self, mock_supplier_registry):
        """Test enrichment client creation failure"""
        # Mock supplier registry to raise exception
        mock_supplier_registry.create_supplier_client.side_effect = Exception("Client creation failed")
        
        client = get_enrichment_client('lcsc')
        
        assert client is None
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_client_invalid_parser(self, mock_supplier_registry):
        """Test enrichment client for invalid parser type"""
        client = get_enrichment_client('unknown')
        
        assert client is None
        mock_supplier_registry.create_supplier_client.assert_not_called()
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_capabilities_success(self, mock_supplier_registry):
        """Test successful capability retrieval"""
        # Mock client with capabilities
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supported_capabilities.return_value = [
            'fetch_datasheet', 'fetch_image', 'fetch_specifications', 
            'fetch_pricing', 'fetch_stock', 'fetch_details'
        ]
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        capabilities = get_enrichment_capabilities('lcsc')
        
        # Should return intersection with CSV-relevant capabilities
        expected_capabilities = ['fetch_datasheet', 'fetch_image', 'fetch_specifications', 'fetch_details']
        assert set(capabilities) == set(expected_capabilities)
        assert 'fetch_pricing' not in capabilities  # Not CSV-relevant
        assert 'fetch_stock' not in capabilities    # Not CSV-relevant
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_capabilities_no_client(self, mock_supplier_registry):
        """Test capability retrieval when no client is available"""
        mock_supplier_registry.create_supplier_client.return_value = None
        
        capabilities = get_enrichment_capabilities('lcsc')
        
        assert capabilities == []
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_capabilities_client_error(self, mock_supplier_registry):
        """Test capability retrieval when client raises error"""
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supported_capabilities.side_effect = Exception("Capability error")
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        capabilities = get_enrichment_capabilities('lcsc')
        
        assert capabilities == []
    
    @patch('MakerMatrix.services.parser_client_registry.csv_parser_registry')
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_all_enrichment_mappings(self, mock_supplier_registry, mock_parser_registry):
        """Test comprehensive mapping information retrieval"""
        # Mock parser info
        mock_parser_registry.get_parser_info.return_value = {
            'parser_type': 'lcsc',
            'name': 'LCSC',
            'description': 'LCSC order CSV files'
        }
        
        # Mock client
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supported_capabilities.return_value = ['fetch_datasheet', 'fetch_image']
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        mappings = get_all_enrichment_mappings()
        
        assert isinstance(mappings, dict)
        assert 'lcsc' in mappings
        
        lcsc_mapping = mappings['lcsc']
        assert lcsc_mapping['parser_type'] == 'lcsc'
        assert lcsc_mapping['supplier_name'] == 'LCSC'
        assert lcsc_mapping['client_available'] == True
        assert lcsc_mapping['supports_enrichment'] == True
        assert 'fetch_datasheet' in lcsc_mapping['enrichment_capabilities']
    
    @patch('MakerMatrix.services.parser_client_registry.csv_parser_registry')
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_validate_mapping_success(self, mock_supplier_registry, mock_parser_registry):
        """Test successful mapping validation"""
        # Mock parser exists
        mock_parser_registry.get_parser_class.return_value = Mock()
        
        # Mock client exists with capabilities
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supported_capabilities.return_value = ['fetch_datasheet', 'fetch_image']
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        result = validate_mapping('lcsc')
        
        assert result['parser_type'] == 'lcsc'
        assert result['parser_exists'] == True
        assert result['client_exists'] == True
        assert result['mapping_exists'] == True
        assert result['capabilities_available'] == True
        assert len(result['errors']) == 0
        assert len(result['capabilities']) > 0
    
    @patch('MakerMatrix.services.parser_client_registry.csv_parser_registry')
    def test_validate_mapping_parser_not_found(self, mock_parser_registry):
        """Test validation when parser doesn't exist"""
        mock_parser_registry.get_parser_class.return_value = None
        
        result = validate_mapping('unknown')
        
        assert result['parser_exists'] == False
        assert "Parser 'unknown' not found in registry" in result['errors']
    
    @patch('MakerMatrix.services.parser_client_registry.csv_parser_registry')
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_validate_mapping_no_client(self, mock_supplier_registry, mock_parser_registry):
        """Test validation when client doesn't exist"""
        # Parser exists
        mock_parser_registry.get_parser_class.return_value = Mock()
        
        # No client available
        mock_supplier_registry.create_supplier_client.return_value = None
        
        result = validate_mapping('lcsc')
        
        assert result['parser_exists'] == True
        assert result['client_exists'] == False
        assert result['mapping_exists'] == True
        assert "Supplier client 'LCSC' not available" in result['errors']
    
    def test_validate_mapping_no_mapping(self):
        """Test validation when no mapping exists"""
        result = validate_mapping('unknown')
        
        assert result['mapping_exists'] == False
        assert "No enrichment mapping found for parser 'unknown'" in result['errors']
    
    def test_prepare_part_for_enrichment_supported_parser(self):
        """Test part preparation for enrichment with supported parser"""
        part_data = {
            'part_name': 'Test Part',
            'part_number': 'TEST123',
            'additional_properties': {
                'lcsc_part_number': 'C12345'
            }
        }
        
        enhanced_part = prepare_part_for_enrichment('lcsc', part_data)
        
        # Verify enrichment metadata was added
        props = enhanced_part['additional_properties']
        assert props['supports_enrichment'] == True
        assert props['enrichment_source'] == 'lcsc'
        assert props['enrichment_supplier'] == 'LCSC'
        assert props['needs_enrichment'] == True
        assert 'available_capabilities' in props
        assert 'enrichment_prepared_at' in props
        
        # Verify original data is preserved
        assert enhanced_part['part_name'] == 'Test Part'
        assert props['lcsc_part_number'] == 'C12345'
    
    def test_prepare_part_for_enrichment_unsupported_parser(self):
        """Test part preparation for enrichment with unsupported parser"""
        part_data = {
            'part_name': 'Test Part',
            'additional_properties': {}
        }
        
        enhanced_part = prepare_part_for_enrichment('unknown', part_data)
        
        # Should not add enrichment metadata
        props = enhanced_part.get('additional_properties', {})
        assert props.get('supports_enrichment') != True
        assert 'enrichment_source' not in props
    
    def test_prepare_part_for_enrichment_missing_additional_properties(self):
        """Test part preparation when additional_properties doesn't exist"""
        part_data = {
            'part_name': 'Test Part'
        }
        
        enhanced_part = prepare_part_for_enrichment('lcsc', part_data)
        
        # Should create additional_properties and add enrichment metadata
        assert 'additional_properties' in enhanced_part
        props = enhanced_part['additional_properties']
        assert props['supports_enrichment'] == True
        assert props['enrichment_source'] == 'lcsc'
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_part_number_success(self, mock_supplier_registry):
        """Test successful part number extraction for enrichment"""
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supplier_part_number.return_value = 'C12345'
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        part_data = {'additional_properties': {'lcsc_part_number': 'C12345'}}
        
        part_number = ParserClientRegistry.get_enrichment_part_number('lcsc', part_data)
        
        assert part_number == 'C12345'
        mock_client.get_supplier_part_number.assert_called_once_with(part_data)
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_part_number_no_client(self, mock_supplier_registry):
        """Test part number extraction when no client available"""
        mock_supplier_registry.create_supplier_client.return_value = None
        
        part_data = {'additional_properties': {'lcsc_part_number': 'C12345'}}
        
        part_number = ParserClientRegistry.get_enrichment_part_number('lcsc', part_data)
        
        assert part_number is None
    
    @patch('MakerMatrix.services.parser_client_registry.supplier_registry')
    def test_get_enrichment_part_number_client_error(self, mock_supplier_registry):
        """Test part number extraction when client raises error"""
        mock_client = Mock(spec=BaseSupplierClient)
        mock_client.get_supplier_part_number.side_effect = Exception("Extraction failed")
        mock_supplier_registry.create_supplier_client.return_value = mock_client
        
        part_data = {'additional_properties': {'lcsc_part_number': 'C12345'}}
        
        part_number = ParserClientRegistry.get_enrichment_part_number('lcsc', part_data)
        
        assert part_number is None
    
    def test_default_csv_enrichment_capabilities(self):
        """Test that default CSV enrichment capabilities are appropriate"""
        capabilities = ParserClientRegistry.DEFAULT_CSV_ENRICHMENT_CAPABILITIES
        
        # Should include these capabilities
        assert 'fetch_datasheet' in capabilities
        assert 'fetch_image' in capabilities
        assert 'fetch_specifications' in capabilities
        assert 'fetch_details' in capabilities
        
        # Should NOT include these (not relevant for CSV imports)
        assert 'fetch_pricing' not in capabilities  # CSV usually has pricing
        assert 'fetch_stock' not in capabilities    # CSV usually has quantity
    
    def test_get_parsers_with_enrichment(self):
        """Test getting list of parsers that support enrichment"""
        parsers = ParserClientRegistry.get_parsers_with_enrichment()
        
        assert isinstance(parsers, list)
        assert 'lcsc' in parsers
        assert 'digikey' in parsers
        assert 'mouser' in parsers
        assert len(parsers) == 3  # Based on current mapping
    
    @pytest.mark.parametrize("parser_type,expected_supplier", [
        ('lcsc', 'LCSC'),
        ('digikey', 'DIGIKEY'),
        ('mouser', 'MOUSER'),
        ('LCSC', 'LCSC'),  # Test case insensitivity
        ('DigiKey', 'DIGIKEY'),
        ('unknown', None)
    ])
    def test_parser_to_supplier_mapping(self, parser_type, expected_supplier):
        """Test parser type to supplier name mapping"""
        mapping = ParserClientRegistry.PARSER_CLIENT_MAPPING
        result = mapping.get(parser_type.lower())
        assert result == expected_supplier


class TestParserClientRegistryIntegration:
    """Integration tests for parser-client registry with real components"""
    
    def test_real_parser_registry_integration(self):
        """Test integration with real CSV parser registry"""
        from MakerMatrix.services.csv_import.parser_registry import get_available_parser_types
        
        available_parsers = get_available_parser_types()
        mapped_parsers = list(ParserClientRegistry.PARSER_CLIENT_MAPPING.keys())
        
        # All mapped parsers should exist in the parser registry
        for parser_type in mapped_parsers:
            assert parser_type in available_parsers, f"Parser '{parser_type}' not found in registry"
    
    def test_real_supplier_registry_integration(self):
        """Test integration with real supplier registry"""
        from MakerMatrix.clients.suppliers.supplier_registry import get_available_suppliers
        
        available_suppliers = get_available_suppliers()
        mapped_suppliers = list(ParserClientRegistry.PARSER_CLIENT_MAPPING.values())
        
        # All mapped suppliers should exist in the supplier registry
        for supplier_name in mapped_suppliers:
            assert supplier_name in available_suppliers, f"Supplier '{supplier_name}' not found in registry"
    
    @pytest.mark.integration
    def test_end_to_end_enrichment_flow(self):
        """Test complete enrichment flow from parser to client"""
        # Test with LCSC since it's most likely to work without credentials
        parser_type = 'lcsc'
        
        # Check that enrichment is supported
        assert supports_enrichment(parser_type)
        
        # Try to get capabilities (may be empty if client needs credentials)
        capabilities = get_enrichment_capabilities(parser_type)
        # Don't assert on capabilities since client may need credentials
        
        # Test part preparation
        part_data = {
            'part_name': 'Test Part',
            'additional_properties': {'lcsc_part_number': 'C12345'}
        }
        
        enhanced_part = prepare_part_for_enrichment(parser_type, part_data)
        
        # Verify enrichment preparation worked
        props = enhanced_part['additional_properties']
        assert props['supports_enrichment'] == True
        assert props['enrichment_source'] == parser_type
        assert props['enrichment_supplier'] == 'LCSC'
    
    def test_validation_with_real_components(self):
        """Test validation using real parser and supplier registries"""
        # Test validation for each mapped parser
        for parser_type in ParserClientRegistry.PARSER_CLIENT_MAPPING.keys():
            result = validate_mapping(parser_type)
            
            # Parser should exist (we're testing with real registry)
            assert result['parser_exists'] == True, f"Parser '{parser_type}' should exist"
            assert result['mapping_exists'] == True, f"Mapping for '{parser_type}' should exist"
            
            # Client existence depends on whether credentials are configured
            # So we don't assert on client_exists, but check that validation runs
            assert 'errors' in result
            assert isinstance(result['errors'], list)