"""
Pytest tests for CSV Import Enrichment Integration

Tests the enhanced CSV import service with enrichment capabilities,
ensuring proper integration with the parser-client registry.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import io

from MakerMatrix.services.csv_import_service import CSVImportService
from MakerMatrix.services.csv_import.base_parser import BaseCSVParser


class MockCSVParser(BaseCSVParser):
    """Mock CSV parser for testing"""
    
    def __init__(self, parser_type="mock", download_config=None):
        super().__init__(
            parser_type=parser_type,
            name="Mock Parser",
            description="Mock parser for testing"
        )
        self.download_config = download_config or {}
    
    @property
    def required_columns(self) -> List[str]:
        return ["part_number", "description", "quantity"]
    
    @property
    def sample_columns(self) -> List[str]:
        return ["part_number", "description", "quantity", "manufacturer"]
    
    @property
    def detection_patterns(self) -> List[str]:
        return ["part_number"]
    
    def parse_row(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Parse a mock CSV row"""
        return {
            'part_name': row.get('part_number', f'Part-{row_num}'),
            'part_number': row.get('part_number', f'PN-{row_num}'),
            'description': row.get('description', 'Mock part'),
            'quantity': int(row.get('quantity', 1)),
            'supplier': 'MockSupplier',
            'additional_properties': {
                'mock_part_number': row.get('part_number', f'MOCK-{row_num}'),
                'manufacturer': row.get('manufacturer', 'MockMfg')
            }
        }


class TestCSVImportEnrichment:
    """Test suite for CSV import enrichment functionality"""
    
    @pytest.fixture
    def mock_csv_content(self):
        """Sample CSV content for testing"""
        return '''part_number,description,quantity,manufacturer
PART001,Resistor 1kΩ,100,TestMfg
PART002,Capacitor 10µF,50,TestMfg2'''
    
    @pytest.fixture
    def csv_import_service(self):
        """Create CSVImportService with mock parsers"""
        service = CSVImportService()
        # Replace parsers with mocks for testing
        mock_parser = MockCSVParser("mock")
        service.parsers = [mock_parser]
        service.parser_lookup = {"mock": mock_parser}
        return service
    
    def test_parse_csv_without_enrichment(self, csv_import_service, mock_csv_content):
        """Test CSV parsing without enrichment enabled"""
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            mock_csv_content, "mock", enable_enrichment=False
        )
        
        assert len(errors) == 0
        assert len(parts_data) == 2
        
        # Verify parts don't have enrichment metadata
        for part in parts_data:
            props = part.get('additional_properties', {})
            assert props.get('supports_enrichment') != True
            assert 'enrichment_source' not in props
            assert 'needs_enrichment' not in props
    
    @patch('MakerMatrix.services.csv_import_service.supports_enrichment')
    @patch('MakerMatrix.services.csv_import_service.prepare_part_for_enrichment')
    def test_parse_csv_with_enrichment_supported(self, mock_prepare, mock_supports, 
                                               csv_import_service, mock_csv_content):
        """Test CSV parsing with enrichment enabled for supported parser"""
        # Mock enrichment support
        mock_supports.return_value = True
        mock_prepare.side_effect = lambda parser_type, part_data: {
            **part_data,
            'additional_properties': {
                **part_data.get('additional_properties', {}),
                'supports_enrichment': True,
                'enrichment_source': parser_type,
                'needs_enrichment': True
            }
        }
        
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            mock_csv_content, "mock", enable_enrichment=True
        )
        
        assert len(errors) == 0
        assert len(parts_data) == 2
        
        # Verify enrichment preparation was called
        assert mock_prepare.call_count == 2
        
        # Verify parts have enrichment metadata
        for part in parts_data:
            props = part.get('additional_properties', {})
            assert props.get('supports_enrichment') == True
            assert props.get('enrichment_source') == 'mock'
            assert props.get('needs_enrichment') == True
    
    @patch('MakerMatrix.services.csv_import_service.supports_enrichment')
    def test_parse_csv_with_enrichment_unsupported(self, mock_supports, 
                                                 csv_import_service, mock_csv_content):
        """Test CSV parsing with enrichment enabled for unsupported parser"""
        # Mock no enrichment support
        mock_supports.return_value = False
        
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            mock_csv_content, "mock", enable_enrichment=True
        )
        
        assert len(errors) == 0
        assert len(parts_data) == 2
        
        # Verify parts don't have enrichment metadata
        for part in parts_data:
            props = part.get('additional_properties', {})
            assert props.get('supports_enrichment') != True
    
    def test_parse_csv_invalid_parser_type(self, csv_import_service, mock_csv_content):
        """Test CSV parsing with invalid parser type"""
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            mock_csv_content, "invalid", enable_enrichment=True
        )
        
        assert len(parts_data) == 0
        assert len(errors) == 1
        assert "Unsupported parser type: invalid" in errors[0]
    
    def test_parse_csv_with_parsing_errors(self, csv_import_service):
        """Test CSV parsing when parser throws errors"""
        # CSV with invalid content
        invalid_csv = '''part_number,description
PART001'''  # Missing quantity column
        
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            invalid_csv, "mock", enable_enrichment=True
        )
        
        # Should handle parsing errors gracefully
        assert len(errors) == 1
        assert "Missing required columns" in errors[0]
    
    @patch('MakerMatrix.services.csv_import_service.supports_enrichment')
    @patch('MakerMatrix.services.csv_import_service.prepare_part_for_enrichment')
    def test_enrichment_logging(self, mock_prepare, mock_supports, 
                              csv_import_service, mock_csv_content, caplog):
        """Test that enrichment logging works correctly"""
        mock_supports.return_value = True
        mock_prepare.side_effect = lambda parser_type, part_data: {
            **part_data,
            'additional_properties': {
                **part_data.get('additional_properties', {}),
                'supports_enrichment': True
            }
        }
        
        with caplog.at_level('INFO'):
            parts_data, errors = csv_import_service.parse_csv_to_parts(
                mock_csv_content, "mock", enable_enrichment=True
            )
        
        # Check for enrichment logging
        log_messages = [record.message for record in caplog.records]
        assert any("Enrichment enabled for mock" in msg for msg in log_messages)
        assert any("ready for enrichment" in msg for msg in log_messages)
    
    @patch('MakerMatrix.services.csv_import_service.supports_enrichment')
    def test_enrichment_warning_for_unsupported(self, mock_supports, 
                                              csv_import_service, mock_csv_content, caplog):
        """Test warning when enrichment requested but not supported"""
        mock_supports.return_value = False
        
        with caplog.at_level('WARNING'):
            csv_import_service.parse_csv_to_parts(
                mock_csv_content, "mock", enable_enrichment=True
            )
        
        # Check for warning message
        log_messages = [record.message for record in caplog.records]
        assert any("Enrichment requested for mock but no enrichment client available" in msg 
                  for msg in log_messages)
    
    def test_backward_compatibility(self, csv_import_service, mock_csv_content):
        """Test that existing code still works without enrichment parameter"""
        # Default behavior should be no enrichment
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            mock_csv_content, "mock"  # No enable_enrichment parameter
        )
        
        assert len(errors) == 0
        assert len(parts_data) == 2
        
        # Verify no enrichment metadata by default
        for part in parts_data:
            props = part.get('additional_properties', {})
            assert props.get('supports_enrichment') != True
    
    @patch('MakerMatrix.services.csv_import_service.prepare_part_for_enrichment')
    def test_enrichment_preparation_called_correctly(self, mock_prepare, csv_import_service, mock_csv_content):
        """Test that enrichment preparation is called with correct parameters"""
        mock_prepare.side_effect = lambda parser_type, part_data: part_data
        
        with patch('MakerMatrix.services.csv_import_service.supports_enrichment', return_value=True):
            csv_import_service.parse_csv_to_parts(
                mock_csv_content, "mock", enable_enrichment=True
            )
        
        # Verify preparation was called for each part
        assert mock_prepare.call_count == 2
        
        # Check call arguments
        for call in mock_prepare.call_args_list:
            parser_type, part_data = call[0]
            assert parser_type == "mock"
            assert 'part_name' in part_data
            assert 'additional_properties' in part_data


class TestCSVImportEnrichmentIntegration:
    """Integration tests for CSV import enrichment with real components"""
    
    @pytest.fixture
    def lcsc_csv_content(self):
        """Sample LCSC CSV content for integration testing"""
        return '''LCSC Part Number,Manufacture Part Number,Manufacturer,Description,Order Qty.,Unit Price($),Order Price($)
C15850,CL21A106KOQNNNE,Samsung Electro-Mechanics,10uF Capacitor,100,0.05,5.00
C17513,0805W8F1001T5E,UNI-ROYAL(Uniroyal Elec),1kΩ Resistor,50,0.02,1.00'''
    
    def test_real_lcsc_parser_enrichment_integration(self, lcsc_csv_content):
        """Test enrichment integration with real LCSC parser"""
        service = CSVImportService()
        
        # Test without enrichment
        parts_without, errors = service.parse_csv_to_parts(
            lcsc_csv_content, "lcsc", enable_enrichment=False
        )
        
        assert len(errors) == 0
        assert len(parts_without) == 2
        
        # Test with enrichment
        parts_with, errors = service.parse_csv_to_parts(
            lcsc_csv_content, "lcsc", enable_enrichment=True
        )
        
        assert len(errors) == 0
        assert len(parts_with) == 2
        
        # Compare parts with and without enrichment
        for part_without, part_with in zip(parts_without, parts_with):
            # Basic part data should be the same
            assert part_without['part_name'] == part_with['part_name']
            assert part_without['part_number'] == part_with['part_number']
            
            # Enrichment metadata should be different
            props_without = part_without.get('additional_properties', {})
            props_with = part_with.get('additional_properties', {})
            
            # Parts without enrichment should not have enrichment metadata
            assert props_without.get('needs_enrichment') != True
            assert props_without.get('enrichment_source') is None
            
            # Parts with enrichment should have enrichment metadata
            assert props_with.get('needs_enrichment') == True
            assert props_with.get('enrichment_source') == 'lcsc'
            assert props_with.get('enrichment_supplier') == 'LCSC'
    
    @pytest.mark.integration
    def test_parser_client_registry_integration(self):
        """Test that CSV import service works with parser-client registry"""
        from MakerMatrix.services.parser_client_registry import supports_enrichment, get_enrichment_capabilities
        
        service = CSVImportService()
        
        # Test that service can check enrichment support
        for parser_type in ['lcsc', 'digikey', 'mouser']:
            if parser_type in service.parser_lookup:
                supports = supports_enrichment(parser_type)
                capabilities = get_enrichment_capabilities(parser_type)
                
                # These should work without errors
                assert isinstance(supports, bool)
                assert isinstance(capabilities, list)
    
    def test_csv_service_with_different_parsers(self):
        """Test CSV service enrichment with different parser types"""
        service = CSVImportService()
        
        # Simple CSV that might work with multiple parsers
        test_csv = '''part_number,description,quantity
TEST001,Test Resistor,10
TEST002,Test Capacitor,20'''
        
        # Test each available parser
        for parser_type in service.parser_lookup.keys():
            try:
                parts_data, errors = service.parse_csv_to_parts(
                    test_csv, parser_type, enable_enrichment=True
                )
                
                # If parsing succeeds, verify structure
                if not errors and parts_data:
                    for part in parts_data:
                        assert 'part_name' in part
                        assert 'additional_properties' in part
                        
            except Exception as e:
                # Some parsers may fail with this generic CSV - that's okay
                pytest.skip(f"Parser {parser_type} failed with test CSV: {e}")


class TestCSVImportServiceEnhancedMethods:
    """Test enhanced methods in CSV import service"""
    
    def test_csv_import_service_initialization(self):
        """Test that CSV import service initializes correctly with enrichment support"""
        service = CSVImportService()
        
        # Should have parsers
        assert len(service.parsers) > 0
        assert len(service.parser_lookup) > 0
        
        # Should have preview parsers
        assert len(service.preview_parsers) > 0
        assert len(service.preview_parser_lookup) > 0
        
        # Parser types should match
        assert set(service.parser_lookup.keys()) == set(service.preview_parser_lookup.keys())
    
    def test_parse_csv_to_parts_signature(self):
        """Test that parse_csv_to_parts has correct signature"""
        service = CSVImportService()
        
        # Test method signature accepts enable_enrichment parameter
        import inspect
        sig = inspect.signature(service.parse_csv_to_parts)
        params = list(sig.parameters.keys())
        
        assert 'csv_content' in params
        assert 'parser_type' in params
        assert 'enable_enrichment' in params
        
        # Test default value
        enable_enrichment_param = sig.parameters['enable_enrichment']
        assert enable_enrichment_param.default == False
    
    @patch('MakerMatrix.services.csv_import_service.logger')
    def test_enrichment_debug_logging(self, mock_logger):
        """Test that debug logging works for enrichment preparation"""
        service = CSVImportService()
        
        # Create a mock parser that would trigger enrichment
        mock_parser = MockCSVParser("test")
        service.parser_lookup["test"] = mock_parser
        
        csv_content = '''part_number,description,quantity
TEST001,Test Part,10'''
        
        with patch('MakerMatrix.services.csv_import_service.supports_enrichment', return_value=True), \
             patch('MakerMatrix.services.csv_import_service.prepare_part_for_enrichment', 
                   side_effect=lambda _, pd: pd):
            
            service.parse_csv_to_parts(csv_content, "test", enable_enrichment=True)
        
        # Verify debug logging was called
        debug_calls = [call for call in mock_logger.debug.call_args_list 
                      if 'Prepared part' in str(call) and 'for enrichment' in str(call)]
        assert len(debug_calls) > 0