"""
Test script to verify Mouser XLS import works correctly
"""
import asyncio
from pathlib import Path

async def test_mouser_xls_import():
    from MakerMatrix.suppliers.registry import get_supplier

    # Get Mouser supplier
    mouser = get_supplier('mouser')

    # Load test XLS file
    xls_path = Path('/home/ril3y/MakerMatrix/MakerMatrix/tests/mouser_xls_test/271360826.xls')
    print(f"Testing with file: {xls_path}")

    with open(xls_path, 'rb') as f:
        file_content = f.read()

    filename = xls_path.name

    # Test can_import_file
    print(f"\n1. Testing can_import_file('{filename}')...")
    can_import = mouser.can_import_file(filename, file_content)
    print(f"   Result: {can_import}")

    if not can_import:
        print("   ❌ FAILED: File should be importable!")
        return False

    # Test import_order_file
    print(f"\n2. Testing import_order_file...")
    result = await mouser.import_order_file(file_content, 'xls', filename)
    print(f"   Success: {result.success}")
    print(f"   Parts imported: {len(result.parts) if result.parts else 0}")

    if result.success:
        print(f"   ✅ SUCCESS: Imported {len(result.parts)} parts")
        if result.parts:
            print(f"\n   First part:")
            part = result.parts[0]
            print(f"     - Name: {part.get('part_name', 'N/A')}")
            print(f"     - Part #: {part.get('part_number', 'N/A')}")
            print(f"     - Mfr: {part.get('manufacturer', 'N/A')}")
            print(f"     - Qty: {part.get('quantity', 'N/A')}")
        return True
    else:
        print(f"   ❌ FAILED: {result.error_message}")
        if result.warnings:
            print(f"   Warnings: {result.warnings}")
        return False

if __name__ == '__main__':
    success = asyncio.run(test_mouser_xls_import())
    exit(0 if success else 1)
