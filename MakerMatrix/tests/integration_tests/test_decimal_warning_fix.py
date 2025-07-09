from MakerMatrix.tests.test_database_config import setup_test_database_with_admin\n"""
Test that the Decimal warning fix works in real API calls.
"""

import pytest
import io
from pathlib import Path
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


class TestDecimalWarningFix:
    """Test that Decimal warnings are fixed in real API usage."""
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    def test_xls_import_and_get_parts_no_decimal_warnings(self, auth_headers, caplog):
        """Test that XLS import and subsequent part retrieval don't produce Decimal warnings."""
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        # Import XLS file (this creates orders with Decimal pricing)
        import_response = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
            data={
                "parser_type": "mouser",
                "order_number": "DECIMAL-WARNING-TEST-001",
                "order_date": "2024-01-21",
                "notes": "Test decimal warning fix"
            }
        )
        
        assert import_response.status_code == 200
        import_data = import_response.json()
        assert import_data["status"] == "success"
        assert import_data["data"]["successful_imports"] > 0
        
        # Get all parts (this triggers serialization that was causing warnings)
        parts_response = client.get(
            "/api/parts/get_all_parts?page=1&page_size=20",
            headers=auth_headers
        )
        
        assert parts_response.status_code == 200
        parts_data = parts_response.json()
        assert parts_data["status"] == "success"
        assert len(parts_data["data"]) > 0
        
        # Check that no Decimal warnings were logged
        decimal_warnings = [
            record for record in caplog.records 
            if "Expected `float` but got `Decimal`" in record.getMessage()
        ]
        
        # Should have no Decimal warnings with our fix
        assert len(decimal_warnings) == 0, f"Found {len(decimal_warnings)} Decimal warnings in logs"
    
    def test_direct_order_creation_no_warnings(self, auth_headers, caplog):
        """Test that creating orders directly doesn't produce Decimal warnings."""
        # Add a simple part first
        part_data = {
            "part_name": "TEST-DECIMAL-001",
            "part_number": "TD-001",
            "description": "Test part for decimal warning",
            "quantity": 5,
            "supplier": "Test Supplier"
        }
        
        part_response = client.post(
            "/api/parts/add_part",
            headers=auth_headers,
            json=part_data
        )
        
        assert part_response.status_code == 200
        
        # Now get parts which will serialize any order data
        parts_response = client.get(
            "/api/parts/get_all_parts?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert parts_response.status_code == 200
        parts_data = parts_response.json()
        assert parts_data["status"] == "success"
        
        # Check for Decimal warnings
        decimal_warnings = [
            record for record in caplog.records 
            if "Expected `float` but got `Decimal`" in record.getMessage()
        ]
        
        # Should have no warnings
        assert len(decimal_warnings) == 0, f"Found {len(decimal_warnings)} Decimal warnings in logs"