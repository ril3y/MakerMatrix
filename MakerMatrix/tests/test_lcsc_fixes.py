#!/usr/bin/env python3
"""
Test script to verify LCSC supplier fixes for datasheet and image downloading
"""

import asyncio
import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'MakerMatrix'))

from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from sqlmodel import Session


def get_lcsc_parts_from_db():
    """Get LCSC parts from the database"""
    print("🔍 Finding LCSC parts in database...")
    
    try:
        with Session(engine) as session:
            part_repo = PartRepository(engine)
            
            # Get all parts and filter for LCSC supplier
            all_parts = part_repo.get_all_parts(session, page=1, page_size=100)
            lcsc_parts = [part for part in all_parts if part.supplier and 'lcsc' in part.supplier.lower()]
            
            if lcsc_parts:
                print(f"✅ Found {len(lcsc_parts)} LCSC parts in database")
                for i, part in enumerate(lcsc_parts[:5]):  # Show first 5
                    print(f"   {i+1}. {part.part_name} ({part.part_number}) - {part.supplier}")
                return lcsc_parts[:3]  # Return first 3 for testing
            else:
                print("❌ No LCSC parts found in database")
                return []
    except Exception as e:
        print(f"⚠️ Could not access database: {e}")
        return []


async def test_lcsc_supplier():
    """Test LCSC supplier functionality"""
    print("🧪 Testing LCSC Supplier Fixes...")
    print("=" * 50)
    
    # Get real LCSC parts from database
    db_parts = get_lcsc_parts_from_db()
    
    # Initialize LCSC supplier
    supplier = LCSCSupplier()
    
    # Configure with default settings (no credentials needed for LCSC)
    credentials = {}  # LCSC uses public API, no credentials needed
    config = {
        "rate_limit_requests_per_minute": 20,
        "request_timeout": 30
    }
    
    supplier.configure(credentials, config)
    print("✅ Supplier configured successfully")
    
    # Test 1: Connection test
    print("\n🔌 Testing connection...")
    try:
        connection_result = await supplier.test_connection()
        print(f"Connection test: {'✅ SUCCESS' if connection_result.get('success') else '❌ FAILED'}")
        if connection_result.get('success'):
            print(f"   Details: {connection_result.get('details', {})}")
        else:
            print(f"   Error: {connection_result.get('message')}")
    except Exception as e:
        print(f"❌ Connection test failed with exception: {e}")
    
    # Test parts from database if available
    test_parts = []
    if db_parts:
        # Use actual parts from database
        for part in db_parts:
            if part.part_number and part.part_number.upper().startswith('C'):
                test_parts.append(part.part_number)
    
    # Fallback to known LCSC parts if no DB parts found
    if not test_parts:
        print("⚠️ No valid LCSC parts found in DB, using known test parts")
        test_parts = ["C25804", "C1525", "C22775"]  # Known LCSC parts
    
    # Test each part
    for i, part_number in enumerate(test_parts[:2]):  # Test first 2 parts
        print(f"\n{'='*30}")
        print(f"🧪 Testing Part {i+1}: {part_number}")
        print(f"{'='*30}")
        
        # Test part details
        print(f"📋 Getting part details for {part_number}...")
        try:
            part_details = await supplier.get_part_details(part_number)
            if part_details:
                print("✅ Part details retrieved successfully")
                print(f"   Part Number: {part_details.supplier_part_number}")
                print(f"   Manufacturer: {part_details.manufacturer}")
                print(f"   MPN: {part_details.manufacturer_part_number}")
                print(f"   Description: {part_details.description}")
                print(f"   Category: {part_details.category}")
                
                # Test datasheet fetching
                print(f"\n📄 Testing datasheet fetching for {part_number}...")
                try:
                    datasheet_url = await supplier.fetch_datasheet(part_number)
                    if datasheet_url:
                        print(f"✅ Datasheet URL found: {datasheet_url}")
                    else:
                        print("❌ No datasheet URL found")
                except Exception as e:
                    print(f"❌ Datasheet fetching failed: {e}")
                
                # Test image fetching
                print(f"\n🖼️ Testing image fetching for {part_number}...")
                try:
                    image_url = await supplier.fetch_image(part_number)
                    if image_url:
                        print(f"✅ Image URL found: {image_url}")
                    else:
                        print("❌ No image URL found")
                except Exception as e:
                    print(f"❌ Image fetching failed: {e}")
                
            else:
                print("❌ Failed to retrieve part details")
        except Exception as e:
            print(f"❌ Part details failed with exception: {e}")
        
        # Add delay between tests to respect rate limits
        if i < len(test_parts) - 1:
            print("⏳ Waiting 3 seconds for rate limiting...")
            await asyncio.sleep(3)
    
    # Clean up
    await supplier.close()
    print("\n🧹 Cleanup completed")
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")


if __name__ == "__main__":
    asyncio.run(test_lcsc_supplier())