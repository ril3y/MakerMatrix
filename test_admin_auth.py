#!/usr/bin/env python3
"""
Test script to debug admin authentication issue
"""

import requests
import json

# Base URL - adjust if needed
BASE_URL = "http://localhost:57891"

def test_admin_login_and_users():
    """Test admin login and accessing users endpoint"""
    
    # Step 1: Login as admin
    print("1. Logging in as admin...")
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    try:
        login_response = requests.post(f"{BASE_URL}/auth/mobile-login", json=login_data)
        print(f"Login status code: {login_response.status_code}")
        print(f"Login response: {login_response.text}")
        
        if login_response.status_code != 200:
            print("Login failed!")
            return
            
        login_result = login_response.json()
        if login_result.get("status") != "success":
            print(f"Login failed: {login_result.get('message')}")
            return
            
        token = login_result["data"]["access_token"]
        print(f"Token obtained: {token[:50]}...")
        
    except Exception as e:
        print(f"Error during login: {e}")
        return
    
    # Step 2: Test accessing users endpoint
    print("\n2. Accessing /users/all endpoint...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        users_response = requests.get(f"{BASE_URL}/users/all", headers=headers)
        print(f"Users endpoint status code: {users_response.status_code}")
        print(f"Users endpoint response: {users_response.text}")
        
        if users_response.status_code == 200:
            print("SUCCESS: Admin can access users endpoint!")
        elif users_response.status_code == 403:
            print("FAILED: Access denied - this is the issue we're debugging")
        else:
            print(f"UNEXPECTED: Status code {users_response.status_code}")
            
    except Exception as e:
        print(f"Error accessing users endpoint: {e}")

if __name__ == "__main__":
    print("Testing admin authentication and user management access...")
    print("Make sure the backend is running on http://localhost:57891")
    print()
    test_admin_login_and_users()