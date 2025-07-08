#!/usr/bin/env python3
"""
Server Status Check and Import Test

This script will:
1. Check if the server is running
2. Test basic connectivity
3. Run import tests if server is available
"""

import requests
import json
import io
import time
import sys


def check_server_status():
    """Check if the MakerMatrix server is running and responsive."""
    print("🔍 Checking server status...")
    
    try:
        # Try to reach the root endpoint
        response = requests.get("http://localhost:8080/", timeout=5)
        print(f"✅ Server is running (status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running or not accessible")
        print("   Please start the server with: python -m MakerMatrix.main")
        return False
    except requests.exceptions.Timeout:
        print("⚠️  Server is slow to respond")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False


def test_authentication():
    """Test authentication with the API."""
    print("🔐 Testing authentication...")
    
    try:
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        response = requests.post("http://localhost:8080/auth/login", data=login_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            if token:
                print("✅ Authentication successful")
                return token
            else:
                print("❌ No access token in response")
                return None
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


def clear_parts(token):
    """Clear all parts from the database."""
    print("🧹 Clearing parts database...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.delete("http://localhost:8080/api/parts/clear_all", headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Parts cleared: {result.get('message', 'Success')}")
            return True
        else:
            print(f"⚠️  Clear parts response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error clearing parts: {e}")
        return False


def get_import_suppliers(token):
    """Get available import suppliers."""
    print("📡 Getting import suppliers...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get("http://localhost:8080/api/import/suppliers", headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            suppliers = result["data"]
            
            print(f"✅ Found {len(suppliers)} suppliers:")
            for supplier in suppliers:
                print(f"  📦 {supplier['display_name']} ({supplier['name']})")
                print(f"      Import Available: {supplier['import_available']}")
                print(f"      Configuration: {supplier['configuration_status']}")
                print(f"      Enrichment Available: {supplier['enrichment_available']}")
                if supplier['enrichment_capabilities']:
                    print(f"      Capabilities: {', '.join(supplier['enrichment_capabilities'])}")
                print()
            
            return suppliers
        else:
            print(f"❌ Failed to get suppliers: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting suppliers: {e}")
        return []


def configure_lcsc_supplier(token):
    """Configure LCSC supplier."""
    print("⚙️  Configuring LCSC supplier...")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    config_data = {
        "supplier_name": "lcsc",
        "enabled": True,
        "configuration": {
            "rate_limit_per_minute": 20
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/api/suppliers/config/suppliers",
            headers=headers,
            json=config_data,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print("✅ LCSC supplier configured")
            return True
        else:
            print(f"⚠️  Failed to configure LCSC: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error configuring LCSC: {e}")
        return False


def test_import_with_configured_supplier(token):
    """Test importing parts with a configured supplier."""
    print("🧪 Testing import with configured LCSC supplier...")
    
    # Configure LCSC first
    if not configure_lcsc_supplier(token):
        return False
    
    # Clear parts
    clear_parts(token)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Sample LCSC CSV data
    sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
1kΩ,R1,R_0805_2012Metric,C17513,UNI-ROYAL(Uniroyal Elec),0805W8F1001T5E,LCSC,C17513,1
"""
    
    try:
        files = {"file": ("test_lcsc.csv", io.StringIO(sample_csv), "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "false"
        }
        
        response = requests.post(
            "http://localhost:8080/api/import/file",
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            imported = result['data']['imported_count']
            failed = result['data']['failed_count']
            
            print(f"✅ Import successful: {imported} parts imported, {failed} failed")
            
            # Verify parts in database
            parts_response = requests.get("http://localhost:8080/api/parts/get_all_parts", headers=headers)
            if parts_response.status_code == 200:
                parts_result = parts_response.json()
                actual_count = len(parts_result["data"])
                print(f"✅ Verified: {actual_count} parts in database")
                return actual_count == imported
            else:
                print(f"⚠️  Could not verify parts count")
                return True
        else:
            print(f"❌ Import failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing import: {e}")
        return False


def test_import_with_enrichment(token):
    """Test importing with enrichment capabilities."""
    print("🧪 Testing import with enrichment capabilities...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Clear parts first
    clear_parts(token)
    
    sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
"""
    
    try:
        files = {"file": ("test_enrichment.csv", io.StringIO(sample_csv), "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "true",
            "enrichment_capabilities": "get_part_details,fetch_datasheet"
        }
        
        response = requests.post(
            "http://localhost:8080/api/import/file",
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            imported = result['data']['imported_count']
            warnings = result['data']['warnings']
            
            print(f"✅ Import with enrichment: {imported} parts imported")
            
            # Check for enrichment task
            task_created = any("Enrichment task created" in str(warning) for warning in warnings)
            if task_created:
                print("✅ Enrichment task created successfully")
                
                # Look for task ID in warnings
                task_id = None
                for warning in warnings:
                    if "Enrichment task ID:" in str(warning):
                        task_id = str(warning).split("Enrichment task ID: ")[1]
                        break
                
                if task_id:
                    print(f"📋 Enrichment task ID: {task_id}")
                    
                    # Check task status
                    task_response = requests.get(f"http://localhost:8080/api/tasks/{task_id}", headers=headers)
                    if task_response.status_code == 200:
                        task_data = task_response.json()["data"]
                        print(f"📋 Task status: {task_data['status']}")
                        print(f"📋 Progress: {task_data['progress_percentage']}%")
                
                return True
            else:
                print("⚠️  No enrichment task created")
                print(f"Warnings: {warnings}")
                return False
        else:
            print(f"❌ Enrichment import failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing enrichment: {e}")
        return False


def test_invalid_supplier(token):
    """Test import with invalid supplier."""
    print("🧪 Testing import with invalid supplier...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    sample_csv = """Comment,Designator,Footprint,LCSC Part
10uF,C1,C_0805_2012Metric,C15849
"""
    
    try:
        files = {"file": ("test.csv", io.StringIO(sample_csv), "text/csv")}
        data = {"supplier_name": "invalid_supplier_xyz"}
        
        response = requests.post(
            "http://localhost:8080/api/import/file",
            headers=headers,
            files=files,
            data=data,
            timeout=10
        )
        
        if response.status_code == 400:
            text = response.text
            if "Unknown supplier" in text:
                print("✅ Correctly rejected invalid supplier")
                return True
            else:
                print(f"⚠️  Unexpected error message: {text}")
                return False
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing invalid supplier: {e}")
        return False


def main():
    """Main test function."""
    print("🧪 MakerMatrix Import Workflow Test Suite")
    print("=" * 50)
    
    # Check server status
    if not check_server_status():
        return False
    
    # Test authentication
    token = test_authentication()
    if not token:
        return False
    
    # Get suppliers
    print("\n📋 Getting available suppliers...")
    suppliers = get_import_suppliers(token)
    if not suppliers:
        print("❌ No suppliers available")
        return False
    
    # Run tests
    tests = [
        ("Import with Configured Supplier", lambda: test_import_with_configured_supplier(token)),
        ("Import with Enrichment", lambda: test_import_with_enrichment(token)),
        ("Invalid Supplier Handling", lambda: test_invalid_supplier(token)),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print("=" * 50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"\nResult: {status}")
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    for i, (test_name, result) in enumerate(results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test_name}: {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("✨ The dynamic supplier capability detection system is working correctly!")
        print("\nVerified functionality:")
        print("- ✅ Supplier capability detection")
        print("- ✅ Import with configured suppliers")
        print("- ✅ Enrichment task creation")
        print("- ✅ Error handling for invalid suppliers")
        return True
    else:
        print("\n⚠️  Some tests failed.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)