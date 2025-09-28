#!/usr/bin/env python3
"""
Integration test for LCSC enrichment functionality.

Tests the complete LCSC enrichment workflow including:
- Capability validation 
- Data extraction from EasyEDA API
- Field mapping and storage
- Image URL processing
"""

import pytest
import asyncio
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.suppliers.base import PartSearchResult
from MakerMatrix.services.system.part_enrichment_service import PartEnrichmentService
from MakerMatrix.models.models import PartModel
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus, TaskPriority


class TestLCSCEnrichmentIntegration:
    """Integration tests for LCSC enrichment functionality"""
    
    @pytest.fixture
    def mock_lcsc_api_response(self):
        """Mock LCSC EasyEDA API response"""
        return {
            "success": True,
            "code": 200,
            "result": {
                "uuid": "3749926e3b354e2293ee0ca4a5716edc",
                "title": "DZ127S-22-10-55",
                "description": "",
                "docType": 2,
                "type": 3,
                "thumb": "//image.lceda.cn/components/3749926e3b354e2293ee0ca4a5716edc.png",
                "lcsc": {"id": 5807857, "number": "C5160761"},
                "szlcsc": {"id": 5807857, "number": "C5160761"},
                "dataStr": {
                    "head": {
                        "c_para": {
                            "Manufacturer": "DEALON",
                            "Manufacturer Part": "DZ127S-22-10-55",
                            "package": "SMD,P=1.27mm",
                            "Value": "Standing paste Policy 10P 1.27mm Double Row 2x5P SMD,P=1.27mm Pin Headers ROHS",
                            "link": "https://datasheet.lcsc.com/szlcsc/2108132030_DEALON-DZ127S-22-10-55_C5160761.pdf"
                        }
                    }
                },
                "SMT": True,
                "verify": 1,
                "writable": False,
                "isFavorite": False,
                "packageDetail": {}
            }
        }
    
    @pytest.fixture
    def sample_part(self):
        """Create a sample part for testing"""
        return PartModel(
            id="test-part-id",
            part_name="Test LCSC Part",
            part_number="C5160761",
            description="Test part for LCSC enrichment",
            quantity=10,
            supplier="LCSC"
        )
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample enrichment task"""
        return TaskModel(
            id="test-task-id",
            task_type=TaskType.PART_ENRICHMENT,
            name="Test LCSC Enrichment",
            description="Test task for LCSC enrichment",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            input_data='{"part_id": "test-part-id", "supplier": "LCSC", "capabilities": ["get_part_details", "fetch_datasheet"]}',
            created_by_user_id="test-user-id",
            created_at=datetime.utcnow()
        )

    @pytest.fixture
    def sample_product_page_html(self):
        """Load a trimmed sample of the LCSC product page"""
        sample_path = Path("MakerMatrix/tests/data/lcsc/sample_product_page.html")
        return sample_path.read_text(encoding="utf-8")

    def test_lcsc_supplier_capabilities(self):
        """Test that LCSC supplier has the correct capabilities"""
        supplier = LCSCSupplier()
        capabilities = [cap.value for cap in supplier.get_capabilities()]
        
        assert "get_part_details" in capabilities
        assert "fetch_datasheet" in capabilities
        assert "fetch_pricing_stock" in capabilities
        assert "import_orders" in capabilities
    
    @pytest.mark.asyncio
    async def test_lcsc_data_extraction(self, mock_lcsc_api_response):
        """Test LCSC data extraction from API response"""
        supplier = LCSCSupplier()
        
        # Test the internal data processing method
        result = await supplier._parse_easyeda_response(mock_lcsc_api_response, "C5160761")
        
        assert result is not None
        assert result.supplier_part_number == "C5160761"
        assert result.manufacturer == "DEALON"
        assert result.manufacturer_part_number == "DZ127S-22-10-55"
        # Description comes from title field, longer description is in specifications
        assert result.description == "DZ127S-22-10-55"
        assert "Pin Headers" in result.specifications.get("Value", "")
        assert result.image_url == "https://image.lceda.cn/components/3749926e3b354e2293ee0ca4a5716edc.png"
        assert result.datasheet_url == "https://datasheet.lcsc.com/szlcsc/2108132030_DEALON-DZ127S-22-10-55_C5160761.pdf"

    def test_lcsc_product_page_parsing(self, sample_product_page_html):
        """Ensure we can parse key metadata from the public product page."""
        supplier = LCSCSupplier()
        details = supplier._parse_product_page_html(
            sample_product_page_html,
            "https://www.lcsc.com/product-detail/C12084.html",
        )

        assert details["brand"] == "TI"
        assert details["mpn"] == "SN65HVD230DR"
        assert details["image_url"].endswith("sample-image.jpg")
        attributes = details["attributes"]
        assert attributes["Key Attributes"] == "3.3-V CAN TRANSCEIVERS"
        assert attributes["Operating Temperature"] == "-40℃~+85℃"
        assert attributes["Operating Voltage"] == "4V~30V"
        assert details["datasheet_url"].endswith("C12084.pdf")
        assert details["attribute_links"]["Category"].endswith("/category/1029.html")

    @pytest.mark.asyncio
    async def test_easyeda_response_merges_product_page(
        self,
        mock_lcsc_api_response,
        sample_product_page_html,
    ):
        """Product page data should enrich EasyEDA results with richer metadata."""
        supplier = LCSCSupplier()
        parsed_page = supplier._parse_product_page_html(
            sample_product_page_html,
            "https://www.lcsc.com/product-detail/C12084.html",
        )

        with patch.object(LCSCSupplier, "_fetch_product_page_details", return_value=parsed_page):
            result = await supplier._parse_easyeda_response(mock_lcsc_api_response, "C5160761")

        assert result.manufacturer == "TI"
        assert result.manufacturer_part_number == "SN65HVD230DR"
        assert result.description.startswith("CAN Transceiver 17mA")
        assert result.datasheet_url.endswith("C12084.pdf")
        assert result.image_url.endswith("sample-image.jpg")
        assert result.additional_data["key_attributes"] == "3.3-V CAN TRANSCEIVERS"
        assert result.additional_data["lcsc_category_path"].startswith("Integrated Circuits")
        assert result.specifications["Operating Temperature"] == "-40℃~+85℃"
        assert result.specifications["Operating Voltage"] == "4V~30V"
        assert result.specifications["Number of Channels"] == "1"

    def test_lcsc_url_preprocessing(self):
        """Test URL preprocessing for protocol-relative URLs"""
        supplier = LCSCSupplier()
        
        test_data = {
            "thumb": "//image.lceda.cn/components/test.png",
            "nested": {
                "image": "//another.example.com/image.jpg"
            }
        }
        
        processed = supplier._preprocess_lcsc_data(test_data)
        
        assert processed["thumb"] == "https://image.lceda.cn/components/test.png"
        assert processed["nested"]["image"] == "https://another.example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_capability_validation(self):
        """Test that capability validation works with actual supplier capabilities"""
        enrichment_service = PartEnrichmentService()
        
        # Mock supplier config that has limited capabilities
        mock_config = {
            "enabled": True,
            "capabilities": ["fetch_datasheet"]  # Limited compared to actual
        }
        
        # Mock the supplier registry to return LCSC supplier
        with patch('MakerMatrix.suppliers.registry.get_supplier_registry') as mock_get_supplier_registry:
            mock_get_supplier_registry.return_value = {'lcsc': LCSCSupplier}
            
            # Test that validation uses actual supplier capabilities, not config
            capabilities = enrichment_service._determine_capabilities(
                "LCSC", 
                mock_config, 
                ["get_part_details", "fetch_datasheet"]
            )
            
            # Should succeed because actual LCSC supplier supports these capabilities
            assert "get_part_details" in capabilities
            assert "fetch_datasheet" in capabilities
    
    def test_json_serialization_helper(self):
        """Test JSON serialization helper for datetime objects"""
        enrichment_service = PartEnrichmentService()
        
        test_data = {
            "string_field": "test",
            "datetime_field": datetime.utcnow(),
            "nested": {
                "another_datetime": datetime.utcnow(),
                "number": 42
            },
            "list_with_datetime": [datetime.utcnow(), "string", 123]
        }
        
        serialized = enrichment_service._ensure_json_serializable(test_data)
        
        # All datetime objects should be converted to ISO format strings
        assert isinstance(serialized["datetime_field"], str)
        assert isinstance(serialized["nested"]["another_datetime"], str)
        assert isinstance(serialized["list_with_datetime"][0], str)
        
        # Other types should remain unchanged
        assert serialized["string_field"] == "test"
        assert serialized["nested"]["number"] == 42
        assert serialized["list_with_datetime"][1] == "string"
        assert serialized["list_with_datetime"][2] == 123
    
    def test_part_search_result_field_mapping(self, sample_part, mock_lcsc_api_response):
        """Test that PartSearchResult fields are mapped correctly"""
        enrichment_service = PartEnrichmentService()
        
        # Mock enrichment results with the expected structure
        enrichment_results = {
            "part_data": {
                "success": True,
                "datasheet_url": "https://example.com/datasheet.pdf",
                "image_url": "https://example.com/image.png",
                "manufacturer": "DEALON",
                "manufacturer_part_number": "DZ127S-22-10-55",
                "description": "Test part description",
                "category": "Headers"
            }
        }
        
        # Test the conversion to PartSearchResult
        result = enrichment_service._convert_enrichment_to_part_search_result(
            sample_part, enrichment_results, "LCSC"
        )
        
        assert result is not None
        assert result.supplier_part_number == sample_part.part_number
        assert result.manufacturer == "DEALON"
        assert result.manufacturer_part_number == "DZ127S-22-10-55"
        assert result.description == "Test part description"
        assert result.image_url == "https://example.com/image.png"
        assert result.datasheet_url == "https://example.com/datasheet.pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
