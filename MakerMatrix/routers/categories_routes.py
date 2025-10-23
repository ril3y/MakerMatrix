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

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# WebSocket for real-time updates
from MakerMatrix.services.system.websocket_service import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/get_all_categories", response_model=ResponseSchema[CategoriesListResponse])
@standard_error_handling
async def get_all_categories() -> ResponseSchema[CategoriesListResponse]:
    """
    Get all categories in the system.

    Returns:
        ResponseSchema: A response containing all categories
    """
    category_service = CategoryService()
    service_response = category_service.get_all_categories()
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=CategoriesListResponse(**data), message=service_response.message)


@router.post("/add_category", response_model=ResponseSchema[CategoryResponse])
@standard_error_handling
async def add_category(
    category_data: CategoryModel,
    request: Request,
    current_user: UserModel = Depends(require_permission("categories:create")),
) -> ResponseSchema[CategoryResponse]:
    """
    Add a new category to the system.

    Args:
        category_data: The category data to add

    Returns:
        ResponseSchema: A response containing the created category
    """
    if not category_data.name:
        raise ValueError("Category name is required")

    category_service = CategoryService()
    service_response = category_service.add_category(category_data)
    data = validate_service_response(service_response)

    # Log category creation activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()
        await activity_service.log_category_created(
            category_id=data["id"], category_name=data["name"], user=current_user, request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log category creation activity: {e}")

    # Broadcast category creation via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="created",
            entity_type="category",
            entity_id=data["id"],
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username,
            entity_data=data,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast category creation: {e}")

    return BaseRouter.build_success_response(
        data=CategoryResponse.model_validate(data), message=service_response.message
    )


@router.put("/update_category/{category_id}", response_model=ResponseSchema[CategoryResponse])
@standard_error_handling
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    request: Request,
    current_user: UserModel = Depends(require_permission("categories:update")),
) -> ResponseSchema[CategoryResponse]:
    """
    Update a category's fields.

    Args:
        category_id: The ID of the category to update
        category_data: The fields to update

    Returns:
        ResponseSchema: A response containing the updated category
    """
    if not category_id:
        raise ValueError("Category ID is required")

    category_service = CategoryService()
    service_response = category_service.update_category(category_id, category_data)
    data = validate_service_response(service_response)

    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()

        # Create changes dict from the update data
        changes = {k: v for k, v in category_data.model_dump().items() if v is not None}

        await activity_service.log_category_updated(
            category_id=category_id, category_name=data["name"], changes=changes, user=current_user, request=request
        )
    except Exception as activity_error:
        logger.warning(f"Failed to log category update activity: {activity_error}")

    # Broadcast category update via websocket
    try:
        # Create changes dict from the update data
        changes_dict = {k: v for k, v in category_data.model_dump().items() if v is not None}

        await websocket_manager.broadcast_crud_event(
            action="updated",
            entity_type="category",
            entity_id=category_id,
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username,
            changes=changes_dict,
            entity_data=data,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast category update: {e}")

    return BaseRouter.build_success_response(
        data=CategoryResponse.model_validate(data), message=service_response.message
    )


@router.get("/get_category", response_model=ResponseSchema[CategoryResponse])
@standard_error_handling
async def get_category(
    category_id: Optional[str] = None, name: Optional[str] = None
) -> ResponseSchema[CategoryResponse]:
    """
    Get a category by ID or name.

    Args:
        category_id: Optional ID of the category to retrieve
        name: Optional name of the category to retrieve

    Returns:
        ResponseSchema: A response containing the requested category
    """
    if not category_id and not name:
        raise ValueError("Either 'category_id' or 'name' must be provided")

    category_service = CategoryService()
    service_response = category_service.get_category(category_id=category_id, name=name)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=CategoryResponse.model_validate(data), message=service_response.message
    )


@router.delete("/remove_category", response_model=ResponseSchema[CategoryResponse])
@standard_error_handling
async def remove_category(
    request: Request,
    current_user: UserModel = Depends(require_permission("categories:delete")),
    cat_id: Optional[str] = None,
    name: Optional[str] = None,
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
        raise ValueError("Either category ID or name must be provided")

    category_service = CategoryService()
    service_response = category_service.remove_category(id=cat_id, name=name)
    data = validate_service_response(service_response)

    # Log category deletion activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service

        activity_service = get_activity_service()
        await activity_service.log_category_deleted(
            category_id=data["id"], category_name=data["name"], user=current_user, request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log category deletion activity: {e}")

    # Broadcast category deletion via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="deleted",
            entity_type="category",
            entity_id=data["id"],
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username,
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast category deletion: {e}")

    return BaseRouter.build_success_response(
        data=CategoryResponse.model_validate(data), message=service_response.message
    )


@router.delete("/delete_all_categories", response_model=ResponseSchema[DeleteCategoriesResponse])
@standard_error_handling
@log_activity("categories_cleared", "User {username} cleared all categories")
async def delete_all_categories(
    current_user: UserModel = Depends(require_permission("admin")),
) -> ResponseSchema[DeleteCategoriesResponse]:
    """
    Delete all categories from the system - USE WITH CAUTION! (Admin only)

    Returns:
        ResponseSchema: A response containing the deletion status
    """
    response = CategoryService.delete_all_categories()

    return BaseRouter.build_success_response(
        data=DeleteCategoriesResponse(deleted_count=response["data"]["deleted_count"]), message=response["message"]
    )
