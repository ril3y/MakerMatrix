from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError
from MakerMatrix.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserCreate, UserModel, PasswordUpdate
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.dependencies import oauth2_scheme
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Define a standard OAuth2 token response model
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenResponse(ResponseSchema[Token]):
    pass

# Define a model for mobile login
class MobileLoginRequest(BaseModel):
    username: str
    password: str

router = APIRouter()
auth_service = AuthService()
user_repository = UserRepository()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    return auth_service.get_current_user(token)


@router.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "password_change_required": user.password_change_required}
    )
    refresh_token = auth_service.create_refresh_token(data={"sub": user.username})

    user.last_login = datetime.utcnow()
    user_repository.update_user(user.id, last_login=user.last_login)

    # Return a shape that includes top-level "access_token" and "token_type",
    # so Swagger/OpenAPI picks them up for "Authorize".
    content = {
        "access_token": access_token,
        "token_type": "bearer",
        "status": "success",
        "message": "Login successful",
    }

    response = JSONResponse(content=content)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # For HTTPS in production
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )
    return response


@router.post("/auth/mobile-login", response_model=TokenResponse)
async def mobile_login(login_data: MobileLoginRequest):
    """
    Login endpoint specifically for mobile applications.
    Returns a token that can be used for authentication.
    """
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = auth_service.create_access_token(
        data={
            "sub": user.username,
            "password_change_required": user.password_change_required
        }
    )

    # Update last login time
    user.last_login = datetime.utcnow()
    user_repository.update_user(user.id, last_login=user.last_login)
    
    # Return token response
    return ResponseSchema(
        status="success",
        message="Login successful",
        data=Token(
            access_token=access_token,
            token_type="bearer"
        )
    )


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