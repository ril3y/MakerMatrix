#!/usr/bin/env python3
"""
Test the new supplier_part_number approach for enrichment
"""

import asyncio
import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "MakerMatrix"))

from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService
from sqlmodel import Session


async def test_new_approach():
    """Test the new supplier_part_number approach"""
    print("🧪 Testing New supplier_part_number Approach")
    print("=" * 60)

    # Test 1: LCSC Import
    print("\n📥 Step 1: Testing LCSC CSV Import...")
    supplier = LCSCSupplier()
    supplier.configure({}, {"rate_limit_requests_per_minute": 20})

    # Sample CSV with one part
    sample_csv = """LCSC Part Number,Customer NO.,Product Remark,Manufacture Part Number,Manufacturer,Package,Product Model,Marked Price(USD),Customer Part Number,Order Qty.,Min\\Mult Order Qty.,Unit Price(USD),Order Price(USD),Description,RoHS
C25804,,10K 1% 0603,0603WAF1002T5E,UNI-ROYAL(厚声),0603,resistors,0.004,0.004,10,5\\5,0.004,0.04,RES SMD 10KOHM 1% 1/10W 0603,YES"""

    try:
        csv_bytes = sample_csv.encode("utf-8")
        import_result = await supplier.import_order_file(csv_bytes, "csv", "test_lcsc.csv")

        if import_result.success and import_result.parts:
            part_data = import_result.parts[0]
            print(f"✅ Import successful!")
            print(f"   Part Name: {part_data.get('part_name')}")
            print(
                f"   supplier_part_number: {part_data.get('supplier_part_number')} {'✅' if part_data.get('supplier_part_number') else '❌'}"
            )
            print(f"   Manufacturer: {part_data.get('manufacturer')}")
            print(f"   MPN: {part_data.get('manufacturer_part_number')}")

            # Test 2: Create part in database
            print(f"\n💾 Step 2: Creating part in database...")
            part_service = PartService()
            created_response = part_service.add_part(part_data)

            if created_response.get("status") == "success":
                created_part = created_response.get("data")
                part_id = created_part.get("id")
                print(f"✅ Part created successfully!")
                print(f"   Part ID: {part_id}")

                # Test 3: Verify database storage
                print(f"\n🔍 Step 3: Verifying database storage...")
                with Session(isolated_test_engine) as session:
                    part_repo = PartRepository(engine)
                    db_part = part_repo.get_part_by_id(session, part_id)

                    if db_part:
                        print(f"✅ Part retrieved from database!")
                        print(f"   Part Name: {db_part.part_name}")
                        print(
                            f"   supplier_part_number: {repr(db_part.supplier_part_number)} {'✅' if db_part.supplier_part_number else '❌'}"
                        )
                        print(f"   part_number: {repr(db_part.part_number)} (legacy field)")
                        print(f"   Manufacturer: {db_part.manufacturer}")
                        print(f"   MPN: {db_part.manufacturer_part_number}")

                        # Test 4: Test enrichment logic
                        print(f"\n🔧 Step 4: Testing enrichment part number selection...")
                        from MakerMatrix.services.system.enrichment_task_handlers import PartEnrichmentTaskHandler

                        handler = PartEnrichmentTaskHandler()
                        selected_part_number = handler._get_supplier_part_number(db_part, "lcsc")

                        print(f"✅ Enrichment will use: {selected_part_number}")

                        if selected_part_number == db_part.supplier_part_number:
                            print(f"✅ SUCCESS: Enrichment correctly uses supplier_part_number!")
                            print(f"   This should work for enrichment: {selected_part_number}")
                        else:
                            print(f"❌ ERROR: Enrichment not using supplier_part_number")
                            print(f"   Expected: {db_part.supplier_part_number}")
                            print(f"   Got: {selected_part_number}")

                        # Test 5: Verify enrichment would work
                        print(f"\n🧪 Step 5: Testing if enrichment would work...")
                        if selected_part_number and selected_part_number.upper().startswith("C"):
                            print(f"✅ Part number format is valid for LCSC: {selected_part_number}")

                            # Test actual LCSC API call
                            part_details = await supplier.get_part_details(selected_part_number)
                            if part_details:
                                print(f"✅ LCSC API call successful!")
                                print(f"   Found: {part_details.manufacturer} {part_details.manufacturer_part_number}")
                            else:
                                print(f"❌ LCSC API call failed")
                        else:
                            print(f"❌ Invalid part number format for LCSC: {selected_part_number}")
                    else:
                        print(f"❌ Failed to retrieve part from database")
            else:
                print(f"❌ Failed to create part: {created_response.get('message')}")
        else:
            print(f"❌ Import failed: {import_result.error_message}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await supplier.close()

    print("\n" + "=" * 60)
    print("🏁 Test completed!")


if __name__ == "__main__":
    asyncio.run(test_new_approach())
