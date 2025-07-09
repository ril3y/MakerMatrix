from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from MakerMatrix.models.user_models import UserCreate, UserUpdate, PasswordUpdate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.auth.dependencies import oauth2_scheme
from MakerMatrix.routers.base import BaseRouter, standard_error_handling, log_activity

router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()
base_router = BaseRouter()


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return auth_service.get_current_user(token)


@router.post("/register", response_model=ResponseSchema)
@standard_error_handling
async def register_user(user_data: UserCreate):
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
async def update_user(user_id: str, user_data: UserUpdate):
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
async def update_password(user_id: str, password_data: PasswordUpdate):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
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

    return base_router.build_success_response(
        message="Password updated successfully",
        data=updated_user.to_dict()
    )


@router.delete("/{user_id}", response_model=ResponseSchema)
@standard_error_handling
async def delete_user(user_id: str):
    if user_repository.delete_user(user_id):
        return base_router.build_success_response(
            message="User deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.post("/roles/add_role", response_model=ResponseSchema)
@standard_error_handling
async def create_role(role_data: RoleCreate) -> ResponseSchema[Dict[str, Any]]:
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
async def update_role(role_id: str, role_data: RoleUpdate) -> ResponseSchema[Dict[str, Any]]:
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
async def delete_role(role_id: str) -> ResponseSchema[Optional[Dict[str, Any]]]:
    if user_repository.delete_role(role_id):
        return base_router.build_success_response(
            message="Role deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )
