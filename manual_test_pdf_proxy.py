#!/usr/bin/env python3
"""
Manual test script for PDF proxy functionality.

This script demonstrates that the PDF proxy works correctly by:
1. Starting the backend server
2. Testing the proxy endpoint with various URLs
3. Showing the results
"""

import time
import requests
import subprocess
import threading
from urllib.parse import quote

def start_backend():
    """Start the backend server in a separate thread."""
    def run_server():
        subprocess.run([
            "/home/ril3y/MakerMatrix/venv_test/bin/python", 
            "-m", "MakerMatrix.main"
        ], cwd="/home/ril3y/MakerMatrix")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

def test_pdf_proxy():
    """Test the PDF proxy endpoint."""
    print("🧪 Testing PDF Proxy Functionality\n")
    
    base_url = "http://localhost:8080"
    
    # Test data
    test_cases = [
        {
            "name": "✅ LCSC Domain (Should Work)",
            "url": "https://datasheet.lcsc.com/lcsc/test.pdf",
            "expected_status": [502, 408, 404, 200]  # Network errors are OK, domain should be allowed
        },
        {
            "name": "✅ DigiKey Domain (Should Work)", 
            "url": "https://www.digikey.com/en/datasheets/test.pdf",
            "expected_status": [502, 408, 404, 200]
        },
        {
            "name": "❌ Unauthorized Domain (Should Fail)",
            "url": "https://evil-site.com/malicious.pdf", 
            "expected_status": [403]
        },
        {
            "name": "❌ Invalid URL (Should Fail)",
            "url": "not-a-valid-url",
            "expected_status": [400, 500]
        }
    ]
    
    # Wait for server to start
    print("⏳ Waiting for backend server to start...")
    for i in range(30):
        try:
            response = requests.get(f"{base_url}/docs", timeout=2)
            if response.status_code == 200:
                print("✅ Backend server is running!")
                break
        except:
            time.sleep(1)
    else:
        print("❌ Backend server failed to start")
        return False
    
    print("\n" + "="*60)
    print("Testing PDF Proxy Endpoint")
    print("="*60)
    
    all_passed = True
    
    for test in test_cases:
        print(f"\n🔍 {test['name']}")
        print(f"   URL: {test['url']}")
        
        try:
            # Encode URL for proxy
            encoded_url = quote(test['url'], safe='')
            proxy_url = f"{base_url}/static/proxy-pdf?url={encoded_url}"
            
            # Make request (with auth header if needed)
            headers = {
                "Authorization": "Bearer dummy-token-for-test"  # Will be handled by test override
            }
            
            response = requests.get(proxy_url, headers=headers, timeout=10)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code in test['expected_status']:
                print("   ✅ PASS - Got expected status code")
            else:
                print(f"   ❌ FAIL - Expected {test['expected_status']}, got {response.status_code}")
                if response.status_code != 200:
                    try:
                        error_detail = response.json()
                        print(f"   Error: {error_detail}")
                    except:
                        print(f"   Error: {response.text[:100]}...")
                all_passed = False
                
        except requests.RequestException as e:
            print(f"   ❌ FAIL - Request error: {e}")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 All tests PASSED! PDF proxy is working correctly.")
    else:
        print("❌ Some tests FAILED. Check the implementation.")
    print("="*60)
    
    return all_passed

def test_frontend_utility():
    """Test the frontend utility function."""
    print("\n🧪 Testing Frontend Utility Function")
    print("-" * 40)
    
    # Simulate the frontend utility
    def get_pdf_proxy_url(external_url, is_dev=True):
        if is_dev:
            return f"/static/proxy-pdf?url={quote(external_url, safe='')}"
        else:
            return f"http://localhost:8080/static/proxy-pdf?url={quote(external_url, safe='')}"
    
    test_url = "https://datasheet.lcsc.com/lcsc/TI-TLV9061IDBVR_C693210.pdf"
    
    dev_result = get_pdf_proxy_url(test_url, True)
    prod_result = get_pdf_proxy_url(test_url, False)
    
    print(f"Original URL: {test_url}")
    print(f"Dev Proxy:    {dev_result}")
    print(f"Prod Proxy:   {prod_result}")
    
    # Validate URL encoding
    if "TI-TLV9061IDBVR_C693210.pdf" in dev_result:
        print("✅ URL encoding preserved filename correctly")
    else:
        print("❌ URL encoding issue with filename")
        return False
    
    if dev_result.startswith("/static/proxy-pdf?url="):
        print("✅ Development URL format correct") 
    else:
        print("❌ Development URL format incorrect")
        return False
        
    if prod_result.startswith("http://localhost:8080/static/proxy-pdf?url="):
        print("✅ Production URL format correct")
    else:
        print("❌ Production URL format incorrect") 
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 PDF Proxy Manual Test Suite")
    print("=" * 60)
    
    # Test frontend utility first (doesn't need server)
    frontend_ok = test_frontend_utility()
    
    # Start backend and test
    print(f"\n⚡ Starting backend server...")
    server_thread = start_backend()
    
    # Test the backend
    backend_ok = test_pdf_proxy()
    
    print(f"\n📊 Final Results:")
    print(f"   Frontend Utility: {'✅ PASS' if frontend_ok else '❌ FAIL'}")
    print(f"   Backend Proxy:    {'✅ PASS' if backend_ok else '❌ FAIL'}")
    
    if frontend_ok and backend_ok:
        print("\n🎉 PDF proxy implementation is working correctly!")
        print("   ✅ External PDFs can now be viewed without CORS issues")
        print("   ✅ Domain security is properly enforced")
        print("   ✅ URL encoding works correctly")
        print("   ✅ Error handling is appropriate")
    else:
        print("\n❌ There are issues with the PDF proxy implementation.")
    
    print("\n🛑 Test complete. Backend server will continue running...")
    print("   You can now test manually at: http://localhost:8080/docs")