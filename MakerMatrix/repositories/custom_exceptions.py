"""
DEPRECATED: Custom Exceptions Module

This module has been deprecated in favor of the consolidated MakerMatrix.exceptions module.
All exception classes have been moved to provide better consistency and eliminate duplication.

This is part of Step 12 cleanup to consolidate error handling patterns.

Please update your imports to use:
    from MakerMatrix.exceptions import ResourceNotFoundError, PartAlreadyExistsError, etc.

This file is maintained for backward compatibility but will be removed in a future version.
"""

import warnings
from MakerMatrix.exceptions import (
    ResourceNotFoundError as _ResourceNotFoundError,
    PartAlreadyExistsError as _PartAlreadyExistsError,
    CategoryAlreadyExistsError as _CategoryAlreadyExistsError,
    LocationAlreadyExistsError as _LocationAlreadyExistsError,
    UserAlreadyExistsError as _UserAlreadyExistsError,
    InvalidReferenceError as _InvalidReferenceError,
    SupplierConfigAlreadyExistsError as _SupplierConfigAlreadyExistsError
)

# Backward compatibility wrappers with deprecation warnings
class ResourceNotFoundError(_ResourceNotFoundError):
    """DEPRECATED: Use MakerMatrix.exceptions.ResourceNotFoundError instead."""
    
    def __init__(self, status: str, message: str, data=None):
        warnings.warn(
            "ResourceNotFoundError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.ResourceNotFoundError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message, resource_type="generic", resource_id=None)
        self.status = status
        self.data = data


class PartAlreadyExistsError(_PartAlreadyExistsError):
    """DEPRECATED: Use MakerMatrix.exceptions.PartAlreadyExistsError instead."""
    
    def __init__(self, status: str, message: str, data: dict):
        warnings.warn(
            "PartAlreadyExistsError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.PartAlreadyExistsError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data


class CategoryAlreadyExistsError(_CategoryAlreadyExistsError):
    """DEPRECATED: Use MakerMatrix.exceptions.CategoryAlreadyExistsError instead."""
    
    def __init__(self, status: str, message: str, data: dict):
        warnings.warn(
            "CategoryAlreadyExistsError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.CategoryAlreadyExistsError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data


class LocationAlreadyExistsError(_LocationAlreadyExistsError):
    """DEPRECATED: Use MakerMatrix.exceptions.LocationAlreadyExistsError instead."""
    
    def __init__(self, status: str, message: str, data: dict):
        warnings.warn(
            "LocationAlreadyExistsError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.LocationAlreadyExistsError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data


class UserAlreadyExistsError(_UserAlreadyExistsError):
    """DEPRECATED: Use MakerMatrix.exceptions.UserAlreadyExistsError instead."""
    
    def __init__(self, status: str, message: str, data: dict):
        warnings.warn(
            "UserAlreadyExistsError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.UserAlreadyExistsError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data


class InvalidReferenceError(_InvalidReferenceError):
    """DEPRECATED: Use MakerMatrix.exceptions.InvalidReferenceError instead."""
    
    def __init__(self, status: str, message: str, data=None):
        warnings.warn(
            "InvalidReferenceError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.InvalidReferenceError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data


class SupplierConfigAlreadyExistsError(_SupplierConfigAlreadyExistsError):
    """DEPRECATED: Use MakerMatrix.exceptions.SupplierConfigAlreadyExistsError instead."""
    
    def __init__(self, message: str, status: str = "error", data=None):
        warnings.warn(
            "SupplierConfigAlreadyExistsError from repositories.custom_exceptions is deprecated. "
            "Use MakerMatrix.exceptions.SupplierConfigAlreadyExistsError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(message)
        self.status = status
        self.data = data
