"""
Supplier Registry

Central registry for discovering and instantiating supplier implementations.
Provides a factory pattern for getting supplier instances.
"""

from typing import Dict, List, Type, Optional
from .base import BaseSupplier, SupplierInfo
from .exceptions import SupplierNotFoundError


class SupplierRegistry:
    """
    Registry for managing supplier implementations.

    Suppliers are automatically discovered and registered when imported.
    Use get_supplier() to get instances, get_available_suppliers() to list them.
    """

    _suppliers: Dict[str, Type[BaseSupplier]] = {}
    _supplier_info_cache: Dict[str, SupplierInfo] = {}

    @classmethod
    def register(cls, name: str, supplier_class: Type[BaseSupplier]):
        """Register a supplier implementation"""
        if not issubclass(supplier_class, BaseSupplier):
            raise ValueError(f"Supplier class must inherit from BaseSupplier")

        cls._suppliers[name.lower()] = supplier_class
        # Clear info cache when registering new supplier
        if name.lower() in cls._supplier_info_cache:
            del cls._supplier_info_cache[name.lower()]

    @classmethod
    def get_supplier(cls, name: str) -> BaseSupplier:
        """Get an instance of the specified supplier"""
        name = name.lower()
        if name not in cls._suppliers:
            raise SupplierNotFoundError(f"Supplier '{name}' not found", supplier_name=name)

        return cls._suppliers[name]()

    @classmethod
    def get_available_suppliers(cls) -> List[str]:
        """Get list of all registered supplier names"""
        return list(cls._suppliers.keys())

    @classmethod
    def get_supplier_info(cls, name: str) -> SupplierInfo:
        """Get information about a specific supplier"""
        name = name.lower()

        # Use cached info if available
        if name in cls._supplier_info_cache:
            return cls._supplier_info_cache[name]

        # Get fresh info from supplier instance
        supplier = cls.get_supplier(name)
        info = supplier.get_supplier_info()
        cls._supplier_info_cache[name] = info
        return info

    @classmethod
    def get_all_supplier_info(cls) -> Dict[str, SupplierInfo]:
        """Get information about all registered suppliers"""
        result = {}
        for name in cls.get_available_suppliers():
            result[name] = cls.get_supplier_info(name)
        return result

    @classmethod
    def is_supplier_available(cls, name: str) -> bool:
        """Check if a supplier is available"""
        return name.lower() in cls._suppliers

    @classmethod
    def clear_cache(cls):
        """Clear the supplier info cache"""
        cls._supplier_info_cache.clear()


def register_supplier(name: str):
    """Decorator for automatically registering suppliers"""

    def decorator(supplier_class: Type[BaseSupplier]):
        SupplierRegistry.register(name, supplier_class)
        return supplier_class

    return decorator


# Convenience functions for easier access
def get_supplier(name: str) -> BaseSupplier:
    """Get an instance of the specified supplier"""
    return SupplierRegistry.get_supplier(name)


def get_available_suppliers() -> List[str]:
    """Get list of all available supplier names"""
    return SupplierRegistry.get_available_suppliers()


def get_supplier_info(name: str) -> SupplierInfo:
    """Get information about a specific supplier"""
    return SupplierRegistry.get_supplier_info(name)


def get_all_supplier_info() -> Dict[str, SupplierInfo]:
    """Get information about all registered suppliers"""
    return SupplierRegistry.get_all_supplier_info()


def get_supplier_registry() -> Dict[str, Type[BaseSupplier]]:
    """Get the raw supplier registry (class references)"""
    return SupplierRegistry._suppliers.copy()
