from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Request, Depends

from MakerMatrix.models.models import CategoryModel, CategoryUpdate
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.exceptions import ResourceNotFoundError, CategoryAlreadyExistsError
from MakerMatrix.schemas.part_response import CategoryResponse, DeleteCategoriesResponse, CategoriesListResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/get_all_categories", response_model=ResponseSchema[CategoriesListResponse])
async def get_all_categories() -> ResponseSchema[CategoriesListResponse]:
    """
    Get all categories in the system.
    
    Returns:
        ResponseSchema: A response containing all categories
    """
    try:
        category_service = CategoryService()
        service_response = category_service.get_all_categories()
        
        if not service_response.success:
            raise HTTPException(status_code=400, detail=service_response.message)
        
        return ResponseSchema(
            status="success",
            message=service_response.message,
            data=CategoriesListResponse(**service_response.data)
        )
    except Exception as e:
        logger.error(f"Error in get_all_categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_category", response_model=ResponseSchema[CategoryResponse])
async def add_category(
    category_data: CategoryModel,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[CategoryResponse]:
    """
    Add a new category to the system.
    
    Args:
        category_data: The category data to add
        
    Returns:
        ResponseSchema: A response containing the created category
    """
    try:
        if not category_data.name:
            raise HTTPException(status_code=400, detail="Category name is required")
        
        category_service = CategoryService()
        service_response = category_service.add_category(category_data)
        
        if not service_response.success:
            if "already exists" in service_response.message:
                raise HTTPException(status_code=409, detail=service_response.message)
            else:
                raise HTTPException(status_code=400, detail=service_response.message)
        
        # Convert response data to CategoryResponse for type safety
        category_response_data = CategoryResponse.model_validate(service_response.data)
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_category_created(
                category_id=service_response.data["id"],
                category_name=service_response.data["name"],
                user=current_user,
                request=request
            )
        except Exception as activity_error:
            logger.warning(f"Failed to log category creation activity: {activity_error}")
            
        return ResponseSchema(
            status="success",
            message=service_response.message,
            data=category_response_data
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like the 409 raised above) as-is
        raise
    except CategoryAlreadyExistsError as cae:
        raise HTTPException(status_code=409, detail=str(cae))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in add_category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_category/{category_id}", response_model=ResponseSchema[CategoryResponse])
async def update_category(
    category_id: str, 
    category_data: CategoryUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[CategoryResponse]:
    """
    Update a category's fields.
    
    Args:
        category_id: The ID of the category to update
        category_data: The fields to update
        
    Returns:
        ResponseSchema: A response containing the updated category
    """
    try:
        if not category_id:
            raise HTTPException(status_code=400, detail="Category ID is required")
            
        category_service = CategoryService()
        service_response = category_service.update_category(category_id, category_data)
        
        if not service_response.success:
            if "not found" in service_response.message:
                raise HTTPException(status_code=404, detail=service_response.message)
            else:
                raise HTTPException(status_code=400, detail=service_response.message)
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            
            # Create changes dict from the update data
            changes = {k: v for k, v in category_data.model_dump().items() if v is not None}
            
            await activity_service.log_category_updated(
                category_id=category_id,
                category_name=service_response.data["name"],
                changes=changes,
                user=current_user,
                request=request
            )
        except Exception as activity_error:
            logger.warning(f"Failed to log category update activity: {activity_error}")
        
        return ResponseSchema(
            status="success",
            message=service_response.message,
            data=CategoryResponse.model_validate(service_response.data)
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like the 404 raised above) as-is
        raise
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in update_category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_category", response_model=ResponseSchema[CategoryResponse])
async def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> ResponseSchema[CategoryResponse]:
    """
    Get a category by ID or name.
    
    Args:
        category_id: Optional ID of the category to retrieve
        name: Optional name of the category to retrieve
        
    Returns:
        ResponseSchema: A response containing the requested category
    """
    try:
        if not category_id and not name:
            raise HTTPException(status_code=400, detail="Either 'category_id' or 'name' must be provided")
            
        category_service = CategoryService()
        service_response = category_service.get_category(category_id=category_id, name=name)
        
        if not service_response.success:
            if "not found" in service_response.message:
                raise HTTPException(status_code=404, detail=service_response.message)
            else:
                raise HTTPException(status_code=400, detail=service_response.message)
        
        return ResponseSchema(
            status="success",
            message=service_response.message,
            data=CategoryResponse.model_validate(service_response.data)
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like the 404 raised above) as-is
        raise
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in get_category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove_category", response_model=ResponseSchema[CategoryResponse])
async def remove_category(
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    cat_id: Optional[str] = None, 
    name: Optional[str] = None
) -> ResponseSchema[CategoryResponse]:
    """
    Remove a category by ID or name.
    
    Args:
        cat_id: Optional ID of the category to remove
        name: Optional name of the category to remove
        
    Returns:
        ResponseSchema: A response containing the removed category
    """
    if not cat_id and not name:
        raise HTTPException(
            status_code=400,
            detail="Either category ID or name must be provided"
        )
            
    try:
        category_service = CategoryService()
        service_response = category_service.remove_category(id=cat_id, name=name)
        
        if not service_response.success:
            if "not found" in service_response.message:
                raise HTTPException(status_code=404, detail=service_response.message)
            else:
                raise HTTPException(status_code=400, detail=service_response.message)
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_category_deleted(
                category_id=service_response.data["id"],
                category_name=service_response.data["name"],
                user=current_user,
                request=request
            )
        except Exception as activity_error:
            logger.warning(f"Failed to log category deletion activity: {activity_error}")
        
        return ResponseSchema(
            status="success",
            message=service_response.message,
            data=CategoryResponse.model_validate(service_response.data)
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like the 404 raised above) as-is
        raise
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in remove_category: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_all_categories", response_model=ResponseSchema[DeleteCategoriesResponse])
async def delete_all_categories(
    current_user: UserModel = Depends(require_permission("admin"))
) -> ResponseSchema[DeleteCategoriesResponse]:
    """
    Delete all categories from the system - USE WITH CAUTION! (Admin only)
    
    Returns:
        ResponseSchema: A response containing the deletion status
    """
    try:
        response = CategoryService.delete_all_categories()
        
        # Log the activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_activity(
                action="cleared",
                entity_type="categories",
                entity_name="All categories",
                user=current_user,
                details=response["data"]
            )
        except Exception as activity_error:
            logger.warning(f"Failed to log categories clear activity: {activity_error}")
        
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=DeleteCategoriesResponse(deleted_count=response["data"]["deleted_count"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))