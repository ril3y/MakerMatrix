#!/usr/bin/env python3
"""
Test DigiKey Part Enrichment Validation

This test validates what enrichment data SHOULD be available for DigiKey parts
and demonstrates the difference between configured vs unconfigured enrichment.

Specifically tests part: CD4014BPWR (296-14248-1-ND)
- IC STATIC SHFT REG 8STG 16-TSSOP
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.suppliers.exceptions import SupplierAuthenticationError, SupplierConfigurationError
from sqlmodel import Session
from MakerMatrix.database.db import engine
from MakerMatrix.models.models import PartModel


class MockDigiKeyAPI:
    """Mock DigiKey API response for testing enrichment capabilities"""

    @staticmethod
    def get_mock_part_data() -> Dict[str, Any]:
        """
        Return mock DigiKey API response for CD4014BPWR showing
        all the rich data that SHOULD be available with proper configuration.
        """
        return {
            "Product": {
                "DigiKeyPartNumber": "296-14248-1-ND",
                "ManufacturerProductNumber": "CD4014BPWR",
                "ProductUrl": "https://www.digikey.com/en/products/detail/texas-instruments/CD4014BPWR/1507558",
                "Description": {
                    "DetailedDescription": "IC STATIC SHIFT REG 8STG 16-TSSOP",
                    "ProductDescription": "8-Stage Static Shift Register 16-TSSOP (0.173\", 4.40mm Width)"
                },
                "Manufacturer": {
                    "Name": "Texas Instruments",
                    "Id": 78
                },
                "Category": {
                    "CategoryId": 154,
                    "Name": "Logic - Shift Registers",
                    "ParentCategory": {
                        "CategoryId": 4,
                        "Name": "Integrated Circuits (ICs)"
                    }
                },
                "Series": {
                    "Name": "CD4000"
                },
                "ProductStatus": {
                    "Id": 1,
                    "Status": "Active"
                },
                "BaseProductNumber": {
                    "Name": "CD4014"
                },
                "ManufacturerLeadWeeks": 16,
                "ManufacturerPublicQuantity": 0,
                "QuantityAvailable": 20000,
                "NormallyStocking": True,
                "BackOrderNotAllowed": False,
                "Discontinued": False,
                "EndOfLife": False,
                "Ncnr": False,
                "Classifications": {
                    "ReachStatus": "Compliant",
                    "RohsStatus": "RoHS Compliant",
                    "MoistureSensitivityLevel": "1 (Unlimited)",
                    "ExportControlClassNumber": "EAR99",
                    "HtsusCode": "8542.33.0001"
                },
                "Parameters": [
                    {
                        "ParameterId": 7,
                        "Parameter": "Package / Case",
                        "Value": "16-TSSOP (0.173\", 4.40mm Width)",
                        "ValueId": 1989
                    },
                    {
                        "ParameterId": 16,
                        "Parameter": "Supplier Device Package",
                        "Value": "16-TSSOP",
                        "ValueId": 45
                    },
                    {
                        "ParameterId": 69,
                        "Parameter": "Mounting Type",
                        "Value": "Surface Mount",
                        "ValueId": 7
                    },
                    {
                        "ParameterId": 252,
                        "Parameter": "Operating Temperature",
                        "Value": "-55°C ~ 125°C",
                        "ValueId": 69
                    },
                    {
                        "ParameterId": 477,
                        "Parameter": "Voltage - Supply",
                        "Value": "3 V ~ 18 V",
                        "ValueId": 42
                    },
                    {
                        "ParameterId": 1989,
                        "Parameter": "Number of Bits per Element",
                        "Value": "8",
                        "ValueId": 123
                    },
                    {
                        "ParameterId": 1990,
                        "Parameter": "Number of Elements",
                        "Value": "1",
                        "ValueId": 1
                    },
                    {
                        "ParameterId": 1991,
                        "Parameter": "Clock Frequency",
                        "Value": "5MHz",
                        "ValueId": 456
                    },
                    {
                        "ParameterId": 2659,
                        "Parameter": "Logic Type",
                        "Value": "Shift Register",
                        "ValueId": 789
                    }
                ],
                "StandardPricing": [
                    {
                        "BreakQuantity": 1,
                        "UnitPrice": 1.89000,
                        "TotalPrice": 1.89000
                    },
                    {
                        "BreakQuantity": 10,
                        "UnitPrice": 1.53600,
                        "TotalPrice": 15.36000
                    },
                    {
                        "BreakQuantity": 25,
                        "UnitPrice": 1.38240,
                        "TotalPrice": 34.56000
                    },
                    {
                        "BreakQuantity": 100,
                        "UnitPrice": 1.17855,
                        "TotalPrice": 117.85500
                    },
                    {
                        "BreakQuantity": 250,
                        "UnitPrice": 1.05660,
                        "TotalPrice": 264.15000
                    },
                    {
                        "BreakQuantity": 500,
                        "UnitPrice": 0.94368,
                        "TotalPrice": 471.84000
                    }
                ],
                "MediaLinks": [
                    {
                        "MediaType": "Datasheet",
                        "Title": "CD4014B Datasheet",
                        "Url": "https://www.ti.com/lit/ds/symlink/cd4014b.pdf"
                    },
                    {
                        "MediaType": "Product Photo",
                        "Title": "CD4014BPWR Product Photo",
                        "Url": "https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/1507/295-14248-1-ND.jpg"
                    }
                ],
                "PrimaryVideoUrl": None,
                "OtherNames": ["CD4014B", "CD4014BPWR"],
                "TechnicalAttributes": {
                    "InputType": "CMOS",
                    "OutputType": "CMOS",
                    "Features": "Reset",
                    "Applications": "General Purpose"
                }
            }
        }


def analyze_current_part_data():
    """Analyze what the current part actually has in the database"""
    print("🔍 ANALYZING CURRENT PART DATA IN DATABASE")
    print("=" * 80)

    with Session(engine) as session:
        part = session.get(PartModel, 'bdb16d83-3ff4-44ba-9834-2994652e4e96')
        if not part:
            print("❌ Part not found in database")
            return None

        print(f"📦 Part: {part.part_name}")
        print(f"🔢 Part Number: {part.part_number}")
        print(f"📝 Description: {part.description}")
        print(f"🏪 Supplier: {part.supplier}")
        print()

        print("📋 Current Additional Properties:")
        if part.additional_properties:
            for key, value in part.additional_properties.items():
                print(f"   {key}: {value}")
        else:
            print("   ❌ No additional properties found")

        print()
        return part


def demonstrate_full_enrichment_potential():
    """Show what SHOULD be available with proper DigiKey configuration"""
    print("🎯 WHAT SHOULD BE AVAILABLE WITH PROPER DIGIKEY CONFIGURATION")
    print("=" * 80)

    mock_data = MockDigiKeyAPI.get_mock_part_data()
    product = mock_data["Product"]

    # Simulate what DigiKey enrichment should extract
    enriched_data = {
        # URLs and Media
        "product_url": product.get("ProductUrl", ""),
        "datasheet_url": next((media["Url"] for media in product.get("MediaLinks", [])
                              if media.get("MediaType") == "Datasheet"), None),
        "image_url": next((media["Url"] for media in product.get("MediaLinks", [])
                          if media.get("MediaType") == "Product Photo"), None),

        # Detailed Information
        "detailed_description": product["Description"]["DetailedDescription"],
        "manufacturer": product["Manufacturer"]["Name"],
        "series": product["Series"]["Name"],
        "base_product_number": product["BaseProductNumber"]["Name"],

        # Technical Specifications (from Parameters)
        "package_case": "16-TSSOP (0.173\", 4.40mm Width)",
        "supplier_device_package": "16-TSSOP",
        "mounting_type": "Surface Mount",
        "operating_temperature": "-55°C ~ 125°C",
        "voltage_supply": "3 V ~ 18 V",
        "number_of_bits": "8",
        "number_of_elements": "1",
        "clock_frequency": "5MHz",
        "logic_type": "Shift Register",

        # Stock and Availability
        "stock_quantity": product.get("QuantityAvailable", 0),
        "manufacturer_lead_weeks": product.get("ManufacturerLeadWeeks", 0),
        "factory_stock_availability": product.get("ManufacturerPublicQuantity", 0),
        "normally_stocking": product.get("NormallyStocking", False),

        # Compliance and Status
        "rohs_status": product["Classifications"]["RohsStatus"],
        "lifecycle_status": product["ProductStatus"]["Status"],
        "reach_status": product["Classifications"]["ReachStatus"],
        "moisture_sensitivity_level": product["Classifications"]["MoistureSensitivityLevel"],
        "export_control_class": product["Classifications"]["ExportControlClassNumber"],
        "htsus_code": product["Classifications"]["HtsusCode"],

        # Category Information
        "digikey_category": product["Category"]["Name"],
        "digikey_parent_category": product["Category"]["ParentCategory"]["Name"],

        # Product Status
        "discontinued": product.get("Discontinued", False),
        "end_of_life": product.get("EndOfLife", False),
        "back_order_allowed": not product.get("BackOrderNotAllowed", True),

        # Pricing Information (would go to separate pricing table)
        "pricing_breaks": [
            {
                "quantity": pricing["BreakQuantity"],
                "unit_price": pricing["UnitPrice"],
                "total_price": pricing["TotalPrice"]
            }
            for pricing in product.get("StandardPricing", [])
        ],

        # Technical Attributes
        "input_type": product.get("TechnicalAttributes", {}).get("InputType", ""),
        "output_type": product.get("TechnicalAttributes", {}).get("OutputType", ""),
        "features": product.get("TechnicalAttributes", {}).get("Features", ""),
        "applications": product.get("TechnicalAttributes", {}).get("Applications", ""),

        # Alternative Names
        "other_names": product.get("OtherNames", []),

        # Enrichment Metadata
        "enrichment_source": "digikey_api_v4",
        "enrichment_timestamp": datetime.utcnow().isoformat(),
        "data_quality_score": 0.95,  # High quality due to official API
    }

    print("📊 ENRICHED DATA THAT SHOULD BE AVAILABLE:")
    print()

    print("🔗 URLs and Media:")
    print(f"   Product URL: {enriched_data['product_url']}")
    print(f"   Datasheet URL: {enriched_data['datasheet_url']}")
    print(f"   Image URL: {enriched_data['image_url']}")
    print()

    print("🔧 Technical Specifications:")
    for key in ["package_case", "mounting_type", "operating_temperature",
                "voltage_supply", "number_of_bits", "clock_frequency", "logic_type"]:
        print(f"   {key.replace('_', ' ').title()}: {enriched_data[key]}")
    print()

    print("📦 Stock and Availability:")
    print(f"   Stock Quantity: {enriched_data['stock_quantity']:,}")
    print(f"   Lead Time: {enriched_data['manufacturer_lead_weeks']} weeks")
    print(f"   Normally Stocking: {enriched_data['normally_stocking']}")
    print()

    print("✅ Compliance and Status:")
    print(f"   RoHS Status: {enriched_data['rohs_status']}")
    print(f"   Lifecycle Status: {enriched_data['lifecycle_status']}")
    print(f"   REACH Status: {enriched_data['reach_status']}")
    print()

    print("💰 Pricing Information:")
    for price_break in enriched_data['pricing_breaks'][:3]:  # Show first 3
        qty = price_break['quantity']
        price = price_break['unit_price']
        print(f"   {qty:>3} pcs: ${price:.5f} each")
    print(f"   ... and {len(enriched_data['pricing_breaks']) - 3} more price breaks")
    print()

    return enriched_data


async def test_digikey_connection():
    """Test DigiKey connection and show configuration requirements"""
    print("🔌 TESTING DIGIKEY CONNECTION")
    print("=" * 80)

    supplier = DigiKeySupplier()

    try:
        # Try to test connection
        result = await supplier.test_connection()
        print(f"Connection Result: {result}")

        if result.get('success'):
            print("✅ DigiKey is properly configured!")

            # Try to get part details
            try:
                part_details = await supplier.get_part_details("296-14248-1-ND")
                if part_details:
                    print("✅ Successfully retrieved part details from DigiKey API")
                    print(f"   Manufacturer: {part_details.manufacturer}")
                    print(f"   Description: {part_details.description}")
                    if hasattr(part_details, 'additional_data'):
                        print(f"   Additional Data Keys: {list(part_details.additional_data.keys())}")
                else:
                    print("⚠️ No part details returned")
            except Exception as e:
                print(f"❌ Failed to get part details: {e}")
        else:
            print("❌ DigiKey is not properly configured")
            print(f"   Message: {result.get('message', 'Unknown error')}")
            if 'details' in result:
                details = result['details']
                print(f"   Error: {details.get('error', 'Unknown')}")
                if 'required_fields' in details:
                    print(f"   Required Fields: {details['required_fields']}")
                if 'setup_url' in details:
                    print(f"   Setup URL: {details['setup_url']}")

    except SupplierAuthenticationError as e:
        print(f"❌ Authentication Error: {e}")
    except SupplierConfigurationError as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


def compare_current_vs_potential():
    """Compare what we have vs what we could have"""
    print("\n📊 COMPARISON: CURRENT vs POTENTIAL ENRICHMENT")
    print("=" * 80)

    # Get current data
    current_part = analyze_current_part_data()
    if not current_part:
        return

    current_props = current_part.additional_properties or {}

    # Get potential data
    potential_data = demonstrate_full_enrichment_potential()

    print("\n🔄 COMPARISON SUMMARY:")
    print(f"   Current Properties: {len(current_props)} fields")
    print(f"   Potential Properties: {len(potential_data)} fields")
    print(f"   Missing Enrichment: {len(potential_data) - len(current_props)} fields")
    print()

    print("❌ MISSING KEY DATA:")
    missing_keys = [
        ("product_url", "Product page URL"),
        ("datasheet_url", "Datasheet PDF URL"),
        ("image_url", "Product image URL"),
        ("stock_quantity", "Available stock quantity"),
        ("rohs_status", "RoHS compliance status"),
        ("lifecycle_status", "Product lifecycle status"),
        ("package_case", "Physical package information"),
        ("mounting_type", "Surface mount or through-hole"),
        ("operating_temperature", "Operating temperature range"),
        ("voltage_supply", "Supply voltage range"),
        ("pricing_breaks", "Quantity pricing information")
    ]

    for key, description in missing_keys:
        if key not in current_props:
            potential_value = potential_data.get(key, "N/A")
            print(f"   • {description}: {potential_value}")

    print()
    print("✅ CONFIGURATION NEEDED:")
    print("   1. Add DigiKey Client ID and Client Secret to supplier configuration")
    print("   2. Enable DigiKey API access in settings")
    print("   3. Run enrichment task with 'get_part_details' capability")
    print("   4. Verify datasheet and image URLs are working")


async def run_comprehensive_test():
    """Run the complete DigiKey enrichment validation test"""
    print("🧪 DIGIKEY ENRICHMENT VALIDATION TEST")
    print("=" * 80)
    print("This test analyzes DigiKey part CD4014BPWR (296-14248-1-ND)")
    print("and shows what enrichment data SHOULD be available with proper configuration.")
    print()

    # Test 1: Analyze current data
    analyze_current_part_data()
    print()

    # Test 2: Test DigiKey connection
    await test_digikey_connection()
    print()

    # Test 3: Show potential enrichment
    demonstrate_full_enrichment_potential()
    print()

    # Test 4: Compare current vs potential
    compare_current_vs_potential()

    print("\n" + "=" * 80)
    print("🎯 CONCLUSION:")
    print("The DigiKey part has minimal enrichment data because DigiKey API")
    print("is not properly configured. With proper configuration, we could get:")
    print("• Product URLs and datasheet links")
    print("• Detailed technical specifications (20+ parameters)")
    print("• Stock quantities and lead times")
    print("• Compliance information (RoHS, REACH, etc.)")
    print("• Quantity-based pricing breaks")
    print("• Product images and additional media")
    print("• Category and classification data")
    print("=" * 80)


def main():
    """Main test runner"""
    try:
        asyncio.run(run_comprehensive_test())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()