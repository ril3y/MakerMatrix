"""
Test McMaster-Carr enrichment field mappings

This test verifies that the enrichment field mappings work correctly
for extracting part numbers from McMaster-Carr URLs.
"""

import pytest
import re
from MakerMatrix.suppliers.mcmaster_carr import McMasterCarrSupplier
from MakerMatrix.suppliers.base import EnrichmentFieldMapping


class TestMcMasterEnrichmentMapping:
    """Test McMaster-Carr enrichment field mappings"""

    def test_mcmaster_has_enrichment_mappings(self):
        """Test that McMaster-Carr has enrichment field mappings defined"""
        supplier = McMasterCarrSupplier()

        # Check that the method exists and returns mappings
        mappings = supplier.get_enrichment_field_mappings()

        assert isinstance(mappings, list)
        assert len(mappings) > 0

        # Check the first mapping
        mapping = mappings[0]
        assert isinstance(mapping, EnrichmentFieldMapping)
        assert mapping.field_name == "supplier_part_number"
        assert mapping.display_name == "McMaster-Carr Part Number"
        assert mapping.required_for_enrichment is True
        assert len(mapping.url_patterns) > 0

    def test_url_pattern_extraction(self):
        """Test that URL patterns correctly extract part numbers"""
        supplier = McMasterCarrSupplier()
        mappings = supplier.get_enrichment_field_mappings()

        # Get the supplier part number mapping
        part_number_mapping = next(
            (m for m in mappings if m.field_name == "supplier_part_number"),
            None
        )

        assert part_number_mapping is not None

        # Test URLs with expected part numbers
        test_cases = [
            ("https://www.mcmaster.com/91253A194/", "91253A194"),
            ("https://mcmaster.com/91253A194", "91253A194"),
            ("https://www.mcmaster.com/screws/91253A194/", "91253A194"),
            ("https://mcmaster.com/fasteners/socket-screws/91253A194", "91253A194"),
            ("https://www.mcmaster.com/91253A194?param=value", "91253A194"),
            ("https://www.mcmaster.com/91253A194#section", "91253A194"),
            ("https://www.mcmaster.com/ABC123XYZ/", "ABC123XYZ"),
        ]

        for url, expected_part in test_cases:
            extracted = None

            # Try each pattern to extract the part number
            for pattern in part_number_mapping.url_patterns:
                match = re.search(pattern, url)
                if match:
                    extracted = match.group(1)
                    break

            assert extracted == expected_part, f"Failed to extract {expected_part} from {url}, got {extracted}"

    def test_pattern_does_not_match_invalid_urls(self):
        """Test that patterns don't match non-McMaster URLs"""
        supplier = McMasterCarrSupplier()
        mappings = supplier.get_enrichment_field_mappings()

        part_number_mapping = mappings[0]

        # URLs that should NOT extract anything
        invalid_urls = [
            "https://www.digikey.com/product/12345",
            "https://www.adafruit.com/product/4567",
            "https://www.example.com/91253A194",
        ]

        for url in invalid_urls:
            # First check if this is even a McMaster URL using get_url_patterns
            is_mcmaster = False
            for pattern in supplier.get_url_patterns():
                if re.search(pattern, url, re.IGNORECASE):
                    is_mcmaster = True
                    break

            assert not is_mcmaster, f"URL {url} incorrectly identified as McMaster"

    def test_enrichment_field_mapping_structure(self):
        """Test that the enrichment field mapping has all required fields"""
        supplier = McMasterCarrSupplier()
        mappings = supplier.get_enrichment_field_mappings()

        for mapping in mappings:
            # Check required fields
            assert hasattr(mapping, 'field_name')
            assert hasattr(mapping, 'display_name')
            assert hasattr(mapping, 'url_patterns')
            assert hasattr(mapping, 'example')
            assert hasattr(mapping, 'required_for_enrichment')

            # Check types
            assert isinstance(mapping.field_name, str)
            assert isinstance(mapping.display_name, str)
            assert isinstance(mapping.url_patterns, list)
            assert isinstance(mapping.example, str)
            assert isinstance(mapping.required_for_enrichment, bool)

            # Check patterns are valid regex
            for pattern in mapping.url_patterns:
                assert isinstance(pattern, str)
                # Should not raise exception
                re.compile(pattern)

    def test_example_part_number_format(self):
        """Test that the example part number matches the expected format"""
        supplier = McMasterCarrSupplier()
        mappings = supplier.get_enrichment_field_mappings()

        part_number_mapping = mappings[0]

        # The example should be a valid McMaster part number
        example = part_number_mapping.example
        assert example == "91253A194"

        # The example should match at least one pattern
        test_url = f"https://www.mcmaster.com/{example}/"
        matched = False

        for pattern in part_number_mapping.url_patterns:
            match = re.search(pattern, test_url)
            if match and match.group(1) == example:
                matched = True
                break

        assert matched, f"Example {example} doesn't match its own patterns"

    def test_integration_with_backend_endpoint(self):
        """Test that the mappings work with the backend endpoint structure"""

        # Simulate what the backend endpoint would return
        supplier = McMasterCarrSupplier()
        mappings = supplier.get_enrichment_field_mappings()

        # Convert to the format expected by the API
        api_response = []
        for mapping in mappings:
            api_response.append({
                "field_name": mapping.field_name,
                "display_name": mapping.display_name,
                "url_patterns": mapping.url_patterns,
                "example": mapping.example,
                "description": mapping.description,
                "required_for_enrichment": mapping.required_for_enrichment
            })

        # Verify the response structure
        assert len(api_response) > 0
        for item in api_response:
            assert "field_name" in item
            assert "display_name" in item
            assert "url_patterns" in item
            assert isinstance(item["url_patterns"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])