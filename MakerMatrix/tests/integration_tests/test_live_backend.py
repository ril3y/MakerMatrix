"""
Test the live backend server to verify routes work
"""
import pytest
import requests


def test_live_backend_suppliers_configured():
    """Test the /api/suppliers/configured endpoint on live backend"""
    base_url = "http://localhost:8080"
    
    # Step 1: Login to get token
    login_response = requests.post(f"{base_url}/auth/login", data={
        "username": "admin",
        "password": "Admin123!"
    })
    
    print(f"Login status: {login_response.status_code}")
    print(f"Login response: {login_response.text}")
    
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Test the suppliers/configured endpoint
    suppliers_response = requests.get(f"{base_url}/api/suppliers/configured", headers=headers)
    
    print(f"Suppliers status: {suppliers_response.status_code}")
    print(f"Suppliers headers: {dict(suppliers_response.headers)}")
    print(f"Suppliers response: {suppliers_response.text}")
    
    # This should NOT return HTML
    assert not suppliers_response.text.startswith("<!doctype"), "API returned HTML instead of JSON"
    assert not suppliers_response.text.startswith("<html"), "API returned HTML instead of JSON"
    
    # Should be successful and return JSON
    assert suppliers_response.status_code == 200, f"API call failed: {suppliers_response.status_code} {suppliers_response.text}"
    
    # Should be valid JSON
    try:
        data = suppliers_response.json()
        print(f"Valid JSON response: {data}")
        assert "status" in data
        assert "data" in data
    except Exception as e:
        pytest.fail(f"Response is not valid JSON: {e}")


def test_frontend_vs_backend_ports():
    """Test if frontend and backend are on different ports causing issues"""
    
    # Test if backend is actually running on 8080
    try:
        response = requests.get("http://localhost:8080/", timeout=5)
        print(f"Backend (8080) status: {response.status_code}")
        print(f"Backend (8080) response: {response.text[:100]}")
    except requests.exceptions.ConnectionError:
        pytest.fail("Backend not running on port 8080")
    
    # Test what's running on 5173 (frontend port)
    try:
        response = requests.get("http://localhost:5173/api/suppliers/configured", timeout=5)
        print(f"Port 5173 API call status: {response.status_code}")
        print(f"Port 5173 API call response: {response.text[:100]}")
        
        # If this returns HTML, it means frontend is serving everything and not proxying to backend
        if response.text.startswith("<!doctype") or response.text.startswith("<html"):
            print("❌ Port 5173 is serving HTML for API calls - this is the problem!")
            print("The frontend dev server is not properly proxying API calls to the backend")
    except requests.exceptions.ConnectionError:
        print("Nothing running on port 5173")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])