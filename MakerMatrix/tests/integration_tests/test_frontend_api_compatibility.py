from MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n"""
Frontend API Compatibility Tests

Tests to ensure the frontend and backend APIs are compatible,
specifically checking that the request/response formats match.
"""

import pytest
import io
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_clean_database():
    """Set up a clean database for each test."""
    SQLModel.metadata.drop_all(isolated_test_engine)
    SQLModel.metadata.create_all(isolated_test_engine)
    create_db_and_tables()

    user_repo = UserRepository()
    user_repo.engine = engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    SQLModel.metadata.drop_all(isolated_test_engine)


@pytest.fixture
def admin_token(setup_clean_database):
    """Get admin authentication token."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": "admin", "password_change_required": False})
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Get authentication headers."""
    return {"Authorization": f"Bearer {admin_token}"}


def test_frontend_file_preview_api_compatibility(auth_headers):
    """Test that file preview API matches frontend expectations."""
    # Simulate frontend FormData request
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("test.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 200
    
    # Validate response structure matches what frontend expects
    data = response.json()
    
    # Frontend expects: result.status === 'success'
    assert data["status"] == "success"
    
    # Frontend expects: result.data.detected_parser
    assert "data" in data
    assert "detected_parser" in data["data"]
    assert data["data"]["detected_parser"] == "lcsc"
    
    # Frontend expects: result.data.is_supported
    assert data["data"]["is_supported"] is True
    
    # Frontend expects: result.data.total_rows
    assert data["data"]["total_rows"] == 1
    
    # Frontend expects: result.data.headers
    assert "headers" in data["data"]
    assert len(data["data"]["headers"]) == 11
    
    # Frontend expects: result.data.preview_rows  
    assert "preview_rows" in data["data"]
    assert len(data["data"]["preview_rows"]) == 1


def test_frontend_file_import_api_compatibility(auth_headers):
    """Test that file import API matches frontend expectations."""
    # Simulate frontend FormData request
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Simulate frontend FormData with all fields
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("test.csv", file_content, "text/csv")},
        data={
            "parser_type": "lcsc",
            "order_number": "ORD-2024-FRONTEND",
            "order_date": "2024-01-20",
            "notes": "Frontend compatibility test"
        }
    )
    
    assert response.status_code == 200
    
    # Validate response structure matches what frontend expects
    data = response.json()
    
    # Frontend expects: result.status === 'success'
    assert data["status"] == "success"
    
    # Frontend expects: result.data.successful_imports
    assert "data" in data
    assert "successful_imports" in data["data"]
    assert data["data"]["successful_imports"] >= 0
    
    # Frontend expects: result.data.imported_parts
    assert "imported_parts" in data["data"]
    
    # Frontend expects: result.data.failures
    assert "failures" in data["data"]
    
    # Frontend expects: result.data.total_rows
    assert "total_rows" in data["data"]
    assert data["data"]["total_rows"] == 1


def test_frontend_auto_detection_compatibility(auth_headers):
    """Test auto-detection without parser_type matches frontend expectations."""
    # Simulate frontend request without parser_type (auto-detection)
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # No parser_type specified - should auto-detect
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("test.csv", file_content, "text/csv")},
        data={
            "order_number": "AUTO-DETECT-TEST",
            "notes": "Auto-detection test"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Auto-detection should work
    assert data["status"] == "success"
    assert data["data"]["total_rows"] == 1


def test_frontend_error_handling_compatibility(auth_headers):
    """Test error handling matches frontend expectations."""
    # Test unsupported file type
    file_content = io.BytesIO(b"This is not a CSV file")
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    
    assert response.status_code == 400
    
    # Frontend error handling expects either:
    # - error.response.data.detail (FastAPI HTTPException)
    # - error.response.data.message (our ResponseSchema)
    error_data = response.json()
    
    # Should have either 'detail' or 'message' field
    has_error_info = "detail" in error_data or "message" in error_data
    assert has_error_info
    
    error_message = error_data.get("detail", "") + error_data.get("message", "")
    assert "Unsupported file type" in error_message


def test_frontend_digikey_compatibility(auth_headers):
    """Test DigiKey format matches frontend expectations."""
    # Test DigiKey auto-detection
    csv_content = """Index,DigiKey Part #,Manufacturer Part Number,Description,Customer Reference,Quantity,Backorder,Unit Price,Extended Price
1,296-8224-1-ND,STM32F103C8T6,IC MCU 32BIT 256KB FLASH 64LQFP,REF123,10,0,$12.50,$125.00"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test preview
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("digikey_test.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["detected_parser"] == "digikey"
    assert data["data"]["is_supported"] is True


def test_frontend_empty_file_handling(auth_headers):
    """Test empty file handling matches frontend expectations."""
    # Test empty file
    file_content = io.BytesIO(b"")
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("empty.csv", file_content, "text/csv")}
    )
    
    # Should handle gracefully - either succeed with empty data or fail gracefully
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] in ["success", "error"]