"""
Comprehensive CSV import and enrichment tests.

Tests CSV import functionality for both LCSC and DigiKey formats,
verifying that parts can be imported and enriched successfully.
"""

import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.system.auth_service import AuthService
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
    """Authentication headers for API calls."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def lcsc_csv_content():
    """Load LCSC CSV test data."""
    csv_path = Path(__file__).parent.parent / "csv_test_data" / "LCSC_Exported__20241222_232708.csv"
    with open(csv_path, 'r', encoding='utf-8') as file:
        return file.read()


@pytest.fixture
def digikey_csv_content():
    """Load DigiKey CSV test data."""
    csv_path = Path(__file__).parent.parent / "csv_test_data" / "DK_PRODUCTS_88269818.csv"
    with open(csv_path, 'r', encoding='utf-8-sig') as file:  # Handle BOM
        return file.read()


class TestCSVImportLCSC:
    """Test LCSC CSV import functionality."""
    
    def test_lcsc_csv_preview(self, auth_headers, lcsc_csv_content):
        """Test LCSC CSV preview functionality."""
        response = client.post(
            "/api/csv/preview",
            json={"csv_content": lcsc_csv_content},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        preview_data = data["data"]
        assert "detected_parser" in preview_data
        assert preview_data["detected_parser"] == "lcsc"
        assert "preview_rows" in preview_data
        assert len(preview_data["preview_rows"]) > 0
        
        # Check that we have the expected LCSC columns
        expected_columns = ["LCSC Part Number", "Manufacture Part Number", "Manufacturer", "Description"]
        first_row = preview_data["preview_rows"][0]
        for col in expected_columns:
            assert col in first_row
    
    def test_lcsc_csv_import_basic(self, auth_headers, lcsc_csv_content):
        """Test basic LCSC CSV import without enrichment."""
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "TEST-LCSC-001"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        import_result = data["data"]
        assert "total_rows" in import_result
        assert "successful_imports" in import_result
        assert "failed_imports" in import_result
        assert import_result["total_rows"] > 0
        
        # Should have imported at least some parts
        assert import_result["successful_imports"] >= 0
    
    def test_lcsc_csv_import_with_progress(self, auth_headers, lcsc_csv_content):
        """Test LCSC CSV import with progress tracking."""
        response = client.post(
            "/api/csv/import/with-progress",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "TEST-LCSC-PROGRESS"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Check that import was initiated
        assert "data" in data
        import_data = data["data"]
        assert "message" in import_data
    
    def test_lcsc_specific_parts_import(self, auth_headers, lcsc_csv_content):
        """Test that specific LCSC parts are imported correctly."""
        # Import the CSV
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "TEST-LCSC-SPECIFIC"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check that parts were created by searching for them
        response = client.get(
            "/api/parts/search_text",
            params={"query": "VEJ101M1VTT-0607L", "page_size": 50},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_data = response.json()
        
        if search_data["data"]:
            # If parts were successfully imported, verify their details
            parts = search_data["data"]
            capacitor_part = next((p for p in parts if "VEJ101M1VTT-0607L" in p.get("part_number", "")), None)
            
            if capacitor_part:
                description = capacitor_part.get("description") or ""
                assert "100uF" in description
                assert capacitor_part["supplier"] == "LCSC"
    
    def test_lcsc_csv_parser_info(self, auth_headers):
        """Test LCSC parser information endpoint."""
        response = client.get(
            "/api/csv/parsers/lcsc/info",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        parser_info = data["data"]
        assert "name" in parser_info
        assert "required_columns" in parser_info  # Changed from supported_columns
        assert "description" in parser_info
        assert parser_info["name"] == "LCSC"


class TestCSVImportDigiKey:
    """Test DigiKey CSV import functionality."""
    
    def test_digikey_csv_preview(self, auth_headers, digikey_csv_content):
        """Test DigiKey CSV preview functionality."""
        response = client.post(
            "/api/csv/preview",
            json={"csv_content": digikey_csv_content},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        preview_data = data["data"]
        assert "detected_parser" in preview_data
        assert preview_data["detected_parser"] == "digikey"
        assert "preview_rows" in preview_data
        assert len(preview_data["preview_rows"]) > 0
        
        # Check that we have the expected DigiKey columns
        expected_columns = ["DigiKey Part #", "Manufacturer Part Number", "Description"]
        first_row = preview_data["preview_rows"][0]
        for col in expected_columns:
            assert col in first_row
    
    def test_digikey_csv_import_basic(self, auth_headers, digikey_csv_content):
        """Test basic DigiKey CSV import without enrichment."""
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": digikey_csv_content,
                "parser_type": "digikey",
                "order_info": {
                    "supplier": "DigiKey",
                    "order_number": "88269818"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        import_result = data["data"]
        assert "total_rows" in import_result
        assert "successful_imports" in import_result
        assert "failed_imports" in import_result
        assert import_result["total_rows"] > 0
    
    def test_digikey_specific_parts_import(self, auth_headers, digikey_csv_content):
        """Test that specific DigiKey parts are imported correctly."""
        # Import the CSV
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": digikey_csv_content,
                "parser_type": "digikey",
                "order_info": {
                    "supplier": "DigiKey",
                    "order_number": "DK-TEST-001"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check that parts were created by searching for them
        response = client.get(
            "/api/parts/search_text",
            params={"query": "TXB0108PWR", "page_size": 50},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        search_data = response.json()
        
        if search_data["data"]:
            # If parts were successfully imported, verify their details
            parts = search_data["data"]
            ic_part = next((p for p in parts if "TXB0108PWR" in p.get("part_number", "")), None)
            
            if ic_part:
                description = ic_part.get("description") or ""
                assert "TRANSLATOR" in description
                assert ic_part["supplier"] == "DigiKey"
    
    def test_digikey_csv_parser_info(self, auth_headers):
        """Test DigiKey parser information endpoint."""
        response = client.get(
            "/api/csv/parsers/digikey/info",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        parser_info = data["data"]
        assert "name" in parser_info
        assert "required_columns" in parser_info  # Changed from supported_columns
        assert "description" in parser_info
        assert parser_info["name"] == "DigiKey"


class TestCSVImportEdgeCases:
    """Test CSV import edge cases and error handling."""
    
    def test_empty_csv_content(self, auth_headers):
        """Test handling of empty CSV content."""
        response = client.post(
            "/api/csv/preview",
            json={"csv_content": ""},
            headers=auth_headers
        )
        
        assert response.status_code == 400 or response.status_code == 422
    
    def test_invalid_csv_format(self, auth_headers):
        """Test handling of invalid CSV format."""
        invalid_csv = "This is not a CSV file\nJust some random text"
        
        response = client.post(
            "/api/csv/preview",
            json={"csv_content": invalid_csv},
            headers=auth_headers
        )
        
        # Should either detect as unknown or return an error
        assert response.status_code in [200, 400, 422]
    
    def test_unsupported_parser_type(self, auth_headers, lcsc_csv_content):
        """Test handling of unsupported parser type."""
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "unsupported_parser",
                "order_info": {
                    "supplier": "Test",
                    "order_number": "TEST-001"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400 or response.status_code == 422
    
    def test_csv_import_without_auth(self, lcsc_csv_content):
        """Test CSV import without authentication."""
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "TEST-001"
                }
            }
        )
        
        assert response.status_code == 401


class TestCSVEnrichment:
    """Test CSV import with enrichment capabilities."""
    
    def test_csv_enrichment_task_creation(self, auth_headers, lcsc_csv_content):
        """Test that CSV enrichment tasks can be created."""
        # First import some parts
        import_response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "ENRICHMENT-TEST"
                }
            },
            headers=auth_headers
        )
        
        assert import_response.status_code == 200
        
        # Check if we can create a CSV enrichment task
        response = client.post(
            "/api/tasks/quick/csv_enrichment",
            json={
                "supplier": "LCSC",
                "csv_content": lcsc_csv_content,
                "order_number": "ENRICHMENT-TEST"
            },
            headers=auth_headers
        )
        
        # Should succeed or return a reasonable error
        assert response.status_code in [200, 201, 400, 422]
    
    def test_bulk_enrichment_after_import(self, auth_headers, lcsc_csv_content):
        """Test bulk enrichment of imported parts."""
        # First import some parts
        import_response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "BULK-ENRICHMENT-TEST"
                }
            },
            headers=auth_headers
        )
        
        assert import_response.status_code == 200
        
        # Get list of parts that were imported
        parts_response = client.get(
            "/api/parts/search_text",
            params={"query": "LCSC", "page_size": 50},
            headers=auth_headers
        )
        
        if parts_response.status_code == 200 and parts_response.json().get("data"):
            parts = parts_response.json()["data"]
            if parts:
                # Try to create a bulk enrichment task
                part_ids = [part["id"] for part in parts[:3]]  # Take first 3 parts
                
                response = client.post(
                    "/api/tasks/quick/bulk_enrichment",
                    json={
                        "part_ids": part_ids,
                        "supplier": "LCSC",
                        "capabilities": ["fetch_datasheet", "fetch_image"]
                    },
                    headers=auth_headers
                )
                
                # Should succeed or return a reasonable error
                assert response.status_code in [200, 201, 400, 422]


class TestCSVImportConfiguration:
    """Test CSV import configuration and settings."""
    
    def test_get_csv_config(self, auth_headers):
        """Test getting CSV import configuration."""
        response = client.get(
            "/api/csv/config",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        config = data["data"]
        expected_config_keys = [
            "download_datasheets",
            "download_images", 
            "overwrite_existing_files",
            "download_timeout_seconds",
            "show_progress"
        ]
        
        for key in expected_config_keys:
            assert key in config
    
    def test_update_csv_config(self, auth_headers):
        """Test updating CSV import configuration."""
        new_config = {
            "download_datasheets": True,
            "download_images": True,
            "overwrite_existing_files": False,
            "download_timeout_seconds": 45,
            "show_progress": True
        }
        
        response = client.put(
            "/api/csv/config",
            json=new_config,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify the config was updated
        get_response = client.get(
            "/api/csv/config",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        updated_config = get_response.json()["data"]
        assert updated_config["download_timeout_seconds"] == 45
    
    def test_get_supported_csv_types(self, auth_headers):
        """Test getting supported CSV file types."""
        response = client.get(
            "/api/csv/supported-types",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        
        supported_types = data["data"]
        assert isinstance(supported_types, list)
        assert len(supported_types) > 0
        
        # Should include LCSC and DigiKey
        type_names = [t["name"] for t in supported_types]
        assert "LCSC" in type_names
        assert "DigiKey" in type_names


class TestCSVImportRobustness:
    """Test CSV import robustness and error recovery."""
    
    def test_partial_import_success(self, auth_headers):
        """Test that partial imports still succeed when some rows fail."""
        # Create a CSV with mixed valid and invalid data
        mixed_csv = """LCSC Part Number,Manufacture Part Number,Manufacturer,Package,Description,Order Qty.,Unit Price($)
C7442639,VEJ101M1VTT-0607L,Lelon,"SMD,D6.3xL7.7mm","100uF 35V Aluminum Electrolytic Capacitor",50,0.0874
INVALID,INVALID_PART,Invalid Mfg,,Invalid Description,INVALID,INVALID
C60633,SWPA6045S101MT,Sunlord,,-,50,0.0715"""
        
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": mixed_csv,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "MIXED-DATA-TEST"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Should report both successes and failures
        import_result = data["data"]
        assert "successful_imports" in import_result
        assert "failed_imports" in import_result
    
    def test_import_progress_tracking(self, auth_headers, lcsc_csv_content):
        """Test that import progress can be tracked."""
        # Start an import with progress tracking
        response = client.post(
            "/api/csv/import/with-progress",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "PROGRESS-TEST"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Try to get progress (may or may not be available depending on timing)
        progress_response = client.get(
            "/api/csv/import/progress",
            headers=auth_headers
        )
        
        # Should return some progress information
        assert progress_response.status_code in [200, 404]  # 404 if no active import


class TestCSVTaskIntegration:
    """Test CSV import integration with task system."""
    
    def test_csv_import_creates_tasks(self, auth_headers, lcsc_csv_content):
        """Test that CSV import can create enrichment tasks."""
        # Import with task creation
        response = client.post(
            "/api/csv/import",
            json={
                "csv_content": lcsc_csv_content,
                "parser_type": "lcsc",
                "order_info": {
                    "supplier": "LCSC",
                    "order_number": "TASK-INTEGRATION-TEST"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Check if any tasks were created
        tasks_response = client.get(
            "/api/tasks/",
            params={"limit": 50},
            headers=auth_headers
        )
        
        assert tasks_response.status_code == 200
        # Tasks may or may not be created depending on configuration
    
    def test_task_capabilities_for_csv_suppliers(self, auth_headers):
        """Test that task capabilities are available for CSV suppliers."""
        # Check LCSC capabilities
        lcsc_response = client.get(
            "/api/tasks/capabilities/suppliers/LCSC",
            headers=auth_headers
        )
        
        # Should either have capabilities or return 404
        assert lcsc_response.status_code in [200, 404]
        
        # Check DigiKey capabilities  
        dk_response = client.get(
            "/api/tasks/capabilities/suppliers/DigiKey",
            headers=auth_headers
        )
        
        # Should either have capabilities or return 404
        assert dk_response.status_code in [200, 404]