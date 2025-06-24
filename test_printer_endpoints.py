#!/usr/bin/env python3
"""
Simple test script to check if the printer endpoints are working.
This will test the actual backend without needing to run the frontend.
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8080"

def test_drivers_endpoint():
    """Test the /printer/drivers endpoint."""
    print("Testing /printer/drivers endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/printer/drivers")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            # Check if we have drivers
            if "drivers" in data:
                print(f"✅ Found {len(data['drivers'])} supported drivers")
                for driver in data['drivers']:
                    print(f"  - {driver.get('name', 'Unknown')} ({driver.get('driver_type', 'Unknown')})")
            else:
                print("❌ No 'drivers' key in response")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the server running on localhost:8080?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_printers_endpoint():
    """Test the /printer/printers endpoint."""
    print("\nTesting /printer/printers endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/printer/printers")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            # Check if we have printers
            if "printers" in data:
                print(f"✅ Found {len(data['printers'])} registered printers")
                for printer in data['printers']:
                    print(f"  - {printer.get('name', 'Unknown')} (ID: {printer.get('printer_id', 'Unknown')})")
            else:
                print("❌ No 'printers' key in response")
        elif response.status_code == 401:
            print("❌ Authentication required - this endpoint needs a valid token")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the server running on localhost:8080?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_server_health():
    """Test if the server is responding."""
    print("Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print(f"❌ Server responded with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - is it running on localhost:8080?")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("=== Printer Endpoint Test Script ===")
    print("This script tests the printer-related endpoints directly.")
    print("Make sure the MakerMatrix backend is running on localhost:8080\n")
    
    test_server_health()
    test_drivers_endpoint()
    test_printers_endpoint()
    
    print("\n=== Test Complete ===")
    print("If the drivers endpoint works but printers endpoint needs auth,")
    print("then the issue is likely in the frontend API service configuration.")