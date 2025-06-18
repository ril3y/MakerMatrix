"""
Supplier System Exceptions

Custom exceptions for the supplier system to provide clear error handling.
"""

class SupplierError(Exception):
    """Base exception for all supplier-related errors"""
    def __init__(self, message: str, supplier_name: str = None, details: dict = None):
        super().__init__(message)
        self.supplier_name = supplier_name
        self.details = details or {}

class SupplierConfigurationError(SupplierError):
    """Raised when supplier configuration is invalid or missing"""
    pass

class SupplierAuthenticationError(SupplierError):
    """Raised when supplier authentication fails"""
    pass

class SupplierConnectionError(SupplierError):
    """Raised when connection to supplier API fails"""
    pass

class SupplierRateLimitError(SupplierError):
    """Raised when supplier rate limit is exceeded"""
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

class SupplierNotFoundError(SupplierError):
    """Raised when requested supplier is not found in registry"""
    pass

class SupplierCapabilityError(SupplierError):
    """Raised when supplier doesn't support requested capability"""
    pass