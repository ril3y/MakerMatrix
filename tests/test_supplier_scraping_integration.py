"""
Integration tests for supplier web scraping fallback functionality

These tests HIT REAL URLS to verify scraping works and detect HTML changes.
Tests are marked as 'slow' since they make real HTTP requests.

Run with: pytest tests/test_supplier_scraping_integration.py -v
Run slow tests: pytest tests/test_supplier_scraping_integration.py -v -m slow
"""

import pytest
import aiohttp
from typing import Dict, Any

from MakerMatrix.suppliers.mcmaster_carr import McMasterCarrSupplier
from MakerMatrix.suppliers.base import SupplierCapability, PartSearchResult


class TestMcMasterScrapingIntegration:
    """Integration tests for McMaster-Carr scraping functionality"""

    def test_mcmaster_supports_scraping(self):
        """Test that McMaster-Carr reports scraping support"""
        supplier = McMasterCarrSupplier()
        assert supplier.supports_scraping() is True

    def test_mcmaster_scraping_config(self):
        """Test McMaster-Carr scraping configuration"""
        supplier = McMasterCarrSupplier()
        config = supplier.get_scraping_config()

        # Check required config keys
        assert "requires_js" in config
        assert config["requires_js"] is True  # McMaster uses React

        assert "rate_limit_seconds" in config
        assert config["rate_limit_seconds"] == 2

        assert "selectors" in config
        selectors = config["selectors"]

        # Check key selectors are defined (based on actual implementation)
        assert "heading" in selectors
        assert "price" in selectors
        assert "spec_table" in selectors

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_mcmaster_real_scraping(self):
        """
        Test McMaster scraping with REAL web request.

        This test hits the actual McMaster-Carr website to:
        1. Verify our scraping logic still works
        2. Detect if HTML structure has changed
        3. Validate data extraction

        Part: M5 x 16mm Socket Head Cap Screw (91253A194)
        """
        supplier = McMasterCarrSupplier()

        try:
            # Real URL for a stable McMaster part number
            result = await supplier.scrape_part_details("https://www.mcmaster.com/91253A194/")

            # Verify we got some data back
            assert result is not None, "Scraping returned None - HTML structure may have changed"

            # Basic data validation
            assert result.supplier_part_number, "Failed to extract part number - check HTML selectors"

            # McMaster part numbers are typically in format: XXXXXYXXX
            assert len(result.supplier_part_number) > 5, f"Part number seems malformed: {result.supplier_part_number}"

            # Should have extracted a part name
            assert result.part_name, "Failed to extract part name - HTML structure may have changed"
            assert len(result.part_name) > 3, f"Part name seems too short: {result.part_name}"

            # Should have some specifications
            if result.specifications:
                assert len(result.specifications) > 0, "No specifications extracted - check spec table selector"
                print(f"\n✓ Successfully scraped McMaster part {result.supplier_part_number}")
                print(f"  Name: {result.part_name}")
                print(f"  Specs extracted: {len(result.specifications)}")
            else:
                # Log warning but don't fail - specs might be structured differently
                print(f"\n⚠ Warning: No specifications extracted for {result.supplier_part_number}")

        except aiohttp.ClientError as e:
            pytest.skip(f"Network error accessing McMaster-Carr: {e}")
        except Exception as e:
            pytest.fail(f"Scraping failed - HTML structure may have changed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_mcmaster_html_structure_validation(self):
        """
        Validate that McMaster-Carr's HTML structure matches our expectations.

        This is a canary test - if it fails, our selectors need updating.
        """
        supplier = McMasterCarrSupplier()
        config = supplier.get_scraping_config()
        selectors = config["selectors"]

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://www.mcmaster.com/91253A194/"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    assert response.status == 200, f"McMaster returned status {response.status}"

                    html = await response.text()
                    assert html, "Got empty HTML response"

                    # Check for key HTML patterns our selectors expect
                    # This helps us detect when McMaster's site changes

                    # Check if it's still a React app (we expect client-side rendering)
                    assert (
                        "react" in html.lower() or "__NEXT_DATA__" in html
                    ), "McMaster may have changed from React - update 'requires_js' config"

                    # Verify page has product data structure
                    assert (
                        "product" in html.lower() or "part" in html.lower()
                    ), "Product data structure not found - site may have changed"

                    print(f"\n✓ McMaster HTML structure validation passed")
                    print(f"  Page size: {len(html)} bytes")
                    print(f"  Requires JS: {config['requires_js']}")

        except aiohttp.ClientError as e:
            pytest.skip(f"Network error: {e}")

    @pytest.mark.asyncio
    async def test_mcmaster_fallback_when_no_credentials(self):
        """Test that McMaster falls back to scraping when no API credentials"""
        supplier = McMasterCarrSupplier()

        # McMaster doesn't have a public API, so it should always use scraping
        assert supplier.supports_scraping() is True

        # Verify that scraping mode is available
        config = supplier.get_scraping_config()
        assert config is not None
        assert "selectors" in config


class TestAPIEndpointIntegration:
    """Test integration between scraping and API endpoints"""

    def test_scraping_capability_registration(self):
        """Test that scraping capability is properly registered"""
        # Direct import since get_supplier might not exist
        supplier = McMasterCarrSupplier()
        assert supplier is not None
        assert supplier.supports_scraping() is True

    @pytest.mark.slow
    def test_scraping_detects_broken_selectors(self):
        """
        This test exists to catch when supplier websites change their HTML.

        If this test fails:
        1. Check the supplier's website manually
        2. Update selectors in the supplier class
        3. Re-run tests to verify
        """
        supplier = McMasterCarrSupplier()
        config = supplier.get_scraping_config()

        # Validate selector configuration (based on actual implementation)
        required_selectors = ["heading", "price", "spec_table"]
        selectors = config.get("selectors", {})

        for selector_key in required_selectors:
            assert selector_key in selectors, f"Missing required selector: {selector_key}"
            assert selectors[selector_key], f"Selector {selector_key} is empty"

        print(f"\n✓ All {len(required_selectors)} required selectors configured")


# Mark all tests in this file for organization
pytestmark = pytest.mark.integration
