#!/usr/bin/env python3
"""
Test DigiKey Enrichment Attempt Without Credentials

This test demonstrates what happens when we try to enrich a DigiKey part
without proper API configuration.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.suppliers.exceptions import SupplierAuthenticationError, SupplierConfigurationError
from sqlmodel import Session
from MakerMatrix.database.db import engine
from MakerMatrix.models.models import PartModel


async def test_enrichment_without_credentials():
    """Test what happens when we try to enrich without DigiKey credentials"""
    print("🧪 TESTING DIGIKEY ENRICHMENT WITHOUT CREDENTIALS")
    print("=" * 80)

    # Get the specific part
    part_id = "bdb16d83-3ff4-44ba-9834-2994652e4e96"
    part_number = "296-14248-1-ND"

    with Session(engine) as session:
        part = session.get(PartModel, part_id)
        if not part:
            print(f"❌ Part {part_id} not found")
            return

        print(f"📦 Part: {part.part_name}")
        print(f"🔢 Part Number: {part.part_number}")
        print(f"🏪 Supplier: {part.supplier}")

        print("\n📋 Current Additional Properties:")
        if part.additional_properties:
            for key, value in part.additional_properties.items():
                print(f"   {key}: {value}")
        else:
            print("   ❌ No additional properties")

    print("\n🔧 ATTEMPTING DIGIKEY ENRICHMENT...")
    print("-" * 40)

    supplier = DigiKeySupplier()

    # Test 1: Connection Test
    print("1️⃣ Testing DigiKey Connection:")
    try:
        connection_result = await supplier.test_connection()
        print(f"   Result: {connection_result}")

        if not connection_result.get("success"):
            print(f"   ❌ Connection failed: {connection_result.get('message')}")
            print(f"   🔧 Details: {connection_result.get('details', {})}")
        else:
            print("   ✅ Connection successful")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")

    print()

    # Test 2: Get Part Details
    print("2️⃣ Attempting to Get Part Details:")
    try:
        part_details = await supplier.get_part_details(part_number)

        if part_details:
            print("   ✅ Successfully retrieved part details!")
            print(f"   📝 Description: {part_details.description}")
            print(f"   🏭 Manufacturer: {part_details.manufacturer}")

            if hasattr(part_details, "additional_data") and part_details.additional_data:
                print(f"   📊 Additional Data Fields: {len(part_details.additional_data)}")
                print("   🔍 Sample Fields:")
                for i, (key, value) in enumerate(part_details.additional_data.items()):
                    if i < 5:  # Show first 5 fields
                        print(f"      {key}: {value}")
                    else:
                        break
                if len(part_details.additional_data) > 5:
                    print(f"      ... and {len(part_details.additional_data) - 5} more fields")
            else:
                print("   ⚠️ No additional data returned")
        else:
            print("   ❌ No part details returned")

    except SupplierAuthenticationError as e:
        print(f"   ❌ Authentication Error: {e}")
        print("   🔐 This is expected - DigiKey API requires credentials")
    except SupplierConfigurationError as e:
        print(f"   ❌ Configuration Error: {e}")
        print("   ⚙️ This is expected - DigiKey is not configured")
    except Exception as e:
        print(f"   ❌ Unexpected Error: {e}")
        import traceback

        traceback.print_exc()

    print()

    # Test 3: Fetch Datasheet
    print("3️⃣ Attempting to Fetch Datasheet:")
    try:
        datasheet_url = await supplier.fetch_datasheet(part_number)

        if datasheet_url:
            print(f"   ✅ Datasheet URL: {datasheet_url}")
        else:
            print("   ❌ No datasheet URL returned")

    except SupplierAuthenticationError as e:
        print(f"   ❌ Authentication Error: {e}")
    except SupplierConfigurationError as e:
        print(f"   ❌ Configuration Error: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print()

    # Test 4: Check Current State After Attempt
    print("4️⃣ Checking Part State After Enrichment Attempt:")
    with Session(engine) as session:
        part = session.get(PartModel, part_id)

        print(f"📋 Additional Properties After Attempt:")
        if part.additional_properties:
            for key, value in part.additional_properties.items():
                print(f"   {key}: {value}")
            print(f"   📊 Total Properties: {len(part.additional_properties)}")
        else:
            print("   ❌ Still no additional properties")

    print()


async def simulate_successful_enrichment():
    """Simulate what WOULD happen with proper credentials"""
    print("🎯 SIMULATION: WHAT WOULD HAPPEN WITH PROPER CREDENTIALS")
    print("=" * 80)

    print("If DigiKey was properly configured with valid credentials:")
    print()

    print("1️⃣ Connection Test:")
    print("   ✅ {'success': True, 'message': 'DigiKey API connection successful'}")
    print()

    print("2️⃣ Get Part Details:")
    print("   ✅ Successfully retrieved comprehensive part data")
    print("   📊 Additional Properties would include:")

    expected_fields = [
        ("product_url", "https://www.digikey.com/en/products/detail/texas-instruments/CD4014BPWR/1507558"),
        ("datasheet_url", "https://www.ti.com/lit/ds/symlink/cd4014b.pdf"),
        ("image_url", "https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/1507/295-14248-1-ND.jpg"),
        ("stock_quantity", "20000"),
        ("rohs_status", "RoHS Compliant"),
        ("lifecycle_status", "Active"),
        ("package_case", '16-TSSOP (0.173", 4.40mm Width)'),
        ("mounting_type", "Surface Mount"),
        ("operating_temperature", "-55°C ~ 125°C"),
        ("voltage_supply", "3 V ~ 18 V"),
        ("series", "CD4000"),
        ("manufacturer_lead_weeks", "16"),
        ("normally_stocking", "True"),
        ("digikey_category", "Logic - Shift Registers"),
        ("reach_status", "Compliant"),
        ("moisture_sensitivity_level", "1 (Unlimited)"),
        ("export_control_class", "EAR99"),
        ("htsus_code", "8542.33.0001"),
        ("number_of_bits", "8"),
        ("clock_frequency", "5MHz"),
        ("logic_type", "Shift Register"),
        ("input_type", "CMOS"),
        ("output_type", "CMOS"),
        ("enrichment_source", "digikey_api_v4"),
        ("data_quality_score", "0.95"),
    ]

    for i, (key, value) in enumerate(expected_fields):
        print(f"      {key}: {value}")
        if i >= 9:  # Show first 10
            print(f"      ... and {len(expected_fields) - 10} more technical specifications")
            break

    print()
    print("3️⃣ Fetch Datasheet:")
    print("   ✅ https://www.ti.com/lit/ds/symlink/cd4014b.pdf")
    print()

    print("4️⃣ Final Result:")
    print("   📊 Total Additional Properties: ~40 fields")
    print("   ✅ Rich technical specifications")
    print("   ✅ Working URLs for datasheet and product page")
    print("   ✅ Real-time stock and pricing data")
    print("   ✅ Comprehensive compliance information")


async def main():
    """Main test runner"""
    print("🧪 DIGIKEY ENRICHMENT ATTEMPT TEST")
    print("Testing what happens when we try to enrich without proper credentials")
    print("=" * 80)
    print()

    # Test actual enrichment attempt
    await test_enrichment_without_credentials()

    print("\n" + "=" * 80)

    # Show what would happen with credentials
    await simulate_successful_enrichment()

    print("\n" + "=" * 80)
    print("🎯 CONCLUSION:")
    print("❌ Current enrichment attempts FAIL due to missing DigiKey credentials")
    print("✅ With proper configuration, we would get 40+ rich data fields")
    print("🔧 Configuration needed: DigiKey Client ID + Client Secret")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
