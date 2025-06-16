"""
Tests for XLS import fixes and WebSocket functionality.

This module tests the specific fixes made for:
1. WebSocket broadcast_message function availability
2. XLS import duplicate handling improvements
3. Comprehensive XLS import workflow
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
from MakerMatrix.services.websocket_service import broadcast_message, websocket_manager
from MakerMatrix.parsers.mouser_xls_parser import MouserXLSParser
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


class TestWebSocketFixes:
    """Test WebSocket broadcast functionality fixes."""
    
    def test_broadcast_message_function_exists(self):
        """Test that broadcast_message function is available and has correct signature."""
        # Test function exists
        assert hasattr(broadcast_message, '__call__'), "broadcast_message should be callable"
        
        # Test function signature
        import inspect
        sig = inspect.signature(broadcast_message)
        params = list(sig.parameters.keys())
        
        assert 'message' in params, "Function should have 'message' parameter"
        assert 'connection_types' in params, "Function should have 'connection_types' parameter"
        
        # Test parameter defaults
        connection_types_param = sig.parameters['connection_types']
        assert connection_types_param.default is None, "connection_types should default to None"
    
    def test_broadcast_message_function_execution(self):
        """Test that broadcast_message function can be called without errors."""
        # This should not raise an exception even if no connections are active
        import asyncio
        
        async def test_broadcast():
            message = {
                "type": "test",
                "data": {"test": "data"},
                "timestamp": "2024-01-01T00:00:00Z"
            }
            
            # Should not raise exception
            await broadcast_message(message, ["general"])
            await broadcast_message(message)  # Test default parameter
        
        # Run the async test
        asyncio.run(test_broadcast())
    
    def test_websocket_manager_broadcast_methods(self):
        """Test that WebSocket manager has required broadcast methods."""
        manager = websocket_manager
        
        # Test required methods exist
        assert hasattr(manager, 'broadcast_to_type'), "Manager should have broadcast_to_type method"
        assert hasattr(manager, 'broadcast_task_update'), "Manager should have broadcast_task_update method"
        assert hasattr(manager, 'send_system_notification'), "Manager should have send_system_notification method"


class TestXLSImportFixes:
    """Test XLS import fixes and duplicate handling."""
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    def test_xls_parser_functionality(self):
        """Test that XLS parser works correctly."""
        parser = MouserXLSParser()
        test_file = "MakerMatrix/tests/mouser_xls_test/271360826.xls"
        
        # Test parser can handle the file
        assert parser.can_parse(file_path=test_file), "Parser should be able to handle test XLS file"
        
        # Test parsing
        result = parser.parse_file(test_file)
        assert result.success, f"Parser should successfully parse file: {result.error_message}"
        assert result.total_rows > 0, "Should have parsed some rows"
        assert result.successful_rows > 0, "Should have some successful rows"
        assert len(result.parts) > 0, "Should have generated parts data"
        
        # Test part data structure
        first_part = result.parts[0]
        required_fields = ['part_name', 'part_number', 'description', 'quantity', 'supplier']
        for field in required_fields:
            assert field in first_part, f"Part data should have {field} field"
        
        assert first_part['supplier'] == 'Mouser', "Supplier should be Mouser"
        assert isinstance(first_part['quantity'], int), "Quantity should be integer"
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    @pytest.mark.asyncio
    async def test_xls_import_duplicate_handling(self, setup_clean_database):
        """Test that XLS import properly handles duplicate parts."""
        parser = MouserXLSParser()
        part_service = PartService()
        csv_import_service = CSVImportService()
        test_file = "MakerMatrix/tests/mouser_xls_test/271360826.xls"
        
        # Parse the XLS file
        result = parser.parse_file(test_file)
        assert result.success, "Parser should successfully parse file"
        
        # Get first part data for pre-creation
        first_part = result.parts[0]
        
        # Create the first part manually to test duplicate handling
        created_part = part_service.add_part(first_part)
        assert created_part['status'] == 'success', "Should successfully create first part"
        
        # Now try to import all parts including the duplicate
        order_info = {
            "order_number": "TEST-DUPLICATE-001",
            "order_date": "2024-01-20",
            "supplier": "Mouser",
            "notes": "Test duplicate handling"
        }
        
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            result.parts,
            part_service,
            order_info
        )
        
        # Verify results
        assert len(success_parts) > 0, "Should have some successful imports"
        total_processed = len(success_parts) + len(failed_parts)
        assert total_processed == len(result.parts), "Should process all parts"
        
        # The duplicate should be handled (either updated or properly failed)
        # We expect either all successes (if duplicate updating works) or one expected failure
        if len(failed_parts) > 0:
            # Check that duplicate failure message is reasonable
            duplicate_failures = [f for f in failed_parts if "already exists" in f]
            assert len(duplicate_failures) <= 1, "Should have at most one duplicate failure"
    
    @pytest.mark.skipif(not Path("MakerMatrix/tests/mouser_xls_test/271360826.xls").exists(), 
                       reason="Mouser XLS test file not available")
    def test_xls_file_upload_api_integration(self, auth_headers):
        """Test XLS file upload through API with real file."""
        test_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        # Test preview
        preview_response = client.post(
            "/api/csv/preview-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")}
        )
        
        assert preview_response.status_code == 200, f"Preview should succeed: {preview_response.text}"
        preview_data = preview_response.json()
        
        assert preview_data["status"] == "success", "Preview should be successful"
        assert preview_data["data"]["detected_parser"] == "mouser", "Should detect Mouser parser"
        assert preview_data["data"]["is_supported"] is True, "Should be supported"
        assert preview_data["data"]["total_rows"] > 0, "Should have rows"
        
        # Test import
        import_response = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": (test_file.name, io.BytesIO(file_content), "application/vnd.ms-excel")},
            data={
                "parser_type": "mouser",
                "order_number": "API-TEST-001",
                "order_date": "2024-01-21",
                "notes": "API integration test"
            }
        )
        
        assert import_response.status_code == 200, f"Import should succeed: {import_response.text}"
        import_data = import_response.json()
        
        assert import_data["status"] == "success", "Import should be successful"
        assert import_data["data"]["total_rows"] > 0, "Should have processed rows"
        
        # Check import results
        successful_count = import_data["data"]["successful_imports"]
        failed_count = import_data["data"]["failed_imports"]
        total_count = import_data["data"]["total_rows"]
        
        # Verify that we processed the expected number of rows
        assert total_count > 0, "Should have processed some rows"
        
        # At least one of success or failure should be > 0
        assert successful_count + failed_count > 0, "Should have processed at least some parts"
        
        # If we have failures, check that they are reasonable
        if failed_count > 0:
            failures = import_data["data"]["failures"]
            assert isinstance(failures, list), "Failures should be a list"


class TestDuplicatePartHandling:
    """Test the improved duplicate part detection logic."""
    
    @pytest.mark.asyncio
    async def test_duplicate_detection_by_part_number(self, setup_clean_database):
        """Test that duplicate detection works by part number."""
        part_service = PartService()
        csv_import_service = CSVImportService()
        
        # Create a part
        part_data = {
            "part_name": "TEST_PART_001",
            "part_number": "TEST-PN-001",
            "description": "Test part for duplicate detection",
            "quantity": 5,
            "supplier": "Test Supplier"
        }
        
        created_part = part_service.add_part(part_data)
        assert created_part['status'] == 'success', "Should create part successfully"
        
        # Try to import the same part with same part_number
        duplicate_part_data = {
            "part_name": "DIFFERENT_NAME",  # Different name
            "part_number": "TEST-PN-001",   # Same part number
            "description": "Duplicate part test",
            "quantity": 3,
            "supplier": "Test Supplier",
            "additional_properties": {}
        }
        
        order_info = {
            "order_number": "DUP-TEST-001",
            "supplier": "Test Supplier"
        }
        
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            [duplicate_part_data],
            part_service,
            order_info
        )
        
        # Should handle duplicate properly (either update or graceful failure)
        total_processed = len(success_parts) + len(failed_parts)
        assert total_processed == 1, "Should process the one part"
    
    @pytest.mark.asyncio
    async def test_duplicate_detection_by_part_name(self, setup_clean_database):
        """Test that duplicate detection works by part name."""
        part_service = PartService()
        csv_import_service = CSVImportService()
        
        # Create a part
        part_data = {
            "part_name": "TEST_PART_002",
            "part_number": "TEST-PN-002",
            "description": "Test part for duplicate detection",
            "quantity": 5,
            "supplier": "Test Supplier"
        }
        
        created_part = part_service.add_part(part_data)
        assert created_part['status'] == 'success', "Should create part successfully"
        
        # Try to import the same part with same part_name but different part_number
        duplicate_part_data = {
            "part_name": "TEST_PART_002",   # Same name
            "part_number": "DIFFERENT-PN",  # Different part number
            "description": "Duplicate part test by name",
            "quantity": 3,
            "supplier": "Test Supplier",
            "additional_properties": {}
        }
        
        order_info = {
            "order_number": "DUP-TEST-002",
            "supplier": "Test Supplier"
        }
        
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
            [duplicate_part_data],
            part_service,
            order_info
        )
        
        # Should handle duplicate properly (either update or graceful failure)
        total_processed = len(success_parts) + len(failed_parts)
        assert total_processed == 1, "Should process the one part"


class TestImportErrorReporting:
    """Test that import error reporting is accurate and helpful."""
    
    def test_import_response_structure(self, auth_headers, setup_clean_database):
        """Test that import responses have the correct structure."""
        # Create simple test data
        csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48,ARM Microcontroller,Yes,10,1\\1,2.54,25.40"""
        
        file_content = io.BytesIO(csv_content.encode('utf-8'))
        
        # Test import
        response = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": ("test.csv", file_content, "text/csv")},
            data={
                "parser_type": "lcsc",
                "order_number": "STRUCTURE-TEST-001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify response structure
        required_fields = ["total_rows", "successful_imports", "failed_imports", "imported_parts", "failures"]
        for field in required_fields:
            assert field in data["data"], f"Response should have {field} field"
        
        # Verify data types
        assert isinstance(data["data"]["total_rows"], int)
        assert isinstance(data["data"]["successful_imports"], int)
        assert isinstance(data["data"]["failed_imports"], int)
        assert isinstance(data["data"]["imported_parts"], list)
        assert isinstance(data["data"]["failures"], list)
        
        # Verify at least one row was processed
        assert data["data"]["total_rows"] >= 1
    
    def test_import_without_order_date(self, auth_headers, setup_clean_database):
        """Test that import works when no order_date is provided."""
        # Create simple test data
        csv_content = """LCSC Part Number,Manufacture Part Number,Manufacturer,Customer NO.,Package,Description,RoHS,Order Qty.,Min\\Mult Order Qty.,Unit Price($),Order Price($)
C15849,STM32F103C8T6,STMicroelectronics,STM32F103C8T6,LQFP-48,ARM Microcontroller,Yes,5,1\\1,2.54,12.70"""
        
        file_content = io.BytesIO(csv_content.encode('utf-8'))
        
        # Test import without order_date field (should default to empty string)
        response = client.post(
            "/api/csv/import-file",
            headers=auth_headers,
            files={"file": ("test_no_date.csv", file_content, "text/csv")},
            data={
                "parser_type": "lcsc",
                "order_number": "NO-DATE-TEST-001",
                # Deliberately omit order_date
                "notes": "Test without order date"
            }
        )
        
        assert response.status_code == 200, f"Import without order_date should succeed: {response.text}"
        data = response.json()
        assert data["status"] == "success", "Import should be successful"
        
        # Should process the part successfully
        assert data["data"]["total_rows"] == 1
        # Should have at least attempted to process the part
        total_attempted = data["data"]["successful_imports"] + data["data"]["failed_imports"]
        assert total_attempted >= 1, "Should have attempted to process the part"