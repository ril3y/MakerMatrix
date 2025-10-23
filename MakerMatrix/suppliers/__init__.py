"""
Modular Supplier System

This package provides a modular, extensible system for integrating with electronic component suppliers.
Each supplier implements a common interface, making it easy to add new suppliers and use them consistently.

Architecture:
- BaseSupplier: Abstract base class defining the supplier interface
- Individual supplier classes: DigiKeySupplier, LCSCSupplier, etc.
- SupplierRegistry: Factory for discovering and instantiating suppliers
- Generic APIs: RESTful endpoints that work with any supplier

Usage:
    from MakerMatrix.suppliers import SupplierRegistry

    # Get a supplier instance
    supplier = SupplierRegistry.get_supplier("digikey")

    # Get what credentials this supplier needs
    credential_fields = supplier.get_credential_schema()

    # Configure and use the supplier
    supplier.configure(config_data)
    results = supplier.search_parts("STM32")
"""

from .base import BaseSupplier, FieldDefinition, SupplierCapability
from .registry import SupplierRegistry
from .exceptions import SupplierError, SupplierConfigurationError, SupplierAuthenticationError

# Import supplier implementations to register them
from . import digikey
from . import lcsc
from . import mouser
from . import mcmaster_carr
from . import bolt_depot
from . import adafruit
from . import seeed_studio

__all__ = [
    "BaseSupplier",
    "FieldDefinition",
    "SupplierCapability",
    "SupplierRegistry",
    "SupplierError",
    "SupplierConfigurationError",
    "SupplierAuthenticationError",
]
