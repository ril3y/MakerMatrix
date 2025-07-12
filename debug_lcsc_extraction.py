#!/usr/bin/env python3
"""
Debug LCSC data extraction specifically
"""

import sys
import os
sys.path.append('/home/ril3y/MakerMatrix')

# Mock data structure from LCSC API response
test_data = {
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
                "Value": "Standing paste Policy 10P 1.27mm Double Row 2x5P SMD,P=1.27mm Pin Headers ROHS"
            }
        }
    },
    "SMT": True
}

# Test the data extraction
from MakerMatrix.suppliers.data_extraction import DataExtractor, extract_common_part_data

def test_lcsc_extraction():
    print("🔍 Testing LCSC Data Extraction")
    print("=" * 50)
    
    # Create extractor
    extractor = DataExtractor("lcsc")
    
    # LCSC extraction config
    extraction_config = {
        "description_paths": ["title", "dataStr.head.c_para.Value", "description"],
        "image_paths": ["thumb", "image_url", "thumbnail", "photo"],
        "datasheet_paths": [
            "packageDetail.dataStr.head.c_para.link",
            "dataStr.head.c_para.link", 
            "dataStr.head.c_para.Datasheet",
            "szlcsc.attributes.Datasheet",
            "packageDetail.datasheet_pdf",
            "datasheet_pdf"
        ],
        "specifications": {
            "manufacturer": ["dataStr.head.c_para.Manufacturer"],
            "manufacturer_part": ["dataStr.head.c_para.Manufacturer Part"],
            "package": ["dataStr.head.c_para.package"],
            "value": ["dataStr.head.c_para.Value"],
            "mounting": ["SMT"]
        },
        "base_url": "https://easyeda.com"
    }
    
    print("📄 Test data:")
    print(f"  thumb: {test_data.get('thumb')}")
    print(f"  title: {test_data.get('title')}")
    print("")
    
    # Test individual extraction methods
    print("🧪 Testing individual extraction methods:")
    
    # Test safe_get for thumb
    thumb_value = extractor.safe_get(test_data, "thumb")
    print(f"  safe_get('thumb'): {thumb_value}")
    
    # Test image URL extraction directly
    image_result = extractor.extract_image_url(test_data, ["thumb"], "https://easyeda.com")
    print(f"  extract_image_url result: success={image_result.success}, value={image_result.value}")
    if not image_result.success:
        print(f"    error: {image_result.error_message}")
        print(f"    warnings: {image_result.warnings}")
    
    # Test with fixed URL
    test_data_fixed = test_data.copy()
    test_data_fixed["thumb"] = "https:" + test_data["thumb"]  # Fix protocol
    print(f"  Fixed thumb URL: {test_data_fixed['thumb']}")
    
    image_result_fixed = extractor.extract_image_url(test_data_fixed, ["thumb"], "https://easyeda.com")
    print(f"  extract_image_url with fixed URL: success={image_result_fixed.success}, value={image_result_fixed.value}")
    if not image_result_fixed.success:
        print(f"    error: {image_result_fixed.error_message}")
        print(f"    warnings: {image_result_fixed.warnings}")
    
    print("")
    
    # Test full extraction
    print("🧪 Testing full data extraction:")
    extracted_data = extract_common_part_data(extractor, test_data, extraction_config)
    print(f"  Extracted keys: {list(extracted_data.keys())}")
    print(f"  Description: {extracted_data.get('description')}")
    print(f"  Image URL: {extracted_data.get('image_url')}")
    print(f"  Datasheet URL: {extracted_data.get('datasheet_url')}")
    print("")
    
    # Test with preprocessed data
    print("🧪 Testing with URL preprocessing:")
    
    def preprocess_lcsc_data(data):
        """Preprocess LCSC data to fix protocol-relative URLs"""
        import copy
        processed_data = copy.deepcopy(data)
        
        def fix_urls(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith("//"):
                        obj[key] = "https:" + value
                    elif isinstance(value, (dict, list)):
                        fix_urls(value)
            elif isinstance(obj, list):
                for item in obj:
                    fix_urls(item)
        
        fix_urls(processed_data)
        return processed_data
    
    processed_data = preprocess_lcsc_data(test_data)
    print(f"  Processed thumb: {processed_data.get('thumb')}")
    
    extracted_data_processed = extract_common_part_data(extractor, processed_data, extraction_config)
    print(f"  Extracted keys: {list(extracted_data_processed.keys())}")
    print(f"  Description: {extracted_data_processed.get('description')}")
    print(f"  Image URL: {extracted_data_processed.get('image_url')}")
    print(f"  Datasheet URL: {extracted_data_processed.get('datasheet_url')}")

if __name__ == "__main__":
    test_lcsc_extraction()