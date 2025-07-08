"""
Supplier System Exceptions

This module now imports from the consolidated MakerMatrix.exceptions module
to eliminate duplication and provide consistent error handling.

This is part of Step 12 cleanup to consolidate error handling patterns.
"""

from MakerMatrix.exceptions import (
    SupplierError,
    SupplierConfigurationError,
    SupplierAuthenticationError,
    SupplierConnectionError,
    SupplierRateLimitError,
    SupplierNotFoundError,
    SupplierCapabilityError,
    SupplierConfigAlreadyExistsError
)

# Re-export for backward compatibility
__all__ = [
    'SupplierError',
    'SupplierConfigurationError',
    'SupplierAuthenticationError',
    'SupplierConnectionError',
    'SupplierRateLimitError',
    'SupplierNotFoundError',
    'SupplierCapabilityError',
    'SupplierConfigAlreadyExistsError'
]