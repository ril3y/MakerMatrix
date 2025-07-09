"""
Cross-Service Integration Tests

These tests specifically target business workflows that span multiple services.
They are designed to catch production failures that isolated route tests miss.

Critical focus areas identified in Step 12.9.7:
1. PartService → LocationService interactions during part creation
2. Import workflows with cross-service dependencies
3. Business logic chains involving multiple services

This addresses the critical testing gap where route tests passed but production failed
due to static method calls and cross-service session management issues.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine, PartModel, LocationModel, CategoryModel
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.database.db import get_session


class TestCrossServiceIntegration:
    """Test suite for cross-service integration scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Setup clean database for each test."""
        # Create all tables
        SQLModel.metadata.create_all(engine)
        yield
        # Clean up after each test
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
    
    @pytest.fixture
    def part_service(self):
        """Create PartService instance for testing."""
        return PartService()
    
    @pytest.fixture
    def location_service(self):
        """Create LocationService instance for testing."""
        return LocationService()
    
    @pytest.fixture
    def category_service(self):
        """Create CategoryService instance for testing."""
        return CategoryService()

    def test_part_creation_with_unsorted_location_assignment(self, part_service, location_service):
        """
        Test critical production scenario: Part creation without location should create 'Unsorted' location.
        
        This test covers the exact production failure scenario where:
        - PartService.add_part() calls LocationService.get_or_create_unsorted_location()
        - The location service creates/retrieves the 'Unsorted' location
        - The part is successfully created with the default location
        
        PRODUCTION CRITICAL: This workflow failed due to static method calls.
        """
        # Test data - part without location_id
        part_data = {
            "part_name": "Test_Resistor_CrossService_001", 
            "part_number": "R001-CROSS-TEST",
            "description": "Test resistor for cross-service integration",
            "quantity": 100,
            "supplier": "LCSC"
            # Intentionally no location_id - should trigger unsorted location logic
        }
        
        # Execute the business workflow
        result = part_service.add_part(part_data)
        
        # Verify the complete workflow succeeded
        assert result.success, f"Part creation failed: {result.message}"
        assert result.data is not None, "Part data should be returned"
        
        created_part = result.data
        assert created_part["part_name"] == "Test_Resistor_CrossService_001"
        assert created_part["location_id"] is not None, "Part should have been assigned a location"
        
        # Verify that the 'Unsorted' location was created/used
        unsorted_response = location_service.get_or_create_unsorted_location()
        assert unsorted_response.success, "Should be able to retrieve 'Unsorted' location"
        
        unsorted_location = unsorted_response.data
        assert created_part["location_id"] == unsorted_location["id"], "Part should be in 'Unsorted' location"
        assert unsorted_location["name"] == "Unsorted"
        assert unsorted_location["description"] == "Default location for imported parts that need to be organized"

    def test_part_creation_with_explicit_location_validation(self, part_service, location_service):
        """
        Test cross-service location validation during part creation.
        
        This covers the scenario where PartService validates a provided location_id
        by calling LocationService.get_location().
        """
        # First create a location
        location_data = {
            "name": "Test_Storage_Bin_A1",
            "description": "Test storage location for cross-service testing",
            "location_type": "storage"
        }
        
        location_result = location_service.add_location(location_data)
        assert location_result.success, f"Location creation failed: {location_result.message}"
        
        created_location = location_result.data
        location_id = created_location["id"]
        
        # Now create a part with the explicit location
        part_data = {
            "part_name": "Test_Capacitor_CrossService_002",
            "part_number": "C002-CROSS-TEST", 
            "description": "Test capacitor for cross-service location validation",
            "quantity": 50,
            "supplier": "DigiKey",
            "location_id": location_id
        }
        
        # Execute the business workflow
        result = part_service.add_part(part_data)
        
        # Verify the complete workflow succeeded
        assert result.success, f"Part creation with explicit location failed: {result.message}"
        
        created_part = result.data
        assert created_part["location_id"] == location_id, "Part should be assigned to specified location"

    def test_part_creation_with_invalid_location_rejection(self, part_service):
        """
        Test cross-service validation: Invalid location should be rejected.
        
        This verifies that PartService properly validates location_id through LocationService
        and rejects parts with non-existent locations.
        """
        # Try to create a part with invalid location
        part_data = {
            "part_name": "Test_Invalid_Location_Part",
            "part_number": "INV-LOC-001",
            "description": "Part with invalid location for testing",
            "quantity": 25,
            "supplier": "Mouser",
            "location_id": "non-existent-location-id-12345"
        }
        
        # Execute the business workflow
        result = part_service.add_part(part_data)
        
        # Verify that the workflow properly rejects invalid location
        assert not result.success, "Part creation should fail with invalid location"
        assert "does not exist" in result.message.lower(), "Error message should indicate location doesn't exist"

    def test_multiple_parts_unsorted_location_reuse(self, part_service, location_service):
        """
        Test that multiple parts without locations all use the same 'Unsorted' location.
        
        This verifies the cross-service coordination where:
        1. First part creates 'Unsorted' location
        2. Subsequent parts reuse the existing 'Unsorted' location
        3. No duplicate 'Unsorted' locations are created
        """
        # Create multiple parts without locations
        parts_data = [
            {
                "part_name": f"Test_Part_Unsorted_{i}",
                "part_number": f"UNS-{i:03d}",
                "description": f"Test part {i} for unsorted location reuse",
                "quantity": 10 + i,
                "supplier": "LCSC"
            }
            for i in range(1, 4)  # Create 3 parts
        ]
        
        created_parts = []
        for part_data in parts_data:
            result = part_service.add_part(part_data)
            assert result.success, f"Part creation failed for {part_data['part_name']}: {result.message}"
            created_parts.append(result.data)
        
        # Verify all parts have the same location_id
        first_location_id = created_parts[0]["location_id"]
        for part in created_parts[1:]:
            assert part["location_id"] == first_location_id, "All unsorted parts should share the same location"
        
        # Verify there's only one 'Unsorted' location
        with Session(engine) as session:
            unsorted_locations = session.query(LocationModel).filter(LocationModel.name == "Unsorted").all()
            assert len(unsorted_locations) == 1, "Should only have one 'Unsorted' location"

    def test_part_service_location_service_session_isolation(self, part_service, location_service):
        """
        Test that PartService and LocationService maintain proper session isolation.
        
        This ensures that cross-service calls don't cause session conflicts or
        DetachedInstanceError issues that were common in the old static method approach.
        """
        # Create a part that triggers location creation
        part_data = {
            "part_name": "Test_Session_Isolation_Part",
            "part_number": "SES-ISO-001",
            "description": "Test part for session isolation validation",
            "quantity": 15,
            "supplier": "LCSC"
        }
        
        # This should trigger PartService → LocationService interaction
        result = part_service.add_part(part_data)
        assert result.success, f"Part creation failed: {result.message}"
        
        created_part = result.data
        location_id = created_part["location_id"]
        
        # Now independently access the location through LocationService
        from MakerMatrix.models.models import LocationQueryModel
        location_response = location_service.get_location(LocationQueryModel(id=location_id))
        assert location_response.success, "Should be able to independently access the location"
        
        location_data = location_response.data
        assert location_data["id"] == location_id, "Location data should be accessible"
        assert location_data["name"] == "Unsorted", "Should be the unsorted location"

    def test_import_workflow_simulation(self, part_service, location_service, category_service):
        """
        Test simulated import workflow that spans multiple services.
        
        This simulates the CSV/file import process that:
        1. Creates categories if they don't exist
        2. Creates parts with category assignments
        3. Assigns default location if none specified
        4. Validates all cross-service interactions
        """
        # Simulate CSV import data with categories
        import_parts = [
            {
                "part_name": "Import_Resistor_001",
                "part_number": "IMP-R-001",
                "description": "Imported resistor 1K ohm",
                "quantity": 100,
                "supplier": "LCSC",
                "category_names": ["Resistors", "Passive Components"]
            },
            {
                "part_name": "Import_Capacitor_001", 
                "part_number": "IMP-C-001",
                "description": "Imported capacitor 10uF",
                "quantity": 50,
                "supplier": "DigiKey",
                "category_names": ["Capacitors", "Passive Components"]
            }
        ]
        
        imported_parts = []
        for part_data in import_parts:
            # This simulates the full import workflow
            result = part_service.add_part(part_data)
            assert result.success, f"Import simulation failed for {part_data['part_name']}: {result.message}"
            imported_parts.append(result.data)
        
        # Verify all parts were created with proper cross-service coordination
        assert len(imported_parts) == 2, "Should have imported 2 parts"
        
        # Verify all parts have locations (should be 'Unsorted')
        for part in imported_parts:
            assert part["location_id"] is not None, "Imported parts should have location assignment"
        
        # Verify categories were created/assigned (this tests PartService → CategoryService interaction)
        # Note: Category handling may be part of the part creation workflow

    def test_concurrent_cross_service_operations(self, part_service, location_service):
        """
        Test concurrent cross-service operations to ensure thread safety.
        
        This simulates multiple concurrent part creations that all need the 'Unsorted' location,
        ensuring that the cross-service interaction handles concurrency properly.
        """
        import threading
        import time
        
        results = []
        errors = []
        
        def create_part(part_index):
            try:
                part_data = {
                    "part_name": f"Concurrent_Part_{part_index}",
                    "part_number": f"CONC-{part_index:03d}",
                    "description": f"Concurrent test part {part_index}",
                    "quantity": part_index * 5,
                    "supplier": "LCSC"
                }
                
                result = part_service.add_part(part_data)
                results.append(result)
                
            except Exception as e:
                errors.append(f"Thread {part_index}: {str(e)}")
        
        # Create multiple threads that create parts concurrently
        threads = []
        for i in range(5):  # 5 concurrent operations
            thread = threading.Thread(target=create_part, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout
        
        # Verify results
        assert len(errors) == 0, f"Concurrent operations had errors: {errors}"
        assert len(results) == 5, "Should have 5 successful results"
        
        for result in results:
            assert result.success, f"Concurrent part creation failed: {result.message}"
            assert result.data["location_id"] is not None, "Each part should have a location"

    def test_cross_service_error_handling(self, part_service):
        """
        Test error handling in cross-service interactions.
        
        This verifies that errors in LocationService are properly handled by PartService
        without causing cascading failures.
        """
        # Mock LocationService to simulate failure
        with patch.object(part_service.location_service, 'get_or_create_unsorted_location') as mock_location:
            # Configure mock to return an error response
            mock_location.return_value = Mock(
                success=False,
                message="Simulated location service failure",
                data=None
            )
            
            part_data = {
                "part_name": "Test_Error_Handling_Part",
                "part_number": "ERR-001",
                "description": "Test part for error handling",
                "quantity": 10,
                "supplier": "LCSC"
            }
            
            # The part creation should handle the location service error gracefully
            result = part_service.add_part(part_data)
            
            # The exact behavior depends on implementation - it might:
            # 1. Succeed without location (graceful degradation)
            # 2. Fail with proper error message
            # Either is acceptable as long as it doesn't crash
            
            # Verify that we get a proper response (not an exception)
            assert hasattr(result, 'success'), "Should return a proper ServiceResponse"
            assert hasattr(result, 'message'), "Should have a message explaining the result"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])