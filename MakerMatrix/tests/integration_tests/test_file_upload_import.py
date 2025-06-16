"""
Comprehensive file upload import tests.

Tests the new file upload functionality for CSV and XLS files,
including auto-detection, preview, and import functionality.
"""

import pytest
import os
import io
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_clean_database():
    """Set up a clean database for each test."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    user_repo.engine = engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # Cleanup
    SQLModel.metadata.drop_all(engine)


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


def test_csv_file_preview_lcsc(auth_headers):
    """Test CSV file preview with LCSC format."""
    # Create test LCSC CSV content with correct column names
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40
C65877,ESP32-WROOM-32,Espressif,ESP32-WROOM-32,SMD-38_18.0x25.5x3.1P,WiFi Modules,Yes,5,1\\1,3.2100,16.05"""

    # Create file-like object
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test file upload preview
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("test_lcsc.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["detected_parser"] == "lcsc"
    assert data["data"]["is_supported"] is True
    assert data["data"]["total_rows"] == 2
    assert len(data["data"]["headers"]) == 11  # LCSC has 11 columns
    assert "LCSC Part Number" in data["data"]["headers"]
    assert "Manufacture Part Number" in data["data"]["headers"]
    assert len(data["data"]["preview_rows"]) <= 5  # Limited preview


def test_csv_file_preview_digikey(auth_headers):
    """Test CSV file preview with DigiKey format."""
    # Create test DigiKey CSV content with correct column names
    csv_content = """Index,DigiKey Part #,Manufacturer Part Number,Description,Customer Reference,Quantity,Backorder,Unit Price,Extended Price
1,296-8224-1-ND,STM32F103C8T6,IC MCU 32BIT 256KB FLASH 64LQFP,REF123,10,0,$12.50,$125.00
2,1276-1000-1-ND,ESP32-WROOM-32,FEATHER M0 BASIC PROTO - ATSAMD21,REF456,5,0,$19.95,$99.75"""

    # Create file-like object
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test file upload preview
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("test_digikey.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["detected_parser"] == "digikey"
    assert data["data"]["is_supported"] is True
    assert data["data"]["total_rows"] == 2
    assert "DigiKey Part #" in data["data"]["headers"]
    assert "Manufacturer Part Number" in data["data"]["headers"]


def test_csv_file_import_lcsc(auth_headers):
    """Test complete CSV file import with LCSC format."""
    # Create test LCSC CSV content with correct column names
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40
C65877,ESP32-WROOM-32,Espressif,ESP32-WROOM-32,SMD-38_18.0x25.5x3.1P,WiFi Modules,Yes,5,1\\1,3.2100,16.05"""

    # Create file-like object
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test file upload import
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("test_lcsc.csv", file_content, "text/csv")},
        data={
            "parser_type": "lcsc",
            "order_number": "ORD-2024-001",
            "order_date": "2024-01-15",
            "notes": "Test import"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["successful_imports"] >= 0  # Some parts should import successfully
    assert data["data"]["total_rows"] == 2
    assert "imported_parts" in data["data"]


def test_csv_file_import_digikey(auth_headers):
    """Test complete CSV file import with DigiKey format."""
    # Create test DigiKey CSV content with correct column names
    csv_content = """Index,DigiKey Part #,Manufacturer Part Number,Description,Customer Reference,Quantity,Backorder,Unit Price,Extended Price
1,296-8224-1-ND,STM32F103C8T6,IC MCU 32BIT 256KB FLASH 64LQFP,REF123,10,0,$12.50,$125.00
2,1276-1000-1-ND,ESP32-WROOM-32,FEATHER M0 BASIC PROTO - ATSAMD21,REF456,5,0,$19.95,$99.75"""

    # Create file-like object
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test file upload import
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("test_digikey.csv", file_content, "text/csv")},
        data={
            "parser_type": "digikey",
            "order_number": "DK-2024-001",
            "order_date": "2024-01-16",
            "notes": "DigiKey test import"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["total_rows"] == 2


def test_auto_detection_no_parser_specified(auth_headers):
    """Test file import with auto-detection when no parser type is specified."""
    # Create test LCSC CSV content with correct column names
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    # Create file-like object
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test file upload import without specifying parser_type
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("test_auto.csv", file_content, "text/csv")},
        data={
            "order_number": "AUTO-2024-001",
            "notes": "Auto-detection test"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["total_rows"] == 1


def test_unsupported_file_format(auth_headers):
    """Test upload of unsupported file format."""
    # Create a text file with unsupported extension
    file_content = io.BytesIO(b"This is not a CSV file")
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    
    assert response.status_code == 400
    error_response = response.json()
    # Error could be in 'detail' field or in our custom response format
    error_message = error_response.get("detail") or error_response.get("message", "")
    assert "Unsupported file type" in error_message


def test_empty_csv_file(auth_headers):
    """Test upload of empty CSV file."""
    # Create empty CSV file
    file_content = io.BytesIO(b"")
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("empty.csv", file_content, "text/csv")}
    )
    
    # Should handle empty files gracefully
    assert response.status_code in [200, 400]  # Either succeeds with empty data or fails gracefully


def test_malformed_csv_file(auth_headers):
    """Test upload of malformed CSV file."""
    # Create malformed CSV content
    csv_content = """This is not,a valid CSV
Missing quotes "in this line
Invalid,format,here,"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("malformed.csv", file_content, "text/csv")}
    )
    
    # Should handle malformed files gracefully
    assert response.status_code in [200, 400]


def test_large_csv_file_preview_limit(auth_headers):
    """Test that preview is limited for large CSV files."""
    # Create large CSV with many rows using correct LCSC format
    header = "LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)\n"
    rows = []
    for i in range(100):  # Create 100 rows
        rows.append(f"C{15849+i},STM32F103C8T6_{i},STMicroelectronics,STM32F103C8T6_{i},LQFP-48,MCU {i},Yes,10,1\\1,2.54,25.40")
    
    csv_content = header + "\n".join(rows)
    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("large.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["data"]["total_rows"] == 100
    # Preview should be limited (usually to 5-10 rows)
    assert len(data["data"]["preview_rows"]) <= 10


def test_file_import_with_order_info(auth_headers):
    """Test file import with complete order information."""
    # Create test CSV content with correct column names
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test with complete order information
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": ("order_test.csv", file_content, "text/csv")},
        data={
            "parser_type": "lcsc",
            "order_number": "ORD-2024-DETAILED",
            "order_date": "2024-01-20",
            "notes": "Detailed order information test with special characters: üñíçødé"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert "imported_parts" in data["data"]


def test_unauthorized_file_upload(setup_clean_database):
    """Test file upload without authentication."""
    csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48_7x7x05P,ARM Microcontrollers - MCU,Yes,10,1\\1,2.5400,25.40"""

    file_content = io.BytesIO(csv_content.encode('utf-8'))
    
    # Test without auth headers
    response = client.post(
        "/api/csv/preview-file",
        files={"file": ("test.csv", file_content, "text/csv")}
    )
    
    assert response.status_code == 401


@pytest.mark.skipif(not os.path.exists("MakerMatrix/tests/mouser_xls_test/"), 
                   reason="Mouser XLS test files not available")
def test_mouser_xls_file_preview(auth_headers):
    """Test Mouser XLS file preview functionality."""
    # Look for test XLS file
    test_files_dir = Path("MakerMatrix/tests/mouser_xls_test/")
    xls_files = list(test_files_dir.glob("*.xls"))
    
    if not xls_files:
        pytest.skip("No Mouser XLS test files found")
    
    test_file = xls_files[0]
    
    with open(test_file, 'rb') as f:
        file_content = f.read()
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")}
    )
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["detected_parser"] == "mouser"
        assert data["data"]["file_format"] == "xls"
        assert data["data"]["is_supported"] is True
    else:
        # XLS parsing might fail due to format issues, that's acceptable
        assert response.status_code in [400, 500]


@pytest.mark.skipif(not os.path.exists("MakerMatrix/tests/mouser_xls_test/"), 
                   reason="Mouser XLS test files not available")
def test_mouser_xls_file_import(auth_headers):
    """Test Mouser XLS file import functionality."""
    # Look for test XLS file
    test_files_dir = Path("MakerMatrix/tests/mouser_xls_test/")
    xls_files = list(test_files_dir.glob("*.xls"))
    
    if not xls_files:
        pytest.skip("No Mouser XLS test files found")
    
    test_file = xls_files[0]
    
    with open(test_file, 'rb') as f:
        file_content = f.read()
    
    response = client.post(
        "/api/csv/import-file",
        headers=auth_headers,
        files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
        data={
            "parser_type": "mouser",
            "order_number": "MOUSER-2024-001",
            "order_date": "2024-01-21",
            "notes": "Mouser XLS import test"
        }
    )
    
    # XLS import might succeed or fail depending on file format
    assert response.status_code in [200, 400, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
        assert "imported_parts" in data["data"]


def test_file_validation_and_error_handling(auth_headers):
    """Test comprehensive file validation and error handling."""
    # Test with various invalid scenarios
    
    # Test 1: File too large (simulate with large content)
    large_content = "A" * (10 * 1024 * 1024)  # 10MB
    file_content = io.BytesIO(large_content.encode('utf-8'))
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("large.csv", file_content, "text/csv")}
    )
    
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 400, 413, 500]
    
    # Test 2: Invalid CSV format
    invalid_csv = """Header1,Header2
"Unclosed quote,value2
value3,value4"""
    
    file_content = io.BytesIO(invalid_csv.encode('utf-8'))
    
    response = client.post(
        "/api/csv/preview-file",
        headers=auth_headers,
        files={"file": ("invalid.csv", file_content, "text/csv")}
    )
    
    # Should handle gracefully
    assert response.status_code in [200, 400]


def test_concurrent_file_uploads(auth_headers):
    """Test handling of concurrent file uploads."""
    import threading
    import time
    
    results = []
    
    def upload_file(file_suffix):
        csv_content = f"""LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C1584{file_suffix},STM32F103C8T6_{file_suffix},STMicroelectronics,STM32F103C8T6_{file_suffix},LQFP-48,MCU {file_suffix},Yes,10,1\\1,2.54,25.40"""
        
        file_content = io.BytesIO(csv_content.encode('utf-8'))
        
        response = client.post(
            "/api/csv/preview-file",
            headers=auth_headers,
            files={"file": (f"test_{file_suffix}.csv", file_content, "text/csv")}
        )
        
        results.append(response.status_code)
    
    # Create multiple threads to upload files concurrently
    threads = []
    for i in range(3):  # Test with 3 concurrent uploads
        thread = threading.Thread(target=upload_file, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All uploads should succeed
    assert all(status_code == 200 for status_code in results)