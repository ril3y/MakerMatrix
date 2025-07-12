#!/usr/bin/env python3
"""
Test session threading fix for LCSC enrichment.
This script tests that the DetachedInstanceError is resolved with the session threading pattern.
"""

import sys
import os
sys.path.append('/home/ril3y/MakerMatrix')

import asyncio
import requests
import json
import time
from datetime import datetime

class SessionThreadingTester:
    def __init__(self):
        self.base_url = "https://localhost:8443"
        self.headers = {"Content-Type": "application/json"}
        self.token = None
        
    def login(self):
        """Login and get JWT token"""
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        try:
            # Use the correct API endpoint with form data
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.headers["Authorization"] = f"Bearer {self.token}"
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def create_test_part(self):
        """Create a test part for enrichment"""
        test_part = {
            "part_number": "C123456",
            "part_name": f"Test LCSC Part {datetime.now().strftime('%H%M%S')}",
            "description": "Test resistor for session threading validation",
            "quantity": 10,
            "supplier": "LCSC",
            "category_names": ["Resistors"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/parts/add_part",
                json=test_part,
                headers=self.headers,
                verify=False
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get("status") == "success":
                    part_data = data.get("data", {})
                    part_id = part_data.get("id")
                    print(f"✅ Test part created: {part_id}")
                    return part_id
                else:
                    print(f"❌ Part creation failed: {data.get('message')}")
                    return None
            else:
                print(f"❌ Part creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Part creation error: {e}")
            return None
    
    def create_enrichment_task(self, part_id):
        """Create LCSC enrichment task"""
        enrichment_data = {
            "part_id": part_id,
            "supplier": "LCSC",
            "capabilities": ["get_part_details", "fetch_datasheet"]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/tasks/quick/part_enrichment",
                json=enrichment_data,
                headers=self.headers,
                verify=False
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get("status") == "success":
                    task_data = data.get("data", {})
                    task_id = task_data.get("id")
                    print(f"✅ Enrichment task created: {task_id}")
                    return task_id
                else:
                    print(f"❌ Task creation failed: {data.get('message')}")
                    return None
            else:
                print(f"❌ Task creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Task creation error: {e}")
            return None
    
    def monitor_task(self, task_id, timeout=60):
        """Monitor task progress and check for DetachedInstanceError"""
        print(f"🔍 Monitoring task {task_id} for {timeout} seconds...")
        
        start_time = time.time()
        last_status = None
        last_progress = None
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/api/tasks/{task_id}",
                    headers=self.headers,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        task_data = data.get("data", {})
                        status = task_data.get("status")
                        progress = task_data.get("progress_percentage", 0)
                        current_step = task_data.get("current_step", "")
                        error_message = task_data.get("error_message", "")
                        
                        # Only print if status or progress changed
                        if status != last_status or progress != last_progress:
                            print(f"📊 Status: {status}, Progress: {progress}%, Step: {current_step}")
                            last_status = status
                            last_progress = progress
                        
                        # Check for DetachedInstanceError
                        if error_message and "DetachedInstanceError" in error_message:
                            print(f"❌ FAILED: DetachedInstanceError still occurring!")
                            print(f"Error: {error_message}")
                            return False
                        
                        # Check if task completed
                        if status == "COMPLETED":
                            print(f"✅ SUCCESS: Task completed without DetachedInstanceError!")
                            result_data = task_data.get("result_data")
                            if result_data:
                                print(f"📄 Result: {json.dumps(result_data, indent=2)}")
                            return True
                        elif status == "FAILED":
                            print(f"❌ Task failed: {error_message}")
                            return False
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"⚠️ Error monitoring task: {e}")
                time.sleep(2)
        
        print(f"⏱️ Timeout: Task monitoring expired after {timeout} seconds")
        return False
    
    def run_test(self):
        """Run the complete session threading test"""
        print("🧪 Starting Session Threading Fix Test")
        print("=" * 50)
        
        # Step 1: Login
        if not self.login():
            return False
        
        # Step 2: Create test part
        part_id = self.create_test_part()
        if not part_id:
            return False
        
        # Step 3: Create enrichment task
        task_id = self.create_enrichment_task(part_id)
        if not task_id:
            return False
        
        # Step 4: Monitor task for DetachedInstanceError
        success = self.monitor_task(task_id, timeout=120)
        
        print("=" * 50)
        if success:
            print("🎉 Session threading fix validation: SUCCESS")
            print("✅ No DetachedInstanceError detected")
            print("✅ LCSC enrichment completed successfully")
        else:
            print("💥 Session threading fix validation: FAILED")
            print("❌ DetachedInstanceError may still be occurring")
        
        return success

if __name__ == "__main__":
    tester = SessionThreadingTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)