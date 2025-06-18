"""
Pytest unit tests for enrichment description update fix.

Tests the enhanced description update logic that properly handles cases where
the part description is just the part number/name and needs to be updated
with enriched description data.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock

from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.models.models import PartModel


class TestEnrichmentDescriptionFix:
    """Test suite for enrichment description update functionality"""
    
    @pytest.fixture
    def enrichment_handler(self):
        """Create enrichment handler with mocked dependencies"""
        mock_part_repo = Mock()
        mock_part_service = Mock()
        return EnrichmentTaskHandlers(mock_part_repo, mock_part_service)
    
    @pytest.fixture
    def sample_part_placeholder_description(self):
        """Create a part with placeholder description (part number as description)"""
        return PartModel(
            part_number="LMR16030SDDAR",
            part_name="LMR16030SDDAR", 
            description="LMR16030SDDAR",  # This is the issue - description = part number
            quantity=5,
            additional_properties={
                "description": "Step-down type Adjustable 800mV~50V 3A 4.3V~60V SO-8-EP DC-DC Converters ROHS",
                "manufacturer": "Texas Instruments"
            }
        )
    
    @pytest.fixture
    def sample_enrichment_results(self):
        """Create sample enrichment results with description"""
        return {
            "fetch_details": {
                "success": True,
                "status": "success",
                "product_description": "Step-down type Adjustable 800mV~50V 3A 4.3V~60V SO-8-EP DC-DC Converters ROHS",
                "manufacturer": "Texas Instruments"
            }
        }

    @pytest.mark.asyncio
    async def test_description_update_from_placeholder(self, enrichment_handler, sample_part_placeholder_description, sample_enrichment_results):
        """Test that description is updated when it matches the part number"""
        part = sample_part_placeholder_description
        enrichment_results = sample_enrichment_results
        
        # Verify initial state
        assert part.description == "LMR16030SDDAR"
        
        # Apply enrichment updates
        await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
        
        # Verify description was updated
        expected_description = "Step-down type Adjustable 800mV~50V 3A 4.3V~60V SO-8-EP DC-DC Converters ROHS"
        assert part.description == expected_description

    @pytest.mark.asyncio  
    async def test_description_fallback_from_additional_properties(self, enrichment_handler):
        """Test that description is updated from additional_properties as fallback"""
        part = PartModel(
            part_number="LMR16030SDDAR",
            part_name="LMR16030SDDAR",
            description="LMR16030SDDAR",  # Placeholder description
            quantity=5,
            additional_properties={
                "description": "Enriched description from additional properties"
            }
        )
        
        # No fetch_details in enrichment_results, should use fallback
        enrichment_results = {}
        
        # Apply enrichment updates
        await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
        
        # Verify description was updated from fallback
        assert part.description == "Enriched description from additional properties"

    @pytest.mark.asyncio
    async def test_description_update_edge_cases(self, enrichment_handler, sample_enrichment_results):
        """Test description update logic for various edge cases"""
        test_cases = [
            {
                "name": "Empty description",
                "description": "",
                "should_update": True
            },
            {
                "name": "None description", 
                "description": None,
                "should_update": True
            },
            {
                "name": "Part number as description",
                "description": "LMR16030SDDAR",
                "should_update": True
            },
            {
                "name": "Part name as description",
                "description": "LMR16030SDDAR",
                "should_update": True
            },
            {
                "name": "Very short description",
                "description": "IC",
                "should_update": True
            },
            {
                "name": "Good existing description",
                "description": "High-quality DC-DC converter with excellent performance characteristics",
                "should_update": False
            }
        ]
        
        for case in test_cases:
            part = PartModel(
                part_number="LMR16030SDDAR",
                part_name="LMR16030SDDAR",
                description=case['description'],
                quantity=1
            )
            
            # Apply enrichment updates
            await enrichment_handler._update_part_from_enrichment_results(part, sample_enrichment_results)
            
            expected_description = "Step-down type Adjustable 800mV~50V 3A 4.3V~60V SO-8-EP DC-DC Converters ROHS"
            was_updated = part.description == expected_description
            
            if case['should_update']:
                assert was_updated, f"Case '{case['name']}': Description should have been updated but wasn't"
                assert part.description == expected_description
            else:
                assert not was_updated, f"Case '{case['name']}': Description should NOT have been updated but was"
                assert part.description == case['description']

    @pytest.mark.asyncio
    async def test_no_update_when_description_already_good(self, enrichment_handler, sample_enrichment_results):
        """Test that good existing descriptions are not overwritten"""
        good_description = "This is already a good, detailed description of the component"
        
        part = PartModel(
            part_number="LMR16030SDDAR",
            part_name="LMR16030SDDAR",
            description=good_description,
            quantity=5
        )
        
        # Apply enrichment updates
        await enrichment_handler._update_part_from_enrichment_results(part, sample_enrichment_results)
        
        # Verify description was NOT changed
        assert part.description == good_description

    @pytest.mark.asyncio
    async def test_enrichment_with_multiple_capabilities(self, enrichment_handler):
        """Test enrichment with multiple capabilities including description update"""
        part = PartModel(
            part_number="C136648",
            part_name="LMR16030SDDAR",
            description="LMR16030SDDAR",  # Should be updated
            quantity=5
        )
        
        enrichment_results = {
            "fetch_details": {
                "success": True,
                "status": "success",
                "product_description": "DC-DC Buck Converter IC",
                "manufacturer": "Texas Instruments"
            },
            "fetch_datasheet": {
                "success": True,
                "status": "success",
                "datasheet_url": "https://example.com/datasheet.pdf"
            },
            "fetch_image": {
                "success": True,
                "status": "success",
                "primary_image_url": "https://example.com/image.jpg",
                "images": [{"url": "https://example.com/image.jpg", "type": "product"}]
            }
        }
        
        # Apply enrichment updates
        await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
        
        # Verify all updates were applied
        assert part.description == "DC-DC Buck Converter IC"
        assert part.image_url == "https://example.com/image.jpg"
        assert part.additional_properties["datasheet_url"] == "https://example.com/datasheet.pdf"

    @pytest.mark.asyncio
    async def test_data_optimization_reduces_duplication(self, enrichment_handler):
        """Test that data optimization reduces duplication in additional_properties"""
        part = PartModel(
            part_number="C136648",
            part_name="LMR16030SDDAR",
            description="LMR16030SDDAR",
            quantity=5,
            image_url="https://example.com/image.jpg",
            additional_properties={
                "enrichment_results": {
                    "fetch_image": {
                        "success": True,
                        "status": "success",
                        "primary_image_url": "https://example.com/image.jpg",  # This should be marked as duplicate
                        "images": [{"url": "https://example.com/image.jpg", "type": "product"}]
                    }
                }
            }
        )
        
        enrichment_results = {
            "fetch_image": {
                "success": True,
                "status": "success",
                "primary_image_url": "https://example.com/image.jpg",
                "images": [{"url": "https://example.com/image.jpg", "type": "product"}]
            }
        }
        
        # Apply enrichment updates (includes optimization)
        await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
        
        # Verify optimization annotations were added
        enrichment_data = part.additional_properties.get("enrichment_results", {}).get("fetch_image", {})
        assert "_note" in enrichment_data
        assert "duplicated in part.image_url" in enrichment_data["_note"]

    def test_optimization_handles_errors_gracefully(self, enrichment_handler):
        """Test that data optimization doesn't break enrichment if it fails"""
        # Create a part that might cause optimization errors
        part = PartModel(
            part_number="TEST123",
            part_name="Test Part",
            description="Test",
            quantity=1
        )
        
        # This should not raise an exception even if optimization fails
        try:
            enrichment_handler._optimize_part_data_storage(part)
        except Exception as e:
            pytest.fail(f"Data optimization should handle errors gracefully, but raised: {e}")

    def test_serialization_helper(self, enrichment_handler):
        """Test the JSON serialization helper method"""
        from datetime import datetime
        
        test_data = {
            "string": "test",
            "number": 123,
            "datetime": datetime(2025, 6, 18, 12, 0, 0),
            "nested": {
                "list": [datetime(2025, 6, 18, 13, 0, 0), "item2"],
                "nested_dict": {"key": datetime(2025, 6, 18, 14, 0, 0)}
            }
        }
        
        serialized = enrichment_handler._serialize_for_json(test_data)
        
        # Verify datetime objects were converted to ISO strings
        assert isinstance(serialized["datetime"], str)
        assert "2025-06-18T12:00:00" in serialized["datetime"]
        assert isinstance(serialized["nested"]["list"][0], str)
        assert isinstance(serialized["nested"]["nested_dict"]["key"], str)