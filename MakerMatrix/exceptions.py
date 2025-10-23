"""
Consolidated MakerMatrix Exception Hierarchy

This module consolidates all exception classes across the MakerMatrix codebase
to eliminate duplication and provide a consistent error handling approach.

This consolidation is part of Step 12 of the cleanup process to:
- Standardize error handling patterns
- Remove duplicate exception classes
- Consolidate error response formats
- Update error logging

Architecture:
- Base exception classes for common error types
- Domain-specific exceptions that inherit from base classes
- Consistent error response structure across all domains
- Integration with BaseService error handling patterns
"""

import logging
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


# =============================================================================
# Base Exception Classes
# =============================================================================


class MakerMatrixException(Exception):
    """Base exception for all MakerMatrix-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {"error_code": self.error_code, "message": self.message, "details": self.details}


class ValidationError(MakerMatrixException):
    """Raised when input validation fails."""

    def __init__(
        self, message: str, field_errors: Optional[Dict[str, str]] = None, missing_fields: Optional[List[str]] = None
    ):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field_errors = field_errors or {}
        self.missing_fields = missing_fields or []

        # Add field errors to details
        if field_errors or missing_fields:
            self.details.update({"field_errors": field_errors, "missing_fields": missing_fields})


class ResourceNotFoundError(MakerMatrixException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        super().__init__(message, error_code="RESOURCE_NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id

        if resource_type or resource_id:
            self.details.update({"resource_type": resource_type, "resource_id": resource_id})


class ResourceAlreadyExistsError(MakerMatrixException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        conflicting_field: Optional[str] = None,
    ):
        super().__init__(message, error_code="RESOURCE_ALREADY_EXISTS")
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.conflicting_field = conflicting_field

        if resource_type or resource_id or conflicting_field:
            self.details.update(
                {"resource_type": resource_type, "resource_id": resource_id, "conflicting_field": conflicting_field}
            )


class InvalidReferenceError(MakerMatrixException):
    """Raised when an invalid reference (foreign key) is provided."""

    def __init__(self, message: str, reference_type: Optional[str] = None, reference_id: Optional[str] = None):
        super().__init__(message, error_code="INVALID_REFERENCE")
        self.reference_type = reference_type
        self.reference_id = reference_id

        if reference_type or reference_id:
            self.details.update({"reference_type": reference_type, "reference_id": reference_id})


class AuthenticationError(MakerMatrixException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTHENTICATION_ERROR")


class AuthorizationError(MakerMatrixException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization failed", required_permission: Optional[str] = None):
        super().__init__(message, error_code="AUTHORIZATION_ERROR")
        self.required_permission = required_permission

        if required_permission:
            self.details.update({"required_permission": required_permission})


class ConfigurationError(MakerMatrixException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_field: Optional[str] = None, config_value: Optional[str] = None):
        super().__init__(message, error_code="CONFIGURATION_ERROR")
        self.config_field = config_field
        self.config_value = config_value

        if config_field or config_value:
            self.details.update({"config_field": config_field, "config_value": config_value})


class ConnectionError(MakerMatrixException):
    """Raised when connection to external service fails."""

    def __init__(self, message: str, service_name: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(message, error_code="CONNECTION_ERROR")
        self.service_name = service_name
        self.endpoint = endpoint

        if service_name or endpoint:
            self.details.update({"service_name": service_name, "endpoint": endpoint})


class RateLimitError(MakerMatrixException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, limit_type: Optional[str] = None):
        super().__init__(message, error_code="RATE_LIMIT_ERROR")
        self.retry_after = retry_after
        self.limit_type = limit_type

        if retry_after or limit_type:
            self.details.update({"retry_after": retry_after, "limit_type": limit_type})


# =============================================================================
# Domain-Specific Exception Classes
# =============================================================================


# Part Management Exceptions
class PartAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a part already exists."""

    def __init__(self, message: str, part_name: Optional[str] = None, part_number: Optional[str] = None):
        super().__init__(message, resource_type="part", conflicting_field="part_name")
        self.part_name = part_name
        self.part_number = part_number

        if part_name or part_number:
            self.details.update({"part_name": part_name, "part_number": part_number})


class PartNotFoundError(ResourceNotFoundError):
    """Raised when a part is not found."""

    def __init__(self, message: str, part_id: Optional[str] = None):
        super().__init__(message, resource_type="part", resource_id=part_id)


# Category Management Exceptions
class CategoryAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a category already exists."""

    def __init__(self, message: str, category_name: Optional[str] = None):
        super().__init__(message, resource_type="category", conflicting_field="name")
        self.category_name = category_name

        if category_name:
            self.details.update({"category_name": category_name})


class CategoryNotFoundError(ResourceNotFoundError):
    """Raised when a category is not found."""

    def __init__(self, message: str, category_id: Optional[str] = None):
        super().__init__(message, resource_type="category", resource_id=category_id)


# Location Management Exceptions
class LocationAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a location already exists."""

    def __init__(self, message: str, location_name: Optional[str] = None):
        super().__init__(message, resource_type="location", conflicting_field="name")
        self.location_name = location_name

        if location_name:
            self.details.update({"location_name": location_name})


class LocationNotFoundError(ResourceNotFoundError):
    """Raised when a location is not found."""

    def __init__(self, message: str, location_id: Optional[str] = None):
        super().__init__(message, resource_type="location", resource_id=location_id)


# Project Management Exceptions
class ProjectAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a project already exists."""

    def __init__(self, message: str, project_name: Optional[str] = None):
        super().__init__(message, resource_type="project", conflicting_field="name")
        self.project_name = project_name

        if project_name:
            self.details.update({"project_name": project_name})


class ProjectNotFoundError(ResourceNotFoundError):
    """Raised when a project is not found."""

    def __init__(self, message: str, project_id: Optional[str] = None):
        super().__init__(message, resource_type="project", resource_id=project_id)


# User Management Exceptions
class UserAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a user already exists."""

    def __init__(self, message: str, username: Optional[str] = None, email: Optional[str] = None):
        super().__init__(message, resource_type="user", conflicting_field="username")
        self.username = username
        self.email = email

        if username or email:
            self.details.update({"username": username, "email": email})


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user is not found."""

    def __init__(self, message: str, user_id: Optional[str] = None):
        super().__init__(message, resource_type="user", resource_id=user_id)


# Supplier Management Exceptions
class SupplierError(MakerMatrixException):
    """Base exception for all supplier-related errors."""

    def __init__(self, message: str, supplier_name: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message, error_code=error_code or "SUPPLIER_ERROR")
        self.supplier_name = supplier_name

        if supplier_name:
            self.details.update({"supplier_name": supplier_name})


class SupplierConfigurationError(ConfigurationError):
    """Raised when supplier configuration is invalid or missing."""

    def __init__(self, message: str, supplier_name: Optional[str] = None, config_field: Optional[str] = None):
        super().__init__(message, config_field=config_field)
        self.supplier_name = supplier_name

        if supplier_name:
            self.details.update({"supplier_name": supplier_name})


class SupplierAuthenticationError(AuthenticationError):
    """Raised when supplier authentication fails."""

    def __init__(self, message: str, supplier_name: Optional[str] = None):
        super().__init__(message)
        self.supplier_name = supplier_name

        if supplier_name:
            self.details.update({"supplier_name": supplier_name})


class SupplierConnectionError(ConnectionError):
    """Raised when connection to supplier API fails."""

    def __init__(self, message: str, supplier_name: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(message, service_name=supplier_name, endpoint=endpoint)


class SupplierRateLimitError(RateLimitError):
    """Raised when supplier rate limit is exceeded."""

    def __init__(self, message: str, supplier_name: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message, retry_after=retry_after, limit_type="supplier")
        self.supplier_name = supplier_name

        if supplier_name:
            self.details.update({"supplier_name": supplier_name})


class SupplierNotFoundError(ResourceNotFoundError):
    """Raised when requested supplier is not found in registry."""

    def __init__(self, message: str, supplier_name: Optional[str] = None):
        super().__init__(message, resource_type="supplier", resource_id=supplier_name)


class SupplierCapabilityError(MakerMatrixException):
    """Raised when supplier doesn't support requested capability."""

    def __init__(self, message: str, supplier_name: Optional[str] = None, capability: Optional[str] = None):
        super().__init__(message, error_code="SUPPLIER_CAPABILITY_ERROR")
        self.supplier_name = supplier_name
        self.capability = capability

        if supplier_name or capability:
            self.details.update({"supplier_name": supplier_name, "capability": capability})


class SupplierConfigAlreadyExistsError(ResourceAlreadyExistsError):
    """Raised when a supplier configuration already exists."""

    def __init__(self, message: str, supplier_name: Optional[str] = None):
        super().__init__(message, resource_type="supplier_config", conflicting_field="supplier_name")
        self.supplier_name = supplier_name

        if supplier_name:
            self.details.update({"supplier_name": supplier_name})


# Printer Management Exceptions
class PrinterError(MakerMatrixException):
    """Base exception for all printer-related errors."""

    def __init__(self, message: str, printer_id: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message, error_code=error_code or "PRINTER_ERROR")
        self.printer_id = printer_id

        if printer_id:
            self.details.update({"printer_id": printer_id})


class PrinterNotFoundError(ResourceNotFoundError):
    """Raised when a requested printer cannot be found."""

    def __init__(self, message: str, printer_id: Optional[str] = None):
        super().__init__(message, resource_type="printer", resource_id=printer_id)


class PrinterOfflineError(PrinterError):
    """Raised when trying to use an offline printer."""

    def __init__(self, message: str = "Printer is offline", printer_id: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="PRINTER_OFFLINE")


class PrinterConnectionError(ConnectionError):
    """Raised when unable to connect to printer."""

    def __init__(self, message: str = "Cannot connect to printer", printer_id: Optional[str] = None):
        super().__init__(message, service_name="printer", endpoint=printer_id)
        self.printer_id = printer_id

        if printer_id:
            self.details.update({"printer_id": printer_id})


class PrinterConfigurationError(ConfigurationError):
    """Raised when printer configuration is invalid."""

    def __init__(self, message: str, printer_id: Optional[str] = None, config_field: Optional[str] = None):
        super().__init__(message, config_field=config_field)
        self.printer_id = printer_id

        if printer_id:
            self.details.update({"printer_id": printer_id})


class InvalidLabelSizeError(PrinterError):
    """Raised when an invalid label size is specified."""

    def __init__(
        self,
        message: str,
        label_size: Optional[str] = None,
        printer_id: Optional[str] = None,
        supported_sizes: Optional[List[str]] = None,
    ):
        super().__init__(message, printer_id=printer_id, error_code="INVALID_LABEL_SIZE")
        self.label_size = label_size
        self.supported_sizes = supported_sizes or []

        if label_size or supported_sizes:
            self.details.update({"label_size": label_size, "supported_sizes": supported_sizes})


class PrintJobError(PrinterError):
    """Raised when a print job fails."""

    def __init__(self, message: str, printer_id: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="PRINT_JOB_ERROR")
        self.job_id = job_id

        if job_id:
            self.details.update({"job_id": job_id})


class PrinterBusyError(PrinterError):
    """Raised when printer is busy with another job."""

    def __init__(self, message: str, printer_id: Optional[str] = None, current_job_id: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="PRINTER_BUSY")
        self.current_job_id = current_job_id

        if current_job_id:
            self.details.update({"current_job_id": current_job_id})


# Task Management Exceptions
class TaskError(MakerMatrixException):
    """Base exception for all task-related errors."""

    def __init__(self, message: str, task_id: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message, error_code=error_code or "TASK_ERROR")
        self.task_id = task_id

        if task_id:
            self.details.update({"task_id": task_id})


class TaskNotFoundError(ResourceNotFoundError):
    """Raised when a task is not found."""

    def __init__(self, message: str, task_id: Optional[str] = None):
        super().__init__(message, resource_type="task", resource_id=task_id)


class TaskSecurityError(AuthorizationError):
    """Raised when task security validation fails."""

    def __init__(self, message: str, task_type: Optional[str] = None, user_id: Optional[str] = None):
        super().__init__(message)
        self.task_type = task_type
        self.user_id = user_id

        if task_type or user_id:
            self.details.update({"task_type": task_type, "user_id": user_id})


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================

# Maintain backward compatibility with existing code
ServiceException = MakerMatrixException
ResourceAlreadyExistsError = ResourceAlreadyExistsError

# Legacy printer exceptions for backward compatibility
LabelTooLargeError = InvalidLabelSizeError
LabelSizeError = InvalidLabelSizeError
UnsupportedOperationError = PrinterError
PreviewGenerationError = PrinterError
PrinterDriverError = PrinterError


# =============================================================================
# Exception Mapping for BaseService Integration
# =============================================================================


def map_exception_to_base_service(exception: Exception) -> MakerMatrixException:
    """
    Map standard exceptions to MakerMatrix exceptions for BaseService integration.

    This function helps integrate the consolidated exception system with the
    existing BaseService error handling patterns.
    """
    if isinstance(exception, MakerMatrixException):
        return exception
    elif isinstance(exception, ValueError):
        return ValidationError(str(exception))
    elif isinstance(exception, KeyError):
        return ResourceNotFoundError(f"Resource not found: {str(exception)}")
    elif isinstance(exception, PermissionError):
        return AuthorizationError(str(exception))
    else:
        return MakerMatrixException(str(exception), error_code="UNKNOWN_ERROR")


# =============================================================================
# Exception Logging Helpers
# =============================================================================


def log_exception(exception: Exception, context: str = None, extra_info: Optional[Dict[str, Any]] = None):
    """
    Centralized exception logging with consistent format.

    Args:
        exception: The exception to log
        context: Additional context about where the exception occurred
        extra_info: Additional information to include in the log
    """
    if isinstance(exception, MakerMatrixException):
        # Log MakerMatrix exceptions with full details
        log_data = {
            "error_code": exception.error_code,
            "error_message": exception.message,  # Renamed to avoid conflict with LogRecord.message
            "details": exception.details,
            "context": context,
        }

        if extra_info:
            log_data.update(extra_info)

        logger.error(f"MakerMatrix Error: {exception.message}", extra=log_data)
    else:
        # Log other exceptions with basic information
        log_data = {
            "exception_type": type(exception).__name__,
            "error_message": str(exception),  # Renamed to avoid conflict with LogRecord.message
            "context": context,
        }

        if extra_info:
            log_data.update(extra_info)

        logger.error(f"Unexpected Error: {str(exception)}", extra=log_data)


def get_http_status_code(exception: Exception) -> int:
    """
    Get appropriate HTTP status code for an exception.

    This function provides a centralized mapping of exceptions to HTTP status codes
    for consistent API responses.
    """
    if isinstance(exception, ValidationError):
        return 422  # Unprocessable Entity
    elif isinstance(exception, ResourceNotFoundError):
        return 404  # Not Found
    elif isinstance(exception, ResourceAlreadyExistsError):
        return 409  # Conflict
    elif isinstance(exception, AuthenticationError):
        return 401  # Unauthorized
    elif isinstance(exception, AuthorizationError):
        return 403  # Forbidden
    elif isinstance(exception, RateLimitError):
        return 429  # Too Many Requests
    elif isinstance(exception, ConfigurationError):
        return 500  # Internal Server Error
    elif isinstance(exception, ConnectionError):
        return 503  # Service Unavailable
    elif isinstance(exception, MakerMatrixException):
        return 400  # Bad Request (default for application errors)
    else:
        return 500  # Internal Server Error (unexpected errors)
