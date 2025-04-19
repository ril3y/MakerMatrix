import pytest
from fastapi.testclient import TestClient
import os
import json

from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel

# Ensure test DB is always clean and tables are created for both app and test client
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Remove test DB file if it exists (for file-based SQLite)
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

def test_mobile_login():
    """Test that the mobile login endpoint works correctly."""
    with TestClient(app) as client:
        # Create login data
        login_data = {
            "username": DEFAULT_ADMIN_USERNAME,
            "password": DEFAULT_ADMIN_PASSWORD
        }
        
        # Send login request
        response = client.post("/auth/login", json=login_data)
        
        # Check response status and structure
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Login successful"
        assert "access_token" in response_data
        assert "token_type" in response_data
        assert response_data["token_type"] == "bearer"
        
        # Extract token
        token = response_data["access_token"]
        assert token is not None and token != ""
        
        # Test token by accessing a protected route
        headers = {"Authorization": f"Bearer {token}"}
        protected_response = client.get("/parts/get_all_parts", headers=headers)
        
        # Verify we can access protected route with the token
        assert protected_response.status_code != 401  # Not unauthorized
        
        # Test with invalid credentials
        invalid_login = {
            "username": "invalid_user",
            "password": "invalid_password"
        }
        invalid_response = client.post("/auth/login", json=invalid_login)
        assert invalid_response.status_code == 401  # Unauthorized 