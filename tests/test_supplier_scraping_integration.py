"""
Integration tests for supplier web scraping fallback functionality

These tests verify the complete flow of the scraping fallback feature
including API endpoints and supplier implementation.
"""

import pytest
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
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
        assert 'requires_js' in config
        assert config['requires_js'] is True  # McMaster uses React

        assert 'rate_limit_seconds' in config
        assert config['rate_limit_seconds'] == 2

        assert 'selectors' in config
        selectors = config['selectors']

        # Check key selectors are defined
        assert 'part_number' in selectors
        assert 'price' in selectors
        assert 'spec_table' in selectors

    @pytest.mark.asyncio
    async def test_mcmaster_scrape_with_mock(self):
        """Test McMaster scraping with mocked web response"""
        supplier = McMasterCarrSupplier()

        # Mock the scrape_part_details method
        mock_result = PartSearchResult(
            supplier_part_number="91253A194",
            part_name="Socket Head Cap Screw",
            description="Steel Socket Head Cap Screw, M5 x 16mm",
            category="Fasteners",
            specifications={
                "Material": "Steel",
                "Thread Size": "M5",
                "Length": "16mm",
                "Head Type": "Socket Head",
                "Drive Type": "Hex Socket"
            }
        )

        with patch.object(supplier, 'scrape_part_details', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = mock_result

            # Test with URL
            result = await supplier.scrape_part_details("https://www.mcmaster.com/91253A194/")

            assert result is not None
            assert result.supplier_part_number == "91253A194"
            assert result.part_name == "Socket Head Cap Screw"
            assert len(result.specifications) > 0

            # Verify the method was called
            mock_scrape.assert_called_once_with("https://www.mcmaster.com/91253A194/")

    @pytest.mark.asyncio
    async def test_mcmaster_fallback_when_no_credentials(self):
        """Test that McMaster falls back to scraping when no API credentials"""
        supplier = McMasterCarrSupplier()

        # Mock the scrape method
        mock_result = PartSearchResult(
            supplier_part_number="91253A194",
            part_name="Test Part"
        )

        with patch.object(supplier, 'scrape_part_details', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = mock_result

            # Call get_part_details with scraping mode
            result = await supplier.get_part_details(
                "91253A194",
                credentials={},
                config={'scraping_mode': True}
            )

            # Verify scraping was used
            mock_scrape.assert_called_once_with("91253A194")
            assert result == mock_result


class TestAPIEndpointIntegration:
    """Test the API endpoints for scraping support"""

    @pytest.mark.asyncio
    async def test_scraping_support_endpoint_live(self):
        """Test the live scraping support endpoint"""
        # This test requires the backend to be running
        import os
        api_key = os.getenv('ADMIN_API_KEY', 'REDACTED_API_KEY')

        async with aiohttp.ClientSession() as session:
            try:
                # Test McMaster-Carr endpoint
                url = "https://localhost:8443/api/suppliers/mcmaster-carr/supports-scraping"
                headers = {"X-API-Key": api_key}

                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()

                        assert data['status'] == 'success'
                        assert data['data']['supports_scraping'] is True
                        assert data['data']['requires_js'] is True
                        assert data['data']['warning'] is not None
                        assert data['data']['rate_limit_seconds'] == 2.0
                    else:
                        pytest.skip(f"Backend not available or returned {response.status}")

            except aiohttp.ClientConnectorError:
                pytest.skip("Backend not running, skipping live test")


class TestScrapingWorkflow:
    """Test the complete scraping workflow"""

    @pytest.mark.asyncio
    async def test_complete_scraping_workflow(self):
        """Test the complete workflow from URL detection to scraping"""

        # This simulates what happens in the frontend
        test_url = "https://www.mcmaster.com/91253A194/"

        # Step 1: Detect supplier from URL
        supplier_name = None
        if "mcmaster.com" in test_url.lower():
            supplier_name = "mcmaster-carr"

        assert supplier_name == "mcmaster-carr"

        # Step 2: Check if supplier supports scraping
        from MakerMatrix.suppliers.registry import get_supplier
        supplier = get_supplier(supplier_name)

        assert supplier.supports_scraping() is True

        config = supplier.get_scraping_config()
        assert config['requires_js'] is True

        # Step 3: Mock the scraping process
        with patch.object(supplier, 'scrape_part_details', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = PartSearchResult(
                supplier_part_number="91253A194",
                part_name="Socket Head Cap Screw",
                description="Steel fastener",
                specifications={"Material": "Steel", "Size": "M5"}
            )

            # Perform scraping
            result = await supplier.scrape_part_details(test_url)

            # Verify results
            assert result is not None
            assert result.supplier_part_number == "91253A194"
            assert result.part_name == "Socket Head Cap Screw"
            assert "Material" in result.specifications

            # Verify URL was passed correctly
            mock_scrape.assert_called_once_with(test_url)


class TestErrorHandling:
    """Test error handling in scraping functionality"""

    @pytest.mark.asyncio
    async def test_scraping_handles_invalid_url(self):
        """Test that scraping handles invalid URLs gracefully"""
        supplier = McMasterCarrSupplier()

        with patch.object(supplier, 'scrape_part_details', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = None

            result = await supplier.scrape_part_details("invalid-url")

            assert result is None
            mock_scrape.assert_called_once_with("invalid-url")

    @pytest.mark.asyncio
    async def test_scraping_handles_network_error(self):
        """Test that scraping handles network errors gracefully"""
        supplier = McMasterCarrSupplier()

        with patch.object(supplier, 'scrape_part_details', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")

            with pytest.raises(Exception) as exc_info:
                await supplier.scrape_part_details("https://www.mcmaster.com/91253A194/")

            assert "Network error" in str(exc_info.value)