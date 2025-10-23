#!/usr/bin/env python3
"""
Test LCSC CSV import fix to ensure part_number is properly mapped
"""

import sys
import os

# Add the MakerMatrix directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "MakerMatrix"))

from MakerMatrix.suppliers.lcsc import LCSCSupplier


async def test_lcsc_csv_import():
    """Test LCSC CSV import with sample data"""
    print("🧪 Testing LCSC CSV Import Fix...")
    print("=" * 50)

    # Create sample LCSC CSV content
    sample_csv_content = """LCSC Part Number,Customer NO.,Product Remark,Manufacture Part Number,Manufacturer,Package,Product Model,Marked Price(USD),Customer Part Number,Order Qty.,Min\\Mult Order Qty.,Unit Price(USD),Order Price(USD),Description,RoHS
C25804,,10K 1% 0603,0603WAF1002T5E,UNI-ROYAL(厚声),0603,resistors,$0.004,$0.004,10,5\\5,$0.004,$0.04,RES SMD 10KOHM 1% 1/10W 0603,YES
C1525,,100nF 50V X7R 0402,CL05B104KO5NNNC,SAMSUNG(三星),0402,MLCC,$0.004,$0.004,20,5\\5,$0.004,$0.08,CAP CER 0.1UF 50V X7R 0402,YES
C22775,,XH-2A 2P,B2B-XH-A(LF)(SN),JST(JST销售),"P=2.5mm","connectors",$0.067,$0.067,5,1\\1,$0.067,$0.335,CONN HEADER XH TOP 2POS 2.5MM,YES"""

    # Initialize LCSC supplier
    supplier = LCSCSupplier()

    # Configure supplier
    credentials = {}
    config = {"rate_limit_requests_per_minute": 20, "request_timeout": 30}

    supplier.configure(credentials, config)
    print("✅ Supplier configured successfully")

    # Test import
    print("\n📥 Testing CSV import...")
    try:
        csv_bytes = sample_csv_content.encode("utf-8")
        import_result = await supplier.import_order_file(csv_bytes, "csv", "test_lcsc_file.csv")

        if import_result.success:
            print(f"✅ Import successful! Imported {import_result.imported_count} parts")

            # Show warnings if any
            if import_result.warnings:
                print("\n⚠️ Warnings:")
                for warning in import_result.warnings:
                    print(f"   - {warning}")

            # Check each imported part
            for i, part_data in enumerate(import_result.parts):
                print(f"\n🔍 Part {i+1} Analysis:")
                print(f"   Part Name: {part_data.get('part_name')}")
                print(
                    f"   Part Number: {part_data.get('part_number')} {'✅' if part_data.get('part_number') else '❌'}"
                )
                print(f"   Manufacturer: {part_data.get('manufacturer')}")
                print(f"   MPN: {part_data.get('manufacturer_part_number')}")
                print(f"   Supplier: {part_data.get('supplier')}")

                # Check if part number is in LCSC format (C followed by digits)
                part_number = part_data.get("part_number")
                if part_number and part_number.upper().startswith("C") and part_number[1:].isdigit():
                    print(f"   ✅ LCSC part number format is correct: {part_number}")
                else:
                    print(f"   ❌ Invalid LCSC part number format: {part_number}")

            if import_result.imported_count == 0:
                print("\n❌ No parts were imported. This might indicate a parsing issue.")

        else:
            print(f"❌ Import failed: {import_result.error_message}")
            if import_result.warnings:
                print("\n⚠️ Warnings:")
                for warning in import_result.warnings:
                    print(f"   - {warning}")

    except Exception as e:
        print(f"❌ Import test failed with exception: {e}")

    print("\n" + "=" * 50)
    print("🏁 Test completed!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_lcsc_csv_import())
