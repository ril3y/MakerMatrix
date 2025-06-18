"""
Unit tests for the dynamic supplier system

Tests the modular supplier architecture including:
- Supplier registry functionality
- Individual supplier implementations
- API endpoint responses
- Frontend service integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from MakerMatrix.suppliers.registry import SupplierRegistry
from MakerMatrix.suppliers.base import BaseSupplier, SupplierInfo, SupplierCapability, FieldDefinition
from MakerMatrix.suppliers.digikey import DigiKeySupplier
from MakerMatrix.suppliers.lcsc import LCSCSupplier
from MakerMatrix.suppliers.mouser import MouserSupplier
from MakerMatrix.routers.supplier_routes import router
from MakerMatrix.models.models import UserModel


class TestSupplierRegistry:
    """Test the supplier registry system"""
    
    def test_registry_has_expected_suppliers(self):
        """Test that all expected suppliers are registered"""
        available_suppliers = SupplierRegistry.get_available_suppliers()
        expected_suppliers = ['digikey', 'lcsc', 'mouser']
        
        assert len(available_suppliers) >= len(expected_suppliers)
        for supplier in expected_suppliers:
            assert supplier in available_suppliers
    
    def test_can_get_supplier_instances(self):
        """Test that we can get supplier instances from registry"""
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            assert supplier is not None
            assert isinstance(supplier, BaseSupplier)
    
    def test_supplier_info_structure(self):
        """Test that supplier info has required fields"""
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            info = supplier.get_supplier_info()
            
            assert isinstance(info, SupplierInfo)
            assert info.name == supplier_name
            assert info.display_name
            assert info.description
            assert isinstance(info.supports_oauth, bool)
    
    def test_supplier_capabilities(self):
        """Test that suppliers have capabilities"""
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            capabilities = supplier.get_capabilities()
            
            assert isinstance(capabilities, list)
            assert len(capabilities) > 0
            for cap in capabilities:
                assert isinstance(cap, SupplierCapability)
    
    def test_supplier_schemas(self):
        """Test that suppliers provide credential and config schemas"""
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            
            cred_schema = supplier.get_credential_schema()
            config_schema = supplier.get_configuration_schema()
            
            assert isinstance(cred_schema, list)
            assert isinstance(config_schema, list)
            
            # LCSC should have no credentials (uses public API)
            if supplier_name == 'lcsc':
                assert len(cred_schema) == 0
            else:
                assert len(cred_schema) > 0


class TestIndividualSuppliers:
    """Test individual supplier implementations"""
    
    def test_digikey_supplier(self):
        """Test DigiKey supplier implementation"""
        supplier = DigiKeySupplier()
        
        # Test info
        info = supplier.get_supplier_info()
        assert info.name == 'digikey'
        assert info.display_name == 'DigiKey Electronics'
        assert info.supports_oauth is True
        
        # Test credentials schema
        cred_schema = supplier.get_credential_schema()
        assert len(cred_schema) >= 2
        field_names = [field.name for field in cred_schema]
        assert 'client_id' in field_names
        assert 'client_secret' in field_names
        
        # Test config schema
        config_schema = supplier.get_configuration_schema()
        assert len(config_schema) > 0
        config_names = [field.name for field in config_schema]
        assert 'sandbox_mode' in config_names
    
    def test_lcsc_supplier(self):
        """Test LCSC supplier implementation"""
        supplier = LCSCSupplier()
        
        # Test info
        info = supplier.get_supplier_info()
        assert info.name == 'lcsc'
        assert info.display_name == 'LCSC Electronics'
        assert info.supports_oauth is False
        
        # Test credentials schema (should be empty - public API)
        cred_schema = supplier.get_credential_schema()
        assert len(cred_schema) == 0
        
        # Test capabilities
        capabilities = supplier.get_capabilities()
        assert SupplierCapability.GET_PART_DETAILS in capabilities
    
    def test_mouser_supplier(self):
        """Test Mouser supplier implementation"""
        supplier = MouserSupplier()
        
        # Test info
        info = supplier.get_supplier_info()
        assert info.name == 'mouser'
        assert info.display_name == 'Mouser Electronics'
        assert info.supports_oauth is False
        
        # Test credentials schema
        cred_schema = supplier.get_credential_schema()
        assert len(cred_schema) >= 1
        field_names = [field.name for field in cred_schema]
        assert 'api_key' in field_names


class TestSupplierAPIEndpoints:
    """Test the supplier API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication"""
        user = Mock(spec=UserModel)
        user.id = "test-user-id"
        user.username = "testuser"
        return user
    
    @pytest.fixture
    def client(self):
        """Test client for API endpoints"""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/suppliers")
        return TestClient(app)
    
    @patch('MakerMatrix.routers.supplier_routes.get_current_user')
    def test_get_all_suppliers_endpoint(self, mock_get_user, client, mock_user):
        """Test the /api/suppliers/ endpoint"""
        mock_get_user.return_value = mock_user
        
        response = client.get("/api/suppliers/")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) >= 3
        assert 'digikey' in data['data']
        assert 'lcsc' in data['data']
        assert 'mouser' in data['data']
    
    @patch('MakerMatrix.routers.supplier_routes.get_current_user')
    def test_get_all_suppliers_info_endpoint(self, mock_get_user, client, mock_user):
        """Test the /api/suppliers/info endpoint"""
        mock_get_user.return_value = mock_user
        
        response = client.get("/api/suppliers/info")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], dict)
        
        # Check that we have info for expected suppliers
        supplier_data = data['data']
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            assert supplier_name in supplier_data
            supplier_info = supplier_data[supplier_name]
            assert 'name' in supplier_info
            assert 'display_name' in supplier_info
            assert 'description' in supplier_info
            assert 'capabilities' in supplier_info
            assert isinstance(supplier_info['capabilities'], list)
    
    @patch('MakerMatrix.routers.supplier_routes.get_current_user')
    def test_get_individual_supplier_info(self, mock_get_user, client, mock_user):
        """Test getting info for individual suppliers"""
        mock_get_user.return_value = mock_user
        
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            response = client.get(f"/api/suppliers/{supplier_name}/info")
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'success'
            assert 'data' in data
            
            supplier_info = data['data']
            assert supplier_info['name'] == supplier_name
            assert 'display_name' in supplier_info
            assert 'capabilities' in supplier_info
    
    @patch('MakerMatrix.routers.supplier_routes.get_current_user')
    def test_get_credential_schema_endpoint(self, mock_get_user, client, mock_user):
        """Test the credential schema endpoints"""
        mock_get_user.return_value = mock_user
        
        # Test DigiKey (should have credentials)
        response = client.get("/api/suppliers/digikey/credentials-schema")
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) >= 2
        
        # Test LCSC (should have no credentials)
        response = client.get("/api/suppliers/lcsc/credentials-schema")
        assert response.status_code == 200
        
        data = response.json()
        assert data['data'] == []
    
    @patch('MakerMatrix.routers.supplier_routes.get_current_user')
    def test_get_config_schema_endpoint(self, mock_get_user, client, mock_user):
        """Test the configuration schema endpoints"""
        mock_get_user.return_value = mock_user
        
        for supplier_name in ['digikey', 'lcsc', 'mouser']:
            response = client.get(f"/api/suppliers/{supplier_name}/config-schema")
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'success'
            assert 'data' in data
            assert isinstance(data['data'], list)


class TestSupplierFrontendIntegration:
    """Test frontend integration scenarios"""
    
    def test_api_response_format_matches_frontend_expectations(self):
        """Test that API responses match what the frontend expects"""
        # This test simulates what the frontend service should receive
        from MakerMatrix.routers.supplier_routes import get_all_suppliers_info
        from MakerMatrix.models.models import UserModel
        
        # Mock user
        mock_user = Mock(spec=UserModel)
        
        # Get the response (this would normally go through FastAPI)
        with patch('MakerMatrix.routers.supplier_routes.get_current_user', return_value=mock_user):
            # Simulate the API call
            suppliers_info = {}
            for name in SupplierRegistry.get_available_suppliers():
                supplier = SupplierRegistry.get_supplier(name)
                info = supplier.get_supplier_info()
                capabilities = [cap.value for cap in supplier.get_capabilities()]
                
                suppliers_info[name] = {
                    'name': info.name,
                    'display_name': info.display_name,
                    'description': info.description,
                    'website_url': info.website_url,
                    'api_documentation_url': info.api_documentation_url,
                    'supports_oauth': info.supports_oauth,
                    'rate_limit_info': info.rate_limit_info,
                    'capabilities': capabilities
                }
            
            # Verify structure matches frontend expectations
            assert isinstance(suppliers_info, dict)
            assert len(suppliers_info) >= 3
            
            for supplier_name, supplier_info in suppliers_info.items():
                assert 'name' in supplier_info
                assert 'display_name' in supplier_info
                assert 'description' in supplier_info
                assert 'capabilities' in supplier_info
                assert isinstance(supplier_info['capabilities'], list)
                assert len(supplier_info['capabilities']) > 0


def test_supplier_system_integration():
    """Integration test for the complete supplier system"""
    # Test that we can:
    # 1. Get list of suppliers
    # 2. Get info for each supplier
    # 3. Get schemas for each supplier
    # 4. Verify data consistency
    
    # 1. Get suppliers
    suppliers = SupplierRegistry.get_available_suppliers()
    assert len(suppliers) >= 3
    
    # 2. Test each supplier
    for supplier_name in suppliers:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        
        # 3. Get info
        info = supplier.get_supplier_info()
        assert info.name == supplier_name
        
        # 4. Get capabilities
        capabilities = supplier.get_capabilities()
        assert len(capabilities) > 0
        
        # 5. Get schemas
        cred_schema = supplier.get_credential_schema()
        config_schema = supplier.get_configuration_schema()
        
        # 6. Verify schema structure
        for field in cred_schema:
            assert isinstance(field, FieldDefinition)
            assert field.name
            assert field.label
            assert field.field_type
        
        for field in config_schema:
            assert isinstance(field, FieldDefinition)
            assert field.name
            assert field.label
            assert field.field_type