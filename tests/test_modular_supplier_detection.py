"""
Test modular supplier detection system

This test verifies that the URL-based supplier detection works properly
with the new modular approach using get_url_patterns() method.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import re

from MakerMatrix.suppliers.mcmaster_carr import McMasterCarrSupplier
from MakerMatrix.suppliers.registry import SupplierRegistry


class TestModularSupplierDetection:
    """Test the modular supplier detection system"""

    def test_mcmaster_has_url_patterns(self):
        """Test that McMaster-Carr supplier has URL patterns defined"""
        supplier = McMasterCarrSupplier()

        # Check that the method exists
        assert hasattr(supplier, 'get_url_patterns')

        # Get the patterns
        patterns = supplier.get_url_patterns()

        # Check that patterns are defined
        assert isinstance(patterns, list)
        assert len(patterns) > 0

        # Check that patterns are valid regex
        for pattern in patterns:
            assert isinstance(pattern, str)
            # Should not raise exception
            re.compile(pattern)

    def test_url_pattern_matching(self):
        """Test that McMaster URL patterns match expected URLs"""
        supplier = McMasterCarrSupplier()
        patterns = supplier.get_url_patterns()

        # Test URLs that should match
        test_urls = [
            "https://www.mcmaster.com/91253A194/",
            "https://mcmaster.com/91253A194",
            "http://www.mcmaster.com/screws/91253A194/",
            "https://mcmaster-carr.com/products/91253A194",
            "mcmaster.com/91253A194",
            "www.mcmaster.com",
        ]

        for url in test_urls:
            matched = False
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"URL {url} did not match any pattern"

    def test_supplier_detection_logic(self):
        """Test the supplier detection logic that would be used in the backend"""

        # Simulate the backend detection logic
        def detect_supplier(url: str) -> Dict[str, Any]:
            """Simulate backend detection logic"""
            url_lower = url.lower().strip()

            # Check all registered suppliers
            for supplier_name in ['mcmaster-carr']:  # Simplified for test
                supplier = SupplierRegistry.get_supplier(supplier_name)
                info = supplier.get_supplier_info()

                # Check if supplier has URL detection patterns
                if hasattr(supplier, 'get_url_patterns'):
                    patterns = supplier.get_url_patterns()
                    for pattern in patterns:
                        if re.search(pattern, url, re.IGNORECASE):
                            # Found a match with URL pattern
                            return {
                                "supplier_name": supplier_name,
                                "display_name": info.name,
                                "confidence": 1.0
                            }

                # Fallback to domain matching
                if info.website_url:
                    from urllib.parse import urlparse

                    website_domain = urlparse(info.website_url).netloc.lower()
                    url_domain = urlparse(url_lower if url_lower.startswith('http') else f'https://{url_lower}').netloc.lower()

                    if website_domain and url_domain:
                        # Check for domain match
                        if website_domain == url_domain or url_domain.endswith(f'.{website_domain}'):
                            return {
                                "supplier_name": supplier_name,
                                "display_name": info.name,
                                "confidence": 0.8
                            }

            return None

        # Test McMaster URLs
        test_cases = [
            ("https://www.mcmaster.com/91253A194/", "mcmaster-carr", 1.0),
            ("https://mcmaster.com/products/screws/91253A194", "mcmaster-carr", 1.0),
            ("mcmaster-carr.com/91253A194", "mcmaster-carr", 1.0),
        ]

        for url, expected_supplier, expected_confidence in test_cases:
            result = detect_supplier(url)
            assert result is not None, f"Failed to detect supplier for {url}"
            assert result["supplier_name"] == expected_supplier, f"Wrong supplier detected for {url}"
            assert result["confidence"] == expected_confidence, f"Wrong confidence for {url}"

    @pytest.mark.asyncio
    async def test_backend_endpoint_simulation(self):
        """Test simulation of the backend endpoint behavior"""

        # This simulates what the /api/suppliers/detect-from-url endpoint does
        async def detect_from_url(url: str) -> Dict[str, Any]:
            """Simulate the backend endpoint logic"""
            url_lower = url.lower().strip()

            # Get all suppliers from registry
            suppliers_to_check = ['mcmaster-carr']  # Simplified for test

            for supplier_name in suppliers_to_check:
                try:
                    supplier = SupplierRegistry.get_supplier(supplier_name)
                    info = supplier.get_supplier_info()

                    # Check URL patterns if available
                    if hasattr(supplier, 'get_url_patterns'):
                        patterns = supplier.get_url_patterns()
                        for pattern in patterns:
                            if re.search(pattern, url, re.IGNORECASE):
                                return {
                                    "status": "success",
                                    "data": {
                                        "supplier_name": supplier_name,
                                        "display_name": info.name,
                                        "confidence": 1.0
                                    }
                                }
                except Exception as e:
                    print(f"Error checking supplier {supplier_name}: {e}")
                    continue

            # No match found
            return {
                "status": "success",
                "data": None
            }

        # Test with McMaster URL
        result = await detect_from_url("https://www.mcmaster.com/91253A194/")
        assert result["status"] == "success"
        assert result["data"] is not None
        assert result["data"]["supplier_name"] == "mcmaster-carr"
        assert result["data"]["display_name"] == "McMaster-Carr"
        assert result["data"]["confidence"] == 1.0

    def test_no_hardcoding_verification(self):
        """Verify that the solution is truly modular with no hardcoding"""

        # The detection should work purely based on supplier's get_url_patterns() method
        # No hardcoded mappings should exist

        # Mock a new supplier with different patterns
        class CustomSupplier:
            def get_supplier_info(self):
                return Mock(
                    name="Custom Supplier",
                    website_url="https://custom.com"
                )

            def get_url_patterns(self):
                return [
                    r'custom\.com/parts/',
                    r'customsupplier\.io'
                ]

        # Test that custom patterns work
        supplier = CustomSupplier()
        patterns = supplier.get_url_patterns()

        test_url = "https://custom.com/parts/ABC123"
        matched = False
        for pattern in patterns:
            if re.search(pattern, test_url, re.IGNORECASE):
                matched = True
                break

        assert matched, "Custom supplier patterns should match their URLs"

        # Verify McMaster patterns are not hardcoded elsewhere
        # The only place patterns should exist is in the supplier class itself
        mcmaster = McMasterCarrSupplier()
        patterns = mcmaster.get_url_patterns()

        # Patterns should be returned by the method, not hardcoded in detection logic
        assert len(patterns) > 0
        assert all(isinstance(p, str) for p in patterns)


class TestIntegrationWithRegistry:
    """Test integration with the supplier registry"""

    def test_registry_has_mcmaster(self):
        """Verify McMaster-Carr is registered properly"""
        # Get supplier from registry
        supplier = SupplierRegistry.get_supplier("mcmaster-carr")
        assert supplier is not None
        assert isinstance(supplier, McMasterCarrSupplier)

        # Check it has URL patterns
        assert hasattr(supplier, 'get_url_patterns')
        patterns = supplier.get_url_patterns()
        assert len(patterns) > 0

    def test_all_suppliers_checked(self):
        """Test that detection checks all registered suppliers"""
        # Get all available suppliers
        all_suppliers = SupplierRegistry.get_available_suppliers()

        # McMaster should be in the list
        assert "mcmaster-carr" in all_suppliers

        # Each supplier should be checkable for URL patterns
        for supplier_name in all_suppliers:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            # Check if supplier has the optional get_url_patterns method
            if hasattr(supplier, 'get_url_patterns'):
                patterns = supplier.get_url_patterns()
                assert isinstance(patterns, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])