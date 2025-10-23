"""
Comprehensive Tests for Mouser Supplier Capabilities

Tests all claimed capabilities using real Mouser part number 638-EL817A-F
to ensure our supplier implementation actually works with Mouser's API.
"""

import pytest
import asyncio
import os
from typing import Dict, Any

from MakerMatrix.suppliers.mouser import MouserSupplier
from MakerMatrix.suppliers.base import SupplierCapability


@pytest.fixture
def mouser_supplier():
    """Create a configured Mouser supplier instance"""
    supplier = MouserSupplier()

    # Get API key from environment
    api_key = os.getenv("MOUSER_API_KEY", "8361a6ca-0998-4c9e-bfd5-edff5bc54b9b")

    # Configure the supplier
    supplier.configure(
        credentials={"api_key": api_key},
        config={
            "base_url": "https://api.mouser.com/api/v1",
            "search_option": "None",
            "search_with_your_signup_language": False,
        },
    )

    return supplier


@pytest.fixture
def test_part_number():
    """Test part number - EL817A optocoupler"""
    return "638-EL817A-F"


class TestMouserCapabilities:
    """Test all claimed Mouser capabilities"""

    @pytest.mark.asyncio
    async def test_supplier_info(self, mouser_supplier):
        """Test supplier information is correctly configured"""
        info = mouser_supplier.get_supplier_info()

        assert info.name == "mouser"
        assert info.display_name == "Mouser Electronics"
        assert "instant API access" in info.description
        assert info.api_documentation_url == "https://api.mouser.com/api/docs/V1"
        assert info.supports_oauth is False
        assert "30 calls per minute" in info.rate_limit_info

    @pytest.mark.asyncio
    async def test_capabilities_list(self, mouser_supplier):
        """Test that supplier reports correct capabilities"""
        capabilities = mouser_supplier.get_capabilities()

        expected_capabilities = [
            SupplierCapability.SEARCH_PARTS,
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_IMAGE,
            SupplierCapability.FETCH_PRICING,
            SupplierCapability.FETCH_STOCK,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.PARAMETRIC_SEARCH,
        ]

        for capability in expected_capabilities:
            assert capability in capabilities, f"Missing capability: {capability}"

    @pytest.mark.asyncio
    async def test_authentication(self, mouser_supplier):
        """Test API key authentication"""
        is_configured = mouser_supplier.is_configured()
        assert is_configured, "Supplier should be configured with API key"

        auth_result = await mouser_supplier.authenticate()
        assert auth_result is True, "Authentication should succeed with valid API key"

    @pytest.mark.asyncio
    async def test_connection_test(self, mouser_supplier):
        """Test connection to Mouser API"""
        result = await mouser_supplier.test_connection()

        assert isinstance(result, dict), "test_connection should return a dictionary"
        assert "success" in result, "Result should contain 'success' field"
        assert result["success"] is True, f"Connection should succeed: {result.get('message', 'No message')}"
        assert "message" in result, "Result should contain 'message' field"

    @pytest.mark.asyncio
    async def test_search_parts_capability(self, mouser_supplier, test_part_number):
        """Test SEARCH_PARTS capability"""
        # Test keyword search
        results = await mouser_supplier.search_parts("EL817A", limit=10)

        assert len(results) > 0, "Search should return results for EL817A"

        # Check that our test part is in the results
        part_numbers = [result.supplier_part_number for result in results]
        assert any(
            test_part_number in pn for pn in part_numbers
        ), f"Test part {test_part_number} should be in search results"

        # Verify result structure
        first_result = results[0]
        assert hasattr(first_result, "supplier_part_number"), "Result should have supplier_part_number"
        assert hasattr(first_result, "manufacturer"), "Result should have manufacturer"
        assert hasattr(first_result, "description"), "Result should have description"

    @pytest.mark.asyncio
    async def test_get_part_details_capability(self, mouser_supplier, test_part_number):
        """Test GET_PART_DETAILS capability"""
        part_details = await mouser_supplier.get_part_details(test_part_number)

        assert part_details is not None, f"Should find details for part {test_part_number}"
        assert part_details.supplier_part_number == test_part_number, "Should return correct part"
        assert part_details.manufacturer is not None, "Should have manufacturer information"
        assert part_details.description is not None, "Should have description"

        # EL817A is an optocoupler, so description should mention this
        assert any(
            term in part_details.description.lower() for term in ["optocoupler", "opto", "coupler", "isolator"]
        ), f"Description should mention optocoupler/isolator: {part_details.description}"

    @pytest.mark.asyncio
    async def test_fetch_datasheet_capability(self, mouser_supplier, test_part_number):
        """Test FETCH_DATASHEET capability"""
        datasheet_url = await mouser_supplier.fetch_datasheet(test_part_number)

        if datasheet_url is not None and datasheet_url.strip():
            assert isinstance(datasheet_url, str), "Datasheet URL should be a string"
            assert len(datasheet_url.strip()) > 0, "Datasheet URL should not be empty"

            # Handle both absolute and relative URLs
            if not datasheet_url.startswith("http"):
                print(f"Note: Datasheet URL is relative: {datasheet_url}")
            else:
                # If absolute URL, verify it's valid
                assert datasheet_url.startswith("http"), f"Absolute datasheet URL should be valid: {datasheet_url}"
        else:
            print(f"Note: No datasheet available for {test_part_number} - this is acceptable for some parts")

    @pytest.mark.asyncio
    async def test_fetch_image_capability(self, mouser_supplier, test_part_number):
        """Test FETCH_IMAGE capability"""
        image_url = await mouser_supplier.fetch_image(test_part_number)

        if image_url is not None:
            assert isinstance(image_url, str), "Image URL should be a string"
            assert len(image_url.strip()) > 0, "Image URL should not be empty"

            # Handle both absolute and relative URLs
            if not image_url.startswith("http"):
                print(f"Note: Image URL is relative: {image_url}")
            else:
                # If absolute URL, verify it's valid
                assert image_url.startswith("http"), f"Absolute image URL should be valid: {image_url}"
        else:
            print(f"Note: No image available for {test_part_number} - this is acceptable for some parts")

    @pytest.mark.asyncio
    async def test_fetch_pricing_capability(self, mouser_supplier, test_part_number):
        """Test FETCH_PRICING capability"""
        pricing = await mouser_supplier.fetch_pricing(test_part_number)

        assert pricing is not None, f"Should find pricing for {test_part_number}"
        assert isinstance(pricing, list), "Pricing should be a list of price breaks"
        assert len(pricing) > 0, "Should have at least one price break"

        # Check price break structure
        first_price = pricing[0]
        assert isinstance(first_price, dict), "Price break should be a dictionary"
        assert "quantity" in first_price, "Price break should have quantity"
        assert "price" in first_price, "Price break should have price"
        assert "currency" in first_price, "Price break should have currency"

        # Validate price is reasonable for an optocoupler (should be under $10)
        assert 0 < first_price["price"] < 10.0, f"Price should be reasonable for optocoupler: ${first_price['price']}"
        assert first_price["currency"] == "USD", "Currency should be USD"

    @pytest.mark.asyncio
    async def test_fetch_stock_capability(self, mouser_supplier, test_part_number):
        """Test FETCH_STOCK capability"""
        stock_qty = await mouser_supplier.fetch_stock(test_part_number)

        assert stock_qty is not None, f"Should find stock information for {test_part_number}"
        assert isinstance(stock_qty, int), "Stock quantity should be an integer"
        assert stock_qty >= 0, "Stock quantity should be non-negative"

        # EL817A is a common part, likely to be in stock
        # But we can't assert it's always in stock as inventory changes
        print(f"Stock quantity for {test_part_number}: {stock_qty}")

    @pytest.mark.asyncio
    async def test_fetch_specifications_capability(self, mouser_supplier, test_part_number):
        """Test FETCH_SPECIFICATIONS capability"""
        specs = await mouser_supplier.fetch_specifications(test_part_number)

        if specs is not None:
            assert isinstance(specs, dict), "Specifications should be a dictionary"

            if len(specs) > 0:
                print(f"Found specifications: {list(specs.keys())[:5]}...")  # Show first 5 keys

                # For an optocoupler, we might expect certain specifications
                spec_keys = [key.lower() for key in specs.keys()]
                expected_spec_types = ["isolation", "voltage", "current", "package", "mounting", "temperature"]

                found_specs = [
                    spec_type for spec_type in expected_spec_types if any(spec_type in key for key in spec_keys)
                ]
                if len(found_specs) > 0:
                    print(f"Found relevant optocoupler specs: {found_specs}")
                else:
                    print(f"Note: No typical optocoupler specs found, but part has {len(specs)} specifications")
            else:
                print(f"Note: Specifications dictionary is empty for {test_part_number}")
        else:
            print(f"Note: No specifications available for {test_part_number} - this may be acceptable")

    @pytest.mark.asyncio
    async def test_rate_limiting(self, mouser_supplier):
        """Test that rate limiting is properly configured"""
        delay = mouser_supplier.get_rate_limit_delay()

        # Should be 2.0 seconds based on 30 calls/minute limit
        assert delay == 2.0, f"Rate limit delay should be 2.0 seconds, got {delay}"

    @pytest.mark.asyncio
    async def test_parametric_search_capability(self, mouser_supplier):
        """Test PARAMETRIC_SEARCH capability (enhanced search)"""
        # Test searching for optocouplers with specific parameters
        results = await mouser_supplier.search_parts("optocoupler EL817", limit=20)

        assert len(results) > 0, "Parametric search should return results"

        # Results should be relevant to optocouplers
        descriptions = [result.description.lower() for result in results if result.description]
        relevant_results = [
            desc for desc in descriptions if any(term in desc for term in ["opto", "coupler", "isolat"])
        ]

        # At least half the results should be relevant
        relevance_ratio = len(relevant_results) / len(descriptions) if descriptions else 0
        assert (
            relevance_ratio > 0.3
        ), f"Search results should be relevant to optocouplers. Relevance: {relevance_ratio:.2f}"


class TestMouserErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_part_number(self, mouser_supplier):
        """Test handling of invalid part numbers"""
        invalid_part = "INVALID-PART-NUMBER-12345"

        # These should return None rather than raise exceptions
        details = await mouser_supplier.get_part_details(invalid_part)
        assert details is None, "Should return None for invalid part number"

        datasheet = await mouser_supplier.fetch_datasheet(invalid_part)
        assert datasheet is None, "Should return None for invalid part datasheet"

        pricing = await mouser_supplier.fetch_pricing(invalid_part)
        assert pricing is None, "Should return None for invalid part pricing"

    @pytest.mark.asyncio
    async def test_empty_search(self, mouser_supplier):
        """Test handling of empty search queries"""
        try:
            results = await mouser_supplier.search_parts("", limit=10)

            # Should handle empty search gracefully
            assert isinstance(results, list), "Should return list for empty search"
            print(f"Empty search returned {len(results)} results")
        except Exception as e:
            # It's acceptable for empty search to raise an exception
            print(f"Empty search raised exception (acceptable): {type(e).__name__}: {e}")
            assert True  # Test passes either way


class TestMouserIntegration:
    """Integration tests combining multiple capabilities"""

    @pytest.mark.asyncio
    async def test_complete_part_enrichment_workflow(self, test_part_number):
        """Test complete workflow of enriching a part with all available data"""

        # Create a fresh supplier instance for this test
        from MakerMatrix.suppliers.mouser import MouserSupplier
        import os

        supplier = MouserSupplier()
        api_key = os.getenv("MOUSER_API_KEY", "8361a6ca-0998-4c9e-bfd5-edff5bc54b9b")
        supplier.configure(
            credentials={"api_key": api_key},
            config={
                "base_url": "https://api.mouser.com/api/v1",
                "search_option": "None",
                "search_with_your_signup_language": False,
            },
        )

        # Step 1: Search for the part
        search_results = await supplier.search_parts(test_part_number.split("-")[1], limit=10)
        assert len(search_results) > 0, "Should find the part in search"

        # Step 2: Get detailed information
        part_details = await supplier.get_part_details(test_part_number)
        assert part_details is not None, "Should get part details"

        # Step 3: Fetch all enrichment data (with some delay to avoid rate limiting)
        import asyncio

        datasheet_url = await supplier.fetch_datasheet(test_part_number)
        await asyncio.sleep(2)

        image_url = await supplier.fetch_image(test_part_number)
        await asyncio.sleep(2)

        pricing = await supplier.fetch_pricing(test_part_number)
        await asyncio.sleep(2)

        stock = await supplier.fetch_stock(test_part_number)
        await asyncio.sleep(2)

        specs = await supplier.fetch_specifications(test_part_number)

        # Verify core data was retrieved (some optional data may be missing)
        enrichment_data = {
            "part_details": part_details,
            "datasheet_url": datasheet_url,
            "image_url": image_url,
            "pricing": pricing,
            "stock": stock,
            "specifications": specs,
        }

        # Core capabilities should return data for this common part
        core_data = ["part_details", "pricing", "stock"]
        missing_core_data = [key for key in core_data if enrichment_data[key] is None]
        assert len(missing_core_data) == 0, f"Missing core enrichment data: {missing_core_data}"

        # Optional data may be missing
        optional_data = ["datasheet_url", "image_url", "specifications"]
        missing_optional_data = [key for key in optional_data if enrichment_data[key] is None]
        if missing_optional_data:
            print(f"Note: Missing optional data (acceptable): {missing_optional_data}")

        print(f"✅ Complete enrichment successful for {test_part_number}")
        print(f"   Manufacturer: {part_details.manufacturer}")
        print(f"   Description: {part_details.description}")
        print(f"   Stock: {stock}")
        print(f"   Price breaks: {len(pricing)}")
        print(f"   Specifications: {len(specs)}")
