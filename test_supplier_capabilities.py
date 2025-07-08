#!/usr/bin/env python3
"""
Quick test script for supplier capability detection.
Run this when the server is available to verify the implementation.
"""

import requests
import json


def test_supplier_capabilities():
    """Test the supplier capabilities endpoint."""
    try:
        print("Testing /api/import/suppliers endpoint...")
        response = requests.get("http://localhost:8080/api/import/suppliers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint working!")
            print(f"Status: {data['status']}")
            print(f"Message: {data['message']}")
            
            suppliers = data["data"]
            print(f"\nFound {len(suppliers)} suppliers:")
            
            for supplier in suppliers:
                print(f"\n📦 {supplier['display_name']} ({supplier['name']})")
                print(f"   Import Available: {supplier['import_available']}")
                print(f"   Configuration: {supplier['configuration_status']}")
                print(f"   Enrichment Available: {supplier['enrichment_available']}")
                
                if supplier['enrichment_capabilities']:
                    print(f"   Capabilities: {', '.join(supplier['enrichment_capabilities'])}")
                else:
                    print(f"   Capabilities: None")
                
                if supplier['missing_credentials']:
                    print(f"   Missing Credentials: {', '.join(supplier['missing_credentials'])}")
            
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        print("Make sure the MakerMatrix server is running on http://localhost:8080")
        return False


def test_task_capabilities():
    """Test the task capabilities endpoint."""
    try:
        print("\nTesting /api/tasks/capabilities/suppliers endpoint...")
        response = requests.get("http://localhost:8080/api/tasks/capabilities/suppliers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Task capabilities endpoint working!")
            
            capabilities = data["data"]
            print(f"\nSupplier capabilities:")
            
            for supplier, caps in capabilities.items():
                print(f"  {supplier}: {', '.join(caps)}")
            
            return True
        else:
            print(f"❌ Task capabilities request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Task capabilities connection error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Supplier Capability Detection")
    print("=" * 50)
    
    success1 = test_supplier_capabilities()
    success2 = test_task_capabilities()
    
    if success1 and success2:
        print("\n✅ All capability detection tests passed!")
        print("\nThe dynamic supplier capability detection system is working correctly.")
        print("\nNext steps:")
        print("1. Configure a supplier (e.g., LCSC) in the web interface")
        print("2. Try importing a CSV file to test the full workflow")
        print("3. Check that enrichment options appear for configured suppliers")
    else:
        print("\n❌ Some tests failed.")
        print("Check that the MakerMatrix server is running and accessible.")