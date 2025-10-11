"""
Test datasheet URL standardization across suppliers
"""

import pytest
from unittest.mock import Mock, patch
from MakerMatrix.suppliers.base import PartSearchResult
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper


class TestDatasheetStandardization:
    """Test that datasheet URLs are properly standardized across all suppliers"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mapper = SupplierDataMapper()

    def test_digikey_datasheet_url_standardization(self):
        """Test DigiKey datasheet URL is properly placed in additional_properties"""
        # Create a mock DigiKey result with datasheet URL
        digikey_result = PartSearchResult(
            supplier_part_number="296-1234-ND",
            manufacturer="Texas Instruments",
            manufacturer_part_number="LM358",
            description="Op Amp Dual General Purpose",
            datasheet_url="https://www.ti.com/lit/ds/symlink/lm358.pdf",
            category="Integrated Circuits",
            stock_quantity=1000,
            pricing=[{"quantity": 1, "price": 0.45, "currency": "USD"}],
            additional_data={
                "digikey_part_number": "296-1234-ND",
                "rohs_status": "Compliant"
            }
        )

        # Map the result
        mapped_data = self.mapper.map_supplier_result_to_part_data(
            digikey_result,
            "DigiKey",
            ["get_part_details", "fetch_datasheet"]
        )

        # Verify datasheet_url is in additional_properties at the root level
        assert 'additional_properties' in mapped_data
        assert 'datasheet_url' in mapped_data['additional_properties']
        assert mapped_data['additional_properties']['datasheet_url'] == "https://www.ti.com/lit/ds/symlink/lm358.pdf"

    def test_mouser_datasheet_url_standardization(self):
        """Test Mouser datasheet URL is properly placed in additional_properties"""
        # Create a mock Mouser result with datasheet URL
        mouser_result = PartSearchResult(
            supplier_part_number="595-LM358",
            manufacturer="Texas Instruments",
            manufacturer_part_number="LM358",
            description="Operational Amplifiers - Op Amps Dual",
            datasheet_url="https://www.mouser.com/datasheet/2/405/lm358-1234567.pdf",
            category="Semiconductors",
            stock_quantity=500,
            pricing=[{"quantity": 1, "price": 0.50, "currency": "USD"}],
            additional_data={
                "mouser_part_number": "595-LM358",
                "lifecycle_status": "Active"
            }
        )

        # Map the result
        mapped_data = self.mapper.map_supplier_result_to_part_data(
            mouser_result,
            "Mouser",
            ["get_part_details", "fetch_datasheet"]
        )

        # Verify datasheet_url is in additional_properties at the root level
        assert 'additional_properties' in mapped_data
        assert 'datasheet_url' in mapped_data['additional_properties']
        assert mapped_data['additional_properties']['datasheet_url'] == "https://www.mouser.com/datasheet/2/405/lm358-1234567.pdf"

    def test_lcsc_datasheet_url_standardization(self):
        """Test LCSC datasheet URL is properly placed in additional_properties"""
        # Create a mock LCSC result with datasheet URL
        lcsc_result = PartSearchResult(
            supplier_part_number="C7470",
            manufacturer="Texas Instruments",
            manufacturer_part_number="LM358P",
            description="Dual Operational Amplifier",
            datasheet_url="https://datasheet.lcsc.com/szlcsc/LM358P_C7470.pdf",
            category="Amplifiers",
            stock_quantity=2000,
            additional_data={
                "lcsc_part_number": "C7470",
                "package": "DIP-8",
                "is_smt": False
            }
        )

        # Map the result
        mapped_data = self.mapper.map_supplier_result_to_part_data(
            lcsc_result,
            "LCSC",
            ["get_part_details", "fetch_datasheet"]
        )

        # Verify datasheet_url is in additional_properties at the root level
        assert 'additional_properties' in mapped_data
        assert 'datasheet_url' in mapped_data['additional_properties']
        assert mapped_data['additional_properties']['datasheet_url'] == "https://datasheet.lcsc.com/szlcsc/LM358P_C7470.pdf"

    def test_datasheet_url_from_additional_data(self):
        """Test datasheet URL extraction from additional_data when not in main field"""
        # Create a result where datasheet URL is only in additional_data
        result = PartSearchResult(
            supplier_part_number="TEST-123",
            manufacturer="Test Corp",
            manufacturer_part_number="TC123",
            description="Test Component",
            datasheet_url=None,  # No URL in main field
            additional_data={
                "lcsc_datasheet_url": "https://example.com/datasheet.pdf",
                "other_field": "value"
            }
        )

        # Map the result
        mapped_data = self.mapper.map_supplier_result_to_part_data(
            result,
            "TestSupplier",
            ["get_part_details"]
        )

        # Verify datasheet_url is extracted from additional_data
        assert 'additional_properties' in mapped_data
        assert 'datasheet_url' in mapped_data['additional_properties']
        assert mapped_data['additional_properties']['datasheet_url'] == "https://example.com/datasheet.pdf"

    def test_no_datasheet_url(self):
        """Test handling when no datasheet URL is available"""
        # Create a result without any datasheet URL
        result = PartSearchResult(
            supplier_part_number="NO-DS-123",
            manufacturer="No Datasheet Corp",
            manufacturer_part_number="NDC123",
            description="Component without datasheet",
            datasheet_url=None,
            additional_data={
                "some_field": "value"
            }
        )

        # Map the result
        mapped_data = self.mapper.map_supplier_result_to_part_data(
            result,
            "TestSupplier",
            ["get_part_details"]
        )

        # Verify no datasheet_url is added when not available
        assert 'additional_properties' in mapped_data
        # datasheet_url should not be present if no datasheet exists
        assert 'datasheet_url' not in mapped_data['additional_properties'] or \
               mapped_data['additional_properties'].get('datasheet_url') is None

    def test_all_datasheet_key_variations(self):
        """Test that various datasheet key variations are recognized"""
        test_cases = [
            ('datasheet_url', 'https://example.com/ds1.pdf'),
            ('lcsc_datasheet_url', 'https://example.com/ds2.pdf'),
            ('DataSheetUrl', 'https://example.com/ds3.pdf'),
            ('datasheet_link', 'https://example.com/ds4.pdf'),
        ]

        for key, expected_url in test_cases:
            result = PartSearchResult(
                supplier_part_number=f"TEST-{key}",
                description="Test",
                datasheet_url=None,
                additional_data={
                    key: expected_url
                }
            )

            mapped_data = self.mapper.map_supplier_result_to_part_data(
                result,
                "TestSupplier",
                []
            )

            assert 'datasheet_url' in mapped_data['additional_properties']
            assert mapped_data['additional_properties']['datasheet_url'] == expected_url, \
                   f"Failed to extract datasheet from key '{key}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])