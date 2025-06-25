from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from MakerMatrix.models.user_models import UserCreate, UserUpdate, PasswordUpdate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.dependencies import oauth2_scheme

router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()


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
async def register_user(user_data: UserCreate):
    try:
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
        return ResponseSchema(
            status="success",
            message="User registered successfully",
            data=user.to_dict()
        )

    except ValueError as e:
        print(f"[DEBUG] Registration error: {str(e)}")
        return ResponseSchema(
            status="error",
            message=str(e),
            data=None
        )


@router.get("/all", response_model=ResponseSchema)
async def get_all_users(current_user=Depends(get_current_user)):
    # Only admin users can access this route
    if not any(role.name == "admin" for role in getattr(current_user, "roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    from MakerMatrix.services.user_service import UserService
    response = UserService.get_all_users()
    return ResponseSchema(**response)


@router.get("/{user_id}", response_model=ResponseSchema)
async def get_user(user_id: str):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return ResponseSchema(
        status="success",
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.get("/by-username/{username}", response_model=ResponseSchema)
async def get_user_by_username(username: str):
    user = user_repository.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return ResponseSchema(
        status="success",
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.put("/{user_id}", response_model=ResponseSchema)
async def update_user(user_id: str, user_data: UserUpdate):
    try:
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
        return ResponseSchema(
            status="success",
            message="User updated successfully",
            data=user.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}/password", response_model=ResponseSchema)
async def update_password(user_id: str, password_data: PasswordUpdate):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        return ResponseSchema(
            status="error",
            message="User not found",
            data=None
        )

    # Verify current password
    if not user_repository.verify_password(password_data.current_password, user.hashed_password):
        return ResponseSchema(
            status="error",
            message="Current password is incorrect",
            data=None
        )

    # Hash and update new password
    new_hashed_password = user_repository.get_password_hash(password_data.new_password)
    updated_user = user_repository.update_password(user_id, new_hashed_password)

    return ResponseSchema(
        status="success",
        message="Password updated successfully",
        data=updated_user.to_dict()
    )


@router.delete("/{user_id}", response_model=ResponseSchema)
async def delete_user(user_id: str):
    if user_repository.delete_user(user_id):
        return ResponseSchema(
            status="success",
            message="User deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.post("/roles/add_role", response_model=ResponseSchema)
async def create_role(role_data: RoleCreate) -> ResponseSchema[Dict[str, Any]]:
    try:
        role = user_repository.create_role(
            name=role_data.name,
            description=role_data.description,
            permissions=role_data.permissions
        )
        return ResponseSchema(
            status="success",
            message="Role created successfully",
            data=role.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/roles/by-name/{name}", response_model=ResponseSchema)
async def get_role_by_name(name: str) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.get_role_by_name(name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return ResponseSchema(
        status="success",
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.get("/roles/{role_id}", response_model=ResponseSchema)
async def get_role(role_id: str) -> ResponseSchema[Dict[str, Any]]:
    role = user_repository.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return ResponseSchema(
        status="success",
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.put("/roles/{role_id}", response_model=ResponseSchema)
async def update_role(role_id: str, role_data: RoleUpdate) -> ResponseSchema[Dict[str, Any]]:
    try:
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
        return ResponseSchema(
            status="success",
            message="Role updated successfully",
            data=role.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/roles/{role_id}", response_model=ResponseSchema)
async def delete_role(role_id: str) -> ResponseSchema[Optional[Dict[str, Any]]]:
    if user_repository.delete_role(role_id):
        return ResponseSchema(
            status="success",
            message="Role deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )
