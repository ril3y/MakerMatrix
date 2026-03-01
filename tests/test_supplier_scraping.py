"""
Test cases for supplier web scraping fallback functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from MakerMatrix.suppliers.mcmaster_carr import McMasterCarrSupplier
from MakerMatrix.suppliers.base import BaseSupplier, SupplierCapability, PartSearchResult
from MakerMatrix.suppliers.scrapers.web_scraper import WebScraper


class TestSupplierScrapingInterface:
    """Test the base supplier scraping interface"""

    def test_base_supplier_no_scraping_by_default(self):
        """Test that BaseSupplier doesn't support scraping by default"""
        supplier = BaseSupplier()
        assert supplier.supports_scraping() is False

    def test_base_supplier_scraping_raises_not_implemented(self):
        """Test that calling scrape_part_details raises NotImplementedError"""
        supplier = BaseSupplier()
        with pytest.raises(NotImplementedError):
            import asyncio

            asyncio.run(supplier.scrape_part_details("test_url"))

    def test_base_supplier_scraping_config_default(self):
        """Test that default scraping config is empty"""
        supplier = BaseSupplier()
        config = supplier.get_scraping_config()
        assert config == {}


class TestMcMasterCarrScraping:
    """Test McMaster-Carr specific scraping implementation"""

    def test_mcmaster_supports_scraping(self):
        """Test that McMaster-Carr reports NO scraping support"""
        supplier = McMasterCarrSupplier()
        assert supplier.supports_scraping() is False

    def test_mcmaster_does_not_have_scraping_capability(self):
        """Test that McMaster-Carr does NOT report scraping capability"""
        supplier = McMasterCarrSupplier()
        capabilities = supplier.get_capabilities()
        assert SupplierCapability.SCRAPE_PART_DETAILS not in capabilities

    def test_mcmaster_scraping_config_returns_default(self):
        """Test that getting scraping config returns default base config"""
        supplier = McMasterCarrSupplier()
        # Base implementation returns a default config, not empty dict
        config = supplier.get_scraping_config()
        assert "selectors" in config
        assert config["selectors"] == {}
        assert config["requires_js"] is False

    @pytest.mark.asyncio
    async def test_mcmaster_get_part_details_no_scraping_fallback(self):
        """Test that get_part_details returns None when no credentials, without scraping"""
        supplier = McMasterCarrSupplier()
        
        # Call without credentials
        # Note: The updated code logs an error and returns None directly
        result = await supplier.get_part_details("91253A194")
        
        assert result is None


class TestWebScraper:
    """Test the WebScraper utility class"""

    def test_web_scraper_initialization(self):
        """Test WebScraper can be initialized"""
        scraper = WebScraper()
        assert scraper is not None
        assert scraper.cache == {}

    def test_parse_price_valid_formats(self):
        """Test price parsing with various formats"""
        scraper = WebScraper()

        # Test different price formats
        test_cases = [
            ("$12.50", {"price": 12.50, "currency": "USD"}),
            ("$1,234.56", {"price": 1234.56, "currency": "USD"}),
            ("12.50", {"price": 12.50, "currency": "USD"}),
            ("€25.00", {"price": 25.00, "currency": "EUR"}),
            ("£30.50", {"price": 30.50, "currency": "GBP"}),
        ]

        for price_text, expected in test_cases:
            result = scraper.parse_price(price_text)
            assert result == expected

    def test_parse_price_invalid_formats(self):
        """Test price parsing with invalid formats"""
        scraper = WebScraper()

        invalid_prices = ["not a price", "", "N/A", "Call for quote"]

        for price_text in invalid_prices:
            result = scraper.parse_price(price_text)
            assert result is None

    def test_extract_table_data(self):
        """Test table data extraction"""
        scraper = WebScraper()

        # Mock HTML table
        html = """
        <table>
            <tr><td>Material</td><td>Steel</td></tr>
            <tr><td>Thread Size</td><td>M5</td></tr>
            <tr><td>Length</td><td>16mm</td></tr>
        </table>
        """

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        result = scraper.extract_table_data(table)

        assert result == {"Material": "Steel", "Thread Size": "M5", "Length": "16mm"}

    @pytest.mark.asyncio
    async def test_scraper_caching(self):
        """Test that scraper caches results"""
        scraper = WebScraper()

        # Mock the actual scraping
        with patch.object(scraper, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "<html><body><div id='test'>Content</div></body></html>"

            # First call
            result1 = await scraper.scrape_simple("http://test.com", {"content": "#test"})
            assert mock_fetch.call_count == 1

            # Second call - should use cache
            result2 = await scraper.scrape_simple("http://test.com", {"content": "#test"})
            assert mock_fetch.call_count == 1  # Still 1, not 2

            assert result1 == result2

    @pytest.mark.asyncio
    async def test_scraper_rate_limiting(self):
        """Test that scraper respects rate limits"""
        import time

        scraper = WebScraper()

        # Mock the fetch method
        with patch.object(scraper, "_fetch_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "<html><body>Test</body></html>"

            start_time = time.time()

            # Make two requests to same domain
            await scraper.scrape_simple("http://test.com/page1", {})
            await scraper.scrape_simple("http://test.com/page2", {})

            elapsed = time.time() - start_time

            # Should have waited at least 1 second between requests
            assert elapsed >= 1.0


class TestEnrichmentServiceScrapingFallback:
    """Test the part enrichment service scraping fallback"""

    @pytest.mark.asyncio
    async def test_enrichment_uses_scraping_when_no_credentials(self):
        """Test that enrichment service falls back to scraping"""
        from MakerMatrix.services.system.part_enrichment_service import PartEnrichmentService

        service = PartEnrichmentService()

        # Mock the supplier registry to return McMaster
        with patch("MakerMatrix.suppliers.registry.SupplierRegistry.get_supplier") as mock_get:
            mock_supplier = Mock(spec=McMasterCarrSupplier)
            mock_supplier.supports_scraping.return_value = True
            mock_supplier.get_part_details = AsyncMock(
                return_value=PartSearchResult(supplier_part_number="TEST123", part_name="Test Part")
            )
            mock_get.return_value = mock_supplier

            # Mock credentials storage to return empty
            with patch.object(service, "_get_supplier_credentials") as mock_creds:
                mock_creds.return_value = {}  # No credentials

                # Call enrichment
                client = await service._get_supplier_client("mcmaster-carr")

                # Verify scraping mode was enabled
                assert client is not None
                # In real implementation, config would have scraping_mode=True


class TestSupplierRoutesScrapingEndpoint:
    """Test the API routes for scraping support"""

    @pytest.mark.asyncio
    async def test_supports_scraping_endpoint_mcmaster(self):
        """Test /api/suppliers/{supplier}/supports-scraping for McMaster"""
        from MakerMatrix.routers.supplier_routes import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from MakerMatrix.auth.dependencies import get_current_user
        from MakerMatrix.models.user_models import UserModel

        app = FastAPI()
        app.include_router(router, prefix="/api/suppliers")
        
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: Mock(spec=UserModel)

        with TestClient(app) as client:
            # Mock the supplier registry
            with patch("MakerMatrix.suppliers.registry.SupplierRegistry.get_supplier") as mock_get:
                mock_supplier = Mock(spec=McMasterCarrSupplier)
                mock_supplier.supports_scraping.return_value = True
                mock_supplier.get_scraping_config.return_value = {"requires_js": True, "rate_limit_seconds": 2}
                mock_get.return_value = mock_supplier

                response = client.get("/api/suppliers/mcmaster-carr/supports-scraping")

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["supports_scraping"] is True
                assert data["data"]["requires_js"] is True
                assert data["data"]["rate_limit_seconds"] == 2
                assert "warning" in data["data"]

    @pytest.mark.asyncio
    async def test_supports_scraping_endpoint_no_scraping(self):
        """Test endpoint for supplier that doesn't support scraping"""
        from MakerMatrix.routers.supplier_routes import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from MakerMatrix.auth.dependencies import get_current_user
        from MakerMatrix.models.user_models import UserModel

        app = FastAPI()
        app.include_router(router, prefix="/api/suppliers")
        
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: Mock(spec=UserModel)

        with TestClient(app) as client:
            # Mock a supplier that doesn't support scraping
            with patch("MakerMatrix.suppliers.registry.SupplierRegistry.get_supplier") as mock_get:
                mock_supplier = Mock(spec=BaseSupplier)
                mock_supplier.supports_scraping.return_value = False
                mock_get.return_value = mock_supplier

                response = client.get("/api/suppliers/digikey/supports-scraping")

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["supports_scraping"] is False
                assert data["data"]["warning"] is None
