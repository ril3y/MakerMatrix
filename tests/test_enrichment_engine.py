"""
Test EnrichmentEngine - Unified enrichment logic for all suppliers

This test suite verifies that the EnrichmentEngine:
1. Provides a single, unified code path for both instant and background enrichment
2. Is completely supplier-agnostic (no hardcoded supplier names)
3. Makes enrichment decisions based on capabilities, not supplier names
4. Properly delegates mapping to suppliers' map_to_standard_format() methods
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from MakerMatrix.services.system.enrichment_engine import EnrichmentEngine, enrichment_engine
from MakerMatrix.suppliers.base import (
    PartSearchResult, EnrichmentResult, SupplierCapability, SupplierInfo
)


class MockSupplier:
    """Mock supplier for testing enrichment engine"""

    def __init__(
        self,
        name: str = "test-supplier",
        supports_scraping: bool = False,
        has_credentials: bool = True,
        scraping_result: PartSearchResult = None,
        api_result: EnrichmentResult = None
    ):
        self.name = name
        self._supports_scraping = supports_scraping
        self._has_credentials = has_credentials
        self._scraping_result = scraping_result
        self._api_result = api_result
        self._configured = False

    def get_supplier_info(self):
        return SupplierInfo(
            name=self.name,
            display_name=f"{self.name.title()} Supplier",
            description=f"Mock {self.name} supplier for testing",
            website_url=f"https://{self.name}.com"
        )

    def supports_scraping(self):
        return self._supports_scraping

    def is_configured(self):
        return self._has_credentials

    def configure(self, credentials, config):
        self._configured = True

    async def scrape_part_details(self, url_or_part_number, force_refresh=False):
        """Simulate scraping"""
        if self._scraping_result:
            return self._scraping_result
        # Default scraping result
        return PartSearchResult(
            supplier_part_number="TEST-123",
            part_name="Test Part (Scraped)",
            manufacturer="Test Mfg",
            manufacturer_part_number="Test Part (Scraped)",  # This is what gets used for part_name in mapping
            description="Scraped part description"
        )

    async def enrich_part(self, supplier_part_number, capabilities=None):
        """Simulate API enrichment"""
        if self._api_result:
            return self._api_result
        # Default API result
        return EnrichmentResult(
            success=True,
            supplier_part_number=supplier_part_number,
            enriched_fields=['part_details'],
            data=PartSearchResult(
                supplier_part_number=supplier_part_number,
                part_name="Test Part (API)",
                manufacturer="Test Mfg",
                manufacturer_part_number="Test Part (API)",  # This is what gets used for part_name in mapping
                description="API enriched part description"
            )
        )

    def map_to_standard_format(self, supplier_data):
        """
        Simulate supplier-specific mapping.

        Returns a FLAT dictionary with all fields mixed together.
        SupplierDataMapper will separate core fields from custom fields automatically.
        """
        if isinstance(supplier_data, PartSearchResult):
            return {
                # Core fields (will be separated by mapper)
                'supplier_part_number': supplier_data.supplier_part_number,
                'part_name': supplier_data.part_name,
                'manufacturer': supplier_data.manufacturer,
                'description': supplier_data.description,
                # Custom field (will end up in additional_properties)
                'custom_field': f"{self.name}_specific_data"
            }
        return {}


class TestEnrichmentEngine:
    """Test the unified EnrichmentEngine"""

    @pytest.mark.asyncio
    async def test_engine_uses_scraping_when_no_credentials(self):
        """Test that engine uses scraping when supplier has no credentials but supports scraping"""
        # Create mock supplier with scraping support but no credentials
        mock_supplier = MockSupplier(
            name="test-scraper",
            supports_scraping=True,
            has_credentials=False
        )

        engine = EnrichmentEngine()

        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            result = await engine.enrich_part(
                supplier_name="test-scraper",
                part_identifier="TEST-123"
            )

        assert result['success'] is True
        assert result['enrichment_method'] == 'scraping'
        assert 'Test Part (Scraped)' in result['data']['part_name']

    @pytest.mark.asyncio
    async def test_engine_uses_api_when_credentials_available(self):
        """Test that engine uses API when credentials are available"""
        # Create mock supplier with credentials
        mock_supplier = MockSupplier(
            name="test-api",
            supports_scraping=False,
            has_credentials=True
        )

        engine = EnrichmentEngine()

        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            result = await engine.enrich_part(
                supplier_name="test-api",
                part_identifier="TEST-123"
            )

        assert result['success'] is True
        assert result['enrichment_method'] == 'api'
        assert 'Test Part (API)' in result['data']['part_name']

    @pytest.mark.asyncio
    async def test_engine_is_supplier_agnostic(self):
        """Test that engine makes decisions based on capabilities, not supplier names"""
        # This test verifies there's NO hardcoding of supplier names

        suppliers_to_test = [
            ("mcmaster-carr", True, False),  # Scraping, no creds
            ("digikey", False, True),        # API, has creds
            ("adafruit", True, False),       # Scraping, no creds
            ("custom-supplier", True, True), # Both
        ]

        engine = EnrichmentEngine()

        for supplier_name, supports_scraping, has_creds in suppliers_to_test:
            mock_supplier = MockSupplier(
                name=supplier_name,
                supports_scraping=supports_scraping,
                has_credentials=has_creds
            )

            with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
                result = await engine.enrich_part(
                    supplier_name=supplier_name,
                    part_identifier="TEST-123"
                )

            assert result['success'] is True

            # Verify enrichment method matches capabilities
            if supports_scraping and not has_creds:
                assert result['enrichment_method'] == 'scraping'
            elif has_creds:
                assert result['enrichment_method'] == 'api'

    @pytest.mark.asyncio
    async def test_engine_delegates_mapping_to_supplier(self):
        """Test that engine delegates data mapping to supplier's map_to_standard_format()"""
        mock_supplier = MockSupplier(
            name="test-mapper",
            has_credentials=True
        )

        engine = EnrichmentEngine()

        # Need to patch both the enrichment engine's get_supplier and the registry's get_supplier
        # so that SupplierDataMapper can find the supplier for custom mapping
        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            with patch('MakerMatrix.suppliers.registry.SupplierRegistry.get_supplier', return_value=mock_supplier):
                result = await engine.enrich_part(
                    supplier_name="test-mapper",
                    part_identifier="TEST-123"
                )

        # Verify supplier's custom mapping was used
        assert result['success'] is True
        # The SupplierDataMapper flattens custom fields from supplier's map_to_standard_format
        # into additional_properties as flat key-value pairs
        assert 'custom_field' in result['data']['additional_properties']
        assert result['data']['additional_properties']['custom_field'] == 'test-mapper_specific_data'

    @pytest.mark.asyncio
    async def test_engine_handles_enrichment_failure(self):
        """Test that engine properly handles enrichment failures"""
        # Create supplier that returns failed enrichment
        failed_result = EnrichmentResult(
            success=False,
            supplier_part_number="TEST-123",
            failed_fields=['part_details'],
            errors={'part_details': 'Part not found'}
        )

        mock_supplier = MockSupplier(
            name="test-fail",
            has_credentials=True,
            api_result=failed_result
        )

        engine = EnrichmentEngine()

        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            result = await engine.enrich_part(
                supplier_name="test-fail",
                part_identifier="NONEXISTENT"
            )

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_engine_handles_missing_supplier(self):
        """Test that engine handles missing/unknown suppliers gracefully"""
        engine = EnrichmentEngine()

        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=None):
            result = await engine.enrich_part(
                supplier_name="unknown-supplier",
                part_identifier="TEST-123"
            )

        assert result['success'] is False
        assert 'not found in registry' in result['error']

    @pytest.mark.asyncio
    async def test_engine_with_force_refresh(self):
        """Test that engine passes force_refresh parameter correctly"""
        force_refresh_called = {'scraping': False, 'api': False}

        async def mock_scrape(url_or_part_number, force_refresh=False):
            force_refresh_called['scraping'] = force_refresh
            return PartSearchResult(
                supplier_part_number="TEST",
                part_name="Test Part",
                manufacturer="Test Mfg",
                manufacturer_part_number="TEST"
            )

        async def mock_enrich(supplier_part_number, capabilities=None):
            # API methods don't typically have force_refresh
            return EnrichmentResult(
                success=True,
                supplier_part_number=supplier_part_number,
                data=PartSearchResult(
                    supplier_part_number=supplier_part_number,
                    manufacturer_part_number=supplier_part_number
                )
            )

        mock_supplier = MockSupplier(supports_scraping=True, has_credentials=False)
        mock_supplier.scrape_part_details = mock_scrape
        mock_supplier.enrich_part = mock_enrich

        engine = EnrichmentEngine()

        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            await engine.enrich_part(
                supplier_name="test",
                part_identifier="TEST",
                force_refresh=True
            )

        assert force_refresh_called['scraping'] is True


class TestUnifiedEnrichmentPaths:
    """Test that both enrichment paths use the same engine"""

    @pytest.mark.asyncio
    async def test_instant_and_background_use_same_logic(self):
        """Verify both instant (URL) and background (button) enrichment use EnrichmentEngine"""
        # This is a conceptual test - both paths should call enrichment_engine.enrich_part()

        mock_supplier = MockSupplier(has_credentials=True)

        # Simulate instant enrichment call (from parts_routes.py)
        engine = EnrichmentEngine()
        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            instant_result = await engine.enrich_part(
                supplier_name="test",
                part_identifier="TEST-123"
            )

        # Simulate background enrichment call (from part_enrichment_service.py)
        with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
            background_result = await engine.enrich_part(
                supplier_name="test",
                part_identifier="TEST-123"
            )

        # Both should produce identical results
        assert instant_result['success'] == background_result['success']
        assert instant_result['enrichment_method'] == background_result['enrichment_method']
        assert instant_result['data']['part_name'] == background_result['data']['part_name']

    def test_singleton_instance_exists(self):
        """Test that a singleton enrichment_engine instance exists for use"""
        # Both enrichment paths should use the same singleton instance
        from MakerMatrix.services.system.enrichment_engine import enrichment_engine

        assert enrichment_engine is not None
        assert isinstance(enrichment_engine, EnrichmentEngine)


class TestSupplierAgnosticDecisionLogic:
    """Test that all enrichment decisions are capability-based, not name-based"""

    @pytest.mark.asyncio
    async def test_no_hardcoded_supplier_names_in_engine(self):
        """Verify EnrichmentEngine contains NO hardcoded supplier names"""
        import inspect
        from MakerMatrix.services.system import enrichment_engine as engine_module

        # Read the source code of the enrichment_engine module
        source = inspect.getsource(engine_module)

        # These supplier names should NOT appear in the engine code
        forbidden_hardcoded_names = [
            'mcmaster-carr',
            'mcmaster_carr',
            'digikey',
            'mouser',
            'lcsc',
            'adafruit'
        ]

        # Check for hardcoded names (case insensitive)
        source_lower = source.lower()
        for supplier_name in forbidden_hardcoded_names:
            # Allow supplier names in comments or docstrings, but not in actual logic
            # This is a simplified check - in reality we'd want to parse the AST
            assert supplier_name.replace('-', '_') not in source_lower or \
                   supplier_name in ['# ', '"""', "'''"], \
                   f"Found hardcoded supplier name '{supplier_name}' in EnrichmentEngine"

    @pytest.mark.asyncio
    async def test_decision_based_on_capabilities_only(self):
        """Test that enrichment method decision is based ONLY on capabilities"""
        engine = EnrichmentEngine()

        # Test matrix: (supports_scraping, has_credentials, expected_method)
        test_matrix = [
            (True, False, 'scraping'),  # Scraping available, no creds → scraping
            (False, True, 'api'),        # No scraping, has creds → API
            (True, True, 'api'),         # Both available → prefer API
            (False, False, 'error'),     # Neither available → error
        ]

        for supports_scraping, has_creds, expected_method in test_matrix:
            mock_supplier = MockSupplier(
                supports_scraping=supports_scraping,
                has_credentials=has_creds
            )

            with patch('MakerMatrix.services.system.enrichment_engine.get_supplier', return_value=mock_supplier):
                result = await engine.enrich_part(
                    supplier_name=f"test-{expected_method}",
                    part_identifier="TEST-123"
                )

            if expected_method == 'error':
                assert result['success'] is False
            else:
                assert result['success'] is True
                assert result['enrichment_method'] == expected_method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
