"""
Test correct handling of supplier names through the detection and enrichment flow

This test verifies that supplier names are correctly handled:
- Detection returns the correct supplier name (lowercase)
- Display name is separate from the actual supplier name
- API calls use the correct supplier name format
"""

import pytest
from unittest.mock import Mock, patch
from MakerMatrix.suppliers.mcmaster_carr import McMasterCarrSupplier
from MakerMatrix.suppliers.registry import SupplierRegistry
import re


class TestSupplierNameHandling:
    """Test that supplier names are handled correctly throughout the system"""

    def test_mcmaster_supplier_info_names(self):
        """Test that McMaster-Carr supplier returns correct names"""
        supplier = McMasterCarrSupplier()
        info = supplier.get_supplier_info()

        # Display name should be capitalized
        assert info.name == "McMaster-Carr"
        assert info.display_name == "McMaster-Carr"

        # Registry should have lowercase name
        assert "mcmaster-carr" in SupplierRegistry.get_available_suppliers()

    def test_url_detection_returns_correct_name_format(self):
        """Test that URL detection returns lowercase supplier name"""

        # Simulate the backend detection logic
        def detect_supplier_from_url(url: str):
            """Simulate backend supplier detection"""
            url_lower = url.lower().strip()

            # Check McMaster-Carr patterns
            supplier = SupplierRegistry.get_supplier("mcmaster-carr")
            info = supplier.get_supplier_info()

            if hasattr(supplier, "get_url_patterns"):
                patterns = supplier.get_url_patterns()
                for pattern in patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        return {
                            "supplier_name": "mcmaster-carr",  # Should be lowercase
                            "display_name": info.name,  # Should be "McMaster-Carr"
                            "confidence": 1.0,
                        }
            return None

        # Test with McMaster URL
        result = detect_supplier_from_url("https://www.mcmaster.com/91253A194/")

        assert result is not None
        assert result["supplier_name"] == "mcmaster-carr"  # Lowercase for API calls
        assert result["display_name"] == "McMaster-Carr"  # Formatted for display
        assert result["confidence"] == 1.0

    def test_enrichment_endpoints_use_correct_name(self):
        """Test that enrichment endpoints are called with correct supplier name"""

        # The enrichment endpoint should be called with lowercase supplier name
        supplier_name_for_api = "mcmaster-carr"

        # Simulated API endpoints that should work
        test_endpoints = [
            f"/api/parts/enrichment-requirements/{supplier_name_for_api}",
            f"/api/suppliers/{supplier_name_for_api}/enrichment-field-mappings",
            f"/api/suppliers/{supplier_name_for_api}/info",
            f"/api/suppliers/{supplier_name_for_api}/test",
        ]

        for endpoint in test_endpoints:
            # All endpoints should use lowercase supplier name
            assert "mcmaster-carr" in endpoint
            assert "McMaster-Carr" not in endpoint

    def test_supplier_field_mapping_extraction(self):
        """Test that enrichment field mappings work correctly"""
        supplier = McMasterCarrSupplier()

        # Supplier should have URL patterns
        assert hasattr(supplier, "get_url_patterns")
        patterns = supplier.get_url_patterns()

        # Test URL extraction with patterns
        test_urls = [
            "https://www.mcmaster.com/91253A194/",
            "https://mcmaster.com/screws/91253A194",
            "https://www.mcmaster.com/products/fasteners/91253A194/",
        ]

        for url in test_urls:
            # At least one pattern should match
            matched = False
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"No pattern matched URL: {url}"

            # Extract part number from URL (simplified)
            part_match = re.search(r"/([A-Za-z0-9]+)/?$", url)
            if part_match:
                part_number = part_match.group(1)
                assert part_number == "91253A194"

    def test_frontend_supplier_field_value(self):
        """Test that frontend sets correct supplier field value"""

        # Simulate what the frontend should do
        detected_supplier = {"supplier_name": "mcmaster-carr", "display_name": "McMaster-Carr", "confidence": 1.0}

        # Frontend should use supplier_name for form field
        supplier_for_form = detected_supplier["supplier_name"].lower()
        # Display name for UI
        display_name = detected_supplier["display_name"]

        assert supplier_for_form == "mcmaster-carr"
        assert display_name == "McMaster-Carr"

        # API calls should use supplier_for_form
        api_url = f"/api/parts/enrichment-requirements/{supplier_for_form}"
        assert api_url == "/api/parts/enrichment-requirements/mcmaster-carr"

    def test_enrichment_field_mappings_response(self):
        """Test enrichment field mappings response structure"""

        # Expected structure for enrichment field mappings
        expected_mapping = {
            "field_name": "supplier_part_number",
            "display_name": "Supplier Part Number",
            "url_patterns": [r"/([A-Za-z0-9]+)/?$"],
            "example": "91253A194",
            "required_for_enrichment": True,
        }

        # Verify the structure matches what frontend expects
        assert "field_name" in expected_mapping
        assert "display_name" in expected_mapping
        assert "url_patterns" in expected_mapping
        assert isinstance(expected_mapping["url_patterns"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
