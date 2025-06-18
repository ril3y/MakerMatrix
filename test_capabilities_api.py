#!/usr/bin/env python3
"""
Test script to check capabilities API endpoint
"""

import asyncio
import logging
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.database.db import engine
from sqlalchemy.orm import Session
from MakerMatrix.models.models import UserModel
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.services.auth_service import AuthService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_capabilities_api():
    """Test the capabilities API endpoint"""
    client = TestClient(app)
    
    # First, create a test user and login
    with Session(engine) as session:
        # Check if admin user exists
        admin_user = session.query(UserModel).filter(UserModel.username == "admin").first()
        if not admin_user:
            print("Admin user not found. Creating one...")
            user_repo = UserRepository(engine)
            auth_service = AuthService()
            
            admin_user = user_repo.create_user(
                session=session,
                username="admin",
                email="admin@test.com",
                password="Admin123!",
                roles=["admin"]
            )
            session.commit()
    
    # Login to get token
    login_response = client.post("/auth/login", data={
        "username": "admin",
        "password": "Admin123!"
    })
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test the capabilities endpoint
    response = client.get("/api/tasks/capabilities/suppliers", headers=headers)
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Capabilities response:")
        
        if "data" in data:
            for supplier_name, capabilities in data["data"].items():
                print(f"\n{supplier_name}:")
                print(f"  Enabled: {capabilities.get('enabled', False)}")
                print(f"  Capabilities: {capabilities.get('capabilities', [])}")
                if 'error' in capabilities:
                    print(f"  Error: {capabilities['error']}")
        else:
            print("No 'data' key in response")
            print(data)
    else:
        print(f"Error response: {response.text}")

if __name__ == "__main__":
    test_capabilities_api()