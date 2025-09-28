"""
Base router infrastructure for centralized error handling and response construction.

This module provides base classes and utilities to eliminate duplication across
route files and ensure consistent error handling and response patterns.
"""

import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from functools import wraps

from fastapi import HTTPException
from fastapi.responses import Response

from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError, 
    PartAlreadyExistsError,
    UserAlreadyExistsError,
    CategoryAlreadyExistsError,
    LocationAlreadyExistsError,
    InvalidReferenceError,
    SupplierConfigAlreadyExistsError
)
from MakerMatrix.exceptions import InvalidLabelSizeError
from MakerMatrix.schemas.response import ResponseSchema

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRouter:
    """
    Base class for all routers providing centralized error handling and response construction.
    
    This eliminates the need for repetitive try/catch blocks and ensures consistent
    error handling across all API endpoints.
    """
    
    @staticmethod
    def build_success_response(
        data: Any = None,
        message: str = "Operation completed successfully",
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        total_parts: Optional[int] = None
    ) -> ResponseSchema:
        """
        Build a standardized success response.

        Args:
            data: Response data
            message: Success message
            page: Page number for paginated responses
            page_size: Items per page for paginated responses
            total_parts: Total count for paginated responses

        Returns:
            Standardized ResponseSchema
        """
        return ResponseSchema(
            status="success",
            message=message,
            data=data,
            page=page,
            page_size=page_size,
            total_parts=total_parts
        )

    @staticmethod
    def build_error_response(
        message: str = "Operation failed",
        data: Any = None
    ) -> ResponseSchema:
        """
        Build a standardized error response.

        Args:
            message: Error message
            data: Optional error data

        Returns:
            Standardized ResponseSchema with error status
        """
        return ResponseSchema(
            status="error",
            message=message,
            data=data
        )
    
    @staticmethod
    def handle_exception(e: Exception) -> HTTPException:
        """
        Convert exceptions to appropriate HTTP exceptions with consistent error handling.
        
        Args:
            e: The exception to handle
            
        Returns:
            HTTPException with appropriate status code and detail
        """
        if isinstance(e, HTTPException):
            return e
        elif isinstance(e, ResourceNotFoundError):
            return HTTPException(status_code=404, detail=str(e))
        elif isinstance(e, (PartAlreadyExistsError, UserAlreadyExistsError, 
                           CategoryAlreadyExistsError, LocationAlreadyExistsError,
                           SupplierConfigAlreadyExistsError)):
            return HTTPException(status_code=409, detail=str(e))
        elif isinstance(e, InvalidReferenceError):
            return HTTPException(status_code=400, detail=str(e))
        elif isinstance(e, InvalidLabelSizeError):
            return HTTPException(status_code=422, detail=str(e))
        elif isinstance(e, ValueError):
            return HTTPException(status_code=400, detail=str(e))
        elif isinstance(e, PermissionError):
            return HTTPException(status_code=403, detail=str(e))
        else:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return HTTPException(status_code=500, detail="Internal server error")


def standard_error_handling(func: Callable) -> Callable:
    """
    Decorator that provides standardized error handling for route functions.
    
    This eliminates the need for repetitive try/catch blocks in every route.
    
    Usage:
        @standard_error_handling
        async def my_route():
            # Your route logic here
            return BaseRouter.build_success_response(data=result)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise BaseRouter.handle_exception(e)
    return wrapper


def sync_standard_error_handling(func: Callable) -> Callable:
    """
    Decorator that provides standardized error handling for synchronous route functions.
    
    Usage:
        @sync_standard_error_handling
        def my_sync_route():
            # Your route logic here
            return BaseRouter.build_success_response(data=result)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise BaseRouter.handle_exception(e)
    return wrapper


def log_activity(activity_type: str, description: str = None):
    """
    Decorator that logs activity for route functions.
    
    Args:
        activity_type: Type of activity being performed
        description: Optional description template (can use {username} placeholder)
        
    Usage:
        @log_activity("part_created", "User {username} created part")
        async def create_part(current_user: UserModel = Depends(get_current_user)):
            # Your route logic here
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs if available
            current_user = kwargs.get('current_user')
            
            try:
                result = await func(*args, **kwargs)
                
                # Log successful activity
                if current_user:
                    try:
                        from MakerMatrix.services.activity_service import get_activity_service
                        activity_service = get_activity_service()
                        
                        final_description = description or f"{activity_type} performed"
                        if "{username}" in final_description and current_user:
                            final_description = final_description.format(username=current_user.username)
                        
                        await activity_service.log_activity(
                            user_id=current_user.id,
                            activity_type=activity_type,
                            description=final_description
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log activity: {e}")
                
                return result
            except Exception as e:
                # Log failed activity
                if current_user:
                    try:
                        from MakerMatrix.services.activity_service import get_activity_service
                        activity_service = get_activity_service()
                        
                        await activity_service.log_activity(
                            user_id=current_user.id,
                            activity_type=f"{activity_type}_failed",
                            description=f"Failed {activity_type}: {str(e)}"
                        )
                    except Exception as log_e:
                        logger.warning(f"Failed to log failed activity: {log_e}")
                
                raise e
                
        return wrapper
    return decorator


def validate_service_response(service_response) -> Any:
    """
    Validate service response and extract data or raise appropriate exception.
    
    Args:
        service_response: Service response object with success flag and data/message
        
    Returns:
        The data from successful service response
        
    Raises:
        HTTPException: If service response indicates failure
    """
    if not service_response.success:
        if "not found" in service_response.message.lower():
            raise HTTPException(status_code=404, detail=service_response.message)
        elif "already exists" in service_response.message.lower():
            raise HTTPException(status_code=409, detail=service_response.message)
        else:
            raise HTTPException(status_code=400, detail=service_response.message)
    
    return service_response.data