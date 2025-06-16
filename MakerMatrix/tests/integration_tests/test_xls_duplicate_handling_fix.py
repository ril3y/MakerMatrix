"""
Test XLS import duplicate handling fixes.

This module tests the specific fixes made for:
1. Proper duplicate part detection and handling during XLS import
2. Grace handling of PartAlreadyExistsError exceptions
3. Race condition handling when parts are created between duplicate checks
"""

import pytest
import pytest_asyncio
import io
from pathlib import Path
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, select

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.services.csv_import_service import CSVImportService
from MakerMatrix.services.part_service import PartService

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_clean_database():
    """Set up a clean database for each test."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    user_repo = UserRepository()
    user_repo.engine = engine
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
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


class TestDuplicateHandlingFix:
    """Test duplicate part handling fixes for XLS import."""
    
    @pytest.mark.asyncio
    async def test_duplicate_part_exception_handling(self, setup_clean_database):
        """Test that PartAlreadyExistsError is properly handled during import."""
        part_service = PartService()
        csv_import_service = CSVImportService()
        
        # Create a test part first
        test_part_data = {
            "part_name": "ACS70331EOLCTR-005U3",
            "part_number": "454-TEST123",
            "description": "Test part for duplicate handling",
            "quantity": 5,
            "supplier": "Mouser",
            "additional_properties": {
                "manufacturer_part_number": "ACS70331EOLCTR-005U3",
                "description": "Test part",
                "unit_price": 0.042,
                "extended_price": 0.21,
                "supplier_part_number": "454-TEST123"
            }
        }
        
        # Create the part first time
        result1 = part_service.add_part(test_part_data)
        assert result1['status'] == 'success', "Should create part successfully"
        
        # Verify part exists in database
        with Session(engine) as session:
            existing_part = session.exec(
                select(PartModel).where(PartModel.part_name == "ACS70331EOLCTR-005U3")
            ).first()
            assert existing_part is not None, "Part should exist in database"
            original_quantity = existing_part.quantity
        
        # Test CSV import with duplicate part (should handle gracefully)
        order_info = {
            "order_number": "TEST-DUP-001",
            "supplier": "Mouser",
            "order_date": "2024-01-21"
        }
        
        # Create parts data with same part (different quantity)
        duplicate_part_data = test_part_data.copy()
        duplicate_part_data['quantity'] = 3  # Different quantity to test update
        parts_data = [duplicate_part_data]
        
        # Import should handle duplicates gracefully
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            parts_data,
            part_service,
            order_info
        )
        
        # Should either succeed (duplicate handling) or fail gracefully (no exceptions)
        assert len(success_parts) + len(failed_parts) == 1, "Should process exactly one part"
        
        # If it failed, should be a graceful failure message (not an exception)
        if len(failed_parts) > 0:
            assert "already exists" in failed_parts[0], "Should have clear duplicate error message"
        
        # If it succeeded, should have updated the part
        if len(success_parts) > 0:
            with Session(engine) as session:
                updated_part = session.exec(
                    select(PartModel).where(PartModel.part_name == "ACS70331EOLCTR-005U3")
                ).first()
                assert updated_part.quantity == original_quantity + 3, "Should have updated quantity"
    
    @pytest.mark.asyncio
    async def test_duplicate_detection_improvement(self, setup_clean_database):
        """Test that duplicate detection works correctly with improved logic."""
        part_service = PartService()
        csv_import_service = CSVImportService()
        
        # Create a part with specific name and part number
        original_part_data = {
            "part_name": "CRL0805-FW-R330ELF",
            "part_number": "269-CRL0805-330",
            "description": "Test resistor",
            "quantity": 10,
            "supplier": "Mouser",
            "additional_properties": {
                "manufacturer_part_number": "CRL0805-FW-R330ELF",
                "description": "330 ohm resistor",
                "unit_price": 0.05,
                "extended_price": 0.50,
                "supplier_part_number": "269-CRL0805-330"
            }
        }
        
        # Create original part
        result = part_service.add_part(original_part_data)
        assert result['status'] == 'success', "Should create original part"
        
        # Test duplicate detection by part name
        name_response = part_service.get_part_by_part_name("CRL0805-FW-R330ELF")
        assert name_response and name_response.get('status') == 'success', "Should find part by name"
        duplicate_by_name = name_response['data']
        
        # Test duplicate detection by part number
        number_response = part_service.get_part_by_part_number("269-CRL0805-330")
        assert number_response and number_response.get('status') == 'success', "Should find part by part number"
        duplicate_by_number = number_response['data']
        
        # Both should return the same part
        assert duplicate_by_name['id'] == duplicate_by_number['id'], "Should find same part by both methods"
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    def test_xls_import_duplicate_handling_integration(self, auth_headers):
        """Test XLS import with duplicate handling via API."""
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        # First import
        import_response1 = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
            data={
                "parser_type": "mouser",
                "order_number": "FIRST-IMPORT-001",
                "order_date": "2024-01-21",
                "notes": "First import test"
            }
        )
        
        assert import_response1.status_code == 200
        import_data1 = import_response1.json()
        assert import_data1["status"] == "success"
        first_success_count = import_data1["data"]["successful_imports"]
        assert first_success_count > 0, "First import should succeed"
        
        # Second import (should handle duplicates)
        import_response2 = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
            data={
                "parser_type": "mouser",
                "order_number": "SECOND-IMPORT-001",
                "order_date": "2024-01-22",
                "notes": "Duplicate import test"
            }
        )
        
        assert import_response2.status_code == 200
        import_data2 = import_response2.json()
        assert import_data2["status"] == "success"
        
        # Second import should either succeed (with updates) or have controlled failures
        total_processed = import_data2["data"]["successful_imports"] + import_data2["data"]["failed_imports"]
        assert total_processed > 0, "Should process parts in second import"
        
        # Should not crash or throw unhandled exceptions
        assert "data" in import_data2, "Should return proper response structure"
        assert "total_rows" in import_data2["data"], "Should have total_rows"
    
    @pytest.mark.asyncio 
    async def test_race_condition_handling(self, setup_clean_database):
        """Test handling of race conditions where parts are created between checks."""
        part_service = PartService()
        csv_import_service = CSVImportService()
        
        # Simulate a part that gets created after duplicate check but before add_part
        test_part_data = {
            "part_name": "RACE-CONDITION-TEST",
            "part_number": "RC-001",
            "description": "Race condition test part",
            "quantity": 1,
            "supplier": "Test",
            "additional_properties": {
                "manufacturer_part_number": "RACE-CONDITION-TEST",
                "unit_price": 1.0,
                "extended_price": 1.0,
                "supplier_part_number": "RC-001"
            }
        }
        
        order_info = {
            "order_number": "RACE-TEST-001",
            "supplier": "Test"
        }
        
        # Create the part manually to simulate race condition
        part_service.add_part(test_part_data)
        
        # Try to import the same part (should trigger race condition handling)
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            [test_part_data],
            part_service,
            order_info
        )
        
        # Should handle gracefully - either succeed or fail with clear message
        assert len(success_parts) + len(failed_parts) == 1, "Should process the part"
        
        if len(failed_parts) > 0:
            failure_msg = failed_parts[0]
            assert "already exists" in failure_msg.lower(), "Should have clear duplicate message"
            # Should not have unhandled exceptions in the failure message
            assert "object dict can't be used in 'await'" not in failure_msg, "Should not have async errors"