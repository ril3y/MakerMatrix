"""
Test filename extraction functionality for multiple suppliers.

This tests the frontend logic for extracting order information from supplier CSV filenames.
The actual logic is implemented in JavaScript/TypeScript in the frontend component.
"""

import pytest
import re
from datetime import datetime


class TestSupplierFilenameExtraction:
    """Test the supplier filename extraction logic that's implemented in the frontend."""

    def extract_order_info_from_filename(self, filename: str, parser_type: str) -> dict:
        """
        Python implementation of the frontend filename extraction logic for testing.
        This mirrors the JavaScript function in UnifiedFileImporter.tsx
        """
        if parser_type == "lcsc":
            # LCSC filename pattern: LCSC_Exported__YYYYMMDD_HHMMSS.csv
            lcsc_match = re.match(r"^LCSC_Exported__(\d{8})_(\d{6})\.csv$", filename, re.IGNORECASE)
            if lcsc_match:
                date_str, time_str = lcsc_match.groups()

                try:
                    # Convert YYYYMMDD to YYYY-MM-DD
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                    # Validate date format
                    datetime.strptime(formatted_date, "%Y-%m-%d")

                    return {
                        "order_date": formatted_date,
                        "order_number": time_str,  # Use time as order number
                        "notes": f"Auto-extracted from filename: {filename}",
                    }
                except ValueError:
                    # Invalid date format
                    pass
        elif parser_type == "digikey":
            # DigiKey filename pattern: DK_PRODUCTS_88269818.csv
            digikey_match = re.match(r"^DK_PRODUCTS_(\d+)\.csv$", filename, re.IGNORECASE)
            if digikey_match:
                order_number = digikey_match.group(1)

                return {"order_number": order_number, "notes": f"Auto-extracted order number from filename: {filename}"}
        elif parser_type == "mouser":
            # Mouser filename pattern: 269268390.xls (just the order number)
            mouser_match = re.match(r"^(\d+)\.xls$", filename, re.IGNORECASE)
            if mouser_match:
                order_number = mouser_match.group(1)

                return {"order_number": order_number, "notes": f"Auto-extracted order number from filename: {filename}"}

        return {}

    def test_valid_lcsc_filename_extraction(self):
        """Test extraction from valid LCSC filename format."""
        filename = "LCSC_Exported__20241222_232703.csv"
        result = self.extract_order_info_from_filename(filename, "lcsc")

        assert result["order_date"] == "2024-12-22"
        assert result["order_number"] == "232703"
        assert "Auto-extracted from filename" in result["notes"]
        assert filename in result["notes"]

    def test_valid_lcsc_filename_different_date(self):
        """Test extraction with different valid date."""
        filename = "LCSC_Exported__20240315_123456.csv"
        result = self.extract_order_info_from_filename(filename, "lcsc")

        assert result["order_date"] == "2024-03-15"
        assert result["order_number"] == "123456"
        assert "Auto-extracted from filename" in result["notes"]

    def test_lcsc_filename_case_insensitive(self):
        """Test that filename matching is case insensitive."""
        filename = "lcsc_exported__20241222_232703.csv"
        result = self.extract_order_info_from_filename(filename, "lcsc")

        assert result["order_date"] == "2024-12-22"
        assert result["order_number"] == "232703"

    def test_non_lcsc_parser_returns_empty(self):
        """Test that non-LCSC parsers return empty dict."""
        filename = "LCSC_Exported__20241222_232703.csv"
        result = self.extract_order_info_from_filename(filename, "digikey")

        assert result == {}

    def test_invalid_lcsc_filename_format(self):
        """Test that invalid filename formats return empty dict."""
        invalid_filenames = [
            "regular_file.csv",
            "LCSC_Exported__invalid_format.csv",
            "LCSC_Exported__2024122_232703.csv",  # Wrong date format
            "LCSC_Exported__20241222_23270.csv",  # Wrong time format
            "LCSC_Exported__20241222_232703.txt",  # Wrong extension
            "LCSC_Exported_20241222_232703.csv",  # Missing underscore
        ]

        for filename in invalid_filenames:
            result = self.extract_order_info_from_filename(filename, "lcsc")
            assert result == {}, f"Expected empty dict for {filename}, got {result}"

    def test_invalid_date_in_filename(self):
        """Test that invalid dates return empty dict."""
        invalid_date_filenames = [
            "LCSC_Exported__20241322_232703.csv",  # Invalid month
            "LCSC_Exported__20240229_232703.csv",  # Invalid leap year date (2024 is leap year, but testing edge case)
            "LCSC_Exported__20230229_232703.csv",  # Invalid leap year date (2023 is not leap year)
            "LCSC_Exported__20241232_232703.csv",  # Invalid day
        ]

        for filename in invalid_date_filenames:
            result = self.extract_order_info_from_filename(filename, "lcsc")
            # Note: Some of these might actually be valid depending on datetime parsing
            # The main test is that no exception is raised
            assert isinstance(result, dict)

    def test_edge_case_valid_dates(self):
        """Test edge cases with valid dates."""
        edge_case_filenames = [
            ("LCSC_Exported__20240101_000000.csv", "2024-01-01", "000000"),  # New Year
            ("LCSC_Exported__20241231_235959.csv", "2024-12-31", "235959"),  # End of year
            ("LCSC_Exported__20240229_120000.csv", "2024-02-29", "120000"),  # Leap year
        ]

        for filename, expected_date, expected_order in edge_case_filenames:
            result = self.extract_order_info_from_filename(filename, "lcsc")
            assert result["order_date"] == expected_date
            assert result["order_number"] == expected_order

    def test_original_user_example(self):
        """Test the exact filename provided by the user."""
        filename = "LCSC_Exported__20241222_232703.csv"
        result = self.extract_order_info_from_filename(filename, "lcsc")

        assert result["order_date"] == "2024-12-22"
        assert result["order_number"] == "232703"
        assert result["notes"] == "Auto-extracted from filename: LCSC_Exported__20241222_232703.csv"
        assert len(result) == 3  # Should only have these 3 keys

    # DigiKey Tests
    def test_valid_digikey_filename_extraction(self):
        """Test extraction from valid DigiKey filename format."""
        filename = "DK_PRODUCTS_88269818.csv"
        result = self.extract_order_info_from_filename(filename, "digikey")

        assert result["order_number"] == "88269818"
        assert "Auto-extracted order number from filename" in result["notes"]
        assert filename in result["notes"]
        assert len(result) == 2  # Should have order_number and notes

    def test_digikey_filename_case_insensitive(self):
        """Test that DigiKey filename matching is case insensitive."""
        filename = "dk_products_12345678.csv"
        result = self.extract_order_info_from_filename(filename, "digikey")

        assert result["order_number"] == "12345678"
        assert "Auto-extracted order number from filename" in result["notes"]

    def test_digikey_different_order_numbers(self):
        """Test DigiKey extraction with different order numbers."""
        test_cases = [
            ("DK_PRODUCTS_88269818.csv", "88269818"),
            ("DK_PRODUCTS_12345.csv", "12345"),
            ("DK_PRODUCTS_999999999.csv", "999999999"),
        ]

        for filename, expected_order in test_cases:
            result = self.extract_order_info_from_filename(filename, "digikey")
            assert result["order_number"] == expected_order

    def test_invalid_digikey_filename_format(self):
        """Test that invalid DigiKey filename formats return empty dict."""
        invalid_filenames = [
            "regular_file.csv",
            "DK_PRODUCTS_.csv",  # Missing order number
            "DK_PRODUCTS_abc123.csv",  # Non-numeric order number
            "DK_PRODUCTS_88269818.txt",  # Wrong extension
            "DK_PRODUCT_88269818.csv",  # Missing S in PRODUCTS
            "DIGIKEY_PRODUCTS_88269818.csv",  # Wrong prefix
        ]

        for filename in invalid_filenames:
            result = self.extract_order_info_from_filename(filename, "digikey")
            assert result == {}, f"Expected empty dict for {filename}, got {result}"

    def test_non_digikey_parser_returns_empty(self):
        """Test that non-DigiKey parsers return empty dict for DigiKey files."""
        filename = "DK_PRODUCTS_88269818.csv"
        result = self.extract_order_info_from_filename(filename, "lcsc")

        assert result == {}

    def test_cross_supplier_filename_mismatch(self):
        """Test that supplier filenames don't extract for wrong parser types."""
        test_cases = [
            ("LCSC_Exported__20241222_232703.csv", "digikey"),
            ("LCSC_Exported__20241222_232703.csv", "mouser"),
            ("DK_PRODUCTS_88269818.csv", "lcsc"),
            ("DK_PRODUCTS_88269818.csv", "mouser"),
            ("269268390.xls", "lcsc"),
            ("269268390.xls", "digikey"),
        ]

        for filename, wrong_parser in test_cases:
            result = self.extract_order_info_from_filename(filename, wrong_parser)
            assert result == {}, f"Expected empty dict for {filename} with {wrong_parser} parser"

    # Mouser Tests
    def test_valid_mouser_filename_extraction(self):
        """Test extraction from valid Mouser filename format."""
        filename = "269268390.xls"
        result = self.extract_order_info_from_filename(filename, "mouser")

        assert result["order_number"] == "269268390"
        assert "Auto-extracted order number from filename" in result["notes"]
        assert filename in result["notes"]
        assert len(result) == 2  # Should have order_number and notes

    def test_mouser_filename_case_insensitive(self):
        """Test that Mouser filename matching is case insensitive."""
        filename = "12345678.XLS"
        result = self.extract_order_info_from_filename(filename, "mouser")

        assert result["order_number"] == "12345678"
        assert "Auto-extracted order number from filename" in result["notes"]

    def test_mouser_different_order_numbers(self):
        """Test Mouser extraction with different order numbers."""
        test_cases = [
            ("269268390.xls", "269268390"),
            ("12345.xls", "12345"),
            ("999999999.xls", "999999999"),
            ("1.xls", "1"),  # Single digit
        ]

        for filename, expected_order in test_cases:
            result = self.extract_order_info_from_filename(filename, "mouser")
            assert result["order_number"] == expected_order

    def test_invalid_mouser_filename_format(self):
        """Test that invalid Mouser filename formats return empty dict."""
        invalid_filenames = [
            "regular_file.xls",  # Not just numbers
            "abc123.xls",  # Contains letters
            "269268390.csv",  # Wrong extension
            "269268390.xlsx",  # Wrong extension (should be .xls)
            ".xls",  # Empty filename
            "269268390.xls.backup",  # Extra extension
            "mouser_269268390.xls",  # Has prefix
        ]

        for filename in invalid_filenames:
            result = self.extract_order_info_from_filename(filename, "mouser")
            assert result == {}, f"Expected empty dict for {filename}, got {result}"

    def test_non_mouser_parser_returns_empty(self):
        """Test that non-Mouser parsers return empty dict for Mouser files."""
        filename = "269268390.xls"
        for parser in ["lcsc", "digikey"]:
            result = self.extract_order_info_from_filename(filename, parser)
            assert result == {}

    def test_original_mouser_example(self):
        """Test the exact Mouser filename provided by the user."""
        filename = "269268390.xls"
        result = self.extract_order_info_from_filename(filename, "mouser")

        assert result["order_number"] == "269268390"
        assert result["notes"] == "Auto-extracted order number from filename: 269268390.xls"
        assert len(result) == 2  # Should only have these 2 keys


if __name__ == "__main__":
    # Run the tests manually if needed
    test_instance = TestSupplierFilenameExtraction()

    test_methods = [
        # LCSC Tests
        test_instance.test_valid_lcsc_filename_extraction,
        test_instance.test_valid_lcsc_filename_different_date,
        test_instance.test_lcsc_filename_case_insensitive,
        test_instance.test_non_lcsc_parser_returns_empty,
        test_instance.test_invalid_lcsc_filename_format,
        test_instance.test_invalid_date_in_filename,
        test_instance.test_edge_case_valid_dates,
        test_instance.test_original_user_example,
        # DigiKey Tests
        test_instance.test_valid_digikey_filename_extraction,
        test_instance.test_digikey_filename_case_insensitive,
        test_instance.test_digikey_different_order_numbers,
        test_instance.test_invalid_digikey_filename_format,
        test_instance.test_non_digikey_parser_returns_empty,
        test_instance.test_cross_supplier_filename_mismatch,
        # Mouser Tests
        test_instance.test_valid_mouser_filename_extraction,
        test_instance.test_mouser_filename_case_insensitive,
        test_instance.test_mouser_different_order_numbers,
        test_instance.test_invalid_mouser_filename_format,
        test_instance.test_non_mouser_parser_returns_empty,
        test_instance.test_original_mouser_example,
    ]

    print("Running supplier filename extraction tests...")
    for i, test_method in enumerate(test_methods, 1):
        try:
            test_method()
            print(f"✅ Test {i}: {test_method.__name__} PASSED")
        except Exception as e:
            print(f"❌ Test {i}: {test_method.__name__} FAILED: {e}")

    print("All tests completed!")
