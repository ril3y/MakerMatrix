"""
Unit tests for Part include parameter functionality
"""

import pytest
from sqlmodel import Session
from MakerMatrix.models.models import PartModel, CategoryModel, engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService
from MakerMatrix.tests.unit_tests.test_database import create_test_db


class TestPartIncludeParameter:
    """Test cases for Part include parameter functionality"""

    def setup_method(self):
        """Set up test database for each test"""
        self.test_db = create_test_db()

    def test_part_to_dict_basic(self):
        """Test part to_dict() without include parameter (default lightweight)"""
        with Session(self.test_db.engine) as session:
            # Create a basic part
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-001",
                description="Test part description",
                quantity=10,
                supplier="LCSC"
            )
            
            # Convert to dict without include parameter
            part_dict = part.to_dict()
            
            # Should NOT include order data by default
            assert "order_summary" not in part_dict
            assert "order_history" not in part_dict
            assert "datasheets" not in part_dict
            
            # Should include basic fields
            assert part_dict["part_name"] == "Test Part"
            assert part_dict["part_number"] == "TEST-001"
            assert part_dict["description"] == "Test part description"
            assert part_dict["categories"] == []

    def test_part_to_dict_include_orders(self):
        """Test part to_dict() with include=['orders']"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-002",
                description="Test part with orders",
                quantity=5,
                supplier="LCSC"
            )
            
            # Convert to dict with orders included
            part_dict = part.to_dict(include=['orders'])
            
            # Should include order data (even if empty)
            assert "order_summary" in part_dict
            assert "order_history" in part_dict
            assert part_dict["order_summary"] is None  # No orders yet
            assert part_dict["order_history"] == []   # Empty list
            
            # Should NOT include datasheets (not requested)
            assert "datasheets" not in part_dict

    def test_part_to_dict_include_datasheets(self):
        """Test part to_dict() with include=['datasheets']"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-003", 
                description="Test part with datasheets",
                quantity=7,
                supplier="DigiKey"
            )
            
            # Convert to dict with datasheets included
            part_dict = part.to_dict(include=['datasheets'])
            
            # Should include datasheet data (even if empty)
            assert "datasheets" in part_dict
            assert part_dict["datasheets"] == []  # Empty list
            
            # Should NOT include order data (not requested)
            assert "order_summary" not in part_dict
            assert "order_history" not in part_dict

    def test_part_to_dict_include_all(self):
        """Test part to_dict() with include=['all']"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-004",
                description="Test part with all data",
                quantity=15,
                supplier="Mouser"
            )
            
            # Convert to dict with all data included
            part_dict = part.to_dict(include=['all'])
            
            # Should include all optional data
            assert "order_summary" in part_dict
            assert "order_history" in part_dict  
            assert "datasheets" in part_dict
            
            # All should be empty for new part
            assert part_dict["order_summary"] is None
            assert part_dict["order_history"] == []
            assert part_dict["datasheets"] == []

    def test_part_to_dict_include_multiple(self):
        """Test part to_dict() with include=['orders', 'datasheets']"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part", 
                part_number="TEST-005",
                description="Test part with multiple includes",
                quantity=20,
                supplier="LCSC"
            )
            
            # Convert to dict with multiple includes
            part_dict = part.to_dict(include=['orders', 'datasheets'])
            
            # Should include both orders and datasheets
            assert "order_summary" in part_dict
            assert "order_history" in part_dict
            assert "datasheets" in part_dict

    def test_part_service_get_by_id_with_include(self):
        """Test PartService.get_part_by_id() with include parameter"""
        import uuid
        # Use the PartService to create the part so it's properly committed
        unique_id = str(uuid.uuid4())[:8]
        part_data = {
            "part_name": f"Service Test Part {unique_id}",
            "part_number": f"SVC-{unique_id}", 
            "description": "Test part for service include test",
            "quantity": 30,
            "supplier": "LCSC"
        }
        
        # Create part using PartService
        create_response = PartService.add_part(part_data)
        assert create_response["status"] == "success"
        part_id = create_response["data"]["id"]
        
        # Test service method without include (lightweight)
        response = PartService.get_part_by_id(part_id)
        assert response["status"] == "success"
        part_data = response["data"]
        
        # Should not have order data in lightweight response
        # Note: The PartResponse schema might still include these fields
        # but they should be None/empty in the basic response
        
        # Test service method with include=orders
        response_with_orders = PartService.get_part_by_id(part_id, include=['orders'])
        assert response_with_orders["status"] == "success"
        part_data_with_orders = response_with_orders["data"]
        
        # This should work without errors
        assert part_data_with_orders["id"] == part_id

    def test_invalid_include_parameter(self):
        """Test part to_dict() with invalid include values"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-006",
                description="Test part for invalid include",
                quantity=5,
                supplier="LCSC"
            )
            
            # Invalid include values should be ignored gracefully
            part_dict = part.to_dict(include=['invalid', 'nonexistent'])
            
            # Should return basic part data without optional fields
            assert "order_summary" not in part_dict
            assert "order_history" not in part_dict
            assert "datasheets" not in part_dict
            assert part_dict["part_name"] == "Test Part"

    def test_empty_include_parameter(self):
        """Test part to_dict() with empty include list"""
        with Session(self.test_db.engine) as session:
            part = PartModel(
                part_name="Test Part",
                part_number="TEST-007",
                description="Test part for empty include",
                quantity=8,
                supplier="LCSC"
            )
            
            # Empty include should be same as no include
            part_dict_empty = part.to_dict(include=[])
            part_dict_none = part.to_dict(include=None)
            part_dict_default = part.to_dict()
            
            # All should be equivalent (no optional data)
            for part_dict in [part_dict_empty, part_dict_none, part_dict_default]:
                assert "order_summary" not in part_dict
                assert "order_history" not in part_dict
                assert "datasheets" not in part_dict
                assert part_dict["part_name"] == "Test Part"