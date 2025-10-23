"""
Tag Routes Module

API endpoints for tag management operations.
Supports CRUD, tag assignment to parts/tools, and tag-based filtering.
"""

from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from MakerMatrix.schemas.tag_schemas import (
    TagCreate,
    TagUpdate,
    TagFilter,
    TagResponse,
    TagWithItemsResponse,
    TagAssignment,
    TagBulkOperation,
    TagMergeRequest,
    TagCleanupRequest,
    TagSummaryResponse,
)
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.tag_service import TagService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, validate_service_response

import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_tag_service() -> TagService:
    """Dependency for getting tag service instance"""
    return TagService()


# === CREATE OPERATIONS ===


@router.post("", response_model=ResponseSchema[TagResponse])
@standard_error_handling
async def create_tag(
    tag: TagCreate,
    request: Request,
    current_user: UserModel = Depends(require_permission("tags:create")),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[TagResponse]:
    """Create a new tag"""
    # Pass created_by to the service for non-system tags
    created_by = current_user.username if (not tag.is_system and current_user) else None

    service_response = tag_service.create_tag(tag, created_by=created_by)
    created_tag = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=TagResponse.model_validate(created_tag), message=service_response.message
    )


# === READ OPERATIONS ===


# Statistics route must come before /{tag_id} to avoid path conflicts
@router.get("/statistics", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def get_tag_statistics(
    current_user: UserModel = Depends(get_current_user), tag_service: TagService = Depends(get_tag_service)
) -> ResponseSchema[Dict[str, Any]]:
    """Get tag system statistics and summary"""
    service_response = tag_service.get_tag_statistics()
    stats_data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=stats_data, message=service_response.message)


@router.get("/{tag_id}", response_model=ResponseSchema[TagResponse])
@standard_error_handling
async def get_tag(
    tag_id: str,
    include_items: bool = Query(default=False, description="Include tagged parts and tools"),
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[TagResponse]:
    """Get a tag by ID"""
    service_response = tag_service.get_tag_by_id(tag_id, include_items)
    tag_data = validate_service_response(service_response)

    ResponseModel = TagWithItemsResponse if include_items else TagResponse
    return BaseRouter.build_success_response(
        data=ResponseModel.model_validate(tag_data), message=service_response.message
    )


@router.get("/name/{tag_name}", response_model=ResponseSchema[TagResponse])
@standard_error_handling
async def get_tag_by_name(
    tag_name: str,
    include_items: bool = Query(default=False, description="Include tagged parts and tools"),
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[TagResponse]:
    """Get a tag by name (case-insensitive)"""
    service_response = tag_service.get_tag_by_name(tag_name, include_items)
    tag_data = validate_service_response(service_response)

    ResponseModel = TagWithItemsResponse if include_items else TagResponse
    return BaseRouter.build_success_response(
        data=ResponseModel.model_validate(tag_data), message=service_response.message
    )


@router.get("", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def get_all_tags(
    search: Optional[str] = Query(None, description="Search term for tag name or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active/inactive status"),
    is_system: Optional[bool] = Query(None, description="Filter by system/user tags"),
    min_usage: Optional[int] = Query(None, ge=0, description="Minimum usage count"),
    max_usage: Optional[int] = Query(None, ge=0, description="Maximum usage count"),
    has_color: Optional[bool] = Query(None, description="Filter tags with/without color"),
    sort_by: str = Query("name", description="Sort field: name, usage_count, created_at, updated_at"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Get all tags with filtering and pagination"""
    filter_params = TagFilter(
        search=search,
        is_active=is_active,
        is_system=is_system,
        min_usage=min_usage,
        max_usage=max_usage,
        has_color=has_color,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    service_response = tag_service.get_all_tags(filter_params)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data={
            "tags": [TagResponse.model_validate(tag) for tag in data["tags"]],
            "total": data["total"],
            "page": data["page"],
            "page_size": data["page_size"],
            "total_pages": data["total_pages"],
        },
        message=service_response.message,
    )


# === UPDATE OPERATIONS ===


@router.put("/{tag_id}", response_model=ResponseSchema[TagResponse])
@standard_error_handling
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    request: Request,
    current_user: UserModel = Depends(require_permission("tags:update")),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[TagResponse]:
    """Update a tag"""
    service_response = tag_service.update_tag(tag_id, tag_data)
    updated_tag = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=TagResponse.model_validate(updated_tag), message=service_response.message
    )


# === DELETE OPERATIONS ===


@router.delete("/{tag_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def delete_tag(
    tag_id: str,
    request: Request,
    current_user: UserModel = Depends(require_permission("tags:delete")),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, str]]:
    """Delete a tag (removes all associations but not the items)"""
    service_response = tag_service.delete_tag(tag_id)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)


# === TAG ASSIGNMENT - PARTS ===


@router.post("/{tag_id}/parts/{part_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def assign_tag_to_part(
    tag_id: str,
    part_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, str]]:
    """Assign a tag to a part"""
    user_id = current_user.username if current_user else None
    service_response = tag_service.assign_tag_to_part(tag_id, part_id, user_id)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)


@router.delete("/{tag_id}/parts/{part_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def remove_tag_from_part(
    tag_id: str,
    part_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, str]]:
    """Remove a tag from a part"""
    service_response = tag_service.remove_tag_from_part(tag_id, part_id)
    validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data={"tag_id": tag_id, "part_id": part_id}, message=service_response.message
    )


# === TAG ASSIGNMENT - TOOLS ===


@router.post("/{tag_id}/tools/{tool_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def assign_tag_to_tool(
    tag_id: str,
    tool_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, str]]:
    """Assign a tag to a tool"""
    user_id = current_user.username if current_user else None
    service_response = tag_service.assign_tag_to_tool(tag_id, tool_id, user_id)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)


@router.delete("/{tag_id}/tools/{tool_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def remove_tag_from_tool(
    tag_id: str,
    tool_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, str]]:
    """Remove a tag from a tool"""
    service_response = tag_service.remove_tag_from_tool(tag_id, tool_id)
    validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data={"tag_id": tag_id, "tool_id": tool_id}, message=service_response.message
    )


# === GET TAGS FOR ITEMS ===


@router.get("/parts/{part_id}/tags", response_model=ResponseSchema[List[TagResponse]])
@standard_error_handling
async def get_tags_for_part(
    part_id: str,
    tag_service: TagService = Depends(get_tag_service),
    current_user: UserModel = Depends(get_current_user),
) -> ResponseSchema[List[TagResponse]]:
    """Get all tags for a specific part"""
    service_response = tag_service.get_tags_for_part(part_id)
    tags = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=[TagResponse.model_validate(tag) for tag in tags], message=service_response.message
    )


@router.get("/tools/{tool_id}/tags", response_model=ResponseSchema[List[TagResponse]])
@standard_error_handling
async def get_tags_for_tool(
    tool_id: str,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[List[TagResponse]]:
    """Get all tags for a specific tool"""
    service_response = tag_service.get_tags_for_tool(tool_id)
    tags = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=[TagResponse.model_validate(tag) for tag in tags], message=service_response.message
    )


# === GET ITEMS BY TAG ===


@router.get("/{tag_id}/parts", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def get_parts_by_tag(
    tag_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Get all parts with a specific tag"""
    service_response = tag_service.get_parts_by_tag(tag_id, page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=data, message=service_response.message)


@router.get("/{tag_id}/tools", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def get_tools_by_tag(
    tag_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Get all tools with a specific tag"""
    service_response = tag_service.get_tools_by_tag(tag_id, page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=data, message=service_response.message)


# === BULK OPERATIONS ===


@router.post("/bulk", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def bulk_tag_operation(
    operation: TagBulkOperation,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Perform bulk tag operations on multiple items"""
    service_response = tag_service.bulk_tag_operation(operation)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)


# === TAG MANAGEMENT OPERATIONS ===


@router.post("/merge", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def merge_tags(
    merge_request: TagMergeRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tags:update")),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Merge multiple tags into one target tag"""
    service_response = tag_service.merge_tags(merge_request)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)


@router.post("/cleanup", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def cleanup_tags(
    cleanup_request: Optional[TagCleanupRequest] = None,
    request: Request = None,
    current_user: UserModel = Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service),
) -> ResponseSchema[Dict[str, Any]]:
    """Clean up unused or duplicate tags"""
    if cleanup_request is None:
        cleanup_request = TagCleanupRequest()

    service_response = tag_service.cleanup_unused_tags(cleanup_request)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(data=result, message=service_response.message)
