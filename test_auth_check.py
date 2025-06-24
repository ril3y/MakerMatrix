#!/usr/bin/env python3
"""
Check what auth endpoints are available and test login.
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_login():
    """Test the login endpoint."""
    print("Testing login endpoint...")
    
    # Try with correct credentials
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login Status Code: {response.status_code}")
        print(f"Login Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                return data["access_token"]
        
    except Exception as e:
        print(f"Login error: {e}")
    
    return None

def test_routes():
    """Test what routes are available."""
    print("\nTesting route availability...")
    
    test_routes = [
        "/",
        "/docs",
        "/printer/drivers",
        "/printer/printers",
        "/auth/login"
    ]
    
    for route in test_routes:
        try:
            response = requests.get(f"{BASE_URL}{route}")
            print(f"{route}: Status {response.status_code}")
        except Exception as e:
            print(f"{route}: Error - {e}")

if __name__ == "__main__":
    print("=== Auth and Route Test ===")
    
    test_routes()
    token = test_login()
    
    if token:
        print(f"\n✅ Successfully got token: {token[:20]}...")
    else:
        print("\n❌ Failed to get auth token")