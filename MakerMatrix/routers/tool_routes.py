"""
Tool Routes Module

API endpoints for tool management operations.
Supports CRUD, checkout/return, maintenance tracking, and search.
"""

from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette import status

from MakerMatrix.schemas.tool_schemas import (
    ToolCreateRequest,
    ToolUpdateRequest,
    ToolCheckoutRequest,
    ToolReturnRequest,
    ToolMaintenanceRequest,
    ToolSearchRequest,
    ToolResponse,
    ToolListResponse,
    ToolStatisticsResponse
)
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.tool_service import ToolService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user_flexible
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, validate_service_response

import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def get_tool_service() -> ToolService:
    """Dependency for getting tool service instance"""
    return ToolService()


# === CREATE OPERATIONS ===

@router.post("/", response_model=ResponseSchema[ToolResponse])
@standard_error_handling
async def create_tool(
    tool: ToolCreateRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:create")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolResponse]:
    """Create a new tool"""
    tool_data = tool.model_dump()
    service_response = tool_service.create_tool(tool_data)
    created_tool = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolResponse.model_validate(created_tool),
        message=service_response.message
    )


# === READ OPERATIONS ===

@router.get("/{tool_id}", response_model=ResponseSchema[ToolResponse])
@standard_error_handling
async def get_tool(
    tool_id: str,
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolResponse]:
    """Get a tool by ID"""
    service_response = tool_service.get_tool_by_id(tool_id)
    tool_data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolResponse.model_validate(tool_data),
        message=service_response.message
    )


@router.get("/", response_model=ResponseSchema[ToolListResponse])
@standard_error_handling
async def get_all_tools(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolListResponse]:
    """Get all tools with pagination"""
    service_response = tool_service.get_all_tools(page, page_size)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolListResponse(
            tools=[ToolResponse.model_validate(tool) for tool in data["tools"]],
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            total_pages=data["total_pages"]
        ),
        message=service_response.message
    )


@router.post("/search", response_model=ResponseSchema[ToolListResponse])
@standard_error_handling
async def search_tools(
    search_params: ToolSearchRequest,
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolListResponse]:
    """Advanced tool search with multiple filters"""
    search_dict = search_params.model_dump()
    service_response = tool_service.search_tools(search_dict)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolListResponse(
            tools=[ToolResponse.model_validate(tool) for tool in data["tools"]],
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            total_pages=data["total_pages"]
        ),
        message=service_response.message
    )


# === UPDATE OPERATIONS ===

@router.put("/{tool_id}", response_model=ResponseSchema[ToolResponse])
@standard_error_handling
async def update_tool(
    tool_id: str,
    tool_data: ToolUpdateRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:update")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolResponse]:
    """Update a tool"""
    update_dict = tool_data.model_dump(exclude_unset=True)
    service_response = tool_service.update_tool(tool_id, update_dict)
    updated_tool = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolResponse.model_validate(updated_tool),
        message=service_response.message
    )


# === DELETE OPERATIONS ===

@router.delete("/{tool_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def delete_tool(
    tool_id: str,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:delete")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[Dict[str, str]]:
    """Delete a tool"""
    service_response = tool_service.delete_tool(tool_id)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=result,
        message=service_response.message
    )


# === CHECKOUT/RETURN OPERATIONS ===

@router.post("/{tool_id}/checkout", response_model=ResponseSchema[ToolResponse])
@standard_error_handling
async def checkout_tool(
    tool_id: str,
    checkout_data: ToolCheckoutRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:use")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolResponse]:
    """Check out a tool to a user"""
    checkout_dict = checkout_data.model_dump()
    service_response = tool_service.checkout_tool(tool_id, checkout_dict)
    tool_data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolResponse.model_validate(tool_data),
        message=service_response.message
    )


@router.post("/{tool_id}/return", response_model=ResponseSchema[ToolResponse])
@standard_error_handling
async def return_tool(
    tool_id: str,
    return_data: ToolReturnRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:use")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolResponse]:
    """Return a checked-out tool"""
    return_dict = return_data.model_dump()
    service_response = tool_service.return_tool(tool_id, return_dict)
    tool_data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolResponse.model_validate(tool_data),
        message=service_response.message
    )


# === MAINTENANCE OPERATIONS ===

@router.post("/{tool_id}/maintenance", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def create_maintenance_record(
    tool_id: str,
    maintenance_data: ToolMaintenanceRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:update")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[Dict[str, Any]]:
    """Create a new maintenance record for a tool"""
    maintenance_dict = maintenance_data.model_dump()
    maintenance_dict['performed_by'] = current_user.username

    service_response = tool_service.create_maintenance_record(tool_id, maintenance_dict)
    record = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=record,
        message=service_response.message or "Maintenance record created successfully"
    )


@router.get("/{tool_id}/maintenance", response_model=ResponseSchema[List[Dict[str, Any]]])
@standard_error_handling
async def get_maintenance_records(
    tool_id: str,
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get all maintenance records for a tool"""
    service_response = tool_service.get_maintenance_records(tool_id)
    records = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=records,
        message=service_response.message
    )


@router.put("/{tool_id}/maintenance/{record_id}", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def update_maintenance_record(
    tool_id: str,
    record_id: str,
    maintenance_data: ToolMaintenanceRequest,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:update")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[Dict[str, Any]]:
    """Update an existing maintenance record"""
    update_dict = maintenance_data.model_dump(exclude_unset=True)
    service_response = tool_service.update_maintenance_record(tool_id, record_id, update_dict)
    record = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=record,
        message=service_response.message or "Maintenance record updated successfully"
    )


@router.delete("/{tool_id}/maintenance/{record_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
async def delete_maintenance_record(
    tool_id: str,
    record_id: str,
    request: Request,
    current_user: UserModel = Depends(require_permission("tools:delete")),
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[Dict[str, str]]:
    """Delete a maintenance record"""
    service_response = tool_service.delete_maintenance_record(tool_id, record_id)
    result = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=result,
        message=service_response.message or "Maintenance record deleted successfully"
    )


# === STATISTICS ===

@router.get("/statistics", response_model=ResponseSchema[ToolStatisticsResponse])
@standard_error_handling
async def get_tool_statistics(
    tool_service: ToolService = Depends(get_tool_service)
) -> ResponseSchema[ToolStatisticsResponse]:
    """Get tool statistics and summary"""
    service_response = tool_service.get_tool_statistics()
    stats_data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ToolStatisticsResponse.model_validate(stats_data),
        message=service_response.message
    )
