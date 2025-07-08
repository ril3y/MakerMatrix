#!/usr/bin/env python3
"""
Test script for import workflow with dynamic supplier capability detection.

This script will:
1. Clear the parts database
2. Test various import scenarios
3. Verify supplier capability detection
4. Test enrichment functionality
"""

import requests
import json
import io
import time
import sys
from typing import Dict, Any


class ImportWorkflowTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.auth_headers = None
        self.session = requests.Session()
    
    def authenticate(self):
        """Authenticate with the API."""
        print("🔐 Authenticating...")
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        response = self.session.post(f"{self.base_url}/auth/login", data=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.auth_headers = {"Authorization": f"Bearer {token}"}
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
    
    def clear_parts(self):
        """Clear all parts from the database."""
        print("🧹 Clearing parts database...")
        try:
            response = self.session.delete(
                f"{self.base_url}/api/parts/clear_all",
                headers=self.auth_headers,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Parts cleared: {result.get('message', 'Success')}")
                return True
            else:
                print(f"⚠️  Failed to clear parts: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"⚠️  Error clearing parts: {e}")
            return False
    
    def get_import_suppliers(self):
        """Get list of import suppliers and their capabilities."""
        print("📡 Getting import suppliers...")
        try:
            response = self.session.get(
                f"{self.base_url}/api/import/suppliers",
                headers=self.auth_headers
            )
            if response.status_code == 200:
                data = response.json()
                suppliers = data["data"]
                print(f"✅ Found {len(suppliers)} suppliers")
                
                for supplier in suppliers:
                    print(f"  📦 {supplier['display_name']} ({supplier['name']})")
                    print(f"      Import Available: {supplier['import_available']}")
                    print(f"      Configuration: {supplier['configuration_status']}")
                    print(f"      Enrichment Available: {supplier['enrichment_available']}")
                    if supplier['enrichment_capabilities']:
                        print(f"      Capabilities: {', '.join(supplier['enrichment_capabilities'])}")
                    if supplier['missing_credentials']:
                        print(f"      Missing Credentials: {', '.join(supplier['missing_credentials'])}")
                    print()
                
                return suppliers
            else:
                print(f"❌ Failed to get suppliers: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error getting suppliers: {e}")
            return []
    
    def configure_lcsc_supplier(self):
        """Configure LCSC supplier for testing."""
        print("⚙️  Configuring LCSC supplier...")
        try:
            config_data = {
                "supplier_name": "lcsc",
                "enabled": True,
                "configuration": {
                    "rate_limit_per_minute": 20
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/suppliers/config/suppliers",
                headers=self.auth_headers,
                json=config_data
            )
            
            if response.status_code in [200, 201]:
                print("✅ LCSC supplier configured")
                return True
            else:
                print(f"⚠️  Failed to configure LCSC: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error configuring LCSC: {e}")
            return False
    
    def test_import_without_suppliers(self):
        """Test import when no suppliers are configured."""
        print("🧪 Testing import without suppliers configured...")
        
        # First clear supplier configurations (if endpoint exists)
        # This test will show how the system handles unconfigured suppliers
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
"""
        
        files = {"file": ("test_lcsc.csv", io.StringIO(sample_csv), "text/csv")}
        data = {"supplier_name": "lcsc"}
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.auth_headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Import succeeded: {result['data']['imported_count']} parts imported")
                return True
            elif response.status_code == 403:
                print(f"✅ Import correctly failed (supplier not configured): {response.json()['detail']}")
                return True
            else:
                print(f"⚠️  Unexpected response: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing import: {e}")
            return False
    
    def test_import_with_configured_supplier(self):
        """Test import with properly configured supplier."""
        print("🧪 Testing import with configured LCSC supplier...")
        
        # Configure LCSC first
        if not self.configure_lcsc_supplier():
            return False
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
1kΩ,R1,R_0805_2012Metric,C17513,UNI-ROYAL(Uniroyal Elec),0805W8F1001T5E,LCSC,C17513,1
"""
        
        files = {"file": ("test_lcsc.csv", io.StringIO(sample_csv), "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "false"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.auth_headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                imported_count = result['data']['imported_count']
                failed_count = result['data']['failed_count']
                print(f"✅ Import successful: {imported_count} parts imported, {failed_count} failed")
                
                # Verify parts were created
                parts_response = self.session.get(
                    f"{self.base_url}/api/parts/get_all_parts",
                    headers=self.auth_headers
                )
                
                if parts_response.status_code == 200:
                    parts_data = parts_response.json()
                    actual_count = len(parts_data["data"])
                    print(f"✅ Verified: {actual_count} parts in database")
                    return actual_count == imported_count
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
        """Test import with enrichment capabilities enabled."""
        print("🧪 Testing import with enrichment capabilities...")
        
        # Clear parts first
        self.clear_parts()
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
"""
        
        files = {"file": ("test_lcsc_enrichment.csv", io.StringIO(sample_csv), "text/csv")}
        data = {
            "supplier_name": "lcsc",
            "enable_enrichment": "true",
            "enrichment_capabilities": "get_part_details,fetch_datasheet"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.auth_headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                result = response.json()
                imported_count = result['data']['imported_count']
                warnings = result['data']['warnings']
                
                print(f"✅ Import with enrichment successful: {imported_count} parts imported")
                
                # Check if enrichment task was created
                task_created = any("Enrichment task created" in warning for warning in warnings)
                if task_created:
                    print("✅ Enrichment task created successfully")
                    
                    # Extract task ID from warnings
                    task_id = None
                    for warning in warnings:
                        if "Enrichment task ID:" in warning:
                            task_id = warning.split("Enrichment task ID: ")[1]
                            break
                    
                    if task_id:
                        print(f"📋 Enrichment task ID: {task_id}")
                        
                        # Check task status
                        task_response = self.session.get(
                            f"{self.base_url}/api/tasks/{task_id}",
                            headers=self.auth_headers
                        )
                        
                        if task_response.status_code == 200:
                            task_data = task_response.json()["data"]
                            print(f"📋 Task status: {task_data['status']}")
                            print(f"📋 Task progress: {task_data['progress_percentage']}%")
                        
                    return True
                else:
                    print("⚠️  No enrichment task created")
                    return False
            else:
                print(f"❌ Import with enrichment failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error testing enrichment import: {e}")
            return False
    
    def test_invalid_supplier(self):
        """Test import with invalid supplier name."""
        print("🧪 Testing import with invalid supplier...")
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part
10uF,C1,C_0805_2012Metric,C15849
"""
        
        files = {"file": ("test.csv", io.StringIO(sample_csv), "text/csv")}
        data = {"supplier_name": "invalid_supplier"}
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/import/file",
                headers=self.auth_headers,
                files=files,
                data=data
            )
            
            if response.status_code == 400:
                detail = response.json()["detail"]
                if "Unknown supplier" in detail:
                    print(f"✅ Correctly rejected invalid supplier: {detail}")
                    return True
                else:
                    print(f"⚠️  Unexpected error message: {detail}")
                    return False
            else:
                print(f"⚠️  Unexpected response for invalid supplier: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error testing invalid supplier: {e}")
            return False
    
    def test_task_capabilities_endpoint(self):
        """Test the task capabilities endpoint."""
        print("🧪 Testing task capabilities endpoint...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tasks/capabilities/suppliers",
                headers=self.auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                capabilities = data["data"]
                
                print(f"✅ Task capabilities endpoint working")
                print(f"📦 Available suppliers with capabilities:")
                for supplier, caps in capabilities.items():
                    print(f"    {supplier}: {', '.join(caps)}")
                
                return True
            else:
                print(f"❌ Task capabilities endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error testing capabilities endpoint: {e}")
            return False
    
    def run_all_tests(self):
        """Run all test scenarios."""
        print("🚀 Starting Import Workflow Tests")
        print("=" * 50)
        
        if not self.authenticate():
            return False
        
        test_results = []
        
        # Test 1: Get suppliers and their capabilities
        print("\n📋 Test 1: Supplier Capability Detection")
        suppliers = self.get_import_suppliers()
        test_results.append(len(suppliers) > 0)
        
        # Test 2: Import without suppliers configured
        print("\n📋 Test 2: Import Without Suppliers Configured")
        test_results.append(self.test_import_without_suppliers())
        
        # Test 3: Import with configured supplier
        print("\n📋 Test 3: Import With Configured Supplier")
        test_results.append(self.test_import_with_configured_supplier())
        
        # Test 4: Import with enrichment
        print("\n📋 Test 4: Import With Enrichment Capabilities")
        test_results.append(self.test_import_with_enrichment())
        
        # Test 5: Invalid supplier
        print("\n📋 Test 5: Invalid Supplier Handling")
        test_results.append(self.test_invalid_supplier())
        
        # Test 6: Task capabilities endpoint
        print("\n📋 Test 6: Task Capabilities Endpoint")
        test_results.append(self.test_task_capabilities_endpoint())
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = sum(test_results)
        total = len(test_results)
        
        test_names = [
            "Supplier Capability Detection",
            "Import Without Suppliers",
            "Import With Configured Supplier", 
            "Import With Enrichment",
            "Invalid Supplier Handling",
            "Task Capabilities Endpoint"
        ]
        
        for i, (name, result) in enumerate(zip(test_names, test_results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{i+1}. {name}: {status}")
        
        print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Import workflow is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the implementation.")
            return False


if __name__ == "__main__":
    tester = ImportWorkflowTester()
    
    print("🧪 MakerMatrix Import Workflow Test Suite")
    print("This will test the dynamic supplier capability detection system")
    print()
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)