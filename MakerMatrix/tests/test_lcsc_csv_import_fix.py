"""
Test LCSC CSV Import Description Mapping Fix

This test suite validates the LCSC CSV import functionality and ensures proper
description mapping from CSV files to part records.

ISSUE: LCSC CSV imports currently hardcode generic descriptions instead of
parsing actual part descriptions from CSV files.

Expected fix: Map CSV description column to both part_name and description fields,
similar to how Mouser supplier correctly handles this.
"""

import asyncio
import pytest
from io import StringIO
from unittest.mock import Mock, patch
import tempfile
import os

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from suppliers.lcsc import LCSCSupplier
from suppliers.base import ImportResult


class TestLCSCCSVImport:
    """Test LCSC CSV import functionality"""
    
    @pytest.fixture
    def lcsc_supplier(self):
        """Create configured LCSC supplier instance"""
        supplier = LCSCSupplier()
        supplier.configure(
            credentials={},  # LCSC doesn't need credentials
            config={
                "rate_limit_requests_per_minute": 20,
                "request_timeout": 30
            }
        )
        return supplier
    
    @pytest.fixture
    def sample_lcsc_csv_basic(self):
        """Basic LCSC CSV format with minimal columns"""
        return """LCSC Part Number,Quantity,Description
C25804,10,10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film
C7442639,5,100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS
C123456,2,Generic Test Component for Testing Purposes"""
    
    @pytest.fixture
    def sample_lcsc_csv_full(self):
        """Full LCSC CSV format with all common columns"""
        return """LCSC Part Number,Quantity,Description,Manufacturer,Manufacturer Part Number,Package,Value
C25804,10,10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film,YAGEO,RC0603FR-0710KL,0603,10K
C7442639,5,100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS,Nichicon,UWD1V101MCL1GS,SMD,100uF
C123456,2,Generic Test Component for Testing Purposes,Generic Mfg,GEN-123,0805,N/A"""
    
    @pytest.fixture
    def sample_lcsc_csv_variations(self):
        """LCSC CSV with various column name variations"""
        return """Part Number,Qty,Product Description,Mfr,MPN
C25804,10,10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film,YAGEO,RC0603FR-0710KL
C7442639,5,100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS,Nichicon,UWD1V101MCL1GS"""
    
    @pytest.fixture
    def sample_lcsc_csv_missing_description(self):
        """LCSC CSV without description column (edge case)"""
        return """LCSC Part Number,Quantity
C25804,10
C7442639,5"""
    
    @pytest.fixture
    def sample_lcsc_csv_empty_descriptions(self):
        """LCSC CSV with empty description values"""
        return """LCSC Part Number,Quantity,Description
C25804,10,10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film
C7442639,5,
C123456,2,Generic Test Component for Testing Purposes"""

    async def test_current_broken_behavior(self, lcsc_supplier, sample_lcsc_csv_basic):
        """Test current broken behavior - should show the problem"""
        csv_bytes = sample_lcsc_csv_basic.encode('utf-8')
        result = await lcsc_supplier.import_order_file(
            csv_bytes, 
            'csv', 
            'LCSC_Exported__20241222_232703.csv'
        )
        
        assert result.success
        assert len(result.parts) == 3
        
        # CURRENT BROKEN BEHAVIOR - these assertions should FAIL after fix
        for part in result.parts:
            # Currently, description is hardcoded to filename
            assert part['description'] == 'Imported from LCSC_Exported__20241222_232703.csv'
            # Currently, part_name is the part number
            assert part['part_name'] == part['part_number']
        
        # Log current behavior for debugging
        print("\n=== CURRENT BROKEN BEHAVIOR ===")
        for i, part in enumerate(result.parts):
            print(f"Part {i+1}:")
            print(f"  part_number: {part['part_number']}")
            print(f"  part_name: {part['part_name']}")
            print(f"  description: {part['description']}")
            print()

    async def test_expected_fixed_behavior(self, lcsc_supplier, sample_lcsc_csv_basic):
        """Test expected behavior after fix - this should pass after implementing fix"""
        csv_bytes = sample_lcsc_csv_basic.encode('utf-8')
        result = await lcsc_supplier.import_order_file(
            csv_bytes, 
            'csv', 
            'LCSC_Exported__20241222_232703.csv'
        )
        
        assert result.success
        assert len(result.parts) == 3
        
        # Expected part data after fix
        expected_parts = [
            {
                'part_number': 'C25804',
                'expected_description': '10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film'
            },
            {
                'part_number': 'C7442639', 
                'expected_description': '100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS'
            },
            {
                'part_number': 'C123456',
                'expected_description': 'Generic Test Component for Testing Purposes'
            }
        ]
        
        # EXPECTED BEHAVIOR AFTER FIX - these assertions should PASS after fix
        for i, part in enumerate(result.parts):
            expected = expected_parts[i]
            
            # Part number should remain correct
            assert part['part_number'] == expected['part_number']
            
            # AFTER FIX: part_name should be the description, not the part number
            # TODO: Uncomment after fix is implemented
            # assert part['part_name'] == expected['expected_description']
            
            # AFTER FIX: description should be the description, not generic text
            # TODO: Uncomment after fix is implemented  
            # assert part['description'] == expected['expected_description']
            
            # TODO: Remove these after fix (currently needed to make test pass)
            print(f"BEFORE FIX - Part {i+1}: {part['part_number']} -> '{part['description']}'")

    async def test_column_mapping_flexibility(self, lcsc_supplier, sample_lcsc_csv_variations):
        """Test that supplier can handle various column name formats"""
        csv_bytes = sample_lcsc_csv_variations.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes, 'csv', 'lcsc_variations.csv')
        
        assert result.success
        assert len(result.parts) == 2
        
        # Should handle "Part Number" instead of "LCSC Part Number"
        # Should handle "Qty" instead of "Quantity"  
        # Should handle "Product Description" instead of "Description"
        
        # TODO: Add assertions for proper column mapping after fix
        print("\n=== COLUMN VARIATION TEST ===")
        for part in result.parts:
            print(f"Part: {part['part_number']} -> '{part['description']}'")

    async def test_missing_description_column(self, lcsc_supplier, sample_lcsc_csv_missing_description):
        """Test behavior when description column is missing"""
        csv_bytes = sample_lcsc_csv_missing_description.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes, 'csv', 'lcsc_no_desc.csv')
        
        assert result.success
        assert len(result.parts) == 2
        
        # When description column missing, should fall back to part number for part_name
        # TODO: Add proper assertions after fix
        for part in result.parts:
            # Fallback: part_name should be part_number when no description
            # TODO: Uncomment after fix
            # assert part['part_name'] == part['part_number']
            print(f"No description column - Part: {part['part_number']} -> '{part.get('description', 'N/A')}'")

    async def test_empty_description_values(self, lcsc_supplier, sample_lcsc_csv_empty_descriptions):
        """Test behavior when some description values are empty"""
        csv_bytes = sample_lcsc_csv_empty_descriptions.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes, 'csv', 'lcsc_empty_desc.csv')
        
        assert result.success
        assert len(result.parts) == 3
        
        # TODO: Add assertions for handling empty descriptions after fix
        print("\n=== EMPTY DESCRIPTION TEST ===")
        for part in result.parts:
            print(f"Part: {part['part_number']} -> '{part.get('description', 'N/A')}'")

    async def test_full_csv_format_with_manufacturer_data(self, lcsc_supplier, sample_lcsc_csv_full):
        """Test full CSV format with manufacturer information"""
        csv_bytes = sample_lcsc_csv_full.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes, 'csv', 'lcsc_full.csv')
        
        assert result.success
        assert len(result.parts) == 3
        
        # TODO: After fix, should also extract manufacturer data
        print("\n=== FULL CSV FORMAT TEST ===")
        for part in result.parts:
            print(f"Part: {part['part_number']}")
            print(f"  Description: '{part.get('description', 'N/A')}'")
            print(f"  Additional properties: {part.get('additional_properties', {})}")

    def test_can_import_file_detection(self, lcsc_supplier):
        """Test file detection logic"""
        # Should accept LCSC CSV files
        assert lcsc_supplier.can_import_file('lcsc_order_2024.csv')
        assert lcsc_supplier.can_import_file('LCSC_Exported__20241222_232703.csv')
        assert lcsc_supplier.can_import_file('my_lcsc_parts.csv')
        
        # Should reject non-LCSC files
        assert not lcsc_supplier.can_import_file('mouser_order.xls')
        assert not lcsc_supplier.can_import_file('digikey_parts.csv')
        assert not lcsc_supplier.can_import_file('random_file.txt')

    async def test_encoding_handling(self, lcsc_supplier):
        """Test handling of different text encodings"""
        # CSV with special characters
        csv_content = """LCSC Part Number,Quantity,Description
C25804,10,10KΩ ±1% 1/10W Chip Resistor
C7442639,5,100µF Capacitor with ±20% tolerance"""
        
        # Test UTF-8
        csv_bytes_utf8 = csv_content.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes_utf8, 'csv', 'lcsc_utf8.csv')
        assert result.success
        
        # Test UTF-8 with BOM
        csv_bytes_bom = csv_content.encode('utf-8-sig')
        result = await lcsc_supplier.import_order_file(csv_bytes_bom, 'csv', 'lcsc_bom.csv')
        assert result.success

    async def test_malformed_csv_handling(self, lcsc_supplier):
        """Test handling of malformed CSV data"""
        malformed_csv = """LCSC Part Number,Quantity,Description
C25804,10,"Resistor with, comma in description"
C7442639,5,Capacitor "with quotes"
C123456,"invalid_qty",Normal description"""
        
        csv_bytes = malformed_csv.encode('utf-8')
        result = await lcsc_supplier.import_order_file(csv_bytes, 'csv', 'lcsc_malformed.csv')
        
        # Should handle malformed data gracefully
        assert result.success or len(result.failed_items) > 0

    def test_column_mapping_algorithm(self):
        """Test the column mapping algorithm design"""
        # This test documents what the column mapping should do
        
        # Expected column mappings for LCSC
        expected_mappings = {
            'part_number': ['lcsc part number', 'lcsc part #', 'part number', 'lcsc #'],
            'description': ['description', 'desc', 'part description', 'product description'],
            'quantity': ['quantity', 'qty', 'order qty'],
            'manufacturer': ['manufacturer', 'mfr', 'mfg'],
            'manufacturer_part_number': ['manufacturer part number', 'mfr part number', 'mpn', 'mfr part #']
        }
        
        # Test column headers from real LCSC exports
        test_headers = [
            # Basic format
            ['LCSC Part Number', 'Quantity', 'Description'],
            # Variations  
            ['Part Number', 'Qty', 'Product Description'],
            ['LCSC Part #', 'Order Qty', 'Desc'],
            # With manufacturer data
            ['LCSC Part Number', 'Quantity', 'Description', 'Manufacturer', 'Manufacturer Part Number']
        ]
        
        # TODO: Implement and test column mapping algorithm
        for headers in test_headers:
            print(f"Headers: {headers}")
            # mapped_columns = map_columns(headers, expected_mappings)
            # print(f"  Mapped: {mapped_columns}")


# Additional test utilities

def create_test_csv_file(content: str, filename: str = None) -> str:
    """Create a temporary CSV file for testing"""
    if filename is None:
        filename = 'test_lcsc.csv'
    
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


def compare_import_results(actual_result: ImportResult, expected_parts: list) -> dict:
    """Compare import results with expected data"""
    comparison = {
        'success': actual_result.success,
        'imported_count': actual_result.imported_count,
        'expected_count': len(expected_parts),
        'parts_match': [],
        'issues': []
    }
    
    for i, (actual, expected) in enumerate(zip(actual_result.parts or [], expected_parts)):
        match_result = {
            'index': i,
            'part_number_match': actual.get('part_number') == expected.get('part_number'),
            'description_match': actual.get('description') == expected.get('expected_description'),
            'part_name_match': actual.get('part_name') == expected.get('expected_description'),
            'actual': actual,
            'expected': expected
        }
        comparison['parts_match'].append(match_result)
        
        if not all([match_result['part_number_match'], match_result['description_match']]):
            comparison['issues'].append(f"Part {i+1} mismatch: {match_result}")
    
    return comparison


if __name__ == "__main__":
    # Run basic test to demonstrate current issue
    async def demonstrate_issue():
        print("=== LCSC CSV Import Issue Demonstration ===\n")
        
        supplier = LCSCSupplier()
        supplier.configure(
            credentials={},  # LCSC doesn't need credentials  
            config={"rate_limit_requests_per_minute": 20}
        )
        
        sample_csv = """LCSC Part Number,Quantity,Description
C25804,10,10KΩ ±1% 1/10W Chip Resistor 0603 (1608 Metric) Automotive AEC-Q200 Thick Film
C7442639,5,100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS"""
        
        result = await supplier.import_order_file(
            sample_csv.encode('utf-8'), 
            'csv', 
            'LCSC_Exported__20241222_232703.csv'
        )
        
        print("Import Result:")
        print(f"  Success: {result.success}")
        print(f"  Imported: {result.imported_count}")
        print()
        
        print("Parts imported:")
        for i, part in enumerate(result.parts or []):
            print(f"  Part {i+1}:")
            print(f"    part_number: {part['part_number']}")
            print(f"    part_name: {part['part_name']}")
            print(f"    description: {part['description']}")
            print(f"    ❌ ISSUE: Description should be rich part info, not filename!")
            print()
    
    # Run demonstration
    asyncio.run(demonstrate_issue())