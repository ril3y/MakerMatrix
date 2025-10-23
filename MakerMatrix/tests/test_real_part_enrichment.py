#!/usr/bin/env python3
"""
Test script to debug LCSC enrichment with the real part that failed
"""

import asyncio
import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "MakerMatrix"))

from MakerMatrix.suppliers.lcsc import LCSCSupplier


async def test_problematic_part():
    """Test the specific part that failed enrichment"""
    print("🔍 Testing problematic part: DZ127S-22-10-55")
    print("=" * 50)

    # Initialize LCSC supplier
    supplier = LCSCSupplier()

    # Configure with default settings
    credentials = {}
    config = {"rate_limit_requests_per_minute": 20, "request_timeout": 30}

    supplier.configure(credentials, config)
    print("✅ Supplier configured successfully")

    # Test cases
    test_cases = [
        {
            "name": "Exact part name from DB",
            "part_number": "DZ127S-22-10-55",
            "expected": "Should fail - not LCSC format",
        },
        {"name": "Try without null part_number", "part_number": None, "expected": "Should fail - null part number"},
        {
            "name": "Valid LCSC part for comparison",
            "part_number": "C25804",
            "expected": "Should succeed - valid LCSC format",
        },
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*30}")
        print(f"🧪 Test {i+1}: {test_case['name']}")
        print(f"Part Number: {test_case['part_number']}")
        print(f"Expected: {test_case['expected']}")
        print(f"{'='*30}")

        if test_case["part_number"] is None:
            print("❌ Cannot test with None part number")
            continue

        try:
            # Test part details
            print(f"📋 Getting part details for {test_case['part_number']}...")
            part_details = await supplier.get_part_details(test_case["part_number"])

            if part_details:
                print("✅ Part details retrieved successfully")
                print(f"   Part Number: {part_details.supplier_part_number}")
                print(f"   Manufacturer: {part_details.manufacturer}")
                print(f"   MPN: {part_details.manufacturer_part_number}")
                print(f"   Description: {part_details.description}")

                # Test datasheet
                print(f"\n📄 Testing datasheet...")
                datasheet_url = await supplier.fetch_datasheet(test_case["part_number"])
                print(f"   Datasheet: {'✅ Found' if datasheet_url else '❌ Not found'}")
                if datasheet_url:
                    print(f"   URL: {datasheet_url}")

                # Test image
                print(f"\n🖼️ Testing image...")
                image_url = await supplier.fetch_image(test_case["part_number"])
                print(f"   Image: {'✅ Found' if image_url else '❌ Not found'}")
                if image_url:
                    print(f"   URL: {image_url}")

            else:
                print("❌ Failed to retrieve part details")
                print("   This explains why enrichment failed!")

        except Exception as e:
            print(f"❌ Exception occurred: {e}")
            print("   This explains why enrichment failed!")

        # Add delay between tests
        if i < len(test_cases) - 1:
            print("⏳ Waiting 3 seconds...")
            await asyncio.sleep(3)

    # Clean up
    await supplier.close()
    print("\n🧹 Cleanup completed")
    print("\n" + "=" * 50)

    print("🎯 ANALYSIS:")
    print("The part 'DZ127S-22-10-55' fails because:")
    print("1. It's not in LCSC format (C followed by digits)")
    print("2. LCSC supplier only works with LCSC part numbers")
    print("3. The enrichment system needs to handle this case better")
    print("\n🏁 Testing completed!")


if __name__ == "__main__":
    asyncio.run(test_problematic_part())
