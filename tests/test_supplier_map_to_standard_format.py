"""
Test map_to_standard_format() for all suppliers

Verifies that all suppliers properly flatten their data into simple key-value pairs
for clean display in the frontend.
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from MakerMatrix.suppliers.base import PartSearchResult
from MakerMatrix.suppliers.registry import get_supplier


class TestLCSCMapping:
    """Test LCSC supplier map_to_standard_format()"""

    def test_lcsc_flattens_specifications(self):
        """Test that LCSC flattens specifications into additional_properties"""
        lcsc = get_supplier("lcsc")
        assert lcsc is not None, "LCSC supplier not found in registry"
        assert hasattr(lcsc, "map_to_standard_format"), "LCSC missing map_to_standard_format method"

        # Create test data with specifications
        test_result = PartSearchResult(
            supplier_part_number="C25804",
            manufacturer="Test Manufacturer",
            manufacturer_part_number="TEST-123",
            description="10K Ohm Resistor",
            category="Resistors",
            image_url="https://example.com/image.jpg",
            datasheet_url="https://example.com/datasheet.pdf",
            specifications={"resistance": "10K", "tolerance": "1%", "package": "0805", "power_rating": "0.125W"},
            additional_data={"is_smt": True, "part_type": "resistor", "lcsc_price": 0.01},
        )

        # Map to standard format
        mapped = lcsc.map_to_standard_format(test_result)

        # Verify core fields
        assert mapped["supplier_part_number"] == "C25804"
        assert mapped["manufacturer"] == "Test Manufacturer"
        assert mapped["description"] == "10K Ohm Resistor"
        assert mapped["category"] == "Resistors"
        assert mapped["image_url"] == "https://example.com/image.jpg"
        assert mapped["datasheet_url"] == "https://example.com/datasheet.pdf"

        # Verify specifications are flattened (no nested dicts)
        assert "specifications" not in mapped, "Should not have nested specifications key"

        # Verify additional_data is flattened
        assert "Is Smt" in mapped or "is_smt" in mapped  # Field name formatting may vary
        assert "Part Type" in mapped or "part_type" in mapped

    def test_lcsc_handles_empty_data(self):
        """Test LCSC handles empty/null data gracefully"""
        lcsc = get_supplier("lcsc")

        test_result = PartSearchResult(supplier_part_number="C12345", specifications=None, additional_data=None)

        mapped = lcsc.map_to_standard_format(test_result)

        assert mapped["supplier_part_number"] == "C12345"
        # Should not crash with None values


class TestAdafruitMapping:
    """Test Adafruit supplier map_to_standard_format()"""

    def test_adafruit_flattens_specifications(self):
        """Test that Adafruit flattens specifications"""
        adafruit = get_supplier("adafruit")
        assert adafruit is not None, "Adafruit supplier not found in registry"
        assert hasattr(adafruit, "map_to_standard_format"), "Adafruit missing map_to_standard_format method"

        test_result = PartSearchResult(
            supplier_part_number="3571",
            manufacturer="Adafruit Industries",
            description="LED Strip",
            specifications={"length": "1m", "led_count": "60", "voltage": "5V"},
            additional_data={"source": "web_scraping", "product_url": "https://adafruit.com/product/3571"},
        )

        mapped = adafruit.map_to_standard_format(test_result)

        # Verify core fields
        assert mapped["supplier_part_number"] == "3571"
        assert mapped["manufacturer"] == "Adafruit Industries"

        # Verify specifications are flattened
        assert "specifications" not in mapped

        # Verify internal fields are skipped
        assert "source" not in mapped  # Should be filtered out


class TestMcMasterMapping:
    """Test McMaster-Carr supplier map_to_standard_format()"""

    def test_mcmaster_flattens_specifications(self):
        """Test that McMaster flattens scraped specifications"""
        mcmaster = get_supplier("mcmaster-carr")
        assert mcmaster is not None, "McMaster-Carr supplier not found in registry"
        assert hasattr(mcmaster, "map_to_standard_format"), "McMaster missing map_to_standard_format method"

        test_result = PartSearchResult(
            supplier_part_number="91253A192",
            manufacturer="McMaster-Carr",
            manufacturer_part_number="91253A192",
            description="Black-Oxide Alloy Steel Socket Head Screw",
            category="Fasteners",
            image_url="https://mcmaster.com/image.jpg",
            specifications={
                "material": "Black-Oxide Alloy Steel",
                "thread_size": "M3 x 0.5mm",
                "length": "15mm",
                "head_type": "Socket Head",
                "drive_style": "Hex",
            },
            additional_data={
                "source": "web_scraping",
                "scraped_at": "2025-01-01T00:00:00",
                "url": "https://mcmaster.com/91253A192",
            },
        )

        mapped = mcmaster.map_to_standard_format(test_result)

        # Verify core fields
        assert mapped["supplier_part_number"] == "91253A192"
        assert mapped["description"] == "Black-Oxide Alloy Steel Socket Head Screw"

        # Verify specifications are flattened with readable names
        assert "Material" in mapped
        assert mapped["Material"] == "Black-Oxide Alloy Steel"
        assert "Thread Size" in mapped
        assert mapped["Thread Size"] == "M3 x 0.5mm"

        # Verify internal tracking fields are excluded
        assert "source" not in mapped
        assert "scraped_at" not in mapped


class TestAllSuppliersHaveMethod:
    """Verify all suppliers implement map_to_standard_format()"""

    @pytest.mark.parametrize(
        "supplier_name", ["lcsc", "adafruit", "mcmaster-carr", "digikey", "mouser", "boltdepot", "seeedstudio"]
    )
    def test_supplier_has_map_to_standard_format(self, supplier_name):
        """Test that each supplier has the map_to_standard_format method"""
        supplier = get_supplier(supplier_name)
        assert supplier is not None, f"{supplier_name} not found in registry"
        assert hasattr(supplier, "map_to_standard_format"), f"{supplier_name} missing map_to_standard_format method"

    @pytest.mark.parametrize(
        "supplier_name", ["lcsc", "adafruit", "mcmaster-carr", "digikey", "mouser", "boltdepot", "seeedstudio"]
    )
    def test_supplier_returns_dict(self, supplier_name):
        """Test that map_to_standard_format returns a dict"""
        supplier = get_supplier(supplier_name)

        test_result = PartSearchResult(supplier_part_number="TEST-123", description="Test Part")

        mapped = supplier.map_to_standard_format(test_result)

        assert isinstance(mapped, dict), f"{supplier_name} should return dict"
        assert "supplier_part_number" in mapped

    @pytest.mark.parametrize(
        "supplier_name", ["lcsc", "adafruit", "mcmaster-carr", "digikey", "mouser", "boltdepot", "seeedstudio"]
    )
    def test_supplier_handles_invalid_input(self, supplier_name):
        """Test that suppliers handle invalid input gracefully"""
        supplier = get_supplier(supplier_name)

        # Test with None
        result = supplier.map_to_standard_format(None)
        assert result == {}

        # Test with wrong type
        result = supplier.map_to_standard_format("not a PartSearchResult")
        assert result == {}

        # Test with empty dict
        result = supplier.map_to_standard_format({})
        assert result == {}


class TestNoNestedObjects:
    """Verify that mapped data contains no nested objects"""

    def test_lcsc_no_nested_objects(self):
        """LCSC should not return nested objects in mapped data"""
        lcsc = get_supplier("lcsc")

        test_result = PartSearchResult(
            supplier_part_number="C25804",
            specifications={"resistance": "10K", "package": "0805"},
            additional_data={
                "is_smt": True,
                "nested": {"should": "be_flattened"},  # This should be converted to string
            },
        )

        mapped = lcsc.map_to_standard_format(test_result)

        # Check that all values are strings, numbers, or booleans (no dicts/lists)
        for key, value in mapped.items():
            assert not isinstance(value, dict), f"Key '{key}' has nested dict value: {value}"
            # Lists and dicts should be converted to strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                pytest.fail(f"Key '{key}' has complex value type: {type(value)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
