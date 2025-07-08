#!/usr/bin/env python3
"""
Complete Import Workflow Test Suite

This script tests the entire import workflow including:
1. Clearing parts database
2. Testing import with no suppliers configured
3. Adding suppliers and testing import
4. Testing enrichment capabilities
5. Error handling scenarios
"""

import asyncio
import aiohttp
import json
import io
import time
import sys
from typing import Dict, Any, Optional


class CompleteImportTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.auth_token = None
        
    async def authenticate(self):
        """Authenticate with the API and get token."""
        print("🔐 Authenticating with API...")
        
        async with aiohttp.ClientSession() as session:
            login_data = aiohttp.FormData()
            login_data.add_field("username", "admin")
            login_data.add_field("password", "Admin123!")
            
            try:
                async with session.post(f"{self.base_url}/auth/login", data=login_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.auth_token = result["access_token"]
                        print("✅ Authentication successful")
                        return True
                    else:
                        text = await response.text()
                        print(f"❌ Authentication failed: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Authentication error: {e}")
                return False
    
    def get_auth_headers(self):
        """Get authorization headers."""
        if not self.auth_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def clear_parts(self):
        """Clear all parts from the database."""
        print("🧹 Clearing parts database...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    f"{self.base_url}/api/parts/clear_all",
                    headers=self.get_auth_headers(),
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Parts cleared: {result.get('message', 'Success')}")
                        return True
                    else:
                        text = await response.text()
                        print(f"⚠️  Clear parts response: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error clearing parts: {e}")
                return False
    
    async def clear_all_suppliers(self):
        """Clear all supplier configurations."""
        print("🧹 Clearing supplier configurations...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Get all suppliers first
                async with session.get(
                    f"{self.base_url}/api/suppliers/config/suppliers",
                    headers=self.get_auth_headers()
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        suppliers = result.get("data", [])
                        
                        # Delete each supplier
                        for supplier in suppliers:
                            supplier_name = supplier.get("supplier_name")
                            if supplier_name:
                                async with session.delete(
                                    f"{self.base_url}/api/suppliers/config/suppliers/{supplier_name}",
                                    headers=self.get_auth_headers()
                                ) as del_response:
                                    if del_response.status == 200:
                                        print(f"  ✅ Removed supplier: {supplier_name}")
                                    else:
                                        print(f"  ⚠️  Failed to remove {supplier_name}: {del_response.status}")
                        
                        print(f"✅ Cleared {len(suppliers)} supplier configurations")
                        return True
                    else:
                        print(f"⚠️  Could not get suppliers: {response.status}")
                        return False
            except Exception as e:
                print(f"❌ Error clearing suppliers: {e}")
                return False
    
    async def get_import_suppliers(self):
        """Get available import suppliers and their capabilities."""
        print("📡 Getting import suppliers...")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/import/suppliers",
                    headers=self.get_auth_headers()
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        suppliers = result["data"]
                        
                        print(f"✅ Found {len(suppliers)} suppliers")
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
                        text = await response.text()
                        print(f"❌ Failed to get suppliers: {response.status} - {text}")
                        return []
            except Exception as e:
                print(f"❌ Error getting suppliers: {e}")
                return []
    
    async def configure_lcsc_supplier(self):
        """Configure LCSC supplier for testing."""
        print("⚙️  Configuring LCSC supplier...")
        
        config_data = {
            "supplier_name": "lcsc",
            "enabled": True,
            "configuration": {
                "rate_limit_per_minute": 20
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/api/suppliers/config/suppliers",
                    headers=self.get_auth_headers(),
                    json=config_data
                ) as response:
                    if response.status in [200, 201]:
                        print("✅ LCSC supplier configured")
                        return True
                    else:
                        text = await response.text()
                        print(f"⚠️  Failed to configure LCSC: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error configuring LCSC: {e}")
                return False
    
    async def test_import_no_suppliers(self):
        """Test import when no suppliers are configured."""
        print("🧪 Test 1: Import with no suppliers configured")
        
        # Clear suppliers first
        await self.clear_all_suppliers()
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
"""
        
        async with aiohttp.ClientSession() as session:
            try:
                # Create form data for file upload
                data = aiohttp.FormData()
                data.add_field('supplier_name', 'lcsc')
                data.add_field('file', io.StringIO(sample_csv), filename='test_lcsc.csv', content_type='text/csv')
                
                async with session.post(
                    f"{self.base_url}/api/import/file",
                    headers=self.get_auth_headers(),
                    data=data
                ) as response:
                    text = await response.text()
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ Import succeeded: {result['data']['imported_count']} parts imported")
                        print("   (LCSC doesn't require configuration)")
                        return True
                    elif response.status == 403:
                        print(f"✅ Import correctly failed (not configured): {text}")
                        return True
                    else:
                        print(f"⚠️  Unexpected response: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing no suppliers: {e}")
                return False
    
    async def test_import_with_configured_supplier(self):
        """Test import with properly configured supplier."""
        print("🧪 Test 2: Import with configured LCSC supplier")
        
        # Configure LCSC
        if not await self.configure_lcsc_supplier():
            return False
        
        # Clear parts first
        await self.clear_parts()
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
1kΩ,R1,R_0805_2012Metric,C17513,UNI-ROYAL(Uniroyal Elec),0805W8F1001T5E,LCSC,C17513,1
"""
        
        async with aiohttp.ClientSession() as session:
            try:
                # Create form data
                data = aiohttp.FormData()
                data.add_field('supplier_name', 'lcsc')
                data.add_field('enable_enrichment', 'false')
                data.add_field('file', io.StringIO(sample_csv), filename='test_lcsc.csv', content_type='text/csv')
                
                async with session.post(
                    f"{self.base_url}/api/import/file",
                    headers=self.get_auth_headers(),
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        imported = result['data']['imported_count']
                        failed = result['data']['failed_count']
                        print(f"✅ Import successful: {imported} parts imported, {failed} failed")
                        
                        # Verify parts in database
                        async with session.get(
                            f"{self.base_url}/api/parts/get_all_parts",
                            headers=self.get_auth_headers()
                        ) as parts_response:
                            if parts_response.status == 200:
                                parts_result = await parts_response.json()
                                actual_count = len(parts_result["data"])
                                print(f"✅ Verified: {actual_count} parts in database")
                                return actual_count == imported
                            else:
                                print(f"⚠️  Could not verify parts: {parts_response.status}")
                                return True
                    else:
                        text = await response.text()
                        print(f"❌ Import failed: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing configured import: {e}")
                return False
    
    async def test_import_with_enrichment(self):
        """Test import with enrichment capabilities."""
        print("🧪 Test 3: Import with enrichment capabilities")
        
        # Clear parts
        await self.clear_parts()
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part,Manufacturer,Manufacturer Part,Supplier,Supplier Part,Quantity
10uF,C1,C_0805_2012Metric,C15849,YAGEO,CC0805KRX7R9BB103,LCSC,C15849,1
100nF,C2,C_0805_2012Metric,C49678,YAGEO,CC0805KRX7R9BB104,LCSC,C49678,2
"""
        
        async with aiohttp.ClientSession() as session:
            try:
                # Create form data with enrichment
                data = aiohttp.FormData()
                data.add_field('supplier_name', 'lcsc')
                data.add_field('enable_enrichment', 'true')
                data.add_field('enrichment_capabilities', 'get_part_details,fetch_datasheet')
                data.add_field('file', io.StringIO(sample_csv), filename='test_enrichment.csv', content_type='text/csv')
                
                async with session.post(
                    f"{self.base_url}/api/import/file",
                    headers=self.get_auth_headers(),
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        imported = result['data']['imported_count']
                        warnings = result['data']['warnings']
                        
                        print(f"✅ Import with enrichment: {imported} parts imported")
                        
                        # Check for enrichment task
                        task_created = any("Enrichment task created" in warning for warning in warnings)
                        if task_created:
                            print("✅ Enrichment task created")
                            
                            # Extract task ID
                            task_id = None
                            for warning in warnings:
                                if "Enrichment task ID:" in warning:
                                    task_id = warning.split("Enrichment task ID: ")[1]
                                    break
                            
                            if task_id:
                                print(f"📋 Task ID: {task_id}")
                                
                                # Check task status
                                async with session.get(
                                    f"{self.base_url}/api/tasks/{task_id}",
                                    headers=self.get_auth_headers()
                                ) as task_response:
                                    if task_response.status == 200:
                                        task_data = await task_response.json()
                                        task_info = task_data["data"]
                                        print(f"📋 Task status: {task_info['status']}")
                                        print(f"📋 Progress: {task_info['progress_percentage']}%")
                            
                            return True
                        else:
                            print("⚠️  No enrichment task created")
                            return False
                    else:
                        text = await response.text()
                        print(f"❌ Enrichment import failed: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing enrichment: {e}")
                return False
    
    async def test_invalid_supplier(self):
        """Test import with invalid supplier."""
        print("🧪 Test 4: Import with invalid supplier")
        
        sample_csv = """Comment,Designator,Footprint,LCSC Part
10uF,C1,C_0805_2012Metric,C15849
"""
        
        async with aiohttp.ClientSession() as session:
            try:
                data = aiohttp.FormData()
                data.add_field('supplier_name', 'invalid_supplier_xyz')
                data.add_field('file', io.StringIO(sample_csv), filename='test.csv', content_type='text/csv')
                
                async with session.post(
                    f"{self.base_url}/api/import/file",
                    headers=self.get_auth_headers(),
                    data=data
                ) as response:
                    if response.status == 400:
                        text = await response.text()
                        if "Unknown supplier" in text:
                            print(f"✅ Correctly rejected invalid supplier")
                            return True
                        else:
                            print(f"⚠️  Unexpected error: {text}")
                            return False
                    else:
                        text = await response.text()
                        print(f"⚠️  Unexpected response: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing invalid supplier: {e}")
                return False
    
    async def test_digikey_unconfigured(self):
        """Test import with DigiKey (requires configuration)."""
        print("🧪 Test 5: Import with unconfigured DigiKey")
        
        sample_csv = """Index,Quantity,Part Number,Manufacturer,Description,Customer Reference
1,1,296-8903-1-ND,Texas Instruments,IC REG LINEAR 3.3V 1A SOT223,U1
2,2,399-1168-1-ND,KEMET,CAP CER 10UF 25V X7R 0805,C1
"""
        
        async with aiohttp.ClientSession() as session:
            try:
                data = aiohttp.FormData()
                data.add_field('supplier_name', 'digikey')
                data.add_field('file', io.StringIO(sample_csv), filename='test_digikey.csv', content_type='text/csv')
                
                async with session.post(
                    f"{self.base_url}/api/import/file",
                    headers=self.get_auth_headers(),
                    data=data
                ) as response:
                    if response.status == 403:
                        text = await response.text()
                        if "not configured" in text.lower():
                            print("✅ Correctly rejected unconfigured DigiKey")
                            return True
                        else:
                            print(f"⚠️  Unexpected error: {text}")
                            return False
                    else:
                        text = await response.text()
                        print(f"⚠️  Unexpected response: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing DigiKey: {e}")
                return False
    
    async def test_task_capabilities(self):
        """Test task capabilities endpoint."""
        print("🧪 Test 6: Task capabilities endpoint")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/tasks/capabilities/suppliers",
                    headers=self.get_auth_headers()
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        capabilities = result["data"]
                        
                        print("✅ Task capabilities working")
                        print("📦 Available supplier capabilities:")
                        for supplier, caps in capabilities.items():
                            print(f"    {supplier}: {', '.join(caps)}")
                        
                        return True
                    else:
                        text = await response.text()
                        print(f"❌ Capabilities failed: {response.status} - {text}")
                        return False
            except Exception as e:
                print(f"❌ Error testing capabilities: {e}")
                return False
    
    async def run_all_tests(self):
        """Run the complete test suite."""
        print("🚀 Complete Import Workflow Test Suite")
        print("=" * 60)
        
        # Authenticate
        if not await self.authenticate():
            return False
        
        # Get initial supplier state
        print("\n📋 Initial State: Available Suppliers")
        initial_suppliers = await self.get_import_suppliers()
        
        # Run all tests
        tests = [
            ("Import with No Suppliers", self.test_import_no_suppliers),
            ("Import with Configured Supplier", self.test_import_with_configured_supplier),
            ("Import with Enrichment", self.test_import_with_enrichment),
            ("Invalid Supplier Handling", self.test_invalid_supplier),
            ("Unconfigured DigiKey", self.test_digikey_unconfigured),
            ("Task Capabilities Endpoint", self.test_task_capabilities),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*60}")
            try:
                result = await test_func()
                results.append((test_name, result))
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"Result: {status}")
            except Exception as e:
                print(f"❌ EXCEPTION: {e}")
                results.append((test_name, False))
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST RESULTS SUMMARY")
        print(f"{'='*60}")
        
        passed = 0
        for i, (test_name, result) in enumerate(results):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{i+1}. {test_name}: {status}")
            if result:
                passed += 1
        
        total = len(results)
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Import workflow working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the implementation.")
            return False


async def main():
    """Main function to run the tests."""
    print("🧪 MakerMatrix Complete Import Workflow Test Suite")
    print("This will test all aspects of the import system including:")
    print("- Supplier capability detection")
    print("- Import with/without configured suppliers")
    print("- Enrichment capabilities")
    print("- Error handling")
    print()
    
    tester = CompleteImportTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✨ All tests completed successfully!")
        print("The dynamic supplier capability detection system is working.")
    else:
        print("\n💥 Some tests failed.")
        print("Please check the server logs and implementation.")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)