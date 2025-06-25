#!/usr/bin/env python3
"""
Quick verification script to test supplier configuration API
Run this while your backend is running to verify the API works
"""

import requests
import json


def test_supplier_api():
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Supplier Configuration API")
    print("=" * 50)
    
    # Step 1: Login
    print("1. Logging in...")
    login_response = requests.post(f"{base_url}/auth/login", data={
        "username": "admin",
        "password": "Admin123!"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Step 2: Check configured suppliers
    print("\n2. Checking configured suppliers...")
    suppliers_response = requests.get(f"{base_url}/api/suppliers/configured", headers=headers)
    
    print(f"Status: {suppliers_response.status_code}")
    print(f"Response: {suppliers_response.text}")
    
    if suppliers_response.status_code == 200:
        data = suppliers_response.json()
        suppliers = data.get('data', [])
        print(f"\n✅ Found {len(suppliers)} configured suppliers:")
        
        for supplier in suppliers:
            print(f"  - ID: {supplier.get('id')}")
            print(f"  - Name: {supplier.get('name')}")
            print(f"  - Configured: {supplier.get('configured')}")
            print(f"  - Enabled: {supplier.get('enabled')}")
            print()
        
        # Test the frontend logic
        print("3. Testing frontend field mapping logic...")
        configured_names = set()
        for s in suppliers:
            supplier_name = s.get('name') or s.get('supplier_name') or s.get('id') or ''
            configured_names.add(supplier_name.upper())
        
        print(f"Configured names (uppercase): {configured_names}")
        
        # Test with common part suppliers
        test_suppliers = ["LCSC", "DIGIKEY", "MOUSER", "ANALOG", "TI"]
        print(f"\nTesting parts with suppliers: {test_suppliers}")
        
        for supplier in test_suppliers:
            found = False
            for configured in configured_names:
                if supplier.upper() in configured or configured in supplier.upper():
                    found = True
                    break
            
            status = "✅ CONFIGURED" if found else "❌ NOT CONFIGURED"
            print(f"  {supplier}: {status}")
    
    else:
        print(f"❌ API call failed: {suppliers_response.status_code}")
        print(f"Response: {suppliers_response.text}")


if __name__ == "__main__":
    try:
        test_supplier_api()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Make sure it's running on http://localhost:8080")
    except Exception as e:
        print(f"❌ Error: {e}")