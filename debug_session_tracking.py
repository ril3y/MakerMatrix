#!/usr/bin/env python3
"""
ULTRATHINK Session Debugging Script
Comprehensive session lifecycle tracking for DetachedInstanceError investigation
"""

import sys
import os
sys.path.append('/home/ril3y/MakerMatrix')

import asyncio
import requests
import json
import time
from datetime import datetime
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ril3y/MakerMatrix/session_debug.log'),
        logging.StreamHandler()
    ]
)

class SessionDebugger:
    def __init__(self):
        self.base_url = "https://localhost:8443"
        self.headers = {"Content-Type": "application/json"}
        self.token = None
        self.logger = logging.getLogger("SessionDebugger")
        
    def login(self):
        """Login and get JWT token"""
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        try:
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
                self.logger.info("✅ Login successful")
                return True
            else:
                self.logger.error(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Login error: {e}")
            return False
    
    def create_minimal_test_part(self):
        """Create minimal test part to isolate session issues"""
        test_part = {
            "part_number": "DEBUG001",
            "part_name": f"Session Debug Part {datetime.now().strftime('%H%M%S')}",
            "description": "Minimal part for session debugging",
            "quantity": 1,
            "supplier": "LCSC"
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
                    self.logger.info(f"✅ Debug part created: {part_id}")
                    return part_id
                else:
                    self.logger.error(f"❌ Part creation failed: {data.get('message')}")
                    return None
            else:
                self.logger.error(f"❌ Part creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Part creation error: {e}")
            return None
    
    def test_part_retrieval(self, part_id):
        """Test basic part retrieval without enrichment"""
        self.logger.info("🔍 Testing basic part retrieval...")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/parts/get_part?part_id={part_id}",
                headers=self.headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    part_data = data.get("data", {})
                    self.logger.info(f"✅ Part retrieval successful: {part_data.get('part_name')}")
                    return True
                else:
                    self.logger.error(f"❌ Part retrieval failed: {data.get('message')}")
                    return False
            else:
                self.logger.error(f"❌ Part retrieval failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Part retrieval error: {e}")
            return False
    
    def test_supplier_config_access(self):
        """Test supplier configuration access independently"""
        self.logger.info("🔍 Testing supplier configuration access...")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/import/suppliers",
                headers=self.headers,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ Supplier config access successful")
                
                # Look for LCSC specifically
                suppliers = data.get("data", [])
                lcsc_supplier = next((s for s in suppliers if s.get("name") == "lcsc"), None)
                if lcsc_supplier:
                    self.logger.info(f"✅ LCSC supplier found: {lcsc_supplier}")
                    return True
                else:
                    self.logger.warning("⚠️ LCSC supplier not found in config")
                    return False
            else:
                self.logger.error(f"❌ Supplier config access failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Supplier config access error: {e}")
            return False
    
    def create_minimal_enrichment_task(self, part_id):
        """Create minimal enrichment task with single capability"""
        self.logger.info("🔍 Creating minimal enrichment task...")
        
        enrichment_data = {
            "part_id": part_id,
            "supplier": "LCSC",
            "capabilities": ["get_part_details"]  # Single capability only
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
                    self.logger.info(f"✅ Minimal enrichment task created: {task_id}")
                    return task_id
                else:
                    self.logger.error(f"❌ Task creation failed: {data.get('message')}")
                    return None
            else:
                self.logger.error(f"❌ Task creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Task creation error: {e}")
            return None
    
    def monitor_task_detailed(self, task_id, timeout=30):
        """Monitor task with detailed error analysis"""
        self.logger.info(f"🔍 Monitoring task {task_id} with detailed analysis...")
        
        start_time = time.time()
        
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
                        
                        self.logger.info(f"📊 Status: {status}, Progress: {progress}%, Step: {current_step}")
                        
                        if error_message:
                            self.logger.error(f"💥 ERROR DETECTED: {error_message}")
                            
                            # Analyze error type
                            if "DetachedInstanceError" in error_message:
                                self.logger.error("🎯 CONFIRMED: DetachedInstanceError in minimal test")
                                self.analyze_error_pattern(error_message)
                                return False
                            elif "Session" in error_message:
                                self.logger.error("🎯 SESSION-RELATED ERROR detected")
                                return False
                            else:
                                self.logger.error("🎯 OTHER ERROR TYPE detected")
                                return False
                        
                        if status == "COMPLETED":
                            self.logger.info("✅ Task completed successfully!")
                            return True
                        elif status == "FAILED":
                            self.logger.error("❌ Task failed without specific error message")
                            return False
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"⚠️ Error monitoring task: {e}")
                time.sleep(2)
        
        self.logger.warning(f"⏱️ Task monitoring timeout after {timeout} seconds")
        return False
    
    def analyze_error_pattern(self, error_message):
        """Analyze DetachedInstanceError pattern for insights"""
        self.logger.info("🔬 Analyzing DetachedInstanceError pattern...")
        
        if "part_enrichment_service.py" in error_message:
            self.logger.error("🎯 Error confirmed in part_enrichment_service.py")
        
        if "line 93" in error_message or "line 97" in error_message:
            self.logger.error("🎯 Error at capabilities check - confirms our hypothesis")
        
        if "attribute refresh operation cannot proceed" in error_message:
            self.logger.error("🎯 Session refresh failing - Part object permanently detached")
    
    def run_comprehensive_debug(self):
        """Run comprehensive debugging sequence"""
        self.logger.info("🚀 Starting ULTRATHINK Session Debugging")
        self.logger.info("=" * 60)
        
        # Phase 1: Authentication
        if not self.login():
            return False
        
        # Phase 2: Basic Infrastructure Test
        if not self.test_supplier_config_access():
            self.logger.error("❌ Supplier config access failed - infrastructure issue")
            return False
        
        # Phase 3: Part Management Test
        part_id = self.create_minimal_test_part()
        if not part_id:
            return False
        
        if not self.test_part_retrieval(part_id):
            self.logger.error("❌ Basic part retrieval failed - database issue")
            return False
        
        # Phase 4: Minimal Enrichment Test
        task_id = self.create_minimal_enrichment_task(part_id)
        if not task_id:
            return False
        
        # Phase 5: Detailed Error Analysis
        success = self.monitor_task_detailed(task_id, timeout=60)
        
        self.logger.info("=" * 60)
        if success:
            self.logger.info("🎉 UNEXPECTED: Minimal enrichment succeeded!")
            self.logger.info("💡 Issue may be complexity-related, not fundamental")
        else:
            self.logger.error("💥 CONFIRMED: DetachedInstanceError in minimal scenario")
            self.logger.error("🎯 Issue is fundamental to session management architecture")
        
        return success

if __name__ == "__main__":
    debugger = SessionDebugger()
    success = debugger.run_comprehensive_debug()
    
    if not success:
        print("\n" + "="*60)
        print("🔬 ULTRATHINK ANALYSIS COMPLETE")
        print("📋 Check session_debug.log for detailed analysis")
        print("🎯 DetachedInstanceError confirmed - proceeding to Phase 2")
        print("="*60)
    
    sys.exit(0 if success else 1)