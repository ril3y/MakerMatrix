from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.dependencies import oauth2_scheme


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return auth_service.get_current_user(token)


@router.post("/add_role", response_model=ResponseSchema)
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


@router.get("/by-name/{name}", response_model=ResponseSchema)
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


@router.get("/{role_id}", response_model=ResponseSchema)
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


@router.put("/{role_id}", response_model=ResponseSchema)
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


@router.delete("/{role_id}", response_model=ResponseSchema)
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