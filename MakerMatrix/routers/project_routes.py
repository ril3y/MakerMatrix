from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Request, Depends

from MakerMatrix.models.user_models import UserModel
from MakerMatrix.exceptions import ProjectAlreadyExistsError, ProjectNotFoundError, ResourceNotFoundError
from MakerMatrix.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectsListResponse,
    ProjectPartAssociation,
    DeleteProjectsResponse
)
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.data.project_service import ProjectService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# WebSocket for real-time updates
from MakerMatrix.services.system.websocket_service import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=ResponseSchema[ProjectsListResponse])
@standard_error_handling
async def get_all_projects() -> ResponseSchema[ProjectsListResponse]:
    """
    Get all projects in the system.

    Returns:
        ResponseSchema: A response containing all projects
    """
    project_service = ProjectService()
    service_response = project_service.get_all_projects()
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ProjectsListResponse(**data),
        message=service_response.message
    )


@router.post("/", response_model=ResponseSchema[ProjectResponse])
@standard_error_handling
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[ProjectResponse]:
    """
    Create a new project.

    Args:
        project_data: The project data to create

    Returns:
        ResponseSchema: A response containing the created project
    """
    if not project_data.name:
        raise ValueError("Project name is required")

    project_service = ProjectService()
    service_response = project_service.add_project(project_data.model_dump())
    data = validate_service_response(service_response)

    # Log project creation activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        await activity_service.log_activity(
            action="project_created",
            entity_type="project",
            entity_id=data["id"],
            entity_name=data["name"],
            user=current_user,
            request=request,
            details={"project_slug": data["slug"], "status": data["status"]}
        )
    except Exception as e:
        logger.warning(f"Failed to log project creation activity: {e}")

    # Broadcast project creation via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="created",
            entity_type="project",
            entity_id=data["id"],
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username,
            entity_data=data
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast project creation: {e}")

    return BaseRouter.build_success_response(
        data=ProjectResponse.model_validate(data),
        message=service_response.message
    )


@router.get("/{project_id}", response_model=ResponseSchema[ProjectResponse])
@standard_error_handling
async def get_project(
    project_id: Optional[str] = None,
    name: Optional[str] = None,
    slug: Optional[str] = None
) -> ResponseSchema[ProjectResponse]:
    """
    Get a project by ID, name, or slug.

    Args:
        project_id: Optional ID of the project to retrieve
        name: Optional name of the project to retrieve
        slug: Optional slug of the project to retrieve

    Returns:
        ResponseSchema: A response containing the requested project
    """
    if not any([project_id, name, slug]):
        raise ValueError("Either 'project_id', 'name', or 'slug' must be provided")

    project_service = ProjectService()
    service_response = project_service.get_project(project_id=project_id, name=name, slug=slug)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=ProjectResponse.model_validate(data),
        message=service_response.message
    )


@router.put("/{project_id}", response_model=ResponseSchema[ProjectResponse])
@standard_error_handling
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[ProjectResponse]:
    """
    Update a project's fields.

    Args:
        project_id: The ID of the project to update
        project_data: The fields to update

    Returns:
        ResponseSchema: A response containing the updated project
    """
    if not project_id:
        raise ValueError("Project ID is required")

    project_service = ProjectService()
    service_response = project_service.update_project(project_id, project_data.model_dump())
    data = validate_service_response(service_response)

    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()

        # Create changes dict from the update data
        changes = {k: v for k, v in project_data.model_dump().items() if v is not None}

        await activity_service.log_activity(
            action="project_updated",
            entity_type="project",
            entity_id=project_id,
            entity_name=data["name"],
            user=current_user,
            request=request,
            details={"changes": changes}
        )
    except Exception as activity_error:
        logger.warning(f"Failed to log project update activity: {activity_error}")

    # Broadcast project update via websocket
    try:
        # Create changes dict from the update data
        changes_dict = {k: v for k, v in project_data.model_dump().items() if v is not None}

        await websocket_manager.broadcast_crud_event(
            action="updated",
            entity_type="project",
            entity_id=project_id,
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username,
            changes=changes_dict,
            entity_data=data
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast project update: {e}")

    return BaseRouter.build_success_response(
        data=ProjectResponse.model_validate(data),
        message=service_response.message
    )


@router.delete("/{project_id}", response_model=ResponseSchema[ProjectResponse])
@standard_error_handling
async def delete_project(
    project_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[ProjectResponse]:
    """
    Delete a project by ID.

    Args:
        project_id: ID of the project to delete

    Returns:
        ResponseSchema: A response containing the deleted project
    """
    if not project_id:
        raise ValueError("Project ID is required")

    project_service = ProjectService()
    service_response = project_service.remove_project(id=project_id)
    data = validate_service_response(service_response)

    # Log project deletion activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        await activity_service.log_activity(
            action="project_deleted",
            entity_type="project",
            entity_id=data["id"],
            entity_name=data["name"],
            user=current_user,
            request=request
        )
    except Exception as e:
        logger.warning(f"Failed to log project deletion activity: {e}")

    # Broadcast project deletion via websocket
    try:
        await websocket_manager.broadcast_crud_event(
            action="deleted",
            entity_type="project",
            entity_id=data["id"],
            entity_name=data["name"],
            user_id=current_user.id,
            username=current_user.username
        )
    except Exception as e:
        logger.warning(f"Failed to broadcast project deletion: {e}")

    return BaseRouter.build_success_response(
        data=ProjectResponse.model_validate(data),
        message=service_response.message
    )


@router.delete("/", response_model=ResponseSchema[DeleteProjectsResponse])
@standard_error_handling
@log_activity("projects_cleared", "User {username} cleared all projects")
async def delete_all_projects(
    current_user: UserModel = Depends(require_permission("admin"))
) -> ResponseSchema[DeleteProjectsResponse]:
    """
    Delete all projects from the system - USE WITH CAUTION! (Admin only)

    Returns:
        ResponseSchema: A response containing the deletion status
    """
    response = ProjectService.delete_all_projects()

    return BaseRouter.build_success_response(
        data=DeleteProjectsResponse(deleted_count=response["data"]["deleted_count"]),
        message=response["message"]
    )


# === Part-Project Association Endpoints ===

@router.post("/{project_id}/parts/{part_id}", response_model=ResponseSchema[dict])
@standard_error_handling
async def add_part_to_project(
    project_id: str,
    part_id: str,
    request: Request,
    notes: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[dict]:
    """
    Add a part to a project.

    Args:
        project_id: The ID of the project
        part_id: The ID of the part to add
        notes: Optional notes about this part's use in the project

    Returns:
        ResponseSchema: Success response with association details
    """
    project_service = ProjectService()
    service_response = project_service.add_part_to_project(part_id, project_id, notes)
    data = validate_service_response(service_response)

    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        await activity_service.log_activity(
            action="part_added_to_project",
            entity_type="project",
            entity_id=project_id,
            entity_name=data.get("project_name", ""),
            user=current_user,
            request=request,
            details={"part_id": part_id, "notes": notes}
        )
    except Exception as e:
        logger.warning(f"Failed to log part addition activity: {e}")

    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )


@router.delete("/{project_id}/parts/{part_id}", response_model=ResponseSchema[dict])
@standard_error_handling
async def remove_part_from_project(
    project_id: str,
    part_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[dict]:
    """
    Remove a part from a project.

    Args:
        project_id: The ID of the project
        part_id: The ID of the part to remove

    Returns:
        ResponseSchema: Success response
    """
    project_service = ProjectService()
    service_response = project_service.remove_part_from_project(part_id, project_id)
    data = validate_service_response(service_response)

    # Log activity
    try:
        from MakerMatrix.services.activity_service import get_activity_service
        activity_service = get_activity_service()
        await activity_service.log_activity(
            action="part_removed_from_project",
            entity_type="project",
            entity_id=project_id,
            entity_name=data.get("project_name", ""),
            user=current_user,
            request=request,
            details={"part_id": part_id}
        )
    except Exception as e:
        logger.warning(f"Failed to log part removal activity: {e}")

    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )


@router.get("/{project_id}/parts", response_model=ResponseSchema[dict])
@standard_error_handling
async def get_project_parts(project_id: str) -> ResponseSchema[dict]:
    """
    Get all parts associated with a project.

    Args:
        project_id: The ID of the project

    Returns:
        ResponseSchema: Response with list of parts in the project
    """
    project_service = ProjectService()
    service_response = project_service.get_parts_for_project(project_id)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )


@router.get("/parts/{part_id}/projects", response_model=ResponseSchema[dict])
@standard_error_handling
async def get_part_projects(part_id: str) -> ResponseSchema[dict]:
    """
    Get all projects associated with a part.

    Args:
        part_id: The ID of the part

    Returns:
        ResponseSchema: Response with list of projects the part belongs to
    """
    project_service = ProjectService()
    service_response = project_service.get_projects_for_part(part_id)
    data = validate_service_response(service_response)

    return BaseRouter.build_success_response(
        data=data,
        message=service_response.message
    )
