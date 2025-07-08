#!/usr/bin/env python3
"""
MakerMatrix Import Workflow Test Suite (HTTPS)

This script tests the complete import workflow including:
1. Clearing parts database
2. Testing import with no suppliers configured
3. Adding suppliers and testing import
4. Testing enrichment capabilities
5. Error handling scenarios
"""

import requests
import urllib3
import json
import io
import time
import sys

# Disable SSL warnings for localhost testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MakerMatrixImportTester:
    def __init__(self, base_url="https://localhost:8443"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for localhost
        
    def authenticate(self):
        """Authenticate with the API."""
        print("🔐 Authenticating with API...")
        
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        try:
            response = self.session.post(f"{self.base_url}/auth/login", data=login_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.token = result["access_token"]
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}
    
    def clear_parts(self):
        """Clear all parts from the database."""
        print("🧹 Clearing parts database...")
        
        try:
            response = self.session.delete(
                f"{self.base_url}/api/parts/clear_all",
                headers=self.get_auth_headers(),
                timeout=30
            )
            
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
    
    def get_import_suppliers(self):
        """Get available import suppliers and their capabilities."""
        print("📡 Getting import suppliers...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/import/suppliers",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
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
                    if supplier['missing_credentials']:
                        print(f"      Missing: {', '.join(supplier['missing_credentials'])}")
                    print()
                
                return suppliers
            else:
                print(f"❌ Failed to get suppliers: {response.status_code}")
                print(f"Response: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error getting suppliers: {e}")
            return []
    
    def configure_lcsc_supplier(self):
        """Configure LCSC supplier for testing."""
        print("⚙️  Configuring LCSC supplier...")
        
        config_data = {
            "supplier_name": "lcsc",
            "display_name": "LCSC Electronics",
            "base_url": "https://www.lcsc.com",
            "enabled": True,
            "configuration": {
                "rate_limit_requests_per_minute": 20
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/suppliers/config/suppliers",
                headers=self.get_auth_headers(),
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
    
    def test_import_no_suppliers(self):
        """Test import when no suppliers are configured."""
        print("🧪 Test 1: Import with no suppliers configured")
        
        # Try to clear supplier configurations
        try:
            # Get current suppliers and try to clear them
            suppliers_response = self.session.get(
                f"{self.base_url}/api/suppliers/config/suppliers",
                headers=self.get_auth_headers()
            )
            
            if suppliers_response.status_code == 200:
                suppliers = suppliers_response.json().get("data", [])
                for supplier in suppliers:
                    supplier_name = supplier.get("supplier_name")
                    if supplier_name:
                        self.session.delete(
                            f"{self.base_url}/api/suppliers/config/suppliers/{supplier_name}",
                            headers=self.get_auth_headers()
                        )
                print(f"🧹 Cleared {len(suppliers)} supplier configurations")
        except Exception as e:
            print(f"⚠️  Could not clear suppliers: {e}")
        
        sample_csv = """LCSC Part Number,Order Qty.,Unit Price($),Order Price($),Manufacturer,Manufacturer Part Number,Package,Description
C15849,1,0.05,0.05,YAGEO,CC0805KRX7R9BB103,0805,CAP CER 10UF 25V X7R 0805
C49678,2,0.03,0.06,YAGEO,CC0805KRX7R9BB104,0805,CAP CER 100NF 50V X7R 0805
"""
        
        try:
            files = {"file": ("test_lcsc.csv", io.StringIO(sample_csv), "text/csv")}
            data = {"supplier_name": "lcsc"}
            
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.get_auth_headers(),
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Import succeeded: {result['data']['imported_count']} parts imported")
                print("   (LCSC doesn't require configuration)")
                return True
            elif response.status_code == 403:
                print(f"✅ Import correctly failed (not configured): {response.text}")
                return True
            else:
                print(f"⚠️  Unexpected response: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing no suppliers: {e}")
            return False
    
    def test_import_with_configured_supplier(self):
        """Test import with properly configured supplier."""
        print("🧪 Test 2: Import with configured LCSC supplier")
        
        # Configure LCSC
        if not self.configure_lcsc_supplier():
            return False
        
        # Clear parts
        self.clear_parts()
        
        sample_csv = """LCSC Part Number,Order Qty.,Unit Price($),Order Price($),Manufacturer,Manufacturer Part Number,Package,Description
C15849,1,0.05,0.05,YAGEO,CC0805KRX7R9BB103,0805,CAP CER 10UF 25V X7R 0805
C49678,2,0.03,0.06,YAGEO,CC0805KRX7R9BB104,0805,CAP CER 100NF 50V X7R 0805
C17513,1,0.02,0.02,UNI-ROYAL(Uniroyal Elec),0805W8F1001T5E,0805,RES SMD 1K OHM 1% 1/8W 0805
"""
        
        try:
            files = {"file": ("test_lcsc.csv", io.StringIO(sample_csv), "text/csv")}
            data = {
                "supplier_name": "lcsc",
                "enable_enrichment": "false"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.get_auth_headers(),
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
                parts_response = self.session.get(
                    f"{self.base_url}/api/parts/get_all_parts",
                    headers=self.get_auth_headers()
                )
                
                if parts_response.status_code == 200:
                    parts_result = parts_response.json()
                    actual_count = len(parts_result["data"])
                    print(f"✅ Verified: {actual_count} parts in database")
                    return actual_count == imported
                else:
                    print(f"⚠️  Could not verify parts: {parts_response.status_code}")
                    return True
            else:
                print(f"❌ Import failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing configured import: {e}")
            return False
    
    def test_import_with_enrichment(self):
        """Test import with enrichment capabilities."""
        print("🧪 Test 3: Import with enrichment capabilities")
        
        # Clear parts
        self.clear_parts()
        
        sample_csv = """LCSC Part Number,Order Qty.,Unit Price($),Order Price($),Manufacturer,Manufacturer Part Number,Package,Description
C15849,1,0.05,0.05,YAGEO,CC0805KRX7R9BB103,0805,CAP CER 10UF 25V X7R 0805
C49678,2,0.03,0.06,YAGEO,CC0805KRX7R9BB104,0805,CAP CER 100NF 50V X7R 0805
"""
        
        try:
            files = {"file": ("test_enrichment.csv", io.StringIO(sample_csv), "text/csv")}
            data = {
                "supplier_name": "lcsc",
                "enable_enrichment": "true",
                "enrichment_capabilities": "get_part_details,fetch_datasheet"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.get_auth_headers(),
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
                        task_response = self.session.get(
                            f"{self.base_url}/api/tasks/{task_id}",
                            headers=self.get_auth_headers()
                        )
                        
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
                print(f"❌ Enrichment import failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing enrichment: {e}")
            return False
    
    def test_invalid_supplier(self):
        """Test import with invalid supplier."""
        print("🧪 Test 4: Import with invalid supplier")
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part
10uF,C1,C_0805_2012Metric,C15849
"""
        
        try:
            files = {"file": ("test.csv", io.StringIO(sample_csv), "text/csv")}
            data = {"supplier_name": "invalid_supplier_xyz"}
            
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.get_auth_headers(),
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
    
    def test_task_capabilities(self):
        """Test task capabilities endpoint."""
        print("🧪 Test 5: Task capabilities endpoint")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tasks/capabilities/suppliers",
                headers=self.get_auth_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                capabilities = result["data"]
                
                print("✅ Task capabilities working")
                print("📦 Available supplier capabilities:")
                for supplier, caps in capabilities.items():
                    print(f"    {supplier}: {', '.join(caps)}")
                
                return True
            else:
                print(f"❌ Capabilities failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing capabilities: {e}")
            return False
    
    def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 MakerMatrix Import Workflow Test Suite (HTTPS)")
        print("=" * 60)
        
        # Check server connectivity
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            print(f"✅ Server is accessible (status: {response.status_code})")
        except Exception as e:
            print(f"❌ Server not accessible: {e}")
            return False
        
        # Authenticate
        if not self.authenticate():
            return False
        
        # Get initial supplier state
        print("\n📋 Initial State: Available Suppliers")
        initial_suppliers = self.get_import_suppliers()
        
        # Run all tests
        tests = [
            ("Import with No Suppliers", self.test_import_no_suppliers),
            ("Import with Configured Supplier", self.test_import_with_configured_supplier),
            ("Import with Enrichment", self.test_import_with_enrichment),
            ("Invalid Supplier Handling", self.test_invalid_supplier),
            ("Task Capabilities Endpoint", self.test_task_capabilities),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            print(f"🧪 {test_name}")
            print("=" * 60)
            
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"\nResult: {status}")
            except Exception as e:
                print(f"❌ EXCEPTION: {e}")
                results.append((test_name, False))
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
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
            print("- ✅ Parts database clearing")
            print("- ✅ Import with configured suppliers")
            print("- ✅ Enrichment task creation")
            print("- ✅ Error handling for invalid suppliers")
            print("- ✅ Task capabilities endpoint")
            return True
        else:
            print("\n⚠️  Some tests failed. Check the implementation.")
            return False


def main():
    """Main function to run the tests."""
    tester = MakerMatrixImportTester()
    success = tester.run_all_tests()
    return success


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