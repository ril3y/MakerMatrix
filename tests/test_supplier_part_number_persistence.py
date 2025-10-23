"""
Test that supplier part numbers persist correctly after enrichment.

This test verifies the fix for the issue where Mouser part numbers entered in the
enrichment modal were not being saved to the part record after enrichment completed.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from MakerMatrix.services.system.part_enrichment_service import PartEnrichmentService
from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
from MakerMatrix.suppliers.base import PartSearchResult
from MakerMatrix.models.models import PartModel


class TestSupplierPartNumberPersistence:
    """Test that supplier part numbers are correctly preserved during enrichment."""

    def test_mouser_part_number_preserved_in_part_search_result(self):
        """Test that Mouser part number from part is used in PartSearchResult."""
        # Create a mock part with a Mouser part number (entered via modal)
        part = Mock(spec=PartModel)
        part.id = "test-part-123"
        part.part_name = "Test Resistor"
        part.part_number = "RC0805FR-071KL"  # Manufacturer part number
        part.supplier_part_number = "652-CRL0805JWR330ELF"  # Mouser part number entered by user
        part.manufacturer = None
        part.manufacturer_part_number = None
        part.description = None

        # Create enrichment service
        service = PartEnrichmentService()

        # Create mock enrichment results (what Mouser API returns)
        enrichment_results = {
            "part_data": {
                "success": True,
                "manufacturer": "Yageo",
                "manufacturer_part_number": "RC0805FR-071KL",
                "description": "RES SMD 1K OHM 1% 1/8W 0805",
                "datasheet_url": "https://www.mouser.com/datasheet/2/447/yageo_datasheet.pdf",
                "image_url": None,
                "category": "Chip Resistor",
                "stock_quantity": 50000,
                "pricing": [{"quantity": 1, "price": 0.10, "currency": "USD"}],
                "specifications": {"Resistance": "1kΩ", "Power": "1/8W"},
                "additional_data": {
                    "mouser_part_number": "652-CRL0805JWR330ELF",  # Mouser returns this in additional_data
                    "product_detail_url": "https://www.mouser.com/ProductDetail/652-CRL0805JWR330ELF",
                },
            }
        }

        # Convert to PartSearchResult
        result = service._convert_enrichment_to_part_search_result(part, enrichment_results, "mouser")

        # Verify the supplier part number is preserved from the part, not lost
        assert result is not None
        assert result.supplier_part_number == "652-CRL0805JWR330ELF"
        assert result.manufacturer == "Yageo"
        assert result.manufacturer_part_number == "RC0805FR-071KL"

    def test_mouser_mapper_preserves_supplier_part_number(self):
        """Test that Mouser data mapper correctly maps the supplier part number."""
        mapper = SupplierDataMapper()

        # Create a PartSearchResult with Mouser data
        result = PartSearchResult(
            supplier_part_number="652-CRL0805JWR330ELF",  # This is what user entered
            manufacturer="Yageo",
            manufacturer_part_number="RC0805FR-071KL",
            description="RES SMD 1K OHM 1% 1/8W 0805",
            category="Chip Resistor",
            datasheet_url="https://www.mouser.com/datasheet/2/447/yageo_datasheet.pdf",
            image_url=None,
            stock_quantity=50000,
            pricing=[{"quantity": 1, "price": 0.10, "currency": "USD"}],
            specifications={"Resistance": "1kΩ", "Power": "1/8W"},
            additional_data={
                "mouser_part_number": "652-CRL0805JWR330ELF",  # Mouser API also returns this
                "product_detail_url": "https://www.mouser.com/ProductDetail/652-CRL0805JWR330ELF",
                "lead_time": "0 Weeks",
                "min_order_qty": 1,
            },
        )

        # Map to part data
        part_data = mapper.map_supplier_result_to_part_data(
            result, "Mouser", enrichment_capabilities=["get_part_details", "fetch_datasheet"]
        )

        # Verify supplier_part_number is preserved
        assert part_data["supplier_part_number"] == "652-CRL0805JWR330ELF"
        assert part_data["manufacturer"] == "Yageo"
        assert part_data["manufacturer_part_number"] == "RC0805FR-071KL"

        # Also verify it's in additional_properties
        assert "mouser_part_number" in part_data["additional_properties"]
        assert part_data["additional_properties"]["mouser_part_number"] == "652-CRL0805JWR330ELF"

    def test_digikey_part_number_preserved_in_part_search_result(self):
        """Test that DigiKey part number from part is used in PartSearchResult."""
        # Create a mock part with a DigiKey part number (entered via modal)
        part = Mock(spec=PartModel)
        part.id = "test-part-456"
        part.part_name = "Test MCU"
        part.part_number = "STM32F103C8T6"  # Manufacturer part number
        part.supplier_part_number = "497-6063-ND"  # DigiKey part number entered by user
        part.manufacturer = None
        part.manufacturer_part_number = None
        part.description = None

        # Create enrichment service
        service = PartEnrichmentService()

        # Create mock enrichment results (what DigiKey API returns)
        enrichment_results = {
            "part_data": {
                "success": True,
                "manufacturer": "STMicroelectronics",
                "manufacturer_part_number": "STM32F103C8T6",
                "description": "IC MCU 32BIT 64KB FLASH 48LQFP",
                "datasheet_url": "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
                "image_url": "https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/123.jpg",
                "category": "Embedded - Microcontrollers",
                "stock_quantity": 12500,
                "pricing": [{"quantity": 1, "price": 2.85, "currency": "USD"}],
                "specifications": {"Core Processor": "ARM Cortex-M3", "Speed": "72MHz"},
                "additional_data": {
                    "digikey_part_number": "497-6063-ND",  # DigiKey returns this in additional_data
                    "product_url": "https://www.digikey.com/en/products/detail/stmicroelectronics/STM32F103C8T6/1646340",
                },
            }
        }

        # Convert to PartSearchResult
        result = service._convert_enrichment_to_part_search_result(part, enrichment_results, "digikey")

        # Verify the supplier part number is preserved from the part, not lost
        assert result is not None
        assert result.supplier_part_number == "497-6063-ND"
        assert result.manufacturer == "STMicroelectronics"
        assert result.manufacturer_part_number == "STM32F103C8T6"

    def test_digikey_mapper_preserves_supplier_part_number(self):
        """Test that DigiKey data mapper correctly maps the supplier part number."""
        mapper = SupplierDataMapper()

        # Create a PartSearchResult with DigiKey data
        result = PartSearchResult(
            supplier_part_number="497-6063-ND",  # This is what user entered
            manufacturer="STMicroelectronics",
            manufacturer_part_number="STM32F103C8T6",
            description="IC MCU 32BIT 64KB FLASH 48LQFP",
            category="Embedded - Microcontrollers",
            datasheet_url="https://www.st.com/resource/en/datasheet/stm32f103c8.pdf",
            image_url="https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/123.jpg",
            stock_quantity=12500,
            pricing=[{"quantity": 1, "price": 2.85, "currency": "USD"}],
            specifications={"Core Processor": "ARM Cortex-M3", "Speed": "72MHz"},
            additional_data={
                "digikey_part_number": "497-6063-ND",  # DigiKey API also returns this
                "product_url": "https://www.digikey.com/en/products/detail/stmicroelectronics/STM32F103C8T6/1646340",
                "lifecycle_status": "Active",
                "rohs_status": "Compliant",
            },
        )

        # Map to part data
        part_data = mapper.map_supplier_result_to_part_data(
            result, "DigiKey", enrichment_capabilities=["get_part_details", "fetch_datasheet"]
        )

        # Verify supplier_part_number is preserved
        assert part_data["supplier_part_number"] == "497-6063-ND"
        assert part_data["manufacturer"] == "STMicroelectronics"
        assert part_data["manufacturer_part_number"] == "STM32F103C8T6"

        # Also verify it's in additional_properties
        assert "digikey_part_number" in part_data["additional_properties"]
        assert part_data["additional_properties"]["digikey_part_number"] == "497-6063-ND"

    def test_fallback_when_no_supplier_part_number(self):
        """Test that system falls back gracefully when no supplier part number is provided."""
        # Create a mock part WITHOUT a supplier part number
        part = Mock(spec=PartModel)
        part.id = "test-part-789"
        part.part_name = "Test Part"
        part.part_number = "MPN123"  # Only has manufacturer part number
        part.supplier_part_number = None  # No supplier part number provided
        part.manufacturer = None
        part.manufacturer_part_number = None
        part.description = None

        # Create enrichment service
        service = PartEnrichmentService()

        # Create mock enrichment results
        enrichment_results = {
            "part_data": {
                "success": True,
                "manufacturer": "TestCorp",
                "manufacturer_part_number": "MPN123",
                "description": "Test Component",
                "additional_data": {
                    "mouser_part_number": "652-MPN123",  # Mouser returns a part number
                },
            }
        }

        # Convert to PartSearchResult
        result = service._convert_enrichment_to_part_search_result(part, enrichment_results, "mouser")

        # Verify it falls back to the Mouser part number from additional_data
        assert result is not None
        assert result.supplier_part_number == "652-MPN123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
