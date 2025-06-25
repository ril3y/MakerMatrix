#!/usr/bin/env python
"""
Test all CRUD operations for parts, locations, and categories
"""
import asyncio
import httpx
import json
from typing import Dict, Any
import sys

# API base URL
BASE_URL = "http://localhost:8080"

# Test credentials
USERNAME = "admin"
PASSWORD = "Admin123!"


class CRUDTester:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.token = None
        self.test_results = []

    async def login(self) -> bool:
        """Login and get authentication token"""
        try:
            response = await self.client.post(
                "/auth/login",
                data={"username": USERNAME, "password": PASSWORD}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    async def test_crud(self, entity_type: str, endpoints: Dict[str, Any]) -> Dict[str, Any]:
        """Test CRUD operations for an entity type"""
        results = {
            "entity": entity_type,
            "tests": {}
        }
        
        print(f"\n🧪 Testing {entity_type} CRUD operations...")
        
        # CREATE
        try:
            create_response = await self.client.post(
                endpoints["create"]["url"],
                json=endpoints["create"]["data"]
            )
            if create_response.status_code in [200, 201]:
                create_data = create_response.json()
                if create_data.get("status") == "success":
                    created_id = create_data["data"].get("id")
                    results["tests"]["create"] = "✅ PASS"
                    print(f"  ✅ CREATE: {entity_type} created with ID: {created_id}")
                else:
                    results["tests"]["create"] = f"❌ FAIL: {create_data.get('message')}"
                    print(f"  ❌ CREATE failed: {create_data.get('message')}")
                    created_id = None
            else:
                results["tests"]["create"] = f"❌ FAIL: HTTP {create_response.status_code}"
                print(f"  ❌ CREATE failed: HTTP {create_response.status_code} - {create_response.text}")
                created_id = None
        except Exception as e:
            results["tests"]["create"] = f"❌ FAIL: {str(e)}"
            print(f"  ❌ CREATE error: {e}")
            created_id = None

        # READ (Get All)
        try:
            read_all_response = await self.client.get(endpoints["read_all"]["url"])
            if read_all_response.status_code == 200:
                read_all_data = read_all_response.json()
                if read_all_data.get("status") == "success":
                    count = len(read_all_data.get("data", []))
                    results["tests"]["read_all"] = f"✅ PASS ({count} items)"
                    print(f"  ✅ READ ALL: Found {count} {entity_type}s")
                else:
                    results["tests"]["read_all"] = f"❌ FAIL: {read_all_data.get('message')}"
                    print(f"  ❌ READ ALL failed: {read_all_data.get('message')}")
            else:
                results["tests"]["read_all"] = f"❌ FAIL: HTTP {read_all_response.status_code}"
                print(f"  ❌ READ ALL failed: HTTP {read_all_response.status_code} - {read_all_response.text}")
        except Exception as e:
            results["tests"]["read_all"] = f"❌ FAIL: {str(e)}"
            print(f"  ❌ READ ALL error: {e}")

        # READ (Get Single)
        if created_id and "read_single" in endpoints:
            try:
                read_url = endpoints["read_single"]["url"].format(id=created_id)
                read_response = await self.client.get(read_url)
                if read_response.status_code == 200:
                    read_data = read_response.json()
                    if read_data.get("status") == "success":
                        results["tests"]["read_single"] = "✅ PASS"
                        print(f"  ✅ READ SINGLE: Retrieved {entity_type} with ID: {created_id}")
                    else:
                        results["tests"]["read_single"] = f"❌ FAIL: {read_data.get('message')}"
                        print(f"  ❌ READ SINGLE failed: {read_data.get('message')}")
                else:
                    results["tests"]["read_single"] = f"❌ FAIL: HTTP {read_response.status_code}"
                    print(f"  ❌ READ SINGLE failed: HTTP {read_response.status_code}")
            except Exception as e:
                results["tests"]["read_single"] = f"❌ FAIL: {str(e)}"
                print(f"  ❌ READ SINGLE error: {e}")

        # UPDATE
        if created_id and "update" in endpoints:
            try:
                update_url = endpoints["update"]["url"].format(id=created_id)
                update_response = await self.client.put(
                    update_url,
                    json=endpoints["update"]["data"]
                )
                if update_response.status_code == 200:
                    update_data = update_response.json()
                    if update_data.get("status") == "success":
                        results["tests"]["update"] = "✅ PASS"
                        print(f"  ✅ UPDATE: Updated {entity_type} with ID: {created_id}")
                    else:
                        results["tests"]["update"] = f"❌ FAIL: {update_data.get('message')}"
                        print(f"  ❌ UPDATE failed: {update_data.get('message')}")
                else:
                    results["tests"]["update"] = f"❌ FAIL: HTTP {update_response.status_code}"
                    print(f"  ❌ UPDATE failed: HTTP {update_response.status_code} - {update_response.text}")
            except Exception as e:
                results["tests"]["update"] = f"❌ FAIL: {str(e)}"
                print(f"  ❌ UPDATE error: {e}")

        # DELETE
        if created_id and "delete" in endpoints:
            try:
                delete_url = endpoints["delete"]["url"].format(id=created_id)
                delete_response = await self.client.delete(delete_url)
                if delete_response.status_code == 200:
                    delete_data = delete_response.json()
                    if delete_data.get("status") == "success":
                        results["tests"]["delete"] = "✅ PASS"
                        print(f"  ✅ DELETE: Deleted {entity_type} with ID: {created_id}")
                    else:
                        results["tests"]["delete"] = f"❌ FAIL: {delete_data.get('message')}"
                        print(f"  ❌ DELETE failed: {delete_data.get('message')}")
                else:
                    results["tests"]["delete"] = f"❌ FAIL: HTTP {delete_response.status_code}"
                    print(f"  ❌ DELETE failed: HTTP {delete_response.status_code}")
            except Exception as e:
                results["tests"]["delete"] = f"❌ FAIL: {str(e)}"
                print(f"  ❌ DELETE error: {e}")
        
        return results

    async def run_all_tests(self):
        """Run all CRUD tests"""
        print("\n🚀 Starting CRUD Operations Test Suite\n")
        
        # Login first
        if not await self.login():
            print("\n❌ Cannot proceed without authentication")
            return
        
        # Define test endpoints for each entity
        test_configs = {
            "Parts": {
                "create": {
                    "url": "/api/parts/add_part",
                    "data": {
                        "part_name": "Test Resistor 10K",
                        "part_number": "TEST-RES-10K",
                        "description": "Test 10K Ohm Resistor",
                        "quantity": 100,
                        "supplier": "Test Supplier"
                    }
                },
                "read_all": {"url": "/api/parts/get_all_parts?page=1&page_size=10"},
                "read_single": {"url": "/api/parts/get_part?part_id={id}"},
                "update": {
                    "url": "/api/parts/update_part/{id}",
                    "data": {
                        "quantity": 150,
                        "description": "Updated Test 10K Ohm Resistor"
                    }
                },
                "delete": {"url": "/api/parts/delete_part?part_id={id}"}
            },
            "Locations": {
                "create": {
                    "url": "/locations/add_location",
                    "data": {
                        "name": "Test Drawer A1",
                        "description": "Test storage drawer",
                        "location_type": "drawer"
                    }
                },
                "read_all": {"url": "/locations/get_all_locations"},
                "read_single": {"url": "/locations/get_location?location_id={id}"},
                "update": {
                    "url": "/locations/update_location/{id}",
                    "data": {
                        "description": "Updated test storage drawer"
                    }
                },
                "delete": {"url": "/locations/delete_location/{id}"}
            },
            "Categories": {
                "create": {
                    "url": "/categories/add_category",
                    "data": {
                        "name": "Test Resistors",
                        "description": "Test category for resistors"
                    }
                },
                "read_all": {"url": "/categories/get_all_categories"},
                "read_single": {"url": "/categories/get_category?category_id={id}"},
                "update": {
                    "url": "/categories/update_category/{id}",
                    "data": {
                        "description": "Updated test category for resistors"
                    }
                },
                "delete": {"url": "/categories/remove_category?cat_id={id}"}
            }
        }
        
        # Run tests for each entity type
        for entity_type, endpoints in test_configs.items():
            result = await self.test_crud(entity_type, endpoints)
            self.test_results.append(result)
        
        # Print summary
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        total_tests = 0
        passed_tests = 0
        
        for result in self.test_results:
            print(f"\n{result['entity']}:")
            for test_name, test_result in result['tests'].items():
                total_tests += 1
                if test_result.startswith("✅"):
                    passed_tests += 1
                print(f"  {test_name}: {test_result}")
        
        print(f"\n{'='*50}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%")
        print(f"{'='*50}\n")
        
        await self.client.aclose()
        
        # Return exit code based on test results
        return 0 if passed_tests == total_tests else 1


async def main():
    tester = CRUDTester()
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())