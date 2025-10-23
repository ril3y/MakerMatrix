#!/usr/bin/env python3
"""
Test Supplier Enrichment Availability

This test verifies that the suppliers API correctly reports enrichment availability
based on configured credentials.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from MakerMatrix.suppliers.registry import get_available_suppliers, get_supplier
from MakerMatrix.suppliers.base import SupplierCapability


async def test_digikey_enrichment_availability():
    """Test DigiKey enrichment availability detection"""
    print("🔍 TESTING DIGIKEY ENRICHMENT AVAILABILITY")
    print("=" * 60)

    # Get DigiKey supplier
    supplier = get_supplier("digikey")
    if not supplier:
        print("❌ DigiKey supplier not found")
        return

    print(f"✅ DigiKey supplier found: {supplier.__class__.__name__}")

    # Check capabilities
    capabilities = supplier.get_capabilities()
    print(f"📋 All capabilities: {[cap.value for cap in capabilities]}")

    # Check enrichment capabilities specifically
    enrichment_caps = [
        SupplierCapability.GET_PART_DETAILS,
        SupplierCapability.FETCH_DATASHEET,
        SupplierCapability.FETCH_PRICING_STOCK,
    ]

    print("\n🔧 ENRICHMENT CAPABILITY ANALYSIS:")
    enrichment_available = False
    available_enrichment_caps = []
    missing_credentials_list = []

    for cap in enrichment_caps:
        if cap in capabilities:
            is_available = supplier.is_capability_available(cap)
            missing_creds = supplier.get_missing_credentials_for_capability(cap)

            print(f"   {cap.value}:")
            print(f"      Available: {is_available}")
            print(f"      Missing credentials: {missing_creds}")

            if is_available:
                available_enrichment_caps.append(cap.value)
                enrichment_available = True
            else:
                missing_credentials_list.extend(missing_creds)

    # Remove duplicates
    missing_credentials_list = list(set(missing_credentials_list))

    print(f"\n📊 SUMMARY:")
    print(f"   Enrichment Available: {enrichment_available}")
    print(f"   Available Capabilities: {available_enrichment_caps}")
    print(f"   Missing Credentials: {missing_credentials_list}")

    return {
        "enrichment_available": enrichment_available,
        "enrichment_capabilities": available_enrichment_caps,
        "enrichment_missing_credentials": missing_credentials_list,
    }


async def test_suppliers_endpoint_logic():
    """Test the logic used in the suppliers endpoint"""
    print("\n🌐 TESTING SUPPLIERS ENDPOINT LOGIC")
    print("=" * 60)

    # Get available suppliers
    available_suppliers = get_available_suppliers()
    print(f"📦 Available suppliers: {list(available_suppliers.keys())}")

    if "digikey" not in available_suppliers:
        print("❌ DigiKey not in available suppliers")
        return

    supplier = available_suppliers["digikey"]

    # Simulate the logic from import_routes.py
    try:
        # Check basic availability
        connection_result = await supplier.test_connection()
        print(f"🔌 Connection test: {connection_result}")

        is_configured = connection_result.get("success", False)
        print(f"⚙️ Is configured: {is_configured}")

        # Check enrichment capabilities (from import_routes.py logic)
        enrichment_capabilities = []
        enrichment_available = False
        enrichment_missing_credentials = []

        # Get all enrichment-related capabilities
        enrichment_capability_types = [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_PRICING_STOCK,
        ]

        for cap in enrichment_capability_types:
            if cap in supplier.get_capabilities():
                cap_available = supplier.is_capability_available(cap)
                print(f"   {cap.value}: available={cap_available}")

                if cap_available:
                    enrichment_capabilities.append(cap.value)
                    enrichment_available = True
                else:
                    # Get missing credentials for this capability
                    missing_for_cap = supplier.get_missing_credentials_for_capability(cap)
                    enrichment_missing_credentials.extend(missing_for_cap)

        # Remove duplicates from missing credentials
        enrichment_missing_credentials = list(set(enrichment_missing_credentials))

        # This is what would be returned to frontend
        result = {
            "name": "digikey",
            "enrichment_capabilities": enrichment_capabilities,
            "enrichment_available": enrichment_available,
            "enrichment_missing_credentials": enrichment_missing_credentials if not is_configured else [],
        }

        print(f"\n📡 ENDPOINT WOULD RETURN:")
        print(f"   enrichment_available: {result['enrichment_available']}")
        print(f"   enrichment_capabilities: {result['enrichment_capabilities']}")
        print(f"   enrichment_missing_credentials: {result['enrichment_missing_credentials']}")

        return result

    except Exception as e:
        print(f"❌ Error testing supplier: {e}")
        return None


async def test_lcsc_for_comparison():
    """Test LCSC for comparison"""
    print("\n🔄 TESTING LCSC FOR COMPARISON")
    print("=" * 60)

    supplier = get_supplier("lcsc")
    if not supplier:
        print("❌ LCSC supplier not found")
        return

    # Check LCSC enrichment availability
    enrichment_caps = [
        SupplierCapability.GET_PART_DETAILS,
        SupplierCapability.FETCH_DATASHEET,
        SupplierCapability.FETCH_PRICING_STOCK,
    ]

    print("🔧 LCSC ENRICHMENT CAPABILITY ANALYSIS:")
    enrichment_available = False
    available_enrichment_caps = []

    for cap in enrichment_caps:
        if cap in supplier.get_capabilities():
            is_available = supplier.is_capability_available(cap)
            missing_creds = supplier.get_missing_credentials_for_capability(cap)

            print(f"   {cap.value}:")
            print(f"      Available: {is_available}")
            print(f"      Missing credentials: {missing_creds}")

            if is_available:
                available_enrichment_caps.append(cap.value)
                enrichment_available = True

    print(f"\n📊 LCSC SUMMARY:")
    print(f"   Enrichment Available: {enrichment_available}")
    print(f"   Available Capabilities: {available_enrichment_caps}")


async def main():
    """Main test runner"""
    print("🧪 SUPPLIER ENRICHMENT AVAILABILITY TEST")
    print("Testing how enrichment availability is determined")
    print("=" * 80)

    # Test DigiKey
    digikey_result = await test_digikey_enrichment_availability()

    # Test endpoint logic
    endpoint_result = await test_suppliers_endpoint_logic()

    # Test LCSC for comparison
    await test_lcsc_for_comparison()

    print("\n" + "=" * 80)
    print("🎯 CONCLUSION:")

    if endpoint_result:
        if endpoint_result["enrichment_available"] and not endpoint_result["enrichment_capabilities"]:
            print("❌ BUG FOUND: enrichment_available=True but no capabilities available")
        elif not endpoint_result["enrichment_available"] and endpoint_result["enrichment_missing_credentials"]:
            print("✅ CORRECT: enrichment_available=False with missing credentials listed")
        elif endpoint_result["enrichment_available"] and endpoint_result["enrichment_capabilities"]:
            print("✅ CORRECT: enrichment_available=True with working capabilities")
        else:
            print(f"⚠️ UNCLEAR STATE: {endpoint_result}")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
