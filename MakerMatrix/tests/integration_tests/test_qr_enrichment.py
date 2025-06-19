"""
Pytest integration tests for QR code part creation with enrichment functionality.
Tests the enhanced add_part endpoint with automatic enrichment capabilities.
"""

import pytest
import requests
import json
import asyncio
from typing import Dict, Any
from unittest.mock import patch, MagicMock

from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.services.part_service import PartService
from MakerMatrix.models.task_models import TaskType, TaskPriority, TaskStatus
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError


class TestQREnrichmentIntegration:
    """Integration tests for QR-based part creation with enrichment"""
    
    @pytest.fixture
    def auth_headers(self, authenticated_client):
        """Get authentication headers for API calls"""
        return {"Authorization": f"Bearer {authenticated_client['token']}"}
    
    @pytest.fixture
    def sample_qr_part_data(self):
        """Sample QR code data from LCSC"""
        return {
            "part_number": "C136648",
            "part_name": "LMR16030SDDAR_TEST",
            "description": "DC-DC Buck Converter IC",
            "quantity": 5,
            "supplier": "LCSC",
            "auto_enrich": True,
            "enrichment_supplier": "LCSC",
            "enrichment_capabilities": ["fetch_datasheet", "fetch_image", "fetch_pricing"]
        }
    
    @pytest.fixture
    def invalid_supplier_data(self):
        """Sample data with invalid supplier"""
        return {
            "part_number": "TEST123",
            "part_name": "Test_Part_Invalid_Supplier",
            "quantity": 1,
            "supplier": "InvalidSupplier",
            "auto_enrich": True,
            "enrichment_supplier": "InvalidSupplier"
        }

    def test_part_create_schema_enrichment_fields(self):
        """Test that PartCreate schema accepts enrichment parameters"""
        part_data = {
            "part_name": "Test Part",
            "quantity": 1,
            "auto_enrich": True,
            "enrichment_supplier": "LCSC",
            "enrichment_capabilities": ["fetch_datasheet"]
        }
        
        part_create = PartCreate(**part_data)
        assert part_create.auto_enrich is True
        assert part_create.enrichment_supplier == "LCSC"
        assert part_create.enrichment_capabilities == ["fetch_datasheet"]

    def test_part_create_schema_default_values(self):
        """Test that enrichment fields have correct defaults"""
        part_data = {
            "part_name": "Test Part",
            "quantity": 1
        }
        
        part_create = PartCreate(**part_data)
        assert part_create.auto_enrich is False
        assert part_create.enrichment_supplier is None
        assert part_create.enrichment_capabilities == []

    @pytest.mark.integration
    def test_qr_part_creation_without_enrichment(self, client, auth_headers):
        """Test basic QR part creation without enrichment"""
        part_data = {
            "part_number": "C123456",
            "part_name": "Basic_QR_Test_Part",
            "description": "Basic test part from QR",
            "quantity": 3,
            "supplier": "LCSC"
            # auto_enrich defaults to False
        }
        
        response = client.post("/parts/add_part", json=part_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["data"]["part_name"] == "Basic_QR_Test_Part"
        assert result["data"]["supplier"] == "LCSC"
        assert "enrichment" not in result["message"].lower()

    @pytest.mark.integration
    def test_qr_part_creation_with_invalid_supplier(self, client, auth_headers, invalid_supplier_data):
        """Test QR part creation with invalid supplier shows warning"""
        response = client.post("/parts/add_part", json=invalid_supplier_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "not configured on backend" in result["message"]

    @pytest.mark.integration 
    @patch('MakerMatrix.suppliers.registry.get_available_suppliers')
    @patch('MakerMatrix.services.supplier_config_service.SupplierConfigService.get_supplier_config')
    @patch('MakerMatrix.services.task_service.get_task_service')
    def test_qr_part_creation_with_enrichment_success(
        self, 
        mock_task_service,
        mock_supplier_config,
        mock_available_suppliers,
        client, 
        auth_headers, 
        sample_qr_part_data
    ):
        """Test successful QR part creation with enrichment"""
        
        # Mock supplier validation
        mock_available_suppliers.return_value = ["LCSC", "DigiKey", "Mouser"]
        mock_supplier_config.return_value = MagicMock()
        
        # Mock task service
        mock_task_instance = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = TaskStatus.COMPLETED
        mock_task_instance.create_task.return_value = mock_task
        mock_task_instance.get_task.return_value = mock_task
        mock_task_service.return_value = mock_task_instance
        
        # Mock part service to return enriched data
        with patch.object(PartService, 'get_part_by_id') as mock_get_part:
            mock_get_part.return_value = {
                "status": "success",
                "data": {
                    "id": "test-part-id",
                    "part_name": "LMR16030SDDAR_TEST",
                    "supplier": "LCSC",
                    "description": "Enriched description with more details",
                    "additional_properties": {"datasheet_url": "http://example.com/datasheet.pdf"}
                }
            }
            
            response = client.post("/parts/add_part", json=sample_qr_part_data, headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert "successfully enriched" in result["message"]
            
            # Verify task was created with correct parameters
            mock_task_instance.create_task.assert_called_once()
            call_args = mock_task_instance.create_task.call_args[0][0]  # First positional arg
            assert call_args.task_type == TaskType.PART_ENRICHMENT
            assert "QR Part Enrichment" in call_args.name
            assert call_args.priority == TaskPriority.HIGH

    @pytest.mark.integration
    @patch('MakerMatrix.suppliers.registry.get_available_suppliers')
    @patch('MakerMatrix.services.supplier_config_service.SupplierConfigService.get_supplier_config')
    def test_qr_part_creation_supplier_not_configured(
        self,
        mock_supplier_config,
        mock_available_suppliers,
        client,
        auth_headers,
        sample_qr_part_data
    ):
        """Test QR part creation when supplier exists but not configured"""
        
        # Mock supplier exists but not configured
        mock_available_suppliers.return_value = ["LCSC", "DigiKey"]
        mock_supplier_config.side_effect = ResourceNotFoundError("Supplier not configured")
        
        response = client.post("/parts/add_part", json=sample_qr_part_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "not properly configured" in result["message"]

    @pytest.mark.integration
    @patch('MakerMatrix.suppliers.registry.get_available_suppliers')
    @patch('MakerMatrix.services.supplier_config_service.SupplierConfigService.get_supplier_config')
    @patch('MakerMatrix.services.task_service.get_task_service')
    def test_qr_part_creation_enrichment_timeout(
        self,
        mock_task_service,
        mock_supplier_config,
        mock_available_suppliers,
        client,
        auth_headers,
        sample_qr_part_data
    ):
        """Test QR part creation when enrichment times out"""
        
        # Mock supplier validation
        mock_available_suppliers.return_value = ["LCSC"]
        mock_supplier_config.return_value = MagicMock()
        
        # Mock task service with task that never completes
        mock_task_instance = MagicMock()
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_task.status = TaskStatus.RUNNING  # Always running, never completes
        mock_task_instance.create_task.return_value = mock_task
        mock_task_instance.get_task.return_value = mock_task
        mock_task_service.return_value = mock_task_instance
        
        # Patch the timeout to be very short for testing
        with patch('MakerMatrix.routers.parts_routes._wait_for_enrichment_completion') as mock_wait:
            mock_wait.return_value = None  # Simulate timeout
            
            response = client.post("/parts/add_part", json=sample_qr_part_data, headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            assert "did not complete within timeout" in result["message"]

    def test_enrichment_capabilities_validation(self):
        """Test that various enrichment capabilities are accepted"""
        valid_capabilities = [
            ["fetch_datasheet"],
            ["fetch_image"], 
            ["fetch_pricing"],
            ["fetch_datasheet", "fetch_image", "fetch_pricing"],
            []  # Empty list should be valid
        ]
        
        for capabilities in valid_capabilities:
            part_data = {
                "part_name": f"Test Part {len(capabilities)}",
                "quantity": 1,
                "auto_enrich": True,
                "enrichment_supplier": "LCSC",
                "enrichment_capabilities": capabilities
            }
            
            part_create = PartCreate(**part_data)
            assert part_create.enrichment_capabilities == capabilities

    def test_qr_data_format_compatibility(self):
        """Test that the schema handles QR data format from the example"""
        # Based on the QR format: {pbn:PICK2311010075,on:GB2311011210,pc:C136648,pm:LMR16030SDDAR,qty:5,mc:10,cc:1,pdi:95387529,hp:0,wc:ZH}
        qr_extracted_data = {
            "part_number": "C136648",  # pc field
            "part_name": "LMR16030SDDAR",  # pm field  
            "quantity": 5,  # qty field
            "supplier": "LCSC",  # Known from QR scanner context
            "auto_enrich": True,
            "enrichment_supplier": "LCSC"
        }
        
        part_create = PartCreate(**qr_extracted_data)
        assert part_create.part_number == "C136648"
        assert part_create.part_name == "LMR16030SDDAR"
        assert part_create.quantity == 5
        assert part_create.auto_enrich is True

    @pytest.mark.integration
    def test_supplier_capabilities_endpoint(self, client, auth_headers):
        """Test that supplier capabilities endpoint works for validation"""
        response = client.get("/tasks/capabilities/suppliers", headers=auth_headers)
        
        # Should return supplier capabilities (even if empty)
        assert response.status_code == 200
        result = response.json()
        assert "data" in result

    def test_part_create_validation_with_enrichment(self):
        """Test that part validation still works with enrichment fields"""
        # Should fail without part_name or part_number
        with pytest.raises(ValueError, match="Either part_name or part_number must be provided"):
            PartCreate(
                quantity=1,
                auto_enrich=True,
                enrichment_supplier="LCSC"
            )
        
        # Should work with part_name
        part = PartCreate(
            part_name="Test Part",
            quantity=1,
            auto_enrich=True,
            enrichment_supplier="LCSC"
        )
        assert part.part_name == "Test Part"
        
        # Should work with part_number
        part = PartCreate(
            part_number="TEST123",
            quantity=1,
            auto_enrich=True,
            enrichment_supplier="LCSC"
        )
        assert part.part_number == "TEST123"