"""
Label Template Routes Module

Provides API endpoints for managing custom label templates including CRUD operations,
search functionality, template validation, and template preview generation.
"""

from typing import Optional, List, Dict, Any
import logging

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from MakerMatrix.models.label_template_models import (
    LabelTemplateModel,
    LabelTemplateCreate,
    LabelTemplateUpdate,
    LabelTemplateResponse,
    TemplatePreviewRequest,
    TemplateCategory,
    LayoutType
)
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError, ValidationError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity, validate_service_response

# Repository imports
from MakerMatrix.repositories.label_template_repository import LabelTemplateRepository, LabelTemplatePresetRepository
from sqlmodel import Session
from MakerMatrix.models.models import engine

logger = logging.getLogger(__name__)
router = APIRouter()


# Response schemas
class TemplateListResponse(BaseModel):
    """Response schema for template lists"""
    templates: List[LabelTemplateResponse]
    total_count: int


class TemplateStatsResponse(BaseModel):
    """Response schema for template statistics"""
    total_templates: int
    system_templates: int
    public_templates: int
    user_templates: int
    category_distribution: Dict[str, int]
    layout_distribution: Dict[str, int]


# Template Management Endpoints

@router.get("/", response_model=ResponseSchema[TemplateListResponse])
@standard_error_handling
async def get_all_templates(
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    layout_type: Optional[LayoutType] = Query(None, description="Filter by layout type"),
    search: Optional[str] = Query(None, description="Search term"),
    is_system: Optional[bool] = Query(None, description="Filter by system templates (true) or user templates (false)"),
    include_public: bool = Query(True, description="Include public templates"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[TemplateListResponse]:
    """
    Get all label templates with optional filtering.

    Returns user's own templates plus public/system templates if include_public is True.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()

            # Handle is_system filter
            if is_system is True:
                # Get only system templates
                templates = repo.get_system_templates(session)
            elif is_system is False:
                # Get only user's own templates (no public/system)
                templates = repo.get_by_user(session, current_user.id, include_public=False)
            elif search or category or layout_type:
                # Use search with filters
                templates = repo.search_templates(
                    session=session,
                    search_term=search,
                    category=category,
                    layout_type=layout_type,
                    user_id=current_user.id,
                    include_public=include_public
                )
            else:
                # Get user templates with optional public/system templates
                templates = repo.get_by_user(session, current_user.id, include_public)

            template_responses = [
                LabelTemplateResponse.model_validate(template) for template in templates
            ]

            return BaseRouter.build_success_response(
                data=TemplateListResponse(
                    templates=template_responses,
                    total_count=len(template_responses)
                ),
                message=f"Retrieved {len(templates)} templates"
            )

    except Exception as e:
        logger.error(f"Error retrieving templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve templates: {str(e)}")


@router.post("/", response_model=ResponseSchema[LabelTemplateResponse])
@standard_error_handling
@log_activity("template_created", "User {username} created template {template_name}")
async def create_template(
    template_data: LabelTemplateCreate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[LabelTemplateResponse]:
    logger.info(f"[DEBUG] Received template creation request: {template_data.model_dump()}")
    """
    Create a new label template.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()

            # Create template model from request data
            # Exclude None values to allow default_factory to work
            template_dict = template_data.model_dump(exclude_none=True)
            template = LabelTemplateModel(
                **template_dict,
                created_by_user_id=current_user.id
            )

            # Create template with validation
            created_template = repo.create_template(session, template)

            # Add template name to activity context
            request.state.activity_context = {"template_name": created_template.name}

            return BaseRouter.build_success_response(
                data=LabelTemplateResponse.model_validate(created_template),
                message=f"Template '{created_template.name}' created successfully"
            )

    except ResourceAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("/{template_id}", response_model=ResponseSchema[LabelTemplateResponse])
@standard_error_handling
async def get_template(
    template_id: str,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[LabelTemplateResponse]:
    """
    Get a specific template by ID.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()
            template = repo.get_by_id(session, template_id)

            if not template:
                raise HTTPException(status_code=404, detail=f"Template with ID '{template_id}' not found")

            # Check access permissions
            if (template.created_by_user_id != current_user.id and
                not template.is_public and
                not template.is_system_template):
                raise HTTPException(status_code=403, detail="Access denied to this template")

            return BaseRouter.build_success_response(
                data=LabelTemplateResponse.model_validate(template),
                message="Template retrieved successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve template: {str(e)}")


@router.put("/{template_id}", response_model=ResponseSchema[LabelTemplateResponse])
@standard_error_handling
@log_activity("template_updated", "User {username} updated template {template_name}")
async def update_template(
    template_id: str,
    template_updates: LabelTemplateUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[LabelTemplateResponse]:
    """
    Update an existing template.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()
            template = repo.get_by_id(session, template_id)

            if not template:
                raise HTTPException(status_code=404, detail=f"Template with ID '{template_id}' not found")

            # Check ownership permissions
            if template.created_by_user_id != current_user.id and not template.is_system_template:
                raise HTTPException(status_code=403, detail="You can only update your own templates")

            # System templates can only be updated by admin users
            if template.is_system_template:
                # Add admin check here when admin role is implemented
                pass

            # Update template
            updates = template_updates.model_dump(exclude_unset=True)
            updated_template = repo.update_template(session, template_id, updates)

            # Add template name to activity context
            request.state.activity_context = {"template_name": updated_template.name}

            return BaseRouter.build_success_response(
                data=LabelTemplateResponse.model_validate(updated_template),
                message=f"Template '{updated_template.name}' updated successfully"
            )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{template_id}", response_model=ResponseSchema[Dict[str, str]])
@standard_error_handling
@log_activity("template_deleted", "User {username} deleted template {template_name}")
async def delete_template(
    template_id: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, str]]:
    """
    Delete a template.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()
            template = repo.get_by_id(session, template_id)

            if not template:
                raise HTTPException(status_code=404, detail=f"Template with ID '{template_id}' not found")

            # Check ownership permissions
            if template.created_by_user_id != current_user.id:
                raise HTTPException(status_code=403, detail="You can only delete your own templates")

            # System templates cannot be deleted
            if template.is_system_template:
                raise HTTPException(status_code=400, detail="System templates cannot be deleted")

            template_name = template.name

            # Soft delete by setting is_active to False
            repo.update_template(session, template_id, {"is_active": False})

            # Add template name to activity context
            request.state.activity_context = {"template_name": template_name}

            return BaseRouter.build_success_response(
                data={"template_id": template_id, "template_name": template_name},
                message=f"Template '{template_name}' deleted successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/{template_id}/duplicate", response_model=ResponseSchema[LabelTemplateResponse])
@standard_error_handling
@log_activity("template_duplicated", "User {username} duplicated template {original_name} as {new_name}")
async def duplicate_template(
    template_id: str,
    request: Request,
    new_name: str = Query(..., description="Name for the duplicated template"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[LabelTemplateResponse]:
    """
    Duplicate an existing template with a new name.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()

            # Get original template
            original = repo.get_by_id(session, template_id)
            if not original:
                raise HTTPException(status_code=404, detail=f"Template with ID '{template_id}' not found")

            # Check access permissions
            if (original.created_by_user_id != current_user.id and
                not original.is_public and
                not original.is_system_template):
                raise HTTPException(status_code=403, detail="Access denied to this template")

            # Duplicate template
            duplicated = repo.duplicate_template(session, template_id, new_name, current_user.id)

            # Add names to activity context
            request.state.activity_context = {
                "original_name": original.name,
                "new_name": duplicated.name
            }

            return BaseRouter.build_success_response(
                data=LabelTemplateResponse.model_validate(duplicated),
                message=f"Template duplicated as '{new_name}'"
            )

    except HTTPException:
        raise
    except ResourceAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error duplicating template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to duplicate template: {str(e)}")


# Template Search and Filtering

@router.get("/search/", response_model=ResponseSchema[TemplateListResponse])
@standard_error_handling
async def search_templates(
    query: str = Query(..., description="Search term"),
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    layout_type: Optional[LayoutType] = Query(None, description="Filter by layout type"),
    label_height_min: Optional[float] = Query(None, description="Minimum label height in mm"),
    label_height_max: Optional[float] = Query(None, description="Maximum label height in mm"),
    include_public: bool = Query(True, description="Include public templates"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[TemplateListResponse]:
    """
    Search templates with advanced filtering options.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()

            label_size_range = None
            if label_height_min is not None and label_height_max is not None:
                label_size_range = (label_height_min, label_height_max)

            templates = repo.search_templates(
                session=session,
                search_term=query,
                category=category,
                layout_type=layout_type,
                user_id=current_user.id,
                include_public=include_public,
                label_size_range=label_size_range
            )

            template_responses = [
                LabelTemplateResponse.model_validate(template) for template in templates
            ]

            return BaseRouter.build_success_response(
                data=TemplateListResponse(
                    templates=template_responses,
                    total_count=len(template_responses)
                ),
                message=f"Found {len(templates)} templates matching search criteria"
            )

    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search templates: {str(e)}")


@router.get("/compatible/{label_height_mm}", response_model=ResponseSchema[TemplateListResponse])
@standard_error_handling
async def get_compatible_templates(
    label_height_mm: float,
    label_width_mm: Optional[float] = Query(None, description="Label width in mm"),
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[TemplateListResponse]:
    """
    Get templates compatible with specific label dimensions.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()

            templates = repo.get_compatible_templates(
                session=session,
                label_height_mm=label_height_mm,
                label_width_mm=label_width_mm
            )

            template_responses = [
                LabelTemplateResponse.model_validate(template) for template in templates
            ]

            return BaseRouter.build_success_response(
                data=TemplateListResponse(
                    templates=template_responses,
                    total_count=len(template_responses)
                ),
                message=f"Found {len(templates)} compatible templates"
            )

    except Exception as e:
        logger.error(f"Error finding compatible templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to find compatible templates: {str(e)}")


# Template Categories and Information

@router.get("/categories/", response_model=ResponseSchema[List[str]])
@standard_error_handling
async def get_template_categories() -> ResponseSchema[List[str]]:
    """
    Get list of all template categories.
    """
    categories = [category.value for category in TemplateCategory]
    return BaseRouter.build_success_response(
        data=categories,
        message="Template categories retrieved successfully"
    )


@router.get("/stats/summary", response_model=ResponseSchema[TemplateStatsResponse])
@standard_error_handling
async def get_template_statistics(
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[TemplateStatsResponse]:
    """
    Get template system statistics.
    """
    try:
        with Session(engine) as session:
            repo = LabelTemplateRepository()
            stats = repo.get_template_statistics(session)

            return BaseRouter.build_success_response(
                data=TemplateStatsResponse(**stats),
                message="Template statistics retrieved successfully"
            )

    except Exception as e:
        logger.error(f"Error retrieving template statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


# Template Validation

@router.post("/validate", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def validate_template(
    template_data: LabelTemplateCreate,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Validate template configuration without saving.
    """
    try:
        # Create temporary template for validation
        temp_template = LabelTemplateModel(
            **template_data.model_dump(),
            created_by_user_id=current_user.id
        )

        # Run validation
        errors = temp_template.validate_template()

        validation_result = {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": []  # Could add warnings in the future
        }

        return BaseRouter.build_success_response(
            data=validation_result,
            message="Template validation completed"
        )

    except Exception as e:
        logger.error(f"Error validating template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate template: {str(e)}")


# Template Preview

@router.post("/preview", response_model=ResponseSchema[Dict[str, Any]])
@standard_error_handling
async def preview_template(
    preview_request: TemplatePreviewRequest,
    current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Generate a preview of a template with sample data.

    Note: This endpoint will be enhanced once the template processing engine is implemented.
    For now, it returns a placeholder response with the template configuration.
    """
    try:
        template_config = None

        if preview_request.template_id:
            # Load template from database
            with Session(engine) as session:
                repo = LabelTemplateRepository()
                template = repo.get_by_id(session, preview_request.template_id)

                if not template:
                    raise HTTPException(status_code=404, detail="Template not found")

                # Check access permissions
                if (template.created_by_user_id != current_user.id and
                    not template.is_public and
                    not template.is_system_template):
                    raise HTTPException(status_code=403, detail="Access denied to this template")

                template_config = LabelTemplateResponse.model_validate(template)

                # Increment usage count
                repo.increment_usage(session, preview_request.template_id)

        elif preview_request.template_config:
            # Use provided template configuration
            template_config = preview_request.template_config

        else:
            raise HTTPException(status_code=400, detail="Either template_id or template_config is required")

        # TODO: Implement actual template processing and preview generation
        # For now, return template configuration and sample data
        preview_result = {
            "template_config": template_config.model_dump() if hasattr(template_config, 'model_dump') else template_config,
            "sample_data": preview_request.sample_data,
            "preview_available": False,
            "message": "Template preview generation will be implemented in Phase 6"
        }

        return BaseRouter.build_success_response(
            data=preview_result,
            message="Template preview data prepared (processing not yet implemented)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating template preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


