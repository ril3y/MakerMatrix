#!/usr/bin/env python3
"""
Test LCSC and DigiKey import with enrichment validation.

This test validates that:
1. LCSC and DigiKey parts can be imported successfully
2. Enrichment tasks are created and executed properly
3. Datasheets and URLs are retrieved and stored correctly
4. All additional properties are populated properly
"""

import asyncio
import json
import os
import sys
from pathlib import Path
import pytest
import time
from typing import Dict, List, Any

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.database.db import engine
from sqlmodel import Session
from MakerMatrix.models.models import PartModel, OrderModel, CategoryModel
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.routers.import_routes import import_file
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.suppliers.registry import get_supplier
from MakerMatrix.services.system.task_service import TaskService
from fastapi import UploadFile
from io import BytesIO


class MockUser:
    """Mock user for testing"""

    def __init__(self):
        self.id = "test-user-id"
        self.username = "testuser"


class MockUploadFile:
    """Mock UploadFile for testing"""

    def __init__(self, content: bytes, filename: str):
        self.content = content
        self.filename = filename
        self._file = BytesIO(content)

    async def read(self) -> bytes:
        return self.content


def clear_database():
    """Clear all data from the database"""
    print("\n🧹 Clearing database...")

    with Session(engine) as session:
        # Disable foreign key constraints temporarily for SQLite
        from sqlalchemy import text

        session.execute(text("PRAGMA foreign_keys = OFF"))

        # Delete all parts, orders, and categories
        session.query(PartModel).delete()
        session.query(OrderModel).delete()
        session.query(CategoryModel).delete()

        # Re-enable foreign key constraints
        session.execute(text("PRAGMA foreign_keys = ON"))

        session.commit()
        print("✅ Database cleared")


def create_lcsc_test_csv():
    """Create a test CSV with real LCSC part numbers for enrichment testing"""
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Package,Description,Order Qty.,Unit Price($)
C7442639,VEJ101M1VTT-0607L,Lelon,"SMD,D6.3xL7.7mm","100uF 35V Aluminum Electrolytic Capacitor",50,0.0874
C60633,SWPA6045S101MT,Sunlord,,-,50,0.0715
C84681,RT8205LGQW,Richtek,QFN-16_3x3x0.75P,IC MOSFET DRIVERS 4.5V-18V,10,0.4951
C5149,LM358DR,Texas Instruments,SOIC-8_3.9x4.9x1.27P,Operational Amplifier 1MHz 36V,25,0.0792
""".strip()
    return csv_content.encode("utf-8")


def create_digikey_test_csv():
    """Create a test CSV with real DigiKey part numbers for enrichment testing"""
    csv_content = """Digi-Key Part Number,Manufacturer,Manufacturer Part Number,Description,Customer Reference,Quantity,Backorder,Unit Price,Extended Price
311-1.00KCRCT-ND,Yageo,RC0805FR-071KL,RES SMD 1K OHM 1% 1/8W 0805,R1,100,0,"$0.10000","$10.00"
399-11785-1-ND,Kemet,C0805C104K5RAC7800,CAP CER 0.1UF 50V X7R 0805,C1,50,0,"$0.20000","$10.00"
TXB0108PWRCT-ND,Texas Instruments,TXB0108PWR,IC TRANSLATOR BIDIRECTIONAL 20TSSOP,U1,10,0,"$1.50000","$15.00"
LM358PDRCT-ND,Texas Instruments,LM358PDR,IC OPAMP GP 1.1MHZ 8SOIC,U2,25,0,"$0.50000","$12.50"
""".strip()
    return csv_content.encode("utf-8")


async def test_lcsc_import_with_enrichment():
    """
    Test LCSC import with enrichment capabilities and validate results.
    """
    print("\n" + "=" * 80)
    print("🧪 TESTING LCSC IMPORT WITH ENRICHMENT VALIDATION")
    print("=" * 80)

    # Step 1: Clear database
    clear_database()

    # Step 2: Create test CSV file
    csv_content = create_lcsc_test_csv()
    print(f"\n📁 Using LCSC test CSV content: {len(csv_content)} bytes")

    # Step 3: Create mock objects for the import
    mock_file = MockUploadFile(csv_content, "lcsc_enrichment_test.csv")
    mock_user = MockUser()

    # Step 4: Test import with enrichment enabled
    print("\n🚀 Starting LCSC import with enrichment...")

    try:
        result = await import_file(
            supplier_name="lcsc",
            file=mock_file,
            order_number="TEST-LCSC-ENRICHMENT-001",
            order_date="2024-12-22",
            notes="Test LCSC import with enrichment validation",
            enable_enrichment=True,
            enrichment_capabilities="get_part_details,fetch_datasheet",
            current_user=mock_user,
        )

        print(f"✅ Import completed successfully!")
        print(f"📊 Import status: {result.status}")
        print(f"📊 Result message: {result.message}")

        # Show actual data structure
        if hasattr(result.data, "imported_count"):
            print(f"📦 Imported parts: {result.data.imported_count}")

    except Exception as e:
        print(f"❌ Import failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise

    # Step 5: Wait for enrichment tasks to potentially run
    print("\n⏳ Waiting for potential enrichment tasks...")
    await asyncio.sleep(3)

    # Step 6: Validate the imported parts and their enrichment data
    print("\n🔍 Validating imported parts and enrichment data...")

    validation_results = validate_parts_enrichment("LCSC")
    return validation_results


async def test_digikey_import_with_enrichment():
    """
    Test DigiKey import with enrichment capabilities and validate results.
    """
    print("\n" + "=" * 80)
    print("🧪 TESTING DIGIKEY IMPORT WITH ENRICHMENT VALIDATION")
    print("=" * 80)

    # Step 1: Clear database
    clear_database()

    # Step 2: Create test CSV file
    csv_content = create_digikey_test_csv()
    print(f"\n📁 Using DigiKey test CSV content: {len(csv_content)} bytes")

    # Step 3: Create mock objects for the import
    mock_file = MockUploadFile(csv_content, "digikey_enrichment_test.csv")
    mock_user = MockUser()

    # Step 4: Test import with enrichment enabled
    print("\n🚀 Starting DigiKey import with enrichment...")

    try:
        result = await import_file(
            supplier_name="digikey",
            file=mock_file,
            order_number="TEST-DK-ENRICHMENT-001",
            order_date="2024-12-22",
            notes="Test DigiKey import with enrichment validation",
            enable_enrichment=True,
            enrichment_capabilities="get_part_details,fetch_datasheet,fetch_pricing_stock",
            current_user=mock_user,
        )

        print(f"✅ Import completed successfully!")
        print(f"📊 Import status: {result.status}")
        print(f"📊 Result message: {result.message}")

        # Show actual data structure
        if hasattr(result.data, "imported_count"):
            print(f"📦 Imported parts: {result.data.imported_count}")

    except Exception as e:
        print(f"❌ Import failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise

    # Step 5: Wait for enrichment tasks to potentially run
    print("\n⏳ Waiting for potential enrichment tasks...")
    await asyncio.sleep(3)

    # Step 6: Validate the imported parts and their enrichment data
    print("\n🔍 Validating imported parts and enrichment data...")

    validation_results = validate_parts_enrichment("DigiKey")
    return validation_results


def validate_parts_enrichment(supplier: str) -> Dict[str, Any]:
    """
    Validate that parts have been enriched with datasheets and URLs correctly.

    Args:
        supplier: The supplier name to filter parts by

    Returns:
        Dictionary with validation results
    """
    print(f"\n🔍 Validating enrichment for {supplier} parts...")

    validation_results = {
        "supplier": supplier,
        "total_parts": 0,
        "parts_with_datasheets": 0,
        "parts_with_urls": 0,
        "parts_with_enrichment_data": 0,
        "validation_errors": [],
        "validation_warnings": [],
        "parts_details": [],
    }

    with Session(engine) as session:
        parts = session.query(PartModel).filter(PartModel.supplier == supplier).all()
        validation_results["total_parts"] = len(parts)

        print(f"📦 Found {len(parts)} parts from {supplier}")

        if len(parts) == 0:
            validation_results["validation_errors"].append(f"No parts found for supplier {supplier}")
            return validation_results

        for i, part in enumerate(parts):
            print(f"\n--- PART {i+1}/{len(parts)} ---")
            print(f"🏷️  Name: {part.part_name}")
            print(f"🔢 Part Number: {part.part_number}")
            print(f"📝 Description: {part.description}")
            print(f"🏪 Supplier: {part.supplier}")

            part_details = {
                "part_name": part.part_name,
                "part_number": part.part_number,
                "supplier": part.supplier,
                "has_datasheet": False,
                "has_url": False,
                "has_enrichment_data": False,
                "datasheet_url": None,
                "product_url": None,
                "enrichment_source": None,
                "enrichment_date": None,
            }

            # Check additional properties for enrichment data
            if part.additional_properties:
                print(f"📋 Additional Properties Found:")

                # Check for datasheet
                datasheet_url = part.additional_properties.get("datasheet_url")
                if datasheet_url:
                    print(f"📄 Datasheet URL: {datasheet_url}")
                    part_details["has_datasheet"] = True
                    part_details["datasheet_url"] = datasheet_url
                    validation_results["parts_with_datasheets"] += 1

                    # Validate datasheet URL format
                    if not datasheet_url.startswith(("http://", "https://")):
                        validation_results["validation_errors"].append(
                            f"Invalid datasheet URL format for {part.part_name}: {datasheet_url}"
                        )
                else:
                    print("⚠️  No datasheet URL found")

                # Check for product URL
                product_url = part.additional_properties.get("product_url")
                if product_url:
                    print(f"🔗 Product URL: {product_url}")
                    part_details["has_url"] = True
                    part_details["product_url"] = product_url
                    validation_results["parts_with_urls"] += 1

                    # Validate product URL format and length
                    if not product_url.startswith(("http://", "https://")):
                        validation_results["validation_errors"].append(
                            f"Invalid product URL format for {part.part_name}: {product_url}"
                        )
                    elif len(product_url) < 50:
                        validation_results["validation_warnings"].append(
                            f"Product URL seems truncated for {part.part_name}: {product_url}"
                        )

                    # Check supplier-specific URL patterns
                    if supplier.lower() == "lcsc" and "lcsc.com" not in product_url.lower():
                        validation_results["validation_warnings"].append(
                            f"LCSC product URL doesn't contain lcsc.com: {product_url}"
                        )
                    elif supplier.lower() == "digikey" and "digikey.com" not in product_url.lower():
                        validation_results["validation_warnings"].append(
                            f"DigiKey product URL doesn't contain digikey.com: {product_url}"
                        )
                else:
                    print("⚠️  No product URL found")

                # Check for enrichment metadata
                enrichment_source = part.additional_properties.get("enrichment_source")
                enrichment_date = part.additional_properties.get("last_enrichment_date")

                if enrichment_source:
                    print(f"🔍 Enrichment Source: {enrichment_source}")
                    part_details["enrichment_source"] = enrichment_source
                    part_details["has_enrichment_data"] = True
                    validation_results["parts_with_enrichment_data"] += 1

                if enrichment_date:
                    print(f"📅 Last Enrichment Date: {enrichment_date}")
                    part_details["enrichment_date"] = enrichment_date

                # Check other enrichment data
                for key, value in part.additional_properties.items():
                    if key not in ["datasheet_url", "product_url", "enrichment_source", "last_enrichment_date"]:
                        print(f"   {key}: {value}")

            else:
                print("⚠️  No additional properties found")
                validation_results["validation_warnings"].append(f"Part {part.part_name} has no additional properties")

            validation_results["parts_details"].append(part_details)

    # Generate summary
    print(f"\n📊 ENRICHMENT VALIDATION SUMMARY FOR {supplier}")
    print(f"📦 Total Parts: {validation_results['total_parts']}")
    print(f"📄 Parts with Datasheets: {validation_results['parts_with_datasheets']}")
    print(f"🔗 Parts with URLs: {validation_results['parts_with_urls']}")
    print(f"🔍 Parts with Enrichment Data: {validation_results['parts_with_enrichment_data']}")

    if validation_results["validation_errors"]:
        print(f"❌ Validation Errors ({len(validation_results['validation_errors'])}):")
        for error in validation_results["validation_errors"]:
            print(f"   • {error}")

    if validation_results["validation_warnings"]:
        print(f"⚠️  Validation Warnings ({len(validation_results['validation_warnings'])}):")
        for warning in validation_results["validation_warnings"]:
            print(f"   • {warning}")

    # Calculate enrichment success rate
    if validation_results["total_parts"] > 0:
        datasheet_rate = (validation_results["parts_with_datasheets"] / validation_results["total_parts"]) * 100
        url_rate = (validation_results["parts_with_urls"] / validation_results["total_parts"]) * 100
        enrichment_rate = (validation_results["parts_with_enrichment_data"] / validation_results["total_parts"]) * 100

        print(f"📈 Datasheet Success Rate: {datasheet_rate:.1f}%")
        print(f"📈 URL Success Rate: {url_rate:.1f}%")
        print(f"📈 Enrichment Success Rate: {enrichment_rate:.1f}%")

        validation_results["datasheet_success_rate"] = datasheet_rate
        validation_results["url_success_rate"] = url_rate
        validation_results["enrichment_success_rate"] = enrichment_rate

    return validation_results


async def test_supplier_capabilities():
    """Test that suppliers have the expected enrichment capabilities"""
    print("\n" + "=" * 80)
    print("🧪 TESTING SUPPLIER ENRICHMENT CAPABILITIES")
    print("=" * 80)

    # Test LCSC capabilities
    print("\n📋 Testing LCSC capabilities...")
    lcsc_supplier = get_supplier("lcsc")
    if lcsc_supplier:
        print(f"✅ LCSC supplier found: {lcsc_supplier.__class__.__name__}")

        # Test connection
        try:
            connection_result = await lcsc_supplier.test_connection()
            print(f"🔌 LCSC connection test: {connection_result}")
        except Exception as e:
            print(f"⚠️  LCSC connection test failed: {e}")

        # Check capabilities
        if hasattr(lcsc_supplier, "get_supported_capabilities"):
            try:
                capabilities = lcsc_supplier.get_supported_capabilities()
                print(f"🔧 LCSC capabilities: {capabilities}")
            except Exception as e:
                print(f"⚠️  Could not get LCSC capabilities: {e}")
    else:
        print("❌ LCSC supplier not found")

    # Test DigiKey capabilities
    print("\n📋 Testing DigiKey capabilities...")
    digikey_supplier = get_supplier("digikey")
    if digikey_supplier:
        print(f"✅ DigiKey supplier found: {digikey_supplier.__class__.__name__}")

        # Test connection
        try:
            connection_result = await digikey_supplier.test_connection()
            print(f"🔌 DigiKey connection test: {connection_result}")
        except Exception as e:
            print(f"⚠️  DigiKey connection test failed: {e}")

        # Check capabilities
        if hasattr(digikey_supplier, "get_supported_capabilities"):
            try:
                capabilities = digikey_supplier.get_supported_capabilities()
                print(f"🔧 DigiKey capabilities: {capabilities}")
            except Exception as e:
                print(f"⚠️  Could not get DigiKey capabilities: {e}")
    else:
        print("❌ DigiKey supplier not found")


async def run_comprehensive_enrichment_test():
    """
    Run comprehensive test for both LCSC and DigiKey import with enrichment validation.
    """
    print("🧪 Starting Comprehensive Import and Enrichment Validation Test")

    results = {
        "test_start_time": time.time(),
        "supplier_capabilities": {},
        "lcsc_results": {},
        "digikey_results": {},
        "overall_success": False,
        "summary": {},
    }

    try:
        # Test 1: Check supplier capabilities
        print("\n" + "=" * 80)
        print("STEP 1: TESTING SUPPLIER CAPABILITIES")
        print("=" * 80)
        await test_supplier_capabilities()

        # Test 2: LCSC import and enrichment
        print("\n" + "=" * 80)
        print("STEP 2: LCSC IMPORT AND ENRICHMENT")
        print("=" * 80)
        lcsc_results = await test_lcsc_import_with_enrichment()
        results["lcsc_results"] = lcsc_results

        # Test 3: DigiKey import and enrichment
        print("\n" + "=" * 80)
        print("STEP 3: DIGIKEY IMPORT AND ENRICHMENT")
        print("=" * 80)
        digikey_results = await test_digikey_import_with_enrichment()
        results["digikey_results"] = digikey_results

        # Test 4: Generate overall summary
        print("\n" + "=" * 80)
        print("STEP 4: OVERALL RESULTS SUMMARY")
        print("=" * 80)

        total_parts = lcsc_results.get("total_parts", 0) + digikey_results.get("total_parts", 0)
        total_with_datasheets = lcsc_results.get("parts_with_datasheets", 0) + digikey_results.get(
            "parts_with_datasheets", 0
        )
        total_with_urls = lcsc_results.get("parts_with_urls", 0) + digikey_results.get("parts_with_urls", 0)
        total_with_enrichment = lcsc_results.get("parts_with_enrichment_data", 0) + digikey_results.get(
            "parts_with_enrichment_data", 0
        )

        total_errors = len(lcsc_results.get("validation_errors", [])) + len(
            digikey_results.get("validation_errors", [])
        )
        total_warnings = len(lcsc_results.get("validation_warnings", [])) + len(
            digikey_results.get("validation_warnings", [])
        )

        print(f"📊 OVERALL RESULTS:")
        print(f"📦 Total Parts Imported: {total_parts}")
        print(f"📄 Total Parts with Datasheets: {total_with_datasheets}")
        print(f"🔗 Total Parts with URLs: {total_with_urls}")
        print(f"🔍 Total Parts with Enrichment: {total_with_enrichment}")
        print(f"❌ Total Validation Errors: {total_errors}")
        print(f"⚠️  Total Validation Warnings: {total_warnings}")

        if total_parts > 0:
            overall_datasheet_rate = (total_with_datasheets / total_parts) * 100
            overall_url_rate = (total_with_urls / total_parts) * 100
            overall_enrichment_rate = (total_with_enrichment / total_parts) * 100

            print(f"📈 Overall Datasheet Success Rate: {overall_datasheet_rate:.1f}%")
            print(f"📈 Overall URL Success Rate: {overall_url_rate:.1f}%")
            print(f"📈 Overall Enrichment Success Rate: {overall_enrichment_rate:.1f}%")

        # Determine overall success
        results["overall_success"] = (
            total_parts > 0 and total_errors == 0 and (total_with_datasheets > 0 or total_with_urls > 0)
        )

        results["summary"] = {
            "total_parts": total_parts,
            "total_with_datasheets": total_with_datasheets,
            "total_with_urls": total_with_urls,
            "total_with_enrichment": total_with_enrichment,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "overall_datasheet_rate": overall_datasheet_rate if total_parts > 0 else 0,
            "overall_url_rate": overall_url_rate if total_parts > 0 else 0,
            "overall_enrichment_rate": overall_enrichment_rate if total_parts > 0 else 0,
        }

        if results["overall_success"]:
            print("\n" + "=" * 80)
            print("🎉 ALL TESTS PASSED!")
            print("✅ Import functionality works correctly")
            print("✅ Enrichment data is being captured")
            print("✅ URLs and datasheets are properly stored")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️  TESTS COMPLETED WITH ISSUES")
            print("❌ Some validation errors or missing enrichment data")
            print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        results["overall_success"] = False
        results["error"] = str(e)

    results["test_end_time"] = time.time()
    results["test_duration"] = results["test_end_time"] - results["test_start_time"]

    return results


def main():
    """Main test runner"""
    print("🧪 Starting Import Enrichment Validation Tests")

    try:
        # Run the comprehensive async test
        results = asyncio.run(run_comprehensive_enrichment_test())

        # Save results to file for analysis
        results_file = Path(__file__).parent / "enrichment_test_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Test results saved to: {results_file}")

        if results["overall_success"]:
            print("\n🎉 COMPREHENSIVE ENRICHMENT VALIDATION PASSED!")
            exit(0)
        else:
            print("\n❌ COMPREHENSIVE ENRICHMENT VALIDATION FAILED!")
            exit(1)

    except Exception as e:
        print(f"\n❌ TEST RUNNER FAILED WITH EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
