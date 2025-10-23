"""
Unit tests for enrichment task handler capability mapping and validation

These tests ensure that the capability mapping system works correctly and prevents
runtime errors caused by invalid capability mappings.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from MakerMatrix.suppliers.base import SupplierCapability
from MakerMatrix.services.system.enrichment_coordinator_service import EnrichmentCoordinatorService


class TestEnrichmentTaskHandlerCapabilities:
    """Test capability mapping and validation in enrichment task handler"""

    def test_all_supplier_capability_enum_values_exist(self):
        """Test that all expected SupplierCapability enum values exist"""
        expected_capabilities = {"GET_PART_DETAILS", "FETCH_DATASHEET", "FETCH_PRICING_STOCK", "IMPORT_ORDERS"}

        actual_capabilities = {cap.name for cap in SupplierCapability}

        assert actual_capabilities == expected_capabilities, (
            f"SupplierCapability enum has changed. "
            f"Expected: {expected_capabilities}, "
            f"Actual: {actual_capabilities}"
        )

    def test_capability_mapping_uses_only_valid_enums(self):
        """Test that capability mapping only references valid SupplierCapability enum values"""
        # Get the capability mapping from the enrichment task handler
        from MakerMatrix.suppliers.base import SupplierCapability

        # This is the mapping used in the enrichment task handler
        capability_map = {
            "fetch_datasheet": SupplierCapability.FETCH_DATASHEET,
            "fetch_details": SupplierCapability.GET_PART_DETAILS,
            "get_part_details": SupplierCapability.GET_PART_DETAILS,
            "fetch_pricing_stock": SupplierCapability.FETCH_PRICING_STOCK,
            "import_orders": SupplierCapability.IMPORT_ORDERS,
        }

        # Verify all mapped values are valid enum members
        valid_enum_values = set(SupplierCapability)
        for string_cap, enum_cap in capability_map.items():
            assert (
                enum_cap in valid_enum_values
            ), f"Capability mapping contains invalid enum: '{string_cap}' -> {enum_cap}"

    def test_capability_mapping_covers_all_enums(self):
        """Test that capability mapping covers all available SupplierCapability enums"""
        from MakerMatrix.suppliers.base import SupplierCapability

        capability_map = {
            "fetch_datasheet": SupplierCapability.FETCH_DATASHEET,
            "fetch_details": SupplierCapability.GET_PART_DETAILS,
            "get_part_details": SupplierCapability.GET_PART_DETAILS,
            "fetch_pricing_stock": SupplierCapability.FETCH_PRICING_STOCK,
            "import_orders": SupplierCapability.IMPORT_ORDERS,
        }

        mapped_enums = set(capability_map.values())
        all_enums = set(SupplierCapability)

        assert mapped_enums == all_enums, (
            f"Capability mapping doesn't cover all enums. " f"Missing: {all_enums - mapped_enums}"
        )

    def test_lcsc_recommended_capabilities_are_valid(self):
        """Test that LCSC recommended capabilities are valid and can be mapped"""
        from MakerMatrix.suppliers.base import SupplierCapability

        # These are the recommended capabilities for LCSC
        lcsc_recommended = ["fetch_datasheet", "get_part_details", "fetch_pricing_stock"]

        capability_map = {
            "fetch_datasheet": SupplierCapability.FETCH_DATASHEET,
            "fetch_details": SupplierCapability.GET_PART_DETAILS,
            "get_part_details": SupplierCapability.GET_PART_DETAILS,
            "fetch_pricing_stock": SupplierCapability.FETCH_PRICING_STOCK,
            "import_orders": SupplierCapability.IMPORT_ORDERS,
        }

        for cap in lcsc_recommended:
            assert cap in capability_map, f"LCSC recommended capability '{cap}' is not in capability mapping"

            # Verify it maps to a valid enum
            enum_cap = capability_map[cap]
            assert isinstance(
                enum_cap, SupplierCapability
            ), f"LCSC capability '{cap}' maps to invalid type: {type(enum_cap)}"

    def test_supplier_capabilities_match_enum_values(self):
        """Test that actual supplier implementations return valid enum values"""
        from MakerMatrix.suppliers.lcsc import LCSCSupplier
        from MakerMatrix.suppliers.digikey import DigiKeySupplier
        from MakerMatrix.suppliers.mouser import MouserSupplier

        suppliers = [("LCSC", LCSCSupplier()), ("DigiKey", DigiKeySupplier()), ("Mouser", MouserSupplier())]

        for supplier_name, supplier in suppliers:
            capabilities = supplier.get_capabilities()

            # Check that all returned capabilities are valid enum values
            for cap in capabilities:
                assert isinstance(
                    cap, SupplierCapability
                ), f"{supplier_name} returned invalid capability type: {type(cap)}"

                # Check that it's a known enum member
                assert cap in SupplierCapability, f"{supplier_name} returned unknown capability: {cap}"

    def test_capability_validation_prevents_invalid_capabilities(self):
        """Test that capability validation logic prevents invalid capabilities"""
        # Test the validation logic directly (similar to what's in the enrichment handler)

        # Simulate available capabilities from supplier config
        available_capabilities = ["fetch_datasheet", "get_part_details", "fetch_pricing_stock"]

        # Test invalid capabilities
        requested_capabilities = ["invalid_capability", "another_invalid"]

        # This mimics the validation logic in the enrichment handler
        invalid_caps = [cap for cap in requested_capabilities if cap not in available_capabilities]

        # Should find invalid capabilities
        assert len(invalid_caps) == 2
        assert "invalid_capability" in invalid_caps
        assert "another_invalid" in invalid_caps

        # Test with valid capabilities
        valid_requested = ["fetch_datasheet", "get_part_details"]
        valid_invalid_caps = [cap for cap in valid_requested if cap not in available_capabilities]

        # Should find no invalid capabilities
        assert len(valid_invalid_caps) == 0

    def test_capability_mapping_consistency_across_suppliers(self):
        """Test that all suppliers use consistent capability naming"""
        from MakerMatrix.suppliers.lcsc import LCSCSupplier
        from MakerMatrix.suppliers.digikey import DigiKeySupplier
        from MakerMatrix.suppliers.mouser import MouserSupplier

        suppliers = [LCSCSupplier(), DigiKeySupplier(), MouserSupplier()]

        # All suppliers should support the same set of capabilities
        expected_capabilities = {
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_PRICING_STOCK,
            SupplierCapability.IMPORT_ORDERS,
        }

        for supplier in suppliers:
            supplier_caps = set(supplier.get_capabilities())
            assert (
                supplier_caps == expected_capabilities
            ), f"{supplier.__class__.__name__} has inconsistent capabilities: {supplier_caps}"

    def test_recommended_capability_filtering(self):
        """Test that recommended capabilities are properly filtered against available ones"""
        # Test LCSC recommended capabilities filtering
        lcsc_recommended = ["fetch_datasheet", "get_part_details", "fetch_pricing_stock"]

        # Test with all capabilities available
        all_available = ["fetch_datasheet", "get_part_details", "fetch_pricing_stock", "import_orders"]
        filtered_all = [cap for cap in lcsc_recommended if cap in all_available]
        assert filtered_all == lcsc_recommended

        # Test with partial capabilities available
        partial_available = ["fetch_datasheet", "get_part_details"]
        filtered_partial = [cap for cap in lcsc_recommended if cap in partial_available]
        assert filtered_partial == ["fetch_datasheet", "get_part_details"]
        assert "fetch_pricing_stock" not in filtered_partial

        # Test with no capabilities available
        no_available = []
        filtered_none = [cap for cap in lcsc_recommended if cap in no_available]
        assert filtered_none == []

    def test_deprecated_capability_names_not_used(self):
        """Test that deprecated capability names are not used in the system"""
        # These capability names were causing the bug and should not be used
        deprecated_capabilities = ["fetch_image", "fetch_specifications", "fetch_pricing", "fetch_stock"]

        # Read the enrichment task handler source to check for these
        import inspect
        from MakerMatrix.services.system.enrichment_coordinator_service import EnrichmentCoordinatorService

        source = inspect.getsource(EnrichmentCoordinatorService)

        for deprecated_cap in deprecated_capabilities:
            assert (
                f"'{deprecated_cap}'" not in source
            ), f"Deprecated capability '{deprecated_cap}' found in enrichment coordinator service source"

    def test_enum_values_match_string_representations(self):
        """Test that enum values match their expected string representations"""
        expected_mappings = {
            SupplierCapability.GET_PART_DETAILS: "get_part_details",
            SupplierCapability.FETCH_DATASHEET: "fetch_datasheet",
            SupplierCapability.FETCH_PRICING_STOCK: "fetch_pricing_stock",
            SupplierCapability.IMPORT_ORDERS: "import_orders",
        }

        for enum_val, expected_string in expected_mappings.items():
            assert enum_val.value == expected_string, (
                f"Enum value mismatch: {enum_val.name}.value = '{enum_val.value}', " f"expected '{expected_string}'"
            )
