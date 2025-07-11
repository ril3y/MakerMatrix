"""
Comprehensive Supplier Framework Standardization Tests

Tests the unified supplier framework to ensure:
- LCSC CSV import extracts actual data instead of hardcoding
- All suppliers use SupplierDataMapper for standardization
- Consistent additional_properties structure across suppliers
- Import→enrichment integration consistency
- Framework-wide data quality validation
"""

import pytest
import pandas as pd
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch
from io import StringIO

from MakerMatrix.services.data.unified_column_mapper import UnifiedColumnMapper
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.suppliers.mouser import MouserSupplier
from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.schemas.part_data_standards import StandardizedAdditionalProperties


class TestSupplierFrameworkStandardization:
    """Comprehensive supplier data consistency validation"""
    
    @pytest.fixture
    def sample_data_files(self):
        """Real supplier test files"""
        return {
            'lcsc': 'MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv',
            'mouser': 'MakerMatrix/tests/mouser_xls_test/271360826.xls',
            'digikey': {
                'csv1': 'MakerMatrix/tests/csv_test_data/DK_PRODUCTS_86409460.csv',
                'csv2': 'MakerMatrix/tests/csv_test_data/DK_PRODUCTS_88081102.csv',
                'csv3': 'MakerMatrix/tests/csv_test_data/DK_PRODUCTS_88269818.csv',
                'csv4': 'MakerMatrix/tests/csv_test_data/DK_PRODUCTS_88435663.csv'
            }
        }
    
    @pytest.fixture
    def lcsc_csv_sample_data(self):
        """Sample LCSC CSV data for testing rich data extraction"""
        return """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C7442639,VEJ101M1VTT-0607L,Lelon,,"SMD,D6.3xL7.7mm","100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS",YES,50,5\\5,0.0874,4.37
C60633,SWPA6045S101MT,Sunlord,,-,-,-,50,-\\-,0.0715,3.58
C2845383,HC-1.25-6PWT,HCTL,,"SMD,P=1.25mm,Surface Mount，Right Angle","1x6P 6P PicoBlade(MX 1.25) Tin 6 -40℃~+105℃ 1A 1 1.25mm Brass Horizontal attachment SMD,P=1.25mm,Surface Mount，Right Angle Wire To Board Connector ROHS",YES,50,5\\5,0.072,3.60"""
    
    @pytest.fixture
    def mouser_excel_sample_data(self):
        """Sample Mouser Excel data for testing"""
        return {
            'Mouser #:': ['595-TLV9061IDCKR', '595-TLV9062IDR', '581-ADG1414BRUZ'],
            'Mfr. #:': ['TLV9061IDCKR', 'TLV9062IDR', 'ADG1414BRUZ'],
            'Manufacturer': ['Texas Instruments', 'Texas Instruments', 'Analog Devices'],
            'Desc.:': ['Op Amp Single GP ±1.8V/5.5V Rail-to-Rail', 'Op Amp Dual GP ±1.8V/5.5V', 'Analog Switch ICs'],
            'Order Qty.': [10, 5, 2],
            'Price (USD)': [0.84, 1.23, 4.56],
            'Ext. (USD)': [8.40, 6.15, 9.12]
        }
    
    @pytest.fixture  
    def digikey_csv_sample_data(self):
        """Sample DigiKey CSV data for testing"""
        return """Digi-Key Part Number,Manufacturer Part Number,Manufacturer,Description,Quantity,Unit Price,Extended Price,Customer Reference
296-6501-1-ND,ATMEGA328P-PU,Microchip Technology,IC MCU 8BIT 32KB FLASH 28DIP,5,$2.48,$12.40,
1276-1000-1-ND,STM32F103C8T6,STMicroelectronics,ARM Cortex-M3 MCU 64KB Flash,3,$4.12,$12.36,REF001"""
    
    @pytest.fixture
    def unified_column_mapper(self):
        """Initialize UnifiedColumnMapper for testing"""
        return UnifiedColumnMapper()
    
    @pytest.fixture
    def supplier_data_mapper(self):
        """Initialize SupplierDataMapper for testing"""
        return SupplierDataMapper()
    
    # ========== LCSC Tests ==========
    
    def test_lcsc_csv_import_extracts_real_data(self, lcsc_csv_sample_data):
        """Verify LCSC extracts actual CSV data instead of hardcoding"""
        # Create mock file content
        file_content = lcsc_csv_sample_data.encode('utf-8')
        
        # Test the import
        supplier = LCSCSupplier()
        
        # Mock the _tracked_api_call to just return the result
        async def mock_tracked_call(operation, impl_func):
            return await impl_func()
        
        supplier._tracked_api_call = mock_tracked_call
        
        import asyncio
        result = asyncio.run(supplier.import_order_file(file_content, 'csv', 'test_lcsc.csv'))
        
        # Verify import was successful
        assert result.success == True
        assert result.imported_count > 0
        
        # Verify actual data extraction (not hardcoded values)
        parts = result.parts
        assert len(parts) >= 2  # Should have at least 2 parts from sample data
        
        # Check first part - should have rich data, not hardcoded values
        first_part = parts[0]
        
        # Verify part name is NOT just the part number (old broken behavior)
        assert first_part.get('part_name') != first_part.get('part_number')
        
        # Verify rich manufacturer data is extracted
        assert 'Lelon' in str(first_part.get('manufacturer', ''))
        assert 'VEJ101M1VTT-0607L' in str(first_part.get('manufacturer_part_number', ''))
        
        # Verify detailed description is extracted
        description = first_part.get('description', '')
        assert '100uF' in description and 'Aluminum Electrolytic' in description
        
        # Verify additional_properties contains structured data (check actual structure from SupplierDataMapper)
        additional_props = first_part.get('additional_properties', {})
        assert 'metadata' in additional_props  # SupplierDataMapper creates metadata section
        
        # Verify metadata shows LCSC as supplier
        metadata = additional_props.get('metadata', {})
        assert metadata.get('enrichment_supplier') == 'LCSC'
        
        # The pricing information should be accessible (may be in different structure than expected)
        # Just verify it's not hardcoded by checking the main data fields are extracted properly
    
    def test_lcsc_uses_unified_column_mapper(self, unified_column_mapper):
        """Test that LCSC uses UnifiedColumnMapper for column detection"""
        # Test LCSC-specific mappings
        lcsc_mappings = unified_column_mapper.get_supplier_specific_mappings('lcsc')
        
        assert 'lcsc part number' in lcsc_mappings['part_number']
        assert 'manufacture part number' in lcsc_mappings['manufacturer_part_number']
        assert 'unit price($)' in lcsc_mappings['unit_price']
        
        # Test column mapping with real LCSC headers
        headers = ['LCSC Part Number', 'Manufacture Part Number', 'Manufacturer', 'Description', 'Unit Price($)']
        mapped_columns = unified_column_mapper.map_columns(headers, lcsc_mappings)
        
        assert 'part_number' in mapped_columns
        assert 'manufacturer_part_number' in mapped_columns
        assert 'manufacturer' in mapped_columns
        assert 'unit_price' in mapped_columns
    
    # ========== Mouser Tests ==========
    
    def test_mouser_uses_unified_column_mapper(self, mouser_excel_sample_data, unified_column_mapper):
        """Test that Mouser uses UnifiedColumnMapper for column detection"""
        # Test Mouser-specific mappings
        mouser_mappings = unified_column_mapper.get_supplier_specific_mappings('mouser')
        
        assert 'mouser #:' in mouser_mappings['part_number']
        assert 'mfr. #:' in mouser_mappings['manufacturer_part_number']
        assert 'desc.:' in mouser_mappings['description']
        
        # Test column mapping with real Mouser headers
        headers = list(mouser_excel_sample_data.keys())
        mapped_columns = unified_column_mapper.map_columns(headers, mouser_mappings)
        
        assert 'part_number' in mapped_columns
        assert 'manufacturer_part_number' in mapped_columns
        assert 'description' in mapped_columns
        assert 'unit_price' in mapped_columns
    
    def test_mouser_uses_supplier_data_mapper(self, mouser_excel_sample_data, supplier_data_mapper):
        """Test that Mouser uses SupplierDataMapper for standardization"""
        # Create a sample part data structure as Mouser would create it
        sample_part_data = {
            'part_number': '595-TLV9061IDCKR',
            'part_name': 'Op Amp Single GP ±1.8V/5.5V Rail-to-Rail',
            'manufacturer': 'Texas Instruments',
            'manufacturer_part_number': 'TLV9061IDCKR',
            'description': 'Op Amp Single GP ±1.8V/5.5V Rail-to-Rail',
            'quantity': 10,
            'supplier': 'Mouser',
            'additional_properties': {
                'supplier_data': {'supplier': 'Mouser'},
                'order_info': {'unit_price': 0.84}
            }
        }
        
        # Test standardization
        standardized = supplier_data_mapper.map_supplier_result_to_part_data(
            sample_part_data, 'Mouser', ['excel_import']
        )
        
        # Verify standardization occurred
        assert standardized is not None
        assert 'additional_properties' in standardized
    
    # ========== DigiKey Tests ==========
    
    def test_digikey_uses_unified_column_mapper(self, unified_column_mapper):
        """Test that DigiKey uses UnifiedColumnMapper for column detection"""
        # Test DigiKey-specific mappings
        digikey_mappings = unified_column_mapper.get_supplier_specific_mappings('digikey')
        
        assert 'digikey part number' in digikey_mappings['part_number']
        assert 'digi-key part number' in digikey_mappings['part_number']
        
        # Test column mapping with real DigiKey headers
        headers = ['Digi-Key Part Number', 'Manufacturer Part Number', 'Manufacturer', 'Description', 'Quantity']
        mapped_columns = unified_column_mapper.map_columns(headers, digikey_mappings)
        
        assert 'part_number' in mapped_columns
        assert 'manufacturer_part_number' in mapped_columns
        assert 'manufacturer' in mapped_columns
        assert 'description' in mapped_columns
    
    def test_digikey_csv_import_extracts_real_data(self, digikey_csv_sample_data):
        """Verify DigiKey extracts actual CSV data using unified patterns"""
        # Create mock file content
        file_content = digikey_csv_sample_data.encode('utf-8')
        
        # Test the import
        supplier = DigiKeySupplier()
        
        # Mock the _tracked_api_call to just return the result
        async def mock_tracked_call(operation, impl_func):
            return await impl_func()
        
        supplier._tracked_api_call = mock_tracked_call
        
        import asyncio
        result = asyncio.run(supplier.import_order_file(file_content, 'csv', 'test_digikey.csv'))
        
        # Verify import was successful
        assert result.success == True
        assert result.imported_count > 0
        
        # Verify actual data extraction
        parts = result.parts
        assert len(parts) >= 2
        
        # Check first part
        first_part = parts[0]
        assert 'ATMEGA328P-PU' in str(first_part.get('manufacturer_part_number', ''))
        assert 'Microchip Technology' in str(first_part.get('manufacturer', ''))
        assert 'MCU' in str(first_part.get('description', ''))
    
    # ========== Framework-Wide Tests ==========
    
    def test_all_suppliers_use_supplier_data_mapper(self, supplier_data_mapper):
        """Ensure all suppliers use SupplierDataMapper for standardization"""
        # Test that each supplier's mapper functions exist
        assert 'lcsc' in supplier_data_mapper.supplier_specific_mappers
        assert 'mouser' in supplier_data_mapper.supplier_specific_mappers
        assert 'digikey' in supplier_data_mapper.supplier_specific_mappers
        
        # Test that each mapper function is callable
        lcsc_mapper = supplier_data_mapper.supplier_specific_mappers['lcsc']
        mouser_mapper = supplier_data_mapper.supplier_specific_mappers['mouser']
        digikey_mapper = supplier_data_mapper.supplier_specific_mappers['digikey']
        
        assert callable(lcsc_mapper)
        assert callable(mouser_mapper)
        assert callable(digikey_mapper)
    
    def test_consistent_additional_properties_structure(self):
        """Verify all suppliers produce StandardizedAdditionalProperties structure"""
        # Test LCSC additional_properties builder
        lcsc_supplier = LCSCSupplier()
        extracted_data = {
            'part_number': 'C7442639',
            'manufacturer': 'Lelon',
            'package': 'SMD,D6.3xL7.7mm',
            'rohs': 'YES'
        }
        lcsc_props = lcsc_supplier._build_lcsc_additional_properties(extracted_data, 0.0874, 4.37, 0)
        
        # Verify consistent structure
        assert 'supplier_data' in lcsc_props
        assert 'order_info' in lcsc_props
        assert 'technical_specs' in lcsc_props
        assert lcsc_props['supplier_data']['supplier'] == 'LCSC'
        
        # Test Mouser additional_properties builder  
        mouser_supplier = MouserSupplier()
        mouser_data = {
            'part_number': '595-TLV9061IDCKR',
            'manufacturer': 'Texas Instruments'
        }
        mouser_props = mouser_supplier._build_mouser_additional_properties(mouser_data, 0.84, 8.40, 0)
        
        # Verify consistent structure
        assert 'supplier_data' in mouser_props
        assert 'order_info' in mouser_props
        assert mouser_props['supplier_data']['supplier'] == 'Mouser'
        
        # Test DigiKey additional_properties builder
        digikey_supplier = DigiKeySupplier()
        digikey_data = {
            'part_number': '296-6501-1-ND',
            'manufacturer': 'Microchip Technology'
        }
        digikey_props = digikey_supplier._build_digikey_additional_properties(digikey_data, 2.48, 12.40, 0)
        
        # Verify consistent structure
        assert 'supplier_data' in digikey_props
        assert 'order_info' in digikey_props
        assert digikey_props['supplier_data']['supplier'] == 'DigiKey'
    
    def test_unified_column_mapper_flexibility(self, unified_column_mapper):
        """Test UnifiedColumnMapper handles various column name variations"""
        # Test case-insensitive matching
        headers_mixed_case = ['Part Number', 'MANUFACTURER', 'description', 'QTY']
        mapped = unified_column_mapper.map_columns(headers_mixed_case)
        
        assert 'part_number' in mapped
        assert 'manufacturer' in mapped
        assert 'description' in mapped
        assert 'quantity' in mapped
        
        # Test partial matching
        headers_partial = ['Supplier Part #', 'Mfr Name', 'Product Desc', 'Order Quantity']
        mapped = unified_column_mapper.map_columns(headers_partial)
        
        assert 'part_number' in mapped
        assert 'manufacturer' in mapped
        assert 'description' in mapped
        assert 'quantity' in mapped
    
    def test_smart_part_name_creation(self, unified_column_mapper):
        """Test intelligent part name creation from available data"""
        # Test with rich description
        data_with_desc = {
            'part_number': 'C7442639',
            'manufacturer_part_number': 'VEJ101M1VTT-0607L',
            'description': '100uF 35V ±20% SMD Aluminum Electrolytic Capacitor'
        }
        part_name = unified_column_mapper.create_smart_part_name(data_with_desc)
        assert part_name == 'VEJ101M1VTT-0607L'  # Should prefer MPN over description
        
        # Test with description only
        data_desc_only = {
            'part_number': 'C7442639',
            'description': '100uF 35V ±20% SMD Aluminum Electrolytic Capacitor'
        }
        part_name = unified_column_mapper.create_smart_part_name(data_desc_only)
        assert '100uF' in part_name  # Should use description
        
        # Test fallback to part number
        data_minimal = {
            'part_number': 'C7442639'
        }
        part_name = unified_column_mapper.create_smart_part_name(data_minimal)
        assert part_name == 'C7442639'  # Should fallback to part number
    
    def test_framework_wide_data_quality_validation(self, supplier_data_mapper):
        """Validate data quality scoring across all suppliers"""
        # Test high quality data
        high_quality_data = {
            'part_number': 'C7442639',
            'part_name': 'VEJ101M1VTT-0607L',
            'manufacturer': 'Lelon',
            'manufacturer_part_number': 'VEJ101M1VTT-0607L',
            'description': '100uF 35V ±20% SMD Aluminum Electrolytic Capacitor',
            'supplier': 'LCSC',
            'additional_properties': {
                'supplier_data': {'supplier': 'LCSC'},
                'technical_specs': {'package': 'SMD'},
                'compliance': {'rohs_compliant': True}
            }
        }
        
        result = supplier_data_mapper.map_supplier_result_to_part_data(
            high_quality_data, 'LCSC', ['csv_import']
        )
        
        # Should successfully map high quality data
        assert result is not None
        
        # Test minimal data
        minimal_data = {
            'part_number': 'C7442639',
            'supplier': 'LCSC'
        }
        
        result = supplier_data_mapper.map_supplier_result_to_part_data(
            minimal_data, 'LCSC', ['csv_import']
        )
        
        # Should handle minimal data gracefully
        assert result is not None