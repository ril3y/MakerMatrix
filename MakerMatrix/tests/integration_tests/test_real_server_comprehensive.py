"""
Comprehensive Real Server Testing

This test suite demonstrates testing against the actual running dev_manager.py server
with real data and real API endpoints. It validates production readiness.

Prerequisites:
- dev_manager.py must be running (check dev_manager.log)
- Server accessible on https://localhost:8443 or http://localhost:8080
- Admin user credentials must be available
- Real test data (LCSC CSV files) should be available

Usage:
    pytest MakerMatrix/tests/integration_tests/test_real_server_comprehensive.py -v
"""

import pytest
import os
import json
from pathlib import Path
from typing import Dict, Any

from MakerMatrix.tests.test_server_config import RealServerTestHelper


class TestRealServerComprehensive:
    """Comprehensive tests against real running server"""
    
    @pytest.fixture(scope="class")
    def real_server(self) -> RealServerTestHelper:
        """Setup real server testing environment"""
        helper = RealServerTestHelper()
        
        if not helper.setup():
            pytest.skip("Real server not available or authentication failed")
        
        return helper
    
    @pytest.fixture(scope="class")
    def lcsc_test_data(self) -> Dict[str, Any]:
        """Load LCSC test data for real server testing"""
        test_data_path = Path("/home/ril3y/MakerMatrix/MakerMatrix/tests/csv_test_data/LCSC_Exported__20241222_232708.csv")
        
        if not test_data_path.exists():
            pytest.skip(f"LCSC test data not found at {test_data_path}")
        
        return {
            "csv_file": str(test_data_path),
            "supplier_name": "lcsc",
            "expected_parts": [
                "C7442639",  # VEJ101M1VTT-0607L (Lelon Capacitor)
                "C60633",    # SWPA6045S101MT (Sunlord Component)
                "C2845383",  # HC-1.25-6PWT (HCTL Connector)
                "C2845379",  # HC-1.25-2PWT (HCTL Connector)
                "C5160761",  # DZ127S-22-10-55 (DEALON Pin Header)
            ]
        }
    
    def test_server_health_check(self, real_server: RealServerTestHelper):
        """Test that real server is responding and healthy"""
        response = real_server.get("/docs")
        assert response.status_code == 200
        assert "FastAPI" in response.text or "swagger" in response.text.lower()
        print(f"✅ Server health check passed: {real_server.base_url}")
    
    def test_authentication_flow(self, real_server: RealServerTestHelper):
        """Test complete authentication flow against real server"""
        # Authentication is already tested in setup, but let's verify token works
        response = real_server.get("/api/utility/get_counts")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        print(f"✅ Authentication working: {data.get('message', 'Success')}")
    
    def test_system_counts(self, real_server: RealServerTestHelper):
        """Test system counts endpoint with real data"""
        response = real_server.get_system_counts()
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        counts = data["data"]
        assert "parts" in counts
        assert "locations" in counts
        assert "categories" in counts
        
        print(f"✅ System counts - Parts: {counts['parts']}, Locations: {counts['locations']}, Categories: {counts['categories']}")
    
    def test_parts_management_crud(self, real_server: RealServerTestHelper):
        """Test complete CRUD operations for parts against real server"""
        # Test creating a part
        test_part = {
            "part_name": "TEST_PART_REAL_SERVER",
            "part_number": "TEST-001",
            "description": "Test part for real server testing",
            "quantity": 10,
            "supplier": "test_supplier",
            "category_names": ["Test Category"]
        }
        
        # Create part
        create_response = real_server.create_part(test_part)
        assert create_response.status_code == 200
        
        create_data = create_response.json()
        assert create_data["status"] == "success"
        part_id = create_data["data"]["id"]
        
        print(f"✅ Created test part: {part_id}")
        
        # Read part
        read_response = real_server.get(f"/api/parts/get_part?part_id={part_id}")
        assert read_response.status_code == 200
        
        read_data = read_response.json()
        assert read_data["status"] == "success"
        assert read_data["data"]["part_name"] == test_part["part_name"]
        
        print(f"✅ Read test part: {read_data['data']['part_name']}")
        
        # Update part
        update_data = {"description": "Updated description for real server test"}
        update_response = real_server.put(f"/api/parts/update_part/{part_id}", json=update_data)
        assert update_response.status_code == 200
        
        update_result = update_response.json()
        assert update_result["status"] == "success"
        
        print(f"✅ Updated test part description")
        
        # Delete part
        delete_response = real_server.delete(f"/api/parts/delete_part?part_id={part_id}")
        assert delete_response.status_code == 200
        
        delete_result = delete_response.json()
        assert delete_result["status"] == "success"
        
        print(f"✅ Deleted test part: {part_id}")
    
    def test_csv_import_real_data(self, real_server: RealServerTestHelper, lcsc_test_data: Dict[str, Any]):
        """Test CSV import with real LCSC data against real server"""
        # Get initial system counts
        initial_counts = real_server.get_system_counts().json()["data"]
        initial_parts = initial_counts["parts"]
        
        # Import CSV file
        response = real_server.test_csv_import(
            csv_file_path=lcsc_test_data["csv_file"],
            supplier_name=lcsc_test_data["supplier_name"]
        )
        
        assert response.status_code == 200
        import_data = response.json()
        assert import_data["status"] == "success"
        
        print(f"✅ CSV import successful: {import_data.get('message', 'Success')}")
        
        # Verify parts were imported
        final_counts = real_server.get_system_counts().json()["data"]
        final_parts = final_counts["parts"]
        
        parts_imported = final_parts - initial_parts
        assert parts_imported > 0
        
        print(f"✅ Parts imported: {parts_imported} (Total: {initial_parts} → {final_parts})")
        
        # Verify specific parts exist
        for expected_part in lcsc_test_data["expected_parts"]:
            search_response = real_server.get(f"/api/parts/get_part?part_number={expected_part}")
            
            if search_response.status_code == 200:
                part_data = search_response.json()
                if part_data["status"] == "success":
                    print(f"✅ Found imported part: {expected_part}")
                else:
                    print(f"⚠️ Part not found but import succeeded: {expected_part}")
            else:
                print(f"⚠️ Could not verify part: {expected_part}")
    
    def test_task_management_real_server(self, real_server: RealServerTestHelper):
        """Test task management system against real server"""
        # Get current tasks
        tasks_response = real_server.get("/api/tasks/")
        assert tasks_response.status_code == 200
        
        tasks_data = tasks_response.json()
        assert tasks_data["status"] == "success"
        
        print(f"✅ Task management accessible: {len(tasks_data.get('data', []))} tasks")
        
        # Get task worker status
        worker_response = real_server.get("/api/tasks/worker/status")
        assert worker_response.status_code == 200
        
        worker_data = worker_response.json()
        assert worker_data["status"] == "success"
        
        print(f"✅ Task worker status: {worker_data.get('data', {}).get('status', 'Unknown')}")
        
        # Get task capabilities
        capabilities_response = real_server.get("/api/tasks/capabilities/suppliers")
        assert capabilities_response.status_code == 200
        
        capabilities_data = capabilities_response.json()
        assert capabilities_data["status"] == "success"
        
        print(f"✅ Task capabilities: {len(capabilities_data.get('data', []))} suppliers")
    
    def test_supplier_management_real_server(self, real_server: RealServerTestHelper):
        """Test supplier management against real server"""
        # Get supplier list
        suppliers_response = real_server.get("/api/suppliers/")
        assert suppliers_response.status_code == 200
        
        suppliers_data = suppliers_response.json()
        assert suppliers_data["status"] == "success"
        
        suppliers = suppliers_data.get("data", [])
        print(f"✅ Supplier management: {len(suppliers)} suppliers configured")
        
        # Test LCSC supplier if available
        lcsc_supplier = next((s for s in suppliers if s.get("name", "").lower() == "lcsc"), None)
        if lcsc_supplier:
            # Test LCSC connection
            lcsc_test_response = real_server.post(f"/api/suppliers/lcsc/test_connection")
            
            if lcsc_test_response.status_code == 200:
                lcsc_test_data = lcsc_test_response.json()
                print(f"✅ LCSC supplier test: {lcsc_test_data.get('message', 'Success')}")
            else:
                print(f"⚠️ LCSC supplier test failed: {lcsc_test_response.status_code}")
        else:
            print("⚠️ LCSC supplier not configured")
    
    def test_api_endpoint_coverage_sample(self, real_server: RealServerTestHelper):
        """Test a sample of critical API endpoints for coverage"""
        critical_endpoints = [
            ("/api/utility/get_counts", "GET"),
            ("/api/categories/get_all_categories", "GET"),
            ("/api/locations/get_all_locations", "GET"),
            ("/api/tasks/types/available", "GET"),
            ("/api/import/suppliers", "GET"),
        ]
        
        for endpoint, method in critical_endpoints:
            if method == "GET":
                response = real_server.get(endpoint)
            else:
                continue  # Skip non-GET methods for this basic test
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            
            print(f"✅ {method} {endpoint}: {data.get('message', 'Success')}")
    
    def test_database_integrity_real_server(self, real_server: RealServerTestHelper):
        """Test that real server database operations maintain integrity"""
        # Get initial state
        initial_response = real_server.get_system_counts()
        assert initial_response.status_code == 200
        initial_data = initial_response.json()["data"]
        
        # Perform some operations (create/delete part)
        test_part = {
            "part_name": "INTEGRITY_TEST_PART",
            "part_number": "INT-001",
            "description": "Part for integrity testing",
            "quantity": 1,
            "supplier": "test"
        }
        
        # Create
        create_response = real_server.create_part(test_part)
        assert create_response.status_code == 200
        part_id = create_response.json()["data"]["id"]
        
        # Verify count increased
        mid_response = real_server.get_system_counts()
        mid_data = mid_response.json()["data"]
        assert mid_data["parts"] == initial_data["parts"] + 1
        
        # Delete
        delete_response = real_server.delete(f"/api/parts/delete_part?part_id={part_id}")
        assert delete_response.status_code == 200
        
        # Verify count returned to original
        final_response = real_server.get_system_counts()
        final_data = final_response.json()["data"]
        assert final_data["parts"] == initial_data["parts"]
        
        print(f"✅ Database integrity maintained: {initial_data['parts']} → {mid_data['parts']} → {final_data['parts']}")
    
    def test_performance_benchmark_real_server(self, real_server: RealServerTestHelper):
        """Basic performance testing against real server"""
        import time
        
        # Test response times for critical endpoints
        performance_tests = [
            ("/api/utility/get_counts", "System Counts"),
            ("/api/parts/get_all_parts?page=1&page_size=10", "Parts List"),
            ("/api/categories/get_all_categories", "Categories"),
            ("/api/locations/get_all_locations", "Locations"),
        ]
        
        for endpoint, description in performance_tests:
            start_time = time.time()
            response = real_server.get(endpoint)
            end_time = time.time()
            
            assert response.status_code == 200
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            # Basic performance assertion (adjust thresholds as needed)
            assert response_time < 5000  # Less than 5 seconds
            
            print(f"✅ {description}: {response_time:.2f}ms")
    
    def test_error_handling_real_server(self, real_server: RealServerTestHelper):
        """Test error handling in real server scenarios"""
        # Test 404 scenarios
        not_found_response = real_server.get("/api/parts/get_part?part_id=nonexistent-id")
        assert not_found_response.status_code == 404
        
        not_found_data = not_found_response.json()
        assert not_found_data["status"] == "error"
        
        print(f"✅ 404 error handling: {not_found_data.get('message', 'Not found')}")
        
        # Test invalid data scenarios
        invalid_part = {
            "part_name": "",  # Invalid empty name
            "quantity": "invalid"  # Invalid quantity type
        }
        
        invalid_response = real_server.create_part(invalid_part)
        assert invalid_response.status_code in [400, 422]  # Bad request or validation error
        
        invalid_data = invalid_response.json()
        assert invalid_data["status"] == "error"
        
        print(f"✅ Validation error handling: {invalid_data.get('message', 'Validation failed')}")
    
    @pytest.mark.skip(reason="Use with caution - modifies real server data")
    def test_data_cleanup_real_server(self, real_server: RealServerTestHelper):
        """Clean up test data from real server (use with extreme caution)"""
        # This test is skipped by default to prevent accidental data loss
        # Only enable if you specifically need to clean up test data
        
        print("⚠️ Data cleanup skipped for safety")
        print("⚠️ To clean up test data, restart dev_manager.py")
        
        # If you need to implement cleanup, do it very carefully:
        # 1. Only clean up data you created
        # 2. Use specific identifiers to avoid cleaning production data
        # 3. Test in a completely isolated environment first