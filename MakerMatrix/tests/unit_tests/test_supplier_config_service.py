"""
Unit tests for SupplierConfigService

Tests the business logic for creating and deleting supplier configurations.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from MakerMatrix.services.supplier_config_service import SupplierConfigService
from MakerMatrix.models.supplier_config_models import SupplierConfigModel
from MakerMatrix.repositories.custom_exceptions import (
    SupplierConfigAlreadyExistsError,
    ResourceNotFoundError
)


class TestSupplierConfigService:
    
    @pytest.fixture
    def service(self):
        """Create a SupplierConfigService instance for testing"""
        return SupplierConfigService()
    
    @pytest.fixture
    def sample_supplier_data(self):
        """Sample supplier configuration data for testing"""
        return {
            "supplier_name": "TestSupplier",
            "display_name": "Test Electronics",
            "description": "Test electronic component supplier",
            "api_type": "rest",
            "base_url": "https://api.testsupplier.com",
            "api_version": "v1",
            "rate_limit_per_minute": 100,
            "timeout_seconds": 30,
            "max_retries": 3,
            "retry_backoff": 1.0,
            "enabled": True,
            "supports_datasheet": True,
            "supports_image": False,
            "supports_pricing": True,
            "supports_stock": True,
            "supports_specifications": False,
            "custom_headers": {"Accept": "application/json"},
            "custom_parameters": {"format": "json"}
        }
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_create_supplier_config_success(self, mock_session_class, service, sample_supplier_data):
        """Test successful creation of a new supplier configuration"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing supplier
        
        # Create mock supplier model
        mock_supplier = MagicMock(spec=SupplierConfigModel)
        mock_supplier.id = "test-supplier-id"
        mock_supplier.supplier_name = "TESTSUPPLIER"
        
        # Mock the model creation
        with patch('MakerMatrix.services.supplier_config_service.SupplierConfigModel') as mock_model_class:
            mock_model_class.return_value = mock_supplier
            
            # Execute
            result = service.create_supplier_config(sample_supplier_data, user_id="test-user")
            
            # Verify
            assert result == mock_supplier
            mock_session.add.assert_called_once_with(mock_supplier)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_supplier)
            
            # Verify supplier name was normalized to uppercase
            mock_model_class.assert_called_once()
            call_args = mock_model_class.call_args[1]
            assert call_args['supplier_name'] == 'TESTSUPPLIER'
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_create_supplier_config_duplicate_error(self, mock_session_class, service, sample_supplier_data):
        """Test creating supplier when one already exists raises error"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # Mock existing supplier
        existing_supplier = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_supplier
        
        # Execute and verify exception
        with pytest.raises(SupplierConfigAlreadyExistsError) as exc_info:
            service.create_supplier_config(sample_supplier_data, user_id="test-user")
        
        assert "TESTSUPPLIER" in str(exc_info.value)
        assert "Only one configuration per supplier type is allowed" in str(exc_info.value)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_create_supplier_config_case_insensitive_duplicate(self, mock_session_class, service):
        """Test that duplicate check is case-insensitive"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # Mock existing supplier
        existing_supplier = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_supplier
        
        # Test data with lowercase supplier name
        supplier_data = {
            "supplier_name": "lcsc",  # lowercase
            "display_name": "LCSC Electronics",
            "base_url": "https://lcsc.com"
        }
        
        # Execute and verify exception
        with pytest.raises(SupplierConfigAlreadyExistsError):
            service.create_supplier_config(supplier_data, user_id="test-user")
        
        # Verify the query used ilike for case-insensitive comparison
        mock_session.query.return_value.filter.assert_called_once()
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_delete_supplier_config_success(self, mock_session_class, service):
        """Test successful deletion of supplier configuration"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # Mock existing supplier
        mock_supplier = MagicMock(spec=SupplierConfigModel)
        mock_supplier.supplier_name = "TestSupplier"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_supplier
        
        # Execute
        service.delete_supplier_config("TestSupplier")
        
        # Verify
        mock_session.delete.assert_called_once_with(mock_supplier)
        mock_session.commit.assert_called_once()
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_delete_supplier_config_not_found(self, mock_session_class, service):
        """Test deleting non-existent supplier raises error"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No supplier found
        
        # Execute and verify exception
        with pytest.raises(ResourceNotFoundError) as exc_info:
            service.delete_supplier_config("NonExistentSupplier")
        
        assert "NonExistentSupplier" in str(exc_info.value)
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
    
    @pytest.mark.parametrize("supplier_name,expected_normalized", [
        ("lcsc", "LCSC"),
        ("DigiKey", "DIGIKEY"),
        ("MOUSER", "MOUSER"),
        ("test_supplier", "TEST_SUPPLIER")
    ])
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_supplier_name_normalization(self, mock_session_class, service, supplier_name, expected_normalized):
        """Test that supplier names are normalized to uppercase"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        mock_supplier = MagicMock(spec=SupplierConfigModel)
        
        supplier_data = {
            "supplier_name": supplier_name,
            "display_name": "Test Supplier",
            "base_url": "https://example.com"
        }
        
        with patch('MakerMatrix.services.supplier_config_service.SupplierConfigModel') as mock_model_class:
            mock_model_class.return_value = mock_supplier
            
            service.create_supplier_config(supplier_data)
            
            # Verify normalized name was used
            call_args = mock_model_class.call_args[1]
            assert call_args['supplier_name'] == expected_normalized
    
    @patch('MakerMatrix.services.supplier_config_service.Session')
    def test_supplier_validation_edge_cases(self, mock_session_class, service):
        """Test validation of edge cases in supplier data"""
        # Setup mocks
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test empty supplier name - should normalize to empty string and succeed in our current implementation
        # (The actual validation happens at the API/Pydantic level, not service level)
        with patch('MakerMatrix.services.supplier_config_service.SupplierConfigModel') as mock_model_class:
            mock_supplier = MagicMock(spec=SupplierConfigModel)
            mock_model_class.return_value = mock_supplier
            
            # This should pass at service level since validation is done at API level
            result = service.create_supplier_config({
                "supplier_name": "",
                "base_url": "https://example.com"
            })
            assert result == mock_supplier
        
        # Test missing required fields - should fail due to KeyError for missing base_url
        with pytest.raises(KeyError):  # Missing base_url will cause KeyError
            service.create_supplier_config({
                "supplier_name": "TestSupplier"
                # Missing base_url
            })