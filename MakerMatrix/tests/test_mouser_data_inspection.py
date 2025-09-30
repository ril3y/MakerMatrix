"""
Test to inspect actual Mouser API response data

This test fetches a real STM32 part from Mouser and prints all the data
we're receiving to understand what additional_properties we should be extracting.

Test Part: 511-STM32F031C6T6TR
Description: ARM Microcontrollers - MCU ARM Cortex-M0 MCU 32Kb Flash 48MHz
Category: ARM Microcontrollers - MCU
"""

import pytest
import asyncio
import os
import json
from pprint import pprint

from MakerMatrix.suppliers.mouser import MouserSupplier


@pytest.fixture
def mouser_supplier():
    """Create a configured Mouser supplier instance"""
    supplier = MouserSupplier()

    # Get API key from environment
    api_key = os.getenv("MOUSER_API_KEY")

    if not api_key:
        pytest.skip("MOUSER_API_KEY not set in environment")

    # Configure the supplier
    supplier.configure(
        credentials={"api_key": api_key},
        config={
            "base_url": "https://api.mouser.com/api/v1",
            "search_option": "None",
            "search_with_your_signup_language": False,
            "request_timeout": 30
        }
    )

    return supplier


@pytest.mark.asyncio
async def test_inspect_stm32_part_data(mouser_supplier):
    """Inspect what data Mouser returns for STM32F031C6T6TR"""

    test_part_number = "511-STM32F031C6T6TR"

    print("\n" + "="*80)
    print(f"Testing Mouser API with part: {test_part_number}")
    print("="*80)

    # Authenticate first
    auth_result = await mouser_supplier.authenticate()
    print(f"\n✅ Authentication: {auth_result}")

    # Get part details
    print(f"\n🔍 Fetching part details for {test_part_number}...")
    part_details = await mouser_supplier.get_part_details(test_part_number)

    if part_details is None:
        print(f"❌ No data found for {test_part_number}")
        pytest.fail(f"Could not find part {test_part_number}")
        return

    print(f"\n✅ Found part: {part_details.manufacturer} {part_details.manufacturer_part_number}")
    print(f"   Description: {part_details.description}")
    print(f"   Category: {part_details.category}")

    # Print all fields we're extracting
    print("\n" + "="*80)
    print("CURRENT EXTRACTED FIELDS")
    print("="*80)

    print("\n📦 Core Fields:")
    print(f"  supplier_part_number: {part_details.supplier_part_number}")
    print(f"  manufacturer: {part_details.manufacturer}")
    print(f"  manufacturer_part_number: {part_details.manufacturer_part_number}")
    print(f"  description: {part_details.description}")
    print(f"  category: {part_details.category}")
    print(f"  datasheet_url: {part_details.datasheet_url}")
    print(f"  image_url: {part_details.image_url}")
    print(f"  stock_quantity: {part_details.stock_quantity}")

    print("\n💰 Pricing:")
    if part_details.pricing:
        for price_break in part_details.pricing[:3]:  # Show first 3 price breaks
            print(f"  {price_break['quantity']}+ units: ${price_break['price']} {price_break['currency']}")
        if len(part_details.pricing) > 3:
            print(f"  ... and {len(part_details.pricing) - 3} more price breaks")
    else:
        print("  No pricing data")

    print("\n🔧 Specifications:")
    if part_details.specifications:
        for key, value in list(part_details.specifications.items())[:10]:  # Show first 10
            print(f"  {key}: {value}")
        if len(part_details.specifications) > 10:
            print(f"  ... and {len(part_details.specifications) - 10} more specifications")
    else:
        print("  No specifications data")

    print("\n📋 Current additional_data:")
    if part_details.additional_data:
        pprint(part_details.additional_data, indent=2, width=100)
    else:
        print("  No additional_data")

    # Now let's examine the RAW API response to see what we're missing
    print("\n" + "="*80)
    print("RAW API RESPONSE ANALYSIS")
    print("="*80)

    # Make a direct API call to see the raw response
    http_client = mouser_supplier._get_http_client()
    credentials = mouser_supplier._credentials or {}
    api_key = credentials.get("api_key")

    url = f"{mouser_supplier._get_base_url()}/search/partnumber"
    params = {"apiKey": api_key}

    config = mouser_supplier._config or {}
    search_data = {
        "SearchByPartRequest": {
            "mouserPartNumber": test_part_number,
            "partSearchOptions": config.get("search_option", "None")
        }
    }

    print(f"\n🌐 Making direct API call to: {url}")
    response = await http_client.post(url, endpoint_type="raw_inspection", params=params, json_data=search_data)

    if response.success:
        search_results = response.data.get("SearchResults", {}) or {}
        parts = search_results.get("Parts", [])

        if parts:
            raw_part = parts[0]

            print("\n📦 ALL AVAILABLE FIELDS IN API RESPONSE:")
            print("-" * 80)

            # Group fields by category
            core_fields = []
            pricing_fields = []
            spec_fields = []
            other_fields = []

            for key, value in raw_part.items():
                if key in ["MouserPartNumber", "Manufacturer", "ManufacturerPartNumber", "Description", "Category"]:
                    core_fields.append((key, value))
                elif "price" in key.lower() or "pricing" in key.lower():
                    pricing_fields.append((key, value))
                elif "attribute" in key.lower() or "spec" in key.lower() or "parameter" in key.lower():
                    spec_fields.append((key, value))
                else:
                    other_fields.append((key, value))

            print("\n🔤 Core Identification Fields:")
            for key, value in core_fields:
                value_preview = str(value)[:100] if value else "None"
                print(f"  {key}: {value_preview}")

            print("\n💰 Pricing Fields:")
            for key, value in pricing_fields:
                value_preview = str(value)[:100] if value else "None"
                print(f"  {key}: {value_preview}")

            print("\n🔧 Specification/Attribute Fields:")
            for key, value in spec_fields:
                if isinstance(value, list) and len(value) > 0:
                    print(f"  {key}: [{len(value)} items]")
                    if len(value) > 0 and isinstance(value[0], dict):
                        print(f"    First item keys: {list(value[0].keys())}")
                else:
                    value_preview = str(value)[:100] if value else "None"
                    print(f"  {key}: {value_preview}")

            print("\n📋 Other Available Fields:")
            for key, value in other_fields:
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {type(value).__name__} (length: {len(value) if value else 0})")
                    if value:
                        # Show a preview of complex types
                        if isinstance(value, dict):
                            print(f"    Keys: {list(value.keys())[:5]}")
                        elif isinstance(value, list) and len(value) > 0:
                            print(f"    First item: {str(value[0])[:80]}")
                else:
                    value_preview = str(value)[:80] if value else "None"
                    print(f"  {key}: {value_preview}")

            # Show complete raw data as JSON
            print("\n" + "="*80)
            print("COMPLETE RAW API RESPONSE (JSON)")
            print("="*80)
            print(json.dumps(raw_part, indent=2, default=str))

            # Analyze what we're missing in additional_data
            print("\n" + "="*80)
            print("ANALYSIS: Fields NOT in additional_data but AVAILABLE in API")
            print("="*80)

            current_additional_data_keys = set(part_details.additional_data.keys()) if part_details.additional_data else set()
            api_keys = set(raw_part.keys())

            # Fields that could be added to additional_data
            potentially_useful = []
            for key in api_keys:
                # Skip fields already in core PartSearchResult
                if key in ["MouserPartNumber", "Manufacturer", "ManufacturerPartNumber", "Description",
                          "Category", "DataSheetUrl", "ImagePath"]:
                    continue

                # Skip pricing (handled separately)
                if "price" in key.lower() and key != "PriceBreaks":
                    continue

                # Skip specs (handled separately)
                if key == "ProductAttributes":
                    continue

                # Check if already in additional_data
                if key.lower() not in [k.lower() for k in current_additional_data_keys]:
                    value = raw_part[key]
                    potentially_useful.append((key, type(value).__name__, str(value)[:60] if value else "None"))

            print("\n🔍 Potentially Useful Fields to Add:")
            for key, type_name, preview in potentially_useful:
                print(f"  {key} ({type_name}): {preview}")

            # Category analysis
            print("\n" + "="*80)
            print("CATEGORY ANALYSIS")
            print("="*80)
            category = raw_part.get("Category", "")
            print(f"\n📂 Mouser Category: '{category}'")
            print(f"   Expected: ARM Microcontrollers - MCU")
            print(f"   Match: {'✅' if 'ARM' in category and 'Microcontroller' in category else '❌'}")

            # Check for component type determination
            description = raw_part.get("Description", "")
            print(f"\n📝 Description: '{description}'")
            print(f"   Contains 'ARM': {'✅' if 'ARM' in description else '❌'}")
            print(f"   Contains 'Cortex': {'✅' if 'Cortex' in description else '❌'}")
            print(f"   Contains 'MCU': {'✅' if 'MCU' in description else '❌'}")

        else:
            print("\n❌ No parts in API response")
    else:
        print(f"\n❌ API call failed: {response.status} - {response.error_message}")

    # Cleanup
    await http_client.close()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
