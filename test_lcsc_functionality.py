#!/usr/bin/env python3
"""
LCSC Supplier Functionality Test Script

Tests the complete LCSC supplier integration end-to-end:
1. Authentication with backend API
2. LCSC supplier configuration and info
3. LCSC CSV import functionality
4. LCSC enrichment capabilities
5. Route validation
"""

import requests
import json
import os
import time
from pathlib import Path

# Configuration
BASE_URL = "https://localhost:8443"
ADMIN_CREDS = {"username": "admin", "password": "Admin123!"}

# Test data
SAMPLE_LCSC_CSV = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C7442639,VEJ101M1VTT-0607L,Lelon,,"SMD,D6.3xL7.7mm","100uF 35V ±20% SMD,D6.3xL7.7mm Aluminum Electrolytic Capacitors - SMD ROHS",YES,50,5\\5,0.0874,4.37
C60633,SWPA6045S101MT,Sunlord,,-,-,-,50,-\\-,0.0715,3.58"""

class LCSCTester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        self.session.verify = False  # For self-signed certificates
        requests.packages.urllib3.disable_warnings()
        
    def authenticate(self):
        """Get authentication token"""
        print("🔐 Authenticating with backend...")
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            data=ADMIN_CREDS
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False
    
    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_lcsc_supplier_info(self):
        """Test LCSC supplier information endpoint"""
        print("\n📋 Testing LCSC supplier info...")
        
        response = self.session.get(
            f"{BASE_URL}/api/suppliers/lcsc/info",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                supplier_info = data.get("data", {})
                print(f"✅ LCSC supplier info retrieved:")
                print(f"   Name: {supplier_info.get('name')}")
                print(f"   Display Name: {supplier_info.get('display_name')}")
                print(f"   Description: {supplier_info.get('description')}")
                return True
            else:
                print(f"❌ LCSC supplier info failed: {data}")
                return False
        else:
            print(f"❌ LCSC supplier info request failed: {response.status_code} - {response.text}")
            return False
    
    def test_lcsc_capabilities(self):
        """Test LCSC capabilities endpoint"""
        print("\n🎯 Testing LCSC capabilities...")
        
        response = self.session.get(
            f"{BASE_URL}/api/suppliers/lcsc/capabilities",
            headers=self.get_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                capabilities = data.get("data", [])
                print(f"✅ LCSC capabilities retrieved:")
                for cap in capabilities:
                    print(f"   - {cap}")
                return True
            else:
                print(f"❌ LCSC capabilities failed: {data}")
                return False
        else:
            print(f"❌ LCSC capabilities request failed: {response.status_code} - {response.text}")
            return False
    
    def test_lcsc_connection(self):
        """Test LCSC connection test"""
        print("\n🔌 Testing LCSC connection...")
        
        response = self.session.post(
            f"{BASE_URL}/api/suppliers/lcsc/test-connection",
            headers=self.get_headers(),
            json={}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                connection_result = data.get("data", {})
                print(f"✅ LCSC connection test successful:")
                print(f"   Success: {connection_result.get('success')}")
                print(f"   Message: {connection_result.get('message')}")
                return True
            else:
                print(f"❌ LCSC connection test failed: {data}")
                return False
        else:
            print(f"❌ LCSC connection test request failed: {response.status_code} - {response.text}")
            return False
    
    def test_lcsc_csv_import(self):
        """Test LCSC CSV import functionality"""
        print("\n📁 Testing LCSC CSV import...")
        
        # Create CSV file
        csv_file = BytesIO(SAMPLE_LCSC_CSV.encode('utf-8'))
        csv_file.name = 'test_lcsc.csv'
        
        files = {
            'file': ('test_lcsc.csv', csv_file, 'text/csv')
        }
        data = {
            'supplier_name': 'lcsc',
            'order_number': 'TEST-LCSC-001',
            'notes': 'LCSC functionality test import'
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/import/file",
            headers=self.get_headers(),
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                import_result = data.get("data", {})
                print(f"✅ LCSC CSV import successful:")
                print(f"   Imported: {import_result.get('imported_count', 0)} parts")
                print(f"   Failed: {import_result.get('failed_count', 0)} parts")
                return True
            else:
                print(f"❌ LCSC CSV import failed: {data}")
                return False
        else:
            print(f"❌ LCSC CSV import request failed: {response.status_code} - {response.text}")
            return False
    
    def test_lcsc_enrichment_task(self):
        """Test LCSC enrichment task creation"""
        print("\n⚡ Testing LCSC enrichment task creation...")
        
        # First, get a part to enrich
        response = self.session.get(
            f"{BASE_URL}/api/parts/get_all_parts?page=1&page_size=1",
            headers=self.get_headers()
        )
        
        if response.status_code != 200:
            print(f"❌ Could not get parts for enrichment test: {response.status_code}")
            return False
        
        parts_data = response.json()
        if not parts_data.get("data") or len(parts_data["data"]) == 0:
            print("⚠️  No parts available for enrichment test")
            return True
        
        part = parts_data["data"][0]
        part_id = part.get("id")
        
        # Create enrichment task
        task_data = {
            "part_id": part_id,
            "supplier": "lcsc",
            "capabilities": ["get_part_details", "fetch_datasheet"]
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/tasks/quick/part_enrichment",
            headers=self.get_headers(),
            json=task_data
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            if data.get("status") == "success":
                task_info = data.get("data", {})
                print(f"✅ LCSC enrichment task created:")
                print(f"   Task ID: {task_info.get('id')}")
                print(f"   Task Type: {task_info.get('task_type')}")
                print(f"   Status: {task_info.get('status')}")
                return True
            else:
                print(f"❌ LCSC enrichment task creation failed: {data}")
                return False
        else:
            print(f"❌ LCSC enrichment task request failed: {response.status_code} - {response.text}")
            return False
    
    def test_supplier_routes(self):
        """Test key supplier-related routes"""
        print("\n🛣️  Testing supplier routes...")
        
        routes_to_test = [
            ("GET", "/api/suppliers"),
            ("GET", "/api/suppliers/lcsc/info"),
            ("GET", "/api/suppliers/lcsc/capabilities"),
            ("GET", "/api/suppliers/lcsc/configuration-options"),
            ("GET", "/api/import/suppliers"),
        ]
        
        results = []
        for method, route in routes_to_test:
            print(f"   Testing {method} {route}")
            
            if method == "GET":
                response = self.session.get(f"{BASE_URL}{route}", headers=self.get_headers())
            else:
                response = self.session.post(f"{BASE_URL}{route}", headers=self.get_headers(), json={})
            
            success = response.status_code in [200, 201]
            status = "✅" if success else "❌"
            print(f"     {status} {response.status_code}")
            
            results.append(success)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Route test results: {success_rate:.1f}% success rate ({sum(results)}/{len(results)} routes passing)")
        
        return success_rate >= 80  # 80% success rate threshold
    
    def run_all_tests(self):
        """Run all LCSC functionality tests"""
        print("🚀 Starting LCSC Supplier Functionality Tests")
        print("=" * 60)
        
        tests = [
            ("Authentication", self.authenticate),
            ("LCSC Supplier Info", self.test_lcsc_supplier_info),
            ("LCSC Capabilities", self.test_lcsc_capabilities),
            ("LCSC Connection Test", self.test_lcsc_connection),
            ("LCSC CSV Import", self.test_lcsc_csv_import),
            ("LCSC Enrichment Task", self.test_lcsc_enrichment_task),
            ("Supplier Routes", self.test_supplier_routes),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
            if result:
                passed += 1
        
        success_rate = passed / len(results) * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}% ({passed}/{len(results)} tests passed)")
        
        if success_rate >= 80:
            print("🎉 LCSC supplier functionality is working correctly!")
            return True
        else:
            print("⚠️  LCSC supplier functionality has issues that need attention.")
            return False

if __name__ == "__main__":
    from io import BytesIO
    
    tester = LCSCTester()
    success = tester.run_all_tests()
    
    exit(0 if success else 1)