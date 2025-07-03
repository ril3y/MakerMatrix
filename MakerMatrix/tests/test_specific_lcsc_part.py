#!/usr/bin/env python3
"""
Test the specific LCSC part number from the re-imported data
"""

import asyncio
import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MakerMatrix'))

from MakerMatrix.suppliers.lcsc import LCSCSupplier


async def test_specific_lcsc_part():
    """Test the specific LCSC part that was just imported"""
    print("🧪 Testing specific LCSC part: C5160761")
    print("=" * 50)
    
    # Initialize LCSC supplier
    supplier = LCSCSupplier()
    
    # Configure with default settings
    credentials = {}
    config = {
        "rate_limit_requests_per_minute": 20,
        "request_timeout": 30
    }
    
    supplier.configure(credentials, config)
    print("✅ Supplier configured successfully")
    
    # Test the specific part number from the import
    test_part_number = "C5160761"
    
    print(f"\n🔍 Testing part number: {test_part_number}")
    print(f"Expected: This should work since it's a valid LCSC format")
    
    try:
        # Test part details
        print(f"\n📋 Getting part details...")
        part_details = await supplier.get_part_details(test_part_number)
        
        if part_details:
            print("✅ Part details retrieved successfully")
            print(f"   Part Number: {part_details.supplier_part_number}")
            print(f"   Manufacturer: {part_details.manufacturer}")
            print(f"   MPN: {part_details.manufacturer_part_number}")
            print(f"   Description: {part_details.description}")
            print(f"   Category: {part_details.category}")
            
            # Test datasheet fetching
            print(f"\n📄 Testing datasheet fetching...")
            datasheet_url = await supplier.fetch_datasheet(test_part_number)
            if datasheet_url:
                print(f"✅ Datasheet URL found: {datasheet_url}")
            else:
                print("❌ No datasheet URL found")
            
            # Test image fetching
            print(f"\n🖼️ Testing image fetching...")
            image_url = await supplier.fetch_image(test_part_number)
            if image_url:
                print(f"✅ Image URL found: {image_url}")
            else:
                print("❌ No image URL found")
                
        else:
            print("❌ Failed to retrieve part details")
            print("   This means the LCSC part number doesn't exist in EasyEDA API")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
    
    # Clean up
    await supplier.close()
    print("\n🧹 Cleanup completed")
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")


if __name__ == "__main__":
    asyncio.run(test_specific_lcsc_part())