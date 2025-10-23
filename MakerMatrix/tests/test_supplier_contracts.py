"""
Supplier Contract Tests

Ensures that all supplier implementations correctly adhere to the BaseSupplier
abstract class contract. These tests are designed to run without any live
API keys or credentials.
"""

import pytest
from typing import List, Dict, Any

from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.suppliers.base import (
    BaseSupplier,
    SupplierInfo,
    SupplierCapability,
    CapabilityRequirement,
    FieldDefinition,
    ConfigurationOption,
    PartSearchResult,
)
from MakerMatrix.suppliers.exceptions import SupplierConfigurationError

# Get all registered suppliers to test them dynamically
ALL_SUPPLIERS = get_available_suppliers()


@pytest.mark.parametrize("supplier_name", ALL_SUPPLIERS)
class TestSupplierContracts:
    """
    Tests that all suppliers correctly adhere to the BaseSupplier contract.
    These tests do not require live API keys and focus on method signatures,
    return types, and handling of unconfigured states.
    """

    def test_supplier_instantiation(self, supplier_name: str):
        """Tests that the supplier can be instantiated without errors."""
        try:
            supplier = get_supplier(supplier_name)
            assert isinstance(supplier, BaseSupplier)
            assert not supplier.is_configured()
        except Exception as e:
            pytest.fail(f"Failed to instantiate supplier '{supplier_name}': {e}")

    def test_get_supplier_info(self, supplier_name: str):
        """Tests the get_supplier_info method."""
        supplier = get_supplier(supplier_name)
        info = supplier.get_supplier_info()
        assert isinstance(info, SupplierInfo)
        assert info.name and isinstance(info.name, str)
        assert info.display_name and isinstance(info.display_name, str)

    def test_get_capabilities(self, supplier_name: str):
        """Tests the get_capabilities method."""
        supplier = get_supplier(supplier_name)
        capabilities = supplier.get_capabilities()
        assert isinstance(capabilities, list)
        if capabilities:
            assert all(isinstance(cap, SupplierCapability) for cap in capabilities)

    def test_get_capability_requirements(self, supplier_name: str):
        """Tests the get_capability_requirements method, which was previously missed by some suppliers."""
        supplier = get_supplier(supplier_name)
        requirements = supplier.get_capability_requirements()
        assert isinstance(requirements, dict)
        if requirements:
            assert all(isinstance(key, SupplierCapability) for key in requirements.keys())
            assert all(isinstance(value, CapabilityRequirement) for value in requirements.values())

    def test_get_credential_schema(self, supplier_name: str):
        """Tests the get_credential_schema method."""
        supplier = get_supplier(supplier_name)
        schema = supplier.get_credential_schema()
        assert isinstance(schema, list)
        if schema:
            assert all(isinstance(field, FieldDefinition) for field in schema)

    def test_get_configuration_options(self, supplier_name: str):
        """Tests the get_configuration_options method."""
        supplier = get_supplier(supplier_name)
        options = supplier.get_configuration_options()
        assert isinstance(options, list)
        assert len(options) > 0, "Supplier must have at least one configuration option"
        assert any(opt.is_default for opt in options), "Supplier must have a default configuration option"
        assert all(isinstance(opt, ConfigurationOption) for opt in options)

    @pytest.mark.asyncio
    async def test_unconfigured_test_connection(self, supplier_name: str):
        """Tests that test_connection handles an unconfigured state gracefully."""
        supplier = get_supplier(supplier_name)
        result = await supplier.test_connection()
        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert not result["success"], "test_connection should fail when unconfigured"

    @pytest.mark.asyncio
    async def test_unconfigured_search_parts(self, supplier_name: str):
        """Tests that search_parts handles an unconfigured state gracefully."""
        supplier = get_supplier(supplier_name)
        if SupplierCapability.SEARCH_PARTS not in supplier.get_capabilities():
            pytest.skip(f"{supplier_name} does not support SEARCH_PARTS")

        try:
            results = await supplier.search_parts("test")
            assert isinstance(results, list)
            assert len(results) == 0, "An unconfigured search should return no results"
        except SupplierConfigurationError:
            # Raising a configuration error is also an acceptable outcome
            pass
        except Exception as e:
            pytest.fail(f"search_parts raised an unexpected exception when unconfigured: {e}")
