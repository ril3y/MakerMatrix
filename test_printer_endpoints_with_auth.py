#!/usr/bin/env python3
"""
Test printer endpoints with authentication.
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8080"

def get_admin_token():
    """Get an admin token for testing."""
    print("Getting admin token...")
    try:
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print("✅ Successfully obtained admin token")
                return data["access_token"]
            else:
                print("❌ No access_token in login response")
                print(f"Response: {data}")
        else:
            print(f"❌ Login failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed during login")
    except Exception as e:
        print(f"❌ Login error: {e}")
    
    return None

def test_drivers_endpoint_with_auth(token):
    """Test the /printer/drivers endpoint with authentication."""
    print("\nTesting /printer/drivers endpoint with auth...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/printer/drivers", headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Drivers endpoint works with auth!")
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            # Check if we have drivers
            if "drivers" in data:
                print(f"Found {len(data['drivers'])} supported drivers")
                for driver in data['drivers']:
                    print(f"  - {driver.get('name', 'Unknown')} ({driver.get('driver_type', 'Unknown')})")
                    print(f"    Models: {driver.get('supported_models', [])}")
                    print(f"    Backends: {driver.get('backends', [])}")
            else:
                print("❌ No 'drivers' key in response")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_printers_endpoint_with_auth(token):
    """Test the /printer/printers endpoint with authentication."""
    print("\nTesting /printer/printers endpoint with auth...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/printer/printers", headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Printers endpoint works with auth!")
            print("Response data:")
            print(json.dumps(data, indent=2))
            
            # Check if we have printers
            if "printers" in data:
                print(f"Found {len(data['printers'])} registered printers")
                for printer in data['printers']:
                    print(f"  - {printer.get('name', 'Unknown')} (ID: {printer.get('printer_id', 'Unknown')})")
                    print(f"    Status: {printer.get('status', 'Unknown')}")
                    print(f"    Model: {printer.get('model', 'Unknown')}")
            else:
                print("❌ No 'printers' key in response")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("=== Printer Endpoint Test Script (With Auth) ===")
    print("Testing printer endpoints with admin authentication.")
    print("Make sure the MakerMatrix backend is running on localhost:8080\n")
    
    # Get authentication token
    token = get_admin_token()
    
    if token:
        test_drivers_endpoint_with_auth(token)
        test_printers_endpoint_with_auth(token)
    else:
        print("❌ Cannot proceed without authentication token")
    
    print("\n=== Test Complete ===")