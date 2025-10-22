from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import logging
from MakerMatrix.models.user_models import UserCreate, UserUpdate, PasswordUpdate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission, require_admin
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity

logger = logging.getLogger(__name__)

router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()
base_router = BaseRouter()


def _remove_default_credentials_from_setup_script():
    """
    Remove default admin credentials from setup_admin.py after password change.
    This is a security measure to prevent hardcoded default passwords.
    """
    try:
        setup_file = Path(__file__).parent.parent / "scripts" / "setup_admin.py"

        if not setup_file.exists():
            logger.warning(f"setup_admin.py not found at {setup_file}")
            return

        # Read the file
        content = setup_file.read_text()

        # Check if default password is still in the file
        if 'DEFAULT_ADMIN_PASSWORD = "Admin123!"' not in content:
            logger.info("Default credentials already removed from setup_admin.py")
            return

        # Replace default credentials with secure comments
        new_content = content.replace(
            '# Default admin credentials\n'
            'DEFAULT_ADMIN_USERNAME = "admin"\n'
            'DEFAULT_ADMIN_EMAIL = "admin@makermatrix.local"\n'
            'DEFAULT_ADMIN_PASSWORD = "Admin123!"  # This should be changed on first login',
            '# Default admin credentials - REMOVED FOR SECURITY\n'
            '# The admin user has changed their password from the default.\n'
            '# Default credentials are no longer stored in this file.\n'
            '# Note: This will prevent automatic admin user creation on fresh installs.\n'
            '# To recreate: manually add credentials here or create via API.\n'
            'DEFAULT_ADMIN_USERNAME = None\n'
            'DEFAULT_ADMIN_EMAIL = None\n'
            'DEFAULT_ADMIN_PASSWORD = None'
        )

        # Write back to file
        setup_file.write_text(new_content)
        logger.info("✅ Default admin credentials removed from setup_admin.py for security")

    except Exception as e:
        logger.error(f"Failed to remove default credentials from setup_admin.py: {e}")
        # Don't raise - this is a non-critical security enhancement


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


@router.post("/register", response_model=ResponseSchema)
@standard_error_handling
async def register_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_admin)
):
    # Hash the password
    hashed_password = user_repository.get_password_hash(user_data.password)
    
    # Create the user
    user = user_repository.create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        roles=user_data.roles
    )
    print(f"[DEBUG] Registered user: {user.username}, roles: {user.roles}")
    
    return base_router.build_success_response(
        message="User registered successfully",
        data=user.to_dict()
    )


@router.get("/me", response_model=ResponseSchema)
@standard_error_handling
async def get_current_user_info(current_user=Depends(get_current_user)):
    """Get current authenticated user information"""
    return base_router.build_success_response(
        message="Current user retrieved successfully",
        data=current_user.to_dict()
    )


@router.get("/all", response_model=ResponseSchema)
@standard_error_handling
async def get_all_users(current_user=Depends(get_current_user)):
    # Only admin users can access this route
    if not any(role.name == "admin" for role in getattr(current_user, "roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    from MakerMatrix.services.user_service import UserService
    user_service = UserService()  # Create instance instead of static call
    response = user_service.get_all_users()
    
    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)
    
    return base_router.build_success_response(
        message=response.message,
        data=response.data
    )


@router.get("/roles", response_model=ResponseSchema)
@standard_error_handling
async def get_all_roles() -> ResponseSchema[List[Dict[str, Any]]]:
    """Get all roles in the system"""
    roles = user_repository.get_all_roles()
    return base_router.build_success_response(
        message="Roles retrieved successfully",
        data=[role.to_dict() for role in roles]
    )


@router.get("/{user_id}", response_model=ResponseSchema)
@standard_error_handling
async def get_user(user_id: str):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return base_router.build_success_response(
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.get("/by-username/{username}", response_model=ResponseSchema)
@standard_error_handling
async def get_user_by_username(username: str):
    user = user_repository.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return base_router.build_success_response(
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.put("/{user_id}", response_model=ResponseSchema)
@standard_error_handling
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(require_permission("users:update"))
):
    user = user_repository.update_user(
        user_id=user_id,
        email=user_data.email,
        is_active=user_data.is_active,
        roles=user_data.roles
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return base_router.build_success_response(
        message="User updated successfully",
        data=user.to_dict()
    )


@router.put("/{user_id}/password", response_model=ResponseSchema)
@standard_error_handling
async def update_password(
    user_id: str,
    password_data: PasswordUpdate,
    current_user: dict = Depends(get_current_user)
):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if current user is admin
    is_admin = any(role.name == "admin" for role in current_user.roles)
    is_editing_self = current_user.id == user_id

    # Admins editing other users don't need current password
    # Users editing themselves must provide current password
    if is_editing_self or not is_admin:
        if not password_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required"
            )

        # Verify current password
        if not user_repository.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

    # Hash and update new password
    new_hashed_password = user_repository.get_password_hash(password_data.new_password)
    updated_user = user_repository.update_password(user_id, new_hashed_password)

    # If this is the admin user changing from default password, remove credentials from setup_admin.py
    if user.username == "admin" and password_data.current_password == "Admin123!":
        _remove_default_credentials_from_setup_script()

    return base_router.build_success_response(
        message="Password updated successfully",
        data=updated_user.to_dict()
    )


@router.delete("/{user_id}", response_model=ResponseSchema)
@standard_error_handling
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_permission("users:delete"))
):
    if user_repository.delete_user(user_id):
        return base_router.build_success_response(
            message="User deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.put("/{user_id}/roles", response_model=ResponseSchema)
@standard_error_handling
async def update_user_roles(
    user_id: str,
    role_ids: List[str] = Body(..., embed=True),
    current_user: dict = Depends(require_admin)
) -> ResponseSchema[Dict[str, Any]]:
    """Update user's roles - will revoke API keys if permissions are downgraded"""
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get current permissions before role change
    old_permissions = set()
    for role in user.roles:
        old_permissions.update(role.permissions)

    # Get new role names from IDs
    role_names = []
    new_permissions = set()
    for role_id in role_ids:
        role = user_repository.get_role_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found"
            )
        role_names.append(role.name)
        new_permissions.update(role.permissions)

    # Detect if this is a permission downgrade
    permissions_removed = old_permissions - new_permissions
    is_downgrade = len(permissions_removed) > 0

    # Update user roles (repository expects role names, not objects)
    updated_user = user_repository.update_user(user_id, roles=role_names)

    # If permissions were removed, revoke all API keys for security
    warning_message = None
    if is_downgrade:
        from MakerMatrix.services.system.api_key_service import APIKeyService
        from MakerMatrix.models.models import engine

        api_key_service = APIKeyService(engine=engine)

        # Get all user's API keys
        keys_response = api_key_service.get_user_api_keys(user_id)
        if keys_response.success and keys_response.data:
            revoked_count = 0
            for key in keys_response.data:
                revoke_response = api_key_service.revoke_api_key(key['id'])
                if revoke_response.success:
                    revoked_count += 1

            if revoked_count > 0:
                warning_message = f"⚠️ User permissions were downgraded. {revoked_count} API key(s) were automatically revoked for security. User must create new API keys with current permissions."

    message = "User roles updated successfully"
    if warning_message:
        message = f"{message}. {warning_message}"

    return base_router.build_success_response(
        message=message,
        data=updated_user.to_dict()
    )


@router.put("/{user_id}/status", response_model=ResponseSchema)
@standard_error_handling
async def update_user_status(
    user_id: str,
    is_active: bool = Body(..., embed=True),
    current_user: dict = Depends(require_admin)
) -> ResponseSchema[Dict[str, Any]]:
    """Toggle user active status"""
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updated_user = user_repository.update_user(user_id, is_active=is_active)

    return base_router.build_success_response(
        message=f"User {'activated' if is_active else 'deactivated'} successfully",
        data=updated_user.to_dict()
    )


@router.post("/roles/add_role", response_model=ResponseSchema)
@standard_error_handling
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(require_admin)
) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.create_role(
        name=role_data.name,
        description=role_data.description,
        permissions=role_data.permissions
    )
    return base_router.build_success_response(
        message="Role created successfully",
        data=role.to_dict()
    )


@router.get("/roles/by-name/{name}", response_model=ResponseSchema)
@standard_error_handling
async def get_role_by_name(name: str) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.get_role_by_name(name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return base_router.build_success_response(
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.get("/roles/{role_id}", response_model=ResponseSchema)
@standard_error_handling
async def get_role(role_id: str) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return base_router.build_success_response(
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.put("/roles/{role_id}", response_model=ResponseSchema)
@standard_error_handling
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(require_admin)
) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.update_role(
        role_id=role_id,
        description=role_data.description,
        permissions=role_data.permissions
    )
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return base_router.build_success_response(
        message="Role updated successfully",
        data=role.to_dict()
    )


@router.delete("/roles/{role_id}", response_model=ResponseSchema)
@standard_error_handling
async def delete_role(
    role_id: str,
    current_user: dict = Depends(require_admin)
) -> ResponseSchema[Optional[Dict[str, Any]]]:
    if user_repository.delete_role(role_id):
        return base_router.build_success_response(
            message="Role deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )
