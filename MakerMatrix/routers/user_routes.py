from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from MakerMatrix.models.user_models import UserCreate, UserUpdate, PasswordUpdate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.dependencies import oauth2_scheme

router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()


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

        return ResponseSchema(
            status="success",
            message="User registered successfully",
            data=user.to_dict()
        )

    except ValueError as e:
        return ResponseSchema(
            status="error",
            message=str(e),
            data=None
        )


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