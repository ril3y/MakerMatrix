"""
Dynamic Supplier Registry

Automatically discovers and registers all supplier clients in the suppliers directory.
No need to manually register or hardcode supplier names - just drop a new supplier 
class into the directory and it becomes available.
"""

import os
import importlib
import inspect
from typing import Dict, Type, List, Optional
from pathlib import Path
import logging

from .base_supplier_client import BaseSupplierClient

logger = logging.getLogger(__name__)


class SupplierRegistry:
    """
    Dynamically discovers and manages supplier clients
    """
    
    def __init__(self):
        self._suppliers: Dict[str, Type[BaseSupplierClient]] = {}
        self._discover_suppliers()
    
    def _discover_suppliers(self):
        """
        Automatically discover all supplier clients in the suppliers directory
        """
        suppliers_dir = Path(__file__).parent
        
        # Find all Python files in the suppliers directory
        for file_path in suppliers_dir.glob("*.py"):
            if file_path.name.startswith("_") or file_path.name in ["base_supplier_client.py", "supplier_registry.py"]:
                continue
                
            module_name = file_path.stem
            try:
                # Import the module dynamically
                module = importlib.import_module(f".{module_name}", package=__package__)
                
                # Find all classes that inherit from BaseSupplierClient
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseSupplierClient) and 
                        obj != BaseSupplierClient and 
                        not inspect.isabstract(obj)):
                        
                        # Extract supplier name from class (remove "Client" suffix if present)
                        supplier_name = obj.__name__
                        if supplier_name.endswith("Client"):
                            supplier_name = supplier_name[:-6]  # Remove "Client"
                        
                        # Register the supplier
                        self._suppliers[supplier_name.upper()] = obj
                        logger.info(f"Discovered supplier: {supplier_name} -> {obj.__name__}")
                        
            except Exception as e:
                logger.warning(f"Failed to import supplier module {module_name}: {e}")
    
    def get_supplier_class(self, supplier_name: str) -> Optional[Type[BaseSupplierClient]]:
        """
        Get a supplier class by name
        
        Args:
            supplier_name: Name of the supplier (case insensitive)
            
        Returns:
            Supplier class or None if not found
        """
        return self._suppliers.get(supplier_name.upper())
    
    def get_available_suppliers(self) -> List[str]:
        """
        Get list of available supplier names
        
        Returns:
            List of supplier names
        """
        return list(self._suppliers.keys())
    
    def create_supplier_client(self, supplier_name: str, **kwargs) -> Optional[BaseSupplierClient]:
        """
        Create an instance of a supplier client
        
        Args:
            supplier_name: Name of the supplier
            **kwargs: Arguments to pass to the supplier constructor
            
        Returns:
            Supplier client instance or None if supplier not found
        """
        supplier_class = self.get_supplier_class(supplier_name)
        if supplier_class:
            try:
                return supplier_class(**kwargs)
            except Exception as e:
                logger.error(f"Failed to create {supplier_name} client: {e}")
                return None
        return None
    
    def reload_suppliers(self):
        """
        Reload all suppliers (useful for development)
        """
        self._suppliers.clear()
        self._discover_suppliers()
    
    def get_supplier_capabilities(self, supplier_name: str) -> List[str]:
        """
        Get capabilities for a specific supplier
        
        Args:
            supplier_name: Name of the supplier
            
        Returns:
            List of capabilities or empty list if supplier not found
        """
        supplier_class = self.get_supplier_class(supplier_name)
        if supplier_class:
            try:
                # Try to create a temporary instance with minimal parameters
                # Most clients should have sensible defaults or allow None for init
                temp_client = self._create_temp_client(supplier_class)
                if temp_client and hasattr(temp_client, 'get_supported_capabilities'):
                    return temp_client.get_supported_capabilities()
            except Exception as e:
                logger.warning(f"Failed to get capabilities for {supplier_name}: {e}")
        return []
    
    def _create_temp_client(self, supplier_class: Type[BaseSupplierClient]) -> Optional[BaseSupplierClient]:
        """
        Create a temporary client instance for getting capabilities
        
        Args:
            supplier_class: Supplier client class
            
        Returns:
            Temporary client instance or None if creation fails
        """
        try:
            # Try different initialization strategies
            init_strategies = [
                # Strategy 1: No parameters
                lambda: supplier_class(),
                
                # Strategy 2: Empty parameters (for clients that accept None)
                lambda: supplier_class(api_key=None),
                lambda: supplier_class(client_id=None, client_secret=None),
                
                # Strategy 3: Dummy parameters (for clients that validate non-None)
                lambda: supplier_class(api_key="dummy"),
                lambda: supplier_class(client_id="dummy", client_secret="dummy"),
                
                # Strategy 4: Mixed parameters
                lambda: supplier_class(api_key="dummy", timeout=30),
                lambda: supplier_class(client_id="dummy", client_secret="dummy", timeout=30),
            ]
            
            for strategy in init_strategies:
                try:
                    return strategy()
                except (TypeError, ValueError):
                    continue  # Try next strategy
            
            logger.debug(f"Could not create temporary instance of {supplier_class.__name__}")
            return None
            
        except Exception as e:
            logger.debug(f"Failed to create temporary client for {supplier_class.__name__}: {e}")
            return None


# Global registry instance
supplier_registry = SupplierRegistry()


# Convenience functions
def get_supplier_class(supplier_name: str) -> Optional[Type[BaseSupplierClient]]:
    """Get a supplier class by name"""
    return supplier_registry.get_supplier_class(supplier_name)


def get_available_suppliers() -> List[str]:
    """Get list of available suppliers"""
    return supplier_registry.get_available_suppliers()


def create_supplier_client(supplier_name: str, **kwargs) -> Optional[BaseSupplierClient]:
    """Create a supplier client instance"""
    return supplier_registry.create_supplier_client(supplier_name, **kwargs)


def get_supplier_capabilities(supplier_name: str) -> List[str]:
    """Get capabilities for a supplier"""
    return supplier_registry.get_supplier_capabilities(supplier_name)


def reload_suppliers():
    """Reload all suppliers"""
    supplier_registry.reload_suppliers()