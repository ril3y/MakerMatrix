from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from MakerMatrix.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserCreate, UserModel, PasswordUpdate
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.dependencies import oauth2_scheme
from fastapi.responses import JSONResponse

router = APIRouter()
auth_service = AuthService()
user_repository = UserRepository()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    return auth_service.get_current_user(token)


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> JSONResponse:
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access and refresh tokens
    access_token = auth_service.create_access_token(
        data={
            "sub": user.username,
            "password_change_required": user.password_change_required
        }
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.username}
    )

    # Update last login time
    user.last_login = datetime.utcnow()
    user_repository.update_user(user.id, last_login=user.last_login)

    response = JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Login successful",
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": user.to_dict(),
                "password_change_required": user.password_change_required
            }
        ).model_dump()
    )

    # Set refresh token as HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # Enable in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 days
    )

    return response


@router.post("/auth/refresh")
async def refresh_token(refresh_token: Optional[str] = Cookie(None)) -> JSONResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = auth_service.verify_token(refresh_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = user_repository.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Create new access token
        access_token = auth_service.create_access_token(
            data={
                "sub": username,
                "password_change_required": user.password_change_required
            }
        )

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Token refreshed successfully",
                data={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "password_change_required": user.password_change_required
                }
            ).model_dump()
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Logout successful",
            data=None
        ).model_dump()
    )

    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.post("/users/register")
async def register_user(user_data: UserCreate) -> ResponseSchema:
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