import pytest
from MakerMatrix.services.csv_import.lcsc_parser import LCSCParser
from MakerMatrix.services.csv_import.digikey_parser import DigikeyParser
from MakerMatrix.services.csv_import.mouser_parser import MouserParser


class TestLCSCParser:
    """Unit tests for LCSC CSV parser"""

    def setup_method(self):
        self.parser = LCSCParser()

    def test_parser_info(self):
        """Test parser information"""
        info = self.parser.get_info()
        assert info['type'] == 'lcsc'
        assert info['name'] == 'LCSC'
        assert 'LCSC Part Number' in info['required_columns']
        assert 'Manufacture Part Number' in info['required_columns']

    def test_can_parse_valid_headers(self):
        """Test detection of valid LCSC headers"""
        valid_headers = [
            'LCSC Part Number', 'Manufacture Part Number', 
            'Description', 'Order Qty.', 'Unit Price($)'
        ]
        assert self.parser.can_parse(valid_headers) is True

    def test_can_parse_invalid_headers(self):
        """Test rejection of invalid headers"""
        invalid_headers = ['Random Header', 'Another Header']
        assert self.parser.can_parse(invalid_headers) is False

    def test_filename_extraction_valid(self):
        """Test valid LCSC filename pattern extraction"""
        result = self.parser.extract_order_info_from_filename("LCSC_Exported__20241222_232705.csv")
        assert result is not None
        assert result['order_date'] == '2024-12-22'
        assert result['order_number'] == '232705'
        assert result['supplier'] == 'LCSC'

    def test_filename_extraction_invalid(self):
        """Test invalid filename patterns"""
        # Invalid format
        assert self.parser.extract_order_info_from_filename("random_file.csv") is None
        
        # Wrong date format
        assert self.parser.extract_order_info_from_filename("LCSC_Exported__2024122_232705.csv") is None
        
        # Missing extension
        assert self.parser.extract_order_info_from_filename("LCSC_Exported__20241222_232705") is None

    def test_parse_valid_row(self):
        """Test parsing a valid LCSC CSV row"""
        row = {
            'LCSC Part Number': 'C1525',
            'Manufacture Part Number': 'STM32F405RGT6',
            'Manufacturer': 'STMicroelectronics',
            'Description': 'ARM Microcontrollers - MCU',
            'Package': 'LQFP-64_10x10x05P',
            'Order Qty.': '2',
            'Unit Price($)': '5.23',
            'Order Price($)': '10.46',
            'Customer NO.': 'REF001',
            'RoHS': 'Yes'
        }

        result = self.parser.parse_row(row, 2)
        
        assert result is not None
        assert result['part_name'] == 'STM32F405RGT6'
        assert result['part_number'] == 'STM32F405RGT6'
        assert result['quantity'] == 2
        assert result['supplier'] == 'LCSC'
        
        properties = result['properties']
        assert properties['lcsc_part_number'] == 'C1525'
        assert properties['manufacturer'] == 'STMicroelectronics'
        assert properties['unit_price'] == 5.23
        assert properties['order_price'] == 10.46
        assert properties['package'] == 'LQFP-64_10x10x05P'

    def test_parse_row_missing_required_fields(self):
        """Test parsing row with missing required fields"""
        row = {
            'LCSC Part Number': '',  # Missing
            'Manufacture Part Number': 'STM32F405RGT6',
            'Description': 'ARM Microcontrollers - MCU',
            'Order Qty.': '2'
        }

        result = self.parser.parse_row(row, 2)
        assert result is None  # Should skip rows with missing part numbers

    def test_parse_row_invalid_quantity(self):
        """Test parsing row with invalid quantity"""
        row = {
            'LCSC Part Number': 'C1525',
            'Manufacture Part Number': 'STM32F405RGT6',
            'Description': 'ARM Microcontrollers - MCU',
            'Order Qty.': 'invalid'  # Invalid quantity
        }

        # Should handle gracefully and default to 0 or skip
        result = self.parser.parse_row(row, 2)
        if result:
            assert result['quantity'] == 0

    def test_component_classification(self):
        """Test automatic component classification"""
        # Test resistor classification
        resistor_row = {
            'LCSC Part Number': 'C1234',
            'Manufacture Part Number': 'RC0603FR-071KL',
            'Description': 'Thick Film Resistor 1K 1% 0603',
            'Order Qty.': '1'
        }
        
        result = self.parser.parse_row(resistor_row, 2)
        assert result is not None
        assert 'Resistors' in result.get('categories', [])
        assert result['properties']['component_type'] == 'Resistor'

        # Test capacitor classification
        capacitor_row = {
            'LCSC Part Number': 'C5678',
            'Manufacture Part Number': 'C1206X7R1A105K',
            'Description': 'MLCC Ceramic Capacitor 1uF 10V',
            'Order Qty.': '1'
        }
        
        result = self.parser.parse_row(capacitor_row, 2)
        assert result is not None
        assert 'Capacitors' in result.get('categories', [])
        assert result['properties']['component_type'] == 'Capacitor'

    def test_price_parsing(self):
        """Test price parsing with various formats"""
        row = {
            'LCSC Part Number': 'C1525',
            'Manufacture Part Number': 'STM32F405RGT6',
            'Description': 'MCU',
            'Order Qty.': '1',
            'Unit Price($)': '5.23',
            'Order Price($)': '5.23'
        }

        result = self.parser.parse_row(row, 2)
        assert result['properties']['unit_price'] == 5.23
        assert result['properties']['order_price'] == 5.23


class TestDigiKeyParser:
    """Unit tests for DigiKey CSV parser"""

    def setup_method(self):
        self.parser = DigikeyParser()

    def test_parser_info(self):
        """Test DigiKey parser information"""
        info = self.parser.get_info()
        assert info['type'] == 'digikey'
        assert info['name'] == 'DigiKey'
        assert 'DigiKey Part #' in info['required_columns']

    def test_can_parse_valid_headers(self):
        """Test detection of valid DigiKey headers"""
        valid_headers = [
            'DigiKey Part #', 'Manufacturer Part Number', 
            'Description', 'Quantity', 'Unit Price'
        ]
        assert self.parser.can_parse(valid_headers) is True

    def test_parse_valid_row(self):
        """Test parsing a valid DigiKey CSV row"""
        row = {
            'DigiKey Part #': 'STM32F405RGT6CT-ND',
            'Manufacturer Part Number': 'STM32F405RGT6',
            'Description': 'IC MCU 32BIT 1MB FLASH 64LQFP',
            'Quantity': '2',
            'Unit Price': '6.45',
            'Extended Price': '12.90',
            'Customer Reference': 'REF001'
        }

        result = self.parser.parse_row(row, 2)
        
        assert result is not None
        assert result['part_name'] == 'STM32F405RGT6'
        assert result['part_number'] == 'STM32F405RGT6'
        assert result['quantity'] == 2
        assert result['supplier'] == 'DigiKey'
        
        properties = result['properties']
        assert properties['supplier_part_number'] == 'STM32F405RGT6CT-ND'
        assert properties['unit_price'] == 6.45
        assert properties['extended_price'] == 12.90


class TestMouserParser:
    """Unit tests for Mouser CSV parser"""

    def setup_method(self):
        self.parser = MouserParser()

    def test_parser_info(self):
        """Test Mouser parser information"""
        info = self.parser.get_info()
        assert info['type'] == 'mouser'
        assert info['name'] == 'Mouser'
        assert 'Mouser Part #' in info['required_columns']

    def test_can_parse_valid_headers(self):
        """Test detection of valid Mouser headers"""
        valid_headers = [
            'Mouser Part #', 'Manufacturer Part Number', 
            'Description', 'Quantity', 'Unit Price'
        ]
        assert self.parser.can_parse(valid_headers) is True

    def test_parse_valid_row(self):
        """Test parsing a valid Mouser CSV row"""
        row = {
            'Mouser Part #': '511-STM32F405RGT6',
            'Manufacturer Part Number': 'STM32F405RGT6',
            'Manufacturer': 'STMicroelectronics',
            'Description': 'ARM MCU 32-bit Cortex-M4',
            'Quantity': '3',
            'Unit Price': '7.20',
            'Extended Price': '21.60'
        }

        result = self.parser.parse_row(row, 2)
        
        assert result is not None
        assert result['part_name'] == 'STM32F405RGT6'
        assert result['part_number'] == 'STM32F405RGT6'
        assert result['quantity'] == 3
        assert result['supplier'] == 'Mouser'
        
        properties = result['properties']
        assert properties['mouser_part_number'] == '511-STM32F405RGT6'
        assert properties['manufacturer'] == 'STMicroelectronics'
        assert properties['unit_price'] == 7.20


class TestBaseParserUtilities:
    """Test base parser utility functions"""

    def setup_method(self):
        self.parser = LCSCParser()

    def test_clean_string(self):
        """Test string cleaning utility"""
        assert self.parser.clean_string("  test  ") == "test"
        assert self.parser.clean_string("") == ""
        assert self.parser.clean_string(None) == ""

    def test_parse_quantity(self):
        """Test quantity parsing utility"""
        assert self.parser.parse_quantity("10") == 10
        assert self.parser.parse_quantity("0") == 0
        assert self.parser.parse_quantity("invalid") == 0
        assert self.parser.parse_quantity("") == 0

    def test_parse_price(self):
        """Test price parsing utility"""
        assert self.parser.parse_price("5.23") == 5.23
        assert self.parser.parse_price("$5.23") == 5.23
        assert self.parser.parse_price("0") == 0.0
        assert self.parser.parse_price("invalid") == 0.0
        assert self.parser.parse_price("") == 0.0

    def test_should_skip_row(self):
        """Test row skipping logic"""
        # Test empty row
        empty_row = {}
        assert self.parser.should_skip_row(empty_row) is True
        
        # Test row with only empty values
        empty_values_row = {"col1": "", "col2": None, "col3": "   "}
        assert self.parser.should_skip_row(empty_values_row) is True
        
        # Test valid row
        valid_row = {"LCSC Part Number": "C1234", "Manufacture Part Number": "Test"}
        assert self.parser.should_skip_row(valid_row) is False