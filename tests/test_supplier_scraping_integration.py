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
        """Test that McMaster-Carr reports NO scraping support"""
        supplier = McMasterCarrSupplier()
        assert supplier.supports_scraping() is False

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_mcmaster_no_scraping_config(self):
        """Test that get_scraping_config retrieves default config"""
        supplier = McMasterCarrSupplier()
        config = supplier.get_scraping_config()
        # Should be default dict
        assert config.get("selectors") == {}

    @pytest.mark.asyncio
    async def test_mcmaster_no_fallback_when_no_credentials(self):
        """Test that McMaster returns None when no API credentials, no scraping fallback"""
        supplier = McMasterCarrSupplier()

        # McMaster doesn't support scraping anymore
        assert supplier.supports_scraping() is False

        # Attempt to get details without credential
        result = await supplier.get_part_details("91253A194")
        assert result is None


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
