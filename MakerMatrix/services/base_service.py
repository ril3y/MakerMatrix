"""
Base service abstraction for consistent database session management and error handling.

This module provides the BaseService class that eliminates the massive duplication
of session management code identified across 50+ service methods in the codebase.

Key features:
- Centralized session context manager
- Consistent error handling and logging
- Standardized transaction management
- Memory leak prevention through proper session cleanup
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Optional, TypeVar, Generic
from abc import ABC

from sqlmodel import Session
from pydantic import BaseModel

from MakerMatrix.models.models import engine
from MakerMatrix.database.db import get_session
from MakerMatrix.exceptions import (
    MakerMatrixException, ValidationError, ResourceNotFoundError, 
    ResourceAlreadyExistsError, map_exception_to_base_service, log_exception
)

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceResponse(BaseModel, Generic[T]):
    """Standardized response format for all service operations."""
    success: bool
    message: str
    data: Optional[T] = None
    errors: Optional[list[str]] = None
    
    @classmethod
    def success_response(cls, message: str, data: T = None) -> 'ServiceResponse[T]':
        """Create a success response."""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, errors: list[str] = None) -> 'ServiceResponse[T]':
        """Create an error response."""
        return cls(success=False, message=message, errors=errors or [])


# Note: Exception classes now imported from MakerMatrix.exceptions
# This eliminates the duplication that was present in the original code


class BaseService(ABC):
    """
    Base service class providing centralized session management and error handling.

    This class eliminates the massive duplication of session management code
    that was repeated across 50+ service methods in the original codebase.

    Usage:
        class PartService(BaseService):
            async def create_part(self, part_data):
                async with self.get_async_session() as session:
                    # Your business logic here
                    return self.success_response("Part created", new_part)
    """

    def __init__(self, engine_override=None):
        """
        Initialize base service.

        Args:
            engine_override: Optional engine to use instead of global engine (for testing)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.engine = engine_override if engine_override is not None else engine

    @contextmanager
    def get_session(self):
        """
        Context manager for synchronous database session management.

        Provides:
        - Automatic session creation and cleanup
        - Transaction management with auto-commit on success
        - Automatic rollback on exceptions
        - Proper session closure to prevent memory leaks

        Usage:
            with self.get_session() as session:
                # Database operations
                result = repository.create(session, data)
                return result
        """
        session = Session(self.engine)
        try:
            self.logger.debug("Database session created")
            yield session
            session.commit()
            self.logger.debug("Database session committed successfully")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session rolled back due to error: {e}")
            raise
        finally:
            session.close()
            self.logger.debug("Database session closed")
    
    @asynccontextmanager
    async def get_async_session(self):
        """
        Async context manager for database session management.

        Similar to get_session() but for async operations.

        Usage:
            async with self.get_async_session() as session:
                # Async database operations
                result = await async_repository.create(session, data)
                return result
        """
        session = Session(self.engine)
        try:
            self.logger.debug("Async database session created")
            yield session
            session.commit()
            self.logger.debug("Async database session committed successfully")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Async database session rolled back due to error: {e}")
            raise
        finally:
            session.close()
            self.logger.debug("Async database session closed")
    
    def success_response(self, message: str, data: Any = None) -> ServiceResponse:
        """Create a standardized success response."""
        self.logger.info(f"Service operation successful: {message}")
        return ServiceResponse.success_response(message, data)
    
    def error_response(self, message: str, errors: list[str] = None) -> ServiceResponse:
        """Create a standardized error response."""
        self.logger.error(f"Service operation failed: {message}")
        if errors:
            self.logger.error(f"Additional errors: {errors}")
        return ServiceResponse.error_response(message, errors)
    
    def handle_exception(self, e: Exception, operation: str) -> ServiceResponse:
        """
        Centralized exception handling for service operations.
        
        Args:
            e: The exception that occurred
            operation: Description of the operation that failed
            
        Returns:
            ServiceResponse with appropriate error information
        """
        # Log the exception with context
        log_exception(e, context=f"{self.__class__.__name__}.{operation}")
        
        # Map to MakerMatrix exception if needed
        mapped_exception = map_exception_to_base_service(e)
        
        if isinstance(mapped_exception, MakerMatrixException):
            return self.error_response(mapped_exception.message, [str(mapped_exception)])
        else:
            return self.error_response(
                f"An unexpected error occurred during {operation}",
                [str(e)]
            )
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: list[str]) -> None:
        """
        Validate that required fields are present in the data.
        
        Args:
            data: The data dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If any required fields are missing
        """
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                {"missing_fields": missing_fields}
            )
    
    def log_operation(self, operation: str, entity_type: str, entity_id: str = None):
        """
        Log service operations for debugging and audit purposes.
        
        Args:
            operation: The operation being performed (create, update, delete, etc.)
            entity_type: The type of entity being operated on
            entity_id: Optional ID of the entity
        """
        entity_info = f" (ID: {entity_id})" if entity_id else ""
        self.logger.info(f"Starting {operation} operation for {entity_type}{entity_info}")


class BaseCRUDService(BaseService, Generic[T]):
    """
    Base CRUD service class providing common Create, Read, Update, Delete operations.
    
    This further reduces duplication by providing standard CRUD patterns that were
    repeated across multiple service classes in the original codebase.
    
    Usage:
        class PartService(BaseCRUDService[PartModel]):
            def __init__(self):
                super().__init__()
                self.repository = PartRepository(engine)
                self.entity_name = "Part"
    """
    
    def __init__(self):
        super().__init__()
        self.repository = None  # To be set by subclasses
        self.entity_name = "Entity"  # To be set by subclasses
    
    def get_by_id(self, entity_id: str) -> ServiceResponse[T]:
        """
        Standard get by ID operation with consistent error handling.
        
        Args:
            entity_id: The ID of the entity to retrieve
            
        Returns:
            ServiceResponse containing the entity or error information
        """
        try:
            self.log_operation("get", self.entity_name, entity_id)
            
            with self.get_session() as session:
                entity = self.repository.get_by_id(session, entity_id)
                if not entity:
                    raise ResourceNotFoundError(f"{self.entity_name} not found with ID: {entity_id}")
                
                return self.success_response(f"{self.entity_name} retrieved successfully", entity)
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}")
    
    def get_by_name(self, name: str) -> ServiceResponse[T]:
        """
        Standard get by name operation with consistent error handling.
        
        Args:
            name: The name of the entity to retrieve
            
        Returns:
            ServiceResponse containing the entity or error information
        """
        try:
            self.log_operation("get", self.entity_name, name)
            
            with self.get_session() as session:
                entity = self.repository.get_by_name(session, name)
                if not entity:
                    raise ResourceNotFoundError(f"{self.entity_name} not found with name: {name}")
                
                return self.success_response(f"{self.entity_name} retrieved successfully", entity)
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}")
    
    def delete_by_id(self, entity_id: str) -> ServiceResponse[Dict[str, str]]:
        """
        Standard delete operation with consistent error handling.
        
        Args:
            entity_id: The ID of the entity to delete
            
        Returns:
            ServiceResponse with deletion confirmation
        """
        try:
            self.log_operation("delete", self.entity_name, entity_id)
            
            with self.get_session() as session:
                entity = self.repository.get_by_id(session, entity_id)
                if not entity:
                    raise ResourceNotFoundError(f"{self.entity_name} not found with ID: {entity_id}")
                
                self.repository.delete(session, entity_id)
                
                return self.success_response(
                    f"{self.entity_name} deleted successfully",
                    {"id": entity_id, "status": "deleted"}
                )
                
        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")