#!/usr/bin/env python3
"""
Pytest test to debug LCSC enrichment and file storage issues
"""
import pytest
import asyncio
import json

from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.services.system.file_download_service import FileDownloadService


class TestLCSCEnrichmentDebug:
    """Test class to debug LCSC enrichment issues"""
    
    @pytest.mark.asyncio
    async def test_lcsc_c588491_enrichment_full_flow(self):
        """Test full enrichment flow for LCSC part C588491"""
        print("\n=== Testing LCSC C588491 Full Enrichment Flow ===")
        
        supplier = LCSCSupplier()
        supplier.configure({})
        
        # Test basic part details extraction
        part_result = await supplier.get_part_details("C588491")
        
        assert part_result is not None, "Should find part C588491"
        print(f"✅ Part found: {part_result.supplier_part_number}")
        print(f"Image URL: {part_result.image_url}")
        print(f"Datasheet URL: {part_result.datasheet_url}")
        
        # Test file download service
        file_service = FileDownloadService()
        
        if part_result.image_url:
            print(f"\n--- Testing Image Download ---")
            image_info = file_service.download_image(
                part_result.image_url, 
                part_result.supplier_part_number,
                "LCSC"
            )
            
            if image_info:
                print(f"✅ Image downloaded: {image_info['filename']}")
                print(f"File size: {image_info['size']} bytes")
                print(f"Image URL for API: {file_service.get_image_url(image_info['image_uuid'])}")
            else:
                print("❌ Image download failed")
        
        if part_result.datasheet_url:
            print(f"\n--- Testing Datasheet Download ---")
            datasheet_info = file_service.download_datasheet(
                part_result.datasheet_url,
                part_result.supplier_part_number,
                "LCSC"
            )
            
            if datasheet_info:
                print(f"✅ Datasheet downloaded: {datasheet_info['filename']}")
                print(f"File size: {datasheet_info['size']} bytes")
                print(f"Datasheet URL for API: {file_service.get_datasheet_url(datasheet_info['filename'])}")
            else:
                print("❌ Datasheet download failed")
        else:
            print("❌ No datasheet URL available from EasyEDA API")
        
        await supplier.close()
    

    @pytest.mark.asyncio 
    async def test_lcsc_data_extraction_paths(self):
        """Test LCSC data extraction specifically for image and datasheet paths"""
        print("\n=== Testing LCSC Data Extraction Paths ===")
        
        supplier = LCSCSupplier()
        supplier.configure({})
        
        # Get raw API response for analysis
        http_client = supplier._get_http_client()
        url = supplier._get_easyeda_api_url("C588491")
        
        response = await http_client.get(url, endpoint_type="test_data_extraction")
        
        if response.success:
            raw_data = response.data
            result_data = raw_data.get("result", {})
            
            print(f"Raw API response keys: {list(result_data.keys())}")
            print(f"thumb field: {result_data.get('thumb')}")
            print(f"dataStr structure exists: {'dataStr' in result_data}")
            
            # Test extraction paths manually
            extractor = supplier._get_data_extractor()
            
            # Test all image paths
            image_paths = supplier._extraction_config["image_paths"]
            print(f"\nTesting image paths: {image_paths}")
            
            for path in image_paths:
                value = extractor.safe_get(result_data, path.split('.'))
                print(f"  {path}: {value}")
            
            # Test all datasheet paths  
            datasheet_paths = supplier._extraction_config["datasheet_paths"]
            print(f"\nTesting datasheet paths: {datasheet_paths}")
            
            for path in datasheet_paths:
                value = extractor.safe_get(result_data, path.split('.'))
                print(f"  {path}: {value}")
        
        await supplier.close()



if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])