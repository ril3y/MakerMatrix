import pytest
from fastapi.testclient import TestClient
import os

from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel

def get_auth_token(client):
    login_data = {
        "username": DEFAULT_ADMIN_USERNAME,
        "password": DEFAULT_ADMIN_PASSWORD
    }
    # Use mobile login endpoint for cleaner JSON handling
    response = client.post("/auth/mobile-login", json=login_data)
    assert response.status_code == 200
    response_data = response.json()
    assert "data" in response_data
    assert "access_token" in response_data["data"]
    return response_data["data"]["access_token"]

def test_create_part_integration():
    with TestClient(app) as client:
        # Authenticate and get token
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Define part data
        part_data = {
            "part_name": "Test Part",
            "part_number": "TP-001",
            "manufacturer": "Test Manufacturer",
            "quantity": 10,
            "location_id": None,  # Add a real location if needed
            "category_names": ["Test Category"]
        }

        # Create the part
        response = client.post("/parts/add_part", json=part_data, headers=headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"]["part_name"] == part_data["part_name"]
        assert response_data["data"]["part_number"] == part_data["part_number"]
        assert response_data["data"]["quantity"] == part_data["quantity"]

        # Optionally, fetch the part and check
        get_response = client.get(f"/parts/get_part?part_name={part_data['part_name']}", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["status"] == "success"
        assert get_data["data"]["part_name"] == part_data["part_name"]
