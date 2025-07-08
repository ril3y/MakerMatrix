import uuid

import pytest
pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine, create_db_and_tables
from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    # Login data for the admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"  # Updated to match the default password in setup_admin.py
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    assert "access_token" in response.json()
    return response.json()["access_token"]


@pytest.fixture
def printer_service() -> PrinterService:
    """Construct a PrinterService that uses the same repository fixture."""
    # Create a test configuration in memory
    test_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }

    # Create a printer service with the test configuration
    printer_service = PrinterService(PrinterRepository())
    printer_service.set_printer_config(test_config)
    return printer_service


def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def setup_part_update_part(admin_token):
    # Initial setup: create a part to update later
    part_data = {
        "part_number": "323329329dj91",
        "part_name": "hammer drill",
        "quantity": 500,
        "description": "A standard hex head screw",
        "location_id": None,
        "category_names": ["hammers", "screwdrivers"],
        "additional_properties": {
            "color": "silver",
            "material": "stainless steel"
        }
    }

    # Make a POST request to add the part to the database
    response = client.post(
        "/api/parts/add_part", 
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response.json()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_code_with_name(printer_service, setup_part_update_part, admin_token):
    # Get the part ID from the setup
    part_id = setup_part_update_part["id"]
    
    # Make a request to print a QR code for the part
    response = client.post(
        f"/printer/print_qr_code/{part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_part_name(printer_service, setup_part_update_part, admin_token):
    # Get the part ID from the setup
    part_id = setup_part_update_part["id"]
    
    # Make a request to print the part name
    response = client.post(
        f"/printer/print_part_name/{part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Part name printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_text_label(printer_service, admin_token):
    # Make a request to print a text label
    response = client.post(
        "/printer/print_text",
        json={"text": "Test Label"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Text label printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_and_text_combined(printer_service, admin_token):
    # Set up printer config
    printer_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }
    
    # Set up label data
    label_data = {
        "qr_data": "https://example.com",
        "text": "Example Label",
        "font_size": 24,
        "qr_size": 200,
        "label_width": 62,
        "label_margin": 5
    }
    
    # Make a request to print a combined QR code and text label
    response = client.post(
        "/printer/print_qr_and_text",
        json={"printer_config": printer_config, "label_data": label_data},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code and text label printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_and_text_combined_fixed_length(printer_service, admin_token):
    # Set up printer config
    printer_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }
    
    # Set up label data with fixed length
    label_data = {
        "qr_data": "https://example.com",
        "text": "Example Label",
        "font_size": 24,
        "qr_size": 200,
        "label_width": 62,
        "label_margin": 5,
        "fixed_label_length": 100
    }
    
    # Make a request to print a combined QR code and text label with fixed length
    response = client.post(
        "/printer/print_qr_and_text",
        json={"printer_config": printer_config, "label_data": label_data},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code and text label printed successfully" in response.json()["message"]
