"""
API Key Management Routes

Provides endpoints for creating, managing, and validating API keys.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from sqlmodel import Session, select
from MakerMatrix.models.api_key_models import APIKeyCreate, APIKeyUpdate
from MakerMatrix.services.system.api_key_service import APIKeyService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.routers.base import BaseRouter, standard_error_handling
from MakerMatrix.database.db import engine

router = APIRouter()
api_key_service = APIKeyService()
base_router = BaseRouter()


@router.post("/", response_model=ResponseSchema)
@standard_error_handling
async def create_api_key(
    key_data: APIKeyCreate, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """
    Create a new API key for the current user.

    The API key will be returned in the response - save it as it won't be shown again!
    """
    response = api_key_service.create_api_key(current_user.id, key_data)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return base_router.build_success_response(message=response.message, data=response.data)


@router.get("/", response_model=ResponseSchema)
@standard_error_handling
async def get_user_api_keys(
    current_user: UserModel = Depends(get_current_user),
) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get all API keys for the current user."""
    response = api_key_service.get_user_api_keys(current_user.id)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return base_router.build_success_response(message=response.message, data=response.data)


@router.get("/{key_id}", response_model=ResponseSchema)
@standard_error_handling
async def get_api_key(
    key_id: str, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Get a specific API key by ID."""
    response = api_key_service.get_api_key(key_id)

    if not response.success:
        raise HTTPException(status_code=404, detail=response.message)

    # Verify the key belongs to the current user (unless admin)
    is_admin = any(role.name == "admin" for role in getattr(current_user, "roles", []))
    if not is_admin and response.data.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only access your own API keys")

    return base_router.build_success_response(message=response.message, data=response.data)


@router.put("/{key_id}", response_model=ResponseSchema)
@standard_error_handling
async def update_api_key(
    key_id: str, update_data: APIKeyUpdate, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Update an API key."""
    # First get the key to verify ownership
    get_response = api_key_service.get_api_key(key_id)
    if not get_response.success:
        raise HTTPException(status_code=404, detail=get_response.message)

    # Verify the key belongs to the current user (unless admin)
    is_admin = any(role.name == "admin" for role in getattr(current_user, "roles", []))
    if not is_admin and get_response.data.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own API keys")

    response = api_key_service.update_api_key(key_id, update_data)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return base_router.build_success_response(message=response.message, data=response.data)


@router.delete("/{key_id}", response_model=ResponseSchema)
@standard_error_handling
async def delete_api_key(
    key_id: str, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Delete an API key permanently."""
    # First get the key to verify ownership
    get_response = api_key_service.get_api_key(key_id)
    if not get_response.success:
        raise HTTPException(status_code=404, detail=get_response.message)

    # Verify the key belongs to the current user (unless admin)
    is_admin = any(role.name == "admin" for role in getattr(current_user, "roles", []))
    if not is_admin and get_response.data.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own API keys")

    response = api_key_service.delete_api_key(key_id)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return base_router.build_success_response(message=response.message, data=response.data)


@router.post("/{key_id}/revoke", response_model=ResponseSchema)
@standard_error_handling
async def revoke_api_key(
    key_id: str, current_user: UserModel = Depends(get_current_user)
) -> ResponseSchema[Dict[str, Any]]:
    """Revoke (deactivate) an API key without deleting it."""
    # First get the key to verify ownership
    get_response = api_key_service.get_api_key(key_id)
    if not get_response.success:
        raise HTTPException(status_code=404, detail=get_response.message)

    # Verify the key belongs to the current user (unless admin)
    is_admin = any(role.name == "admin" for role in getattr(current_user, "roles", []))
    if not is_admin and get_response.data.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only revoke your own API keys")

    response = api_key_service.revoke_api_key(key_id)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return base_router.build_success_response(message=response.message, data=response.data)


@router.get("/admin/all", response_model=ResponseSchema)
@standard_error_handling
async def get_all_api_keys(current_user: UserModel = Depends(get_current_user)) -> ResponseSchema[List[Dict[str, Any]]]:
    """Get all API keys in the system (admin only)."""
    # Only admin users can access this route
    is_admin = any(role.name == "admin" for role in getattr(current_user, "roles", []))
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")

    # Get all users and their keys
    from MakerMatrix.repositories.user_repository import UserRepository

    user_repo = UserRepository()

    # This is a simple implementation - could be optimized
    from MakerMatrix.services.user_service import UserService

    user_service = UserService()
    users_response = user_service.get_all_users()

    all_keys = []
    for user_dict in users_response.data:
        user_id = user_dict.get("id")
        if user_id:
            keys_response = api_key_service.get_user_api_keys(user_id)
            if keys_response.success:
                # Add username to each key for admin view
                for key in keys_response.data:
                    key["username"] = user_dict.get("username")
                all_keys.extend(keys_response.data)

    return base_router.build_success_response(message=f"Found {len(all_keys)} API keys", data=all_keys)


@router.get("/permissions/available", response_model=ResponseSchema)
@standard_error_handling
async def get_available_permissions(
    current_user: UserModel = Depends(get_current_user),
) -> ResponseSchema[List[Dict[str, Any]]]:
    """
    Get all available permissions in the system.

    Returns permissions organized by category, automatically discovered from role definitions.
    This ensures the UI always shows current permissions without hardcoding.
    """
    with Session(engine) as session:
        # Get all roles and collect unique permissions
        roles = session.exec(select(RoleModel)).all()

        all_permissions = set()
        for role in roles:
            if role.permissions:
                all_permissions.update(role.permissions)

        # Define permission categories and their patterns
        permission_categories = {
            "Parts": ["parts:"],
            "Locations": ["locations:"],
            "Categories": ["categories:"],
            "Projects": ["projects:"],
            "Tools": ["tools:"],
            "Tasks": ["tasks:"],
            "Users": ["users:"],
            "API Keys": ["api_keys:"],
            "Backup": ["backup:"],
            "Tags": ["tags:"],
            "Suppliers": ["suppliers:"],
            "Reports": ["reports:"],
            "Database": ["database:"],
            "Dashboard": ["dashboard:"],
            "Admin": ["admin", "all"],
            "System": ["system", "inventory:", "data:", "pricing:", "csv:"],
        }

        # Categorize permissions
        categorized_permissions = []

        for category, patterns in permission_categories.items():
            category_perms = []

            for perm in sorted(all_permissions):
                # Check if permission matches any pattern for this category
                for pattern in patterns:
                    if perm.startswith(pattern) or perm == pattern:
                        # Format the label nicely
                        if ":" in perm:
                            resource, action = perm.split(":", 1)
                            label = f"{resource.title()}: {action.replace('_', ' ').title()}"
                        else:
                            label = perm.replace("_", " ").title()

                        category_perms.append({"value": perm, "label": label, "category": category})
                        break

            # Only add category if it has permissions
            if category_perms:
                categorized_permissions.extend(category_perms)

        return base_router.build_success_response(
            message=f"Found {len(categorized_permissions)} available permissions across {len(set(p['category'] for p in categorized_permissions))} categories",
            data=categorized_permissions,
        )
