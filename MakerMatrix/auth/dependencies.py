from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.models.user_models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    """Dependency to get the current authenticated user."""
    return auth_service.get_current_user(token)


async def get_current_user_from_token(token: str) -> UserModel:
    """Get current user from token (for WebSocket authentication)."""
    return auth_service.get_current_user(token)


async def get_current_user_optional(request: Request) -> Optional[UserModel]:
    """Get current user optionally from request (returns None if not authenticated)."""
    try:
        # Try to extract token from Authorization header
        authorization = request.headers.get("authorization")
        if not authorization:
            return None
        
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            return None
        
        token = authorization[7:]  # Remove "Bearer " prefix
        return auth_service.get_current_user(token)
    except:
        return None


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency to get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
