#!/usr/bin/env python3
"""
Frontend Integration Test for Dynamic Supplier Capability Detection

This script helps verify that the frontend properly integrates with our
dynamic supplier capability detection system.
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FrontendIntegrationTester:
    def __init__(self):
        self.driver = None
        self.base_url = "https://localhost:5173"
        
    def setup_driver(self):
        """Setup Chrome driver for testing."""
        chrome_options = Options()
        chrome_options.add_argument('--ignore-ssl-errors-morph-targets')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            print(f"❌ Could not setup Chrome driver: {e}")
            print("Please ensure Chrome/Chromium is installed")
            return False
    
    def login(self):
        """Login to the application."""
        print("🔐 Logging into MakerMatrix...")
        
        try:
            self.driver.get(f"{self.base_url}/login")
            
            # Wait for login form
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Fill login form
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys("admin")
            password_field.send_keys("Admin123!")
            
            # Submit form
            login_button = self.driver.find_element(By.TYPE, "submit")
            login_button.click()
            
            # Wait for redirect to dashboard
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/dashboard")
            )
            
            print("✅ Login successful")
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    def navigate_to_import(self):
        """Navigate to the import page."""
        print("📁 Navigating to import page...")
        
        try:
            # Look for import link in navigation
            import_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Import"))
            )
            import_link.click()
            
            # Wait for import page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "input[type='file']"))
            )
            
            print("✅ Import page loaded")
            return True
            
        except Exception as e:
            print(f"❌ Failed to navigate to import: {e}")
            return False
    
    def test_supplier_dropdown(self):
        """Test that suppliers are loaded dynamically."""
        print("🧪 Testing supplier dropdown...")
        
        try:
            # First upload a file to trigger supplier detection
            self.upload_test_file()
            
            # Wait for supplier dropdown to appear
            supplier_dropdown = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )
            
            # Get all options
            options = supplier_dropdown.find_elements(By.TAG_NAME, "option")
            suppliers = [opt.text for opt in options if opt.text.strip()]
            
            print(f"✅ Found {len(suppliers)} suppliers in dropdown:")
            for supplier in suppliers:
                print(f"  📦 {supplier}")
            
            # Check for LCSC specifically
            lcsc_found = any("LCSC" in supplier for supplier in suppliers)
            if lcsc_found:
                print("✅ LCSC supplier found in dropdown")
                return True
            else:
                print("⚠️  LCSC supplier not found")
                return False
                
        except Exception as e:
            print(f"❌ Error testing supplier dropdown: {e}")
            return False
    
    def test_enrichment_capabilities_ui(self):
        """Test that enrichment capabilities UI appears."""
        print("🧪 Testing enrichment capabilities UI...")
        
        try:
            # Select LCSC supplier
            supplier_dropdown = self.driver.find_element(By.TAG_NAME, "select")
            lcsc_option = None
            
            for option in supplier_dropdown.find_elements(By.TAG_NAME, "option"):
                if "LCSC" in option.text:
                    lcsc_option = option
                    break
            
            if not lcsc_option:
                print("❌ LCSC option not found")
                return False
            
            lcsc_option.click()
            time.sleep(2)  # Wait for UI to update
            
            # Look for enrichment capabilities section
            try:
                enrichment_section = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Enrichment Capabilities Available')]"))
                )
                print("✅ Enrichment capabilities section found")
                
                # Look for capability checkboxes
                checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                capability_checkboxes = []
                
                for checkbox in checkboxes:
                    # Get the label text associated with this checkbox
                    try:
                        label = checkbox.find_element(By.XPATH, "following-sibling::*")
                        capability_checkboxes.append(label.text)
                    except:
                        pass
                
                if capability_checkboxes:
                    print(f"✅ Found {len(capability_checkboxes)} enrichment capabilities:")
                    for cap in capability_checkboxes:
                        print(f"  ⚡ {cap}")
                    return True
                else:
                    print("⚠️  No capability checkboxes found")
                    return False
                    
            except Exception as e:
                print("⚠️  Enrichment capabilities section not found")
                print("   This might mean LCSC is not configured or doesn't have enrichment capabilities")
                return False
                
        except Exception as e:
            print(f"❌ Error testing enrichment UI: {e}")
            return False
    
    def upload_test_file(self):
        """Upload a test CSV file."""
        print("📤 Uploading test file...")
        
        # Create test CSV content
        test_csv = """LCSC Part Number,Order Qty.,Unit Price($),Order Price($),Manufacturer,Manufacturer Part Number,Package,Description
C15849,1,0.05,0.05,YAGEO,CC0805KRX7R9BB103,0805,CAP CER 10UF 25V X7R 0805
C49678,2,0.03,0.06,YAGEO,CC0805KRX7R9BB104,0805,CAP CER 100NF 50V X7R 0805
"""
        
        # Write to temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_csv)
            temp_file = f.name
        
        try:
            # Find file input
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(temp_file)
            
            time.sleep(3)  # Wait for file processing
            print("✅ Test file uploaded")
            return True
            
        except Exception as e:
            print(f"❌ Failed to upload file: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def test_import_flow(self):
        """Test the complete import flow with enrichment."""
        print("🧪 Testing complete import flow...")
        
        try:
            # Select enrichment capabilities
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            if checkboxes:
                # Select first two capabilities
                for i, checkbox in enumerate(checkboxes[:2]):
                    if not checkbox.is_selected():
                        checkbox.click()
                        print(f"✅ Selected enrichment capability {i+1}")
            
            # Find and click import button
            import_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Import')]"))
            )
            import_button.click()
            
            # Wait for import to complete
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Import successful') or contains(text(), 'parts imported')]"))
            )
            
            print("✅ Import completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Import flow failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all frontend integration tests."""
        print("🚀 Frontend Integration Test Suite")
        print("=" * 50)
        
        if not self.setup_driver():
            return False
        
        try:
            tests = [
                ("Login", self.login),
                ("Navigate to Import", self.navigate_to_import),
                ("Supplier Dropdown", self.test_supplier_dropdown),
                ("Enrichment Capabilities UI", self.test_enrichment_capabilities_ui),
                ("Complete Import Flow", self.test_import_flow),
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
                    
                    if not result:
                        # Take screenshot on failure
                        screenshot_name = f"failure_{test_name.lower().replace(' ', '_')}.png"
                        self.driver.save_screenshot(screenshot_name)
                        print(f"📸 Screenshot saved: {screenshot_name}")
                        
                except Exception as e:
                    print(f"❌ EXCEPTION: {e}")
                    results.append((test_name, False))
            
            # Summary
            print(f"\n{'='*50}")
            print("📊 FRONTEND TEST RESULTS")
            print("=" * 50)
            
            passed = 0
            for i, (test_name, result) in enumerate(results):
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{i+1}. {test_name}: {status}")
                if result:
                    passed += 1
            
            total = len(results)
            print(f"\n🎯 Frontend Tests: {passed}/{total} passed")
            
            if passed == total:
                print("\n🎉 All frontend tests passed!")
                print("✨ Dynamic supplier capability detection is working in the UI!")
                return True
            else:
                print("\n⚠️  Some frontend tests failed.")
                return False
                
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Main function."""
    print("🧪 MakerMatrix Frontend Integration Test")
    print("This will test the UI integration of dynamic supplier capability detection")
    print()
    
    tester = FrontendIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ Frontend integration is working correctly!")
    else:
        print("\n💥 Frontend integration has issues.")
    
    return success


if __name__ == "__main__":
    try:
        import sys
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        print("Note: This test requires Chrome/Chromium browser and selenium")
        print("Install with: pip install selenium")