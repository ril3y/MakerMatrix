"""
Test suite to ensure API response consistency across all endpoints.
This test validates that all API routes return ResponseSchema consistently.
"""
import pytest
import inspect
import importlib
import os
from typing import get_type_hints, get_origin
from pathlib import Path

from MakerMatrix.schemas.response import ResponseSchema


class TestAPIConsistency:
    """Test class to validate API response consistency."""
    
    def get_all_router_modules(self):
        """Get all router modules from the routers directory."""
        routers_dir = Path(__file__).parent.parent.parent / "routers"
        router_modules = []
        
        for file in routers_dir.glob("*.py"):
            if file.name == "__init__.py":
                continue
            
            module_name = f"MakerMatrix.routers.{file.stem}"
            try:
                module = importlib.import_module(module_name)
                router_modules.append((file.stem, module))
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
        
        return router_modules
    
    def get_route_functions(self, router_module):
        """Extract all route functions from a router module."""
        route_functions = []
        
        if not hasattr(router_module, 'router'):
            return route_functions
        
        router = router_module.router
        
        # Get all routes from the router
        for route in router.routes:
            if hasattr(route, 'endpoint') and hasattr(route, 'methods'):
                # Skip WebSocket routes
                if hasattr(route, 'websocket') or 'websocket' in str(type(route)).lower():
                    continue
                    
                endpoint_func = route.endpoint
                route_functions.append({
                    'function': endpoint_func,
                    'name': endpoint_func.__name__,
                    'path': getattr(route, 'path', 'unknown'),
                    'methods': getattr(route, 'methods', set()),
                    'module': router_module.__name__ if hasattr(router_module, '__name__') else 'unknown'
                })
        
        return route_functions
    
    def test_all_routes_use_response_schema(self):
        """Test that all API routes use ResponseSchema in their return type annotations."""
        router_modules = self.get_all_router_modules()
        non_compliant_routes = []
        
        # Routes that are allowed to have different return types
        allowed_exceptions = {
            'get_image',           # Returns FileResponse
            'serve_index_html',    # Returns FileResponse  
            'upload_image',        # Returns plain dict for image_id
            'get_current_user',    # Auth dependency function
            'serve_frontend',      # Static file serving
            'websocket_endpoint',  # WebSocket endpoints
            'download_backup',     # File download
            'export_data',         # File download
        }
        
        for module_name, module in router_modules:
            route_functions = self.get_route_functions(module)
            
            for route_info in route_functions:
                func = route_info['function']
                func_name = route_info['name']
                
                # Skip allowed exceptions
                if func_name in allowed_exceptions:
                    continue
                
                # Skip internal functions (starting with _)
                if func_name.startswith('_'):
                    continue
                
                # Get type hints
                try:
                    type_hints = get_type_hints(func)
                    return_type = type_hints.get('return', None)
                    
                    if return_type is None:
                        non_compliant_routes.append({
                            'module': module_name,
                            'function': func_name,
                            'path': route_info['path'],
                            'methods': route_info['methods'],
                            'issue': 'No return type annotation'
                        })
                        continue
                    
                    # Check if return type is ResponseSchema or ResponseSchema[T]
                    origin_type = get_origin(return_type)
                    
                    is_response_schema = False
                    
                    if origin_type is None:
                        # Direct type (not generic)
                        is_response_schema = return_type == ResponseSchema
                    else:
                        # Generic type - check if it's ResponseSchema[Something]
                        is_response_schema = origin_type == ResponseSchema
                    
                    if not is_response_schema:
                        # Additional check: maybe it's a string representation of ResponseSchema
                        type_str = str(return_type)
                        if 'ResponseSchema' not in type_str:
                            non_compliant_routes.append({
                                'module': module_name,
                                'function': func_name,
                                'path': route_info['path'],
                                'methods': route_info['methods'],
                                'issue': f'Return type is {return_type}, expected ResponseSchema[T]'
                            })
                
                except Exception as e:
                    non_compliant_routes.append({
                        'module': module_name,
                        'function': func_name,
                        'path': route_info['path'],
                        'methods': route_info['methods'],
                        'issue': f'Error analyzing type hints: {e}'
                    })
        
        # Report findings
        if non_compliant_routes:
            error_msg = "Found API routes that don't use ResponseSchema:\n"
            for route in non_compliant_routes:
                error_msg += f"  - {route['module']}.{route['function']} ({route['path']}) [{', '.join(route['methods'])}]: {route['issue']}\n"
            
            pytest.fail(error_msg)
    
    def test_response_schema_structure(self):
        """Test that ResponseSchema has the expected structure."""
        # Verify ResponseSchema has required fields
        schema_fields = ResponseSchema.__annotations__
        
        required_fields = {'status', 'message'}
        for field in required_fields:
            assert field in schema_fields, f"ResponseSchema missing required field: {field}"
        
        # Verify optional fields exist
        optional_fields = {'data', 'page', 'page_size', 'total_parts'}
        for field in optional_fields:
            assert field in schema_fields, f"ResponseSchema missing optional field: {field}"
    
    def test_import_all_router_modules(self):
        """Test that all router modules can be imported successfully."""
        router_modules = self.get_all_router_modules()
        assert len(router_modules) > 0, "No router modules found"
        
        for module_name, module in router_modules:
            assert hasattr(module, 'router'), f"Module {module_name} doesn't have a 'router' attribute"


class TestAPIReturnConsistency:
    """Integration tests to verify actual API return consistency."""
    
    @pytest.mark.integration 
    def test_api_returns_are_valid_response_schema(self):
        """Test that API endpoints return valid ResponseSchema structure."""
        # This test requires the FastAPI test client
        # Will be implemented as integration test
        pass
    
    def test_response_schema_validation(self):
        """Test ResponseSchema validation logic."""
        from pydantic import ValidationError
        
        # Test valid ResponseSchema
        valid_response = ResponseSchema(
            status="success",
            message="Test message",
            data={"test": "data"}
        )
        assert valid_response.status == "success"
        assert valid_response.message == "Test message"
        assert valid_response.data == {"test": "data"}
        
        # Test that status is required
        with pytest.raises(ValidationError):
            ResponseSchema(message="Test message")
        
        # Test that message is required  
        with pytest.raises(ValidationError):
            ResponseSchema(status="success")