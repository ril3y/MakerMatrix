#!/usr/bin/env python3
"""
Test LCSC import with flat additional_properties validation.
This test clears the database, imports parts from the LCSC CSV, and validates the structure.
"""

import pytest
import asyncio
import json
import os
from pathlib import Path

# Set up environment
os.environ['PYTHONPATH'] = '/home/ril3y/MakerMatrix'

from MakerMatrix.database.database import engine, Session
from MakerMatrix.models.models import PartModel, OrderModel, Base
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.routers.import_routes import import_file
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.suppliers.registry import get_supplier
from fastapi import UploadFile
from io import BytesIO
import tempfile


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
        # Delete all parts and orders
        session.query(PartModel).delete()
        session.query(OrderModel).delete()
        session.commit()
        print("✅ Database cleared")


def validate_flat_additional_properties(additional_properties: dict, part_name: str):
    """
    Validate that additional_properties contains only flat key-value pairs.
    No nested objects should be present.
    """
    print(f"\n🔍 Validating flat structure for part: {part_name}")
    print(f"📊 Total properties: {len(additional_properties)}")

    nested_objects = []
    flat_properties = []

    for key, value in additional_properties.items():
        if isinstance(value, dict):
            nested_objects.append(f"{key}: {type(value).__name__}")
        elif isinstance(value, list):
            nested_objects.append(f"{key}: {type(value).__name__}")
        else:
            flat_properties.append(f"{key}: {value}")

    print(f"✅ Flat properties ({len(flat_properties)}):")
    for prop in flat_properties[:10]:  # Show first 10
        print(f"   {prop}")
    if len(flat_properties) > 10:
        print(f"   ... and {len(flat_properties) - 10} more")

    if nested_objects:
        print(f"❌ Found nested objects ({len(nested_objects)}):")
        for obj in nested_objects:
            print(f"   {obj}")
        return False
    else:
        print("✅ All properties are flat key-value pairs")
        return True


async def test_lcsc_import_flat_properties():
    """
    Test LCSC import with flat additional_properties validation.
    """
    print("\n" + "="*80)
    print("🧪 TESTING LCSC IMPORT WITH FLAT ADDITIONAL_PROPERTIES")
    print("="*80)

    # Step 1: Clear database
    clear_database()

    # Step 2: Read the test CSV file
    csv_file_path = "/home/ril3y/MakerMatrix/MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv"
    print(f"\n📁 Reading CSV file: {csv_file_path}")

    with open(csv_file_path, 'rb') as f:
        csv_content = f.read()

    print(f"📄 CSV content length: {len(csv_content)} bytes")

    # Step 3: Create mock objects for the import
    mock_file = MockUploadFile(csv_content, "LCSC_Exported__20241222_232708.csv")
    mock_user = MockUser()

    # Step 4: Test the import function directly
    print("\n🚀 Starting import process...")

    try:
        result = await import_file(
            supplier_name="lcsc",
            file=mock_file,
            order_number="TEST-ORDER-001",
            order_date="2024-12-22",
            notes="Test import for flat properties validation",
            enable_enrichment=False,  # Disable enrichment to focus on import structure
            enrichment_capabilities=None,
            current_user=mock_user
        )

        print(f"✅ Import completed successfully!")
        print(f"📊 Import status: {result.status}")
        print(f"📦 Imported parts: {result.imported_count}")
        print(f"❌ Failed parts: {result.failed_count}")
        print(f"⏭️  Skipped parts: {result.skipped_count}")

        if result.warnings:
            print(f"⚠️  Warnings: {result.warnings}")

        if result.failed_items:
            print(f"❌ Failed items:")
            for item in result.failed_items:
                print(f"   {item}")

    except Exception as e:
        print(f"❌ Import failed with error: {e}")
        raise

    # Step 5: Validate the imported parts
    print("\n🔍 Validating imported parts...")

    with Session(engine) as session:
        parts = session.query(PartModel).all()
        print(f"📦 Found {len(parts)} parts in database")

        if not parts:
            raise AssertionError("No parts found in database after import")

        # Check each part's additional_properties
        all_flat = True
        for i, part in enumerate(parts):
            print(f"\n--- PART {i+1}/{len(parts)} ---")
            print(f"🏷️  Name: {part.part_name}")
            print(f"🔢 Part Number: {part.part_number}")
            print(f"📝 Description: {part.description}")
            print(f"🏪 Supplier: {part.supplier}")

            if part.additional_properties:
                is_flat = validate_flat_additional_properties(
                    part.additional_properties,
                    part.part_name
                )
                if not is_flat:
                    all_flat = False

                # Show sample of properties
                print(f"\n📋 Sample additional_properties:")
                sample_keys = list(part.additional_properties.keys())[:5]
                for key in sample_keys:
                    value = part.additional_properties[key]
                    print(f"   {key}: {value} ({type(value).__name__})")

            else:
                print("⚠️  No additional_properties found")

        if not all_flat:
            print(f"\n❌ VALIDATION FAILED: Some parts have nested objects in additional_properties")
            return False
        else:
            print(f"\n✅ VALIDATION PASSED: All parts have flat additional_properties")
            return True


def main():
    """Main test runner"""
    print("🧪 Starting LCSC Import Flat Properties Test")

    try:
        # Run the async test
        success = asyncio.run(test_lcsc_import_flat_properties())

        if success:
            print("\n" + "="*80)
            print("🎉 ALL TESTS PASSED!")
            print("✅ Import works correctly")
            print("✅ Additional properties are flat")
            print("✅ No nested objects found")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("❌ TESTS FAILED!")
            print("❌ Found nested objects in additional_properties")
            print("="*80)
            exit(1)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()