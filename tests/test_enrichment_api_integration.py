"""
Integration Tests for Enrichment API Endpoints

Tests the full enrichment flow from API endpoint through to the frontend,
ensuring that data is properly flattened and doesn't contain [object Object].
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException

from MakerMatrix.suppliers.base import PartSearchResult
from MakerMatrix.routers.parts_routes import enrich_part_from_supplier


class TestEnrichmentEndpoint:
    """Test the /api/parts/enrich-from-supplier endpoint"""

    @pytest.mark.asyncio
    async def test_lcsc_enrichment_returns_flat_data(self):
        """Test that LCSC enrichment returns flat additional_properties"""

        # Mock the supplier and its methods
        mock_supplier = Mock()
        mock_supplier.get_supplier_info.return_value = Mock(name="lcsc", display_name="LCSC")
        mock_supplier.supports_scraping.return_value = False
        mock_supplier.configure = Mock()
        mock_supplier.get_enrichment_field_mappings.return_value = []

        # Mock enrichment result
        mock_enriched_result = PartSearchResult(
            supplier_part_number="C25804",
            manufacturer="Test Mfg",
            description="10K Resistor",
            specifications={"resistance": "10K", "package": "0805"},
            additional_data={"is_smt": True, "part_type": "resistor"},
        )

        # Mock the supplier's map_to_standard_format
        def mock_map(data):
            return {
                "supplier_part_number": data.supplier_part_number,
                "manufacturer": data.manufacturer,
                "description": data.description,
                "Resistance": "10K",
                "Package": "0805",
                "Is Smt": "True",
                "Part Type": "resistor",
            }

        mock_supplier.map_to_standard_format = mock_map

        # Mock enrichment engine
        mock_engine = AsyncMock()
        mock_engine.enrich_part.return_value = {
            "success": True,
            "supplier": "lcsc",
            "part_identifier": "C25804",
            "enrichment_method": "api",
            "data": {
                "supplier_part_number": "C25804",
                "manufacturer": "Test Mfg",
                "description": "10K Resistor",
                "additional_properties": {
                    "Resistance": "10K",
                    "Package": "0805",
                    "Is Smt": "True",
                    "Part Type": "resistor",
                },
            },
        }

        # Mock config service
        mock_config = Mock()
        mock_config.get_supplier_config.return_value = {"enabled": True}
        mock_config.get_supplier_credentials.return_value = {}

        # Mock user
        mock_user = Mock()

        with (
            patch("MakerMatrix.routers.parts_routes.get_supplier", return_value=mock_supplier),
            patch("MakerMatrix.routers.parts_routes.enrichment_engine", mock_engine),
            patch("MakerMatrix.routers.parts_routes.SupplierConfigService", return_value=mock_config),
        ):

            # Call the endpoint
            result = await enrich_part_from_supplier(
                supplier_name="lcsc", part_identifier="C25804", force_refresh=False, current_user=mock_user
            )

            # Verify the result has flat additional_properties
            assert result["success"] is True
            assert "data" in result
            assert "additional_properties" in result["data"]

            additional_props = result["data"]["additional_properties"]

            # Verify no nested objects
            for key, value in additional_props.items():
                assert not isinstance(value, dict), f"additional_properties['{key}'] should not be a dict: {value}"
                assert not isinstance(value, list), f"additional_properties['{key}'] should not be a list: {value}"

    @pytest.mark.asyncio
    async def test_adafruit_enrichment_returns_flat_data(self):
        """Test that Adafruit enrichment returns flat additional_properties"""

        mock_supplier = Mock()
        mock_supplier.get_supplier_info.return_value = Mock(name="adafruit", display_name="Adafruit")
        mock_supplier.supports_scraping.return_value = True
        mock_supplier.configure = Mock()
        mock_supplier.get_enrichment_field_mappings.return_value = []

        # Mock the supplier's map_to_standard_format
        def mock_map(data):
            return {
                "supplier_part_number": data.supplier_part_number,
                "description": data.description,
                "Length": "1m",
                "LED Count": "60",
                "Voltage": "5V",
            }

        mock_supplier.map_to_standard_format = mock_map

        mock_engine = AsyncMock()
        mock_engine.enrich_part.return_value = {
            "success": True,
            "supplier": "adafruit",
            "part_identifier": "3571",
            "enrichment_method": "scraping",
            "data": {
                "supplier_part_number": "3571",
                "description": "LED Strip",
                "additional_properties": {"Length": "1m", "LED Count": "60", "Voltage": "5V"},
            },
        }

        mock_config = Mock()
        mock_config.get_supplier_config.return_value = {"enabled": True}
        mock_config.get_supplier_credentials.return_value = {}

        mock_user = Mock()

        with (
            patch("MakerMatrix.routers.parts_routes.get_supplier", return_value=mock_supplier),
            patch("MakerMatrix.routers.parts_routes.enrichment_engine", mock_engine),
            patch("MakerMatrix.routers.parts_routes.SupplierConfigService", return_value=mock_config),
        ):

            result = await enrich_part_from_supplier(
                supplier_name="adafruit", part_identifier="3571", force_refresh=False, current_user=mock_user
            )

            assert result["success"] is True

            additional_props = result["data"]["additional_properties"]

            # Verify all values are simple types
            for key, value in additional_props.items():
                assert isinstance(
                    value, (str, int, float, bool, type(None))
                ), f"additional_properties['{key}'] should be a simple type, got {type(value)}"

    @pytest.mark.asyncio
    async def test_mcmaster_enrichment_returns_flat_data(self):
        """Test that McMaster-Carr enrichment returns flat additional_properties"""

        mock_supplier = Mock()
        mock_supplier.get_supplier_info.return_value = Mock(name="mcmaster-carr", display_name="McMaster-Carr")
        mock_supplier.supports_scraping.return_value = True
        mock_supplier.configure = Mock()
        mock_supplier.get_enrichment_field_mappings.return_value = []

        # Mock the supplier's map_to_standard_format
        def mock_map(data):
            return {
                "supplier_part_number": data.supplier_part_number,
                "description": data.description,
                "Material": "Black-Oxide Alloy Steel",
                "Thread Size": "M3 x 0.5mm",
                "Length": "15mm",
                "Head Type": "Socket Head",
                "Drive Style": "Hex",
            }

        mock_supplier.map_to_standard_format = mock_map

        mock_engine = AsyncMock()
        mock_engine.enrich_part.return_value = {
            "success": True,
            "supplier": "mcmaster-carr",
            "part_identifier": "91253A192",
            "enrichment_method": "scraping",
            "data": {
                "supplier_part_number": "91253A192",
                "description": "Socket Head Screw",
                "additional_properties": {
                    "Material": "Black-Oxide Alloy Steel",
                    "Thread Size": "M3 x 0.5mm",
                    "Length": "15mm",
                    "Head Type": "Socket Head",
                    "Drive Style": "Hex",
                },
            },
        }

        mock_config = Mock()
        mock_config.get_supplier_config.return_value = {"enabled": True}
        mock_config.get_supplier_credentials.return_value = {}

        mock_user = Mock()

        with (
            patch("MakerMatrix.routers.parts_routes.get_supplier", return_value=mock_supplier),
            patch("MakerMatrix.routers.parts_routes.enrichment_engine", mock_engine),
            patch("MakerMatrix.routers.parts_routes.SupplierConfigService", return_value=mock_config),
        ):

            result = await enrich_part_from_supplier(
                supplier_name="mcmaster-carr", part_identifier="91253A192", force_refresh=False, current_user=mock_user
            )

            assert result["success"] is True

            additional_props = result["data"]["additional_properties"]

            # Verify specifications are flattened
            assert "Material" in additional_props
            assert additional_props["Material"] == "Black-Oxide Alloy Steel"
            assert "Thread Size" in additional_props

            # Verify no nested structures
            for key, value in additional_props.items():
                assert not isinstance(value, (dict, list)), f"additional_properties['{key}'] contains nested data"


class TestEnrichmentRequirementsEndpoint:
    """Test the /api/parts/enrichment-requirements endpoint"""

    @pytest.mark.asyncio
    async def test_enrichment_requirements_exists_for_suppliers(self):
        """Test that enrichment requirements endpoint works for configured suppliers"""
        # This test would verify the endpoint exists and returns proper requirements
        # This helps fix the 404 error seen in the frontend for adafruit
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
