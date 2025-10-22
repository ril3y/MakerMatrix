from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from MakerMatrix.services.system.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.auth.dependencies import oauth2_scheme
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# BaseRouter infrastructure
from MakerMatrix.routers.base import BaseRouter, standard_error_handling


# Define a standard OAuth2 token response model
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenResponse(ResponseSchema[Token]):
    pass


# Define a model for login requests
class LoginRequest(BaseModel):
    username: str
    password: str


router = APIRouter()
auth_service = AuthService()
user_repository = UserRepository()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    return auth_service.get_current_user(token)


@router.post("/auth/login")
async def login(request: Request):
    # Try to get form data first (for Swagger UI compatibility)
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username and password:
            print(f"[DEBUG] /auth/login: using form data, username={username}")
            user = auth_service.authenticate_user(username, password)
            if not user:
                print(f"[DEBUG] /auth/login: Invalid credentials for username={username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            raise ValueError("No form data")
    except Exception:
        # Try JSON body
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")
            if username and password:
                print(f"[DEBUG] /auth/login: using JSON data, username={username}")
                user = auth_service.authenticate_user(username, password)
                if not user:
                    print(f"[DEBUG] /auth/login: Invalid credentials for username={username}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Incorrect username or password",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            else:
                print("[DEBUG] /auth/login: Missing credentials in JSON")
                raise HTTPException(status_code=400, detail="Missing credentials")
        except HTTPException:
            # Re-raise HTTP exceptions (like 401 auth failures)
            raise
        except Exception as e:
            if "Missing credentials" in str(e):
                raise e
            print(f"[DEBUG] /auth/login: Could not parse request: {e}")
            raise HTTPException(status_code=400, detail="Invalid request format")

    print(f"[DEBUG] /auth/login: Authentication successful for username={username}")

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "password_change_required": user.password_change_required}
    )
    refresh_token = auth_service.create_refresh_token(data={"sub": user.username})

    user.last_login = datetime.utcnow()
    user_repository.update_user(user.id, last_login=user.last_login)

    # Reload user to get updated data with roles
    user_with_roles = user_repository.get_user_by_username(username)

    content = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_with_roles.to_dict(),  # Include user object with roles
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
        max_age=60 * 60 * 24 * 7,
    )
    print(f"[DEBUG] /auth/login: Successful login for username={user.username}")
    return response


class MobileToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # seconds until expiration


@router.post("/auth/mobile-login", response_model=ResponseSchema[MobileToken])
async def mobile_login(login_request: LoginRequest) -> ResponseSchema[MobileToken]:
    """JSON-only login endpoint for mobile and API clients with refresh token."""
    print(f"[DEBUG] /auth/mobile-login: using username={login_request.username}")

    user = auth_service.authenticate_user(login_request.username, login_request.password)
    if not user:
        print(f"[DEBUG] /auth/mobile-login: Invalid credentials for username={login_request.username}")
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

    print(f"[DEBUG] /auth/mobile-login: Successful login for username={user.username}")

    return ResponseSchema(
        status="success",
        message="Login successful",
        data=MobileToken(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        ),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/mobile-refresh", response_model=ResponseSchema[Token])
@standard_error_handling
async def mobile_refresh_token(refresh_request: RefreshRequest) -> ResponseSchema[Token]:
    """Mobile-friendly token refresh endpoint using JSON body instead of cookies."""
    try:
        payload = auth_service.verify_token(refresh_request.refresh_token)
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
            data={"sub": username, "password_change_required": user.password_change_required}
        )

        return BaseRouter.build_success_response(
            data=Token(access_token=access_token, token_type="bearer"), message="Token refreshed successfully"
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/auth/refresh")
@standard_error_handling
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
            data={"sub": username, "password_change_required": user.password_change_required}
        )

        response_data = BaseRouter.build_success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "password_change_required": user.password_change_required,
            },
            message="Token refreshed successfully",
        )

        return JSONResponse(content=response_data.model_dump())

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/auth/logout")
@standard_error_handling
async def logout() -> JSONResponse:
    response_data = BaseRouter.build_success_response(data=None, message="Logout successful")

    response = JSONResponse(content=response_data.model_dump())

    # Clear the refresh token cookie
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")

    return response


@router.post("/auth/guest-login")
@standard_error_handling
async def guest_login() -> JSONResponse:
    """
    Auto-login as a guest viewer without requiring credentials.

    Creates a temporary session with viewer-only permissions (parts:read, tools:read).
    Guest sessions expire after 24 hours.
    """
    print("[DEBUG] /auth/guest-login: Creating guest viewer session")

    # Get or create the viewer role to ensure it exists
    try:
        viewer_role = user_repository.get_role_by_name("viewer")
    except Exception:
        # If viewer role doesn't exist, create it
        viewer_role = user_repository.create_role(
            name="viewer",
            description="Read-only viewer with comprehensive read access",
            permissions=[
                "parts:read",
                "tools:read",
                "dashboard:view",
                "tags:read",
                "projects:read",
                "suppliers:read",
                "locations:read",
                "categories:read",
            ],
        )
        print("[DEBUG] /auth/guest-login: Created viewer role")

    # Create a unique guest username (could be based on IP or session ID in production)
    from uuid import uuid4

    guest_id = str(uuid4())[:8]
    guest_username = f"guest_{guest_id}"

    # Create temporary guest token (no user account needed)
    # Token contains guest indicator and viewer role
    access_token = auth_service.create_access_token(
        data={"sub": guest_username, "is_guest": True, "role": "viewer", "password_change_required": False},
        expires_delta=timedelta(hours=24),  # 24 hours for guest sessions
    )

    # Build guest user object for frontend (no actual DB user created)
    guest_user_data = {
        "id": guest_id,
        "username": guest_username,
        "email": f"guest_{guest_id}@temporary",
        "is_active": True,
        "is_guest": True,
        "roles": [
            {
                "id": viewer_role.id,
                "name": "viewer",
                "permissions": viewer_role.permissions,  # Use actual list from database
            }
        ],
        "password_change_required": False,
        "last_login": datetime.utcnow().isoformat(),
    }

    content = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": guest_user_data,
        "status": "success",
        "message": "Guest login successful - viewing as read-only",
    }

    response = JSONResponse(content=content)
    print(f"[DEBUG] /auth/guest-login: Created guest session for {guest_username}")

    return response


# Registration endpoint removed - use /users/register in user_routes.py instead
