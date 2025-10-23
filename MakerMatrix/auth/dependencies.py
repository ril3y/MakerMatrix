from typing import Optional, Union
from fastapi import Depends, HTTPException, Request, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.services.system.api_key_service import APIKeyService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.api_key_models import APIKeyModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
auth_service = AuthService()
api_key_service = APIKeyService()


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


async def get_user_from_api_key(
    request: Request, x_api_key: Optional[str] = Depends(api_key_header)
) -> Optional[UserModel]:
    """
    Get user from API key in X-API-Key header or Authorization header.
    Returns None if no API key is provided or if it's invalid.
    """
    api_key = x_api_key

    # If not in X-API-Key header, try Authorization header with "ApiKey" scheme
    if not api_key:
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("ApiKey "):
            api_key = authorization[7:]  # Remove "ApiKey " prefix

    if not api_key:
        return None

    # Get client IP for validation
    client_ip = request.client.host if request.client else None

    # Validate the API key
    result = api_key_service.validate_api_key(api_key, ip_address=client_ip)

    if not result.success:
        raise HTTPException(status_code=401, detail=result.message or "Invalid API key")

    api_key_model: APIKeyModel = result.data

    # Get the user associated with this API key
    from MakerMatrix.repositories.user_repository import UserRepository

    user_repo = UserRepository()
    user = user_repo.get_user_by_id(api_key_model.user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User associated with API key not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    return user


async def get_current_user(
    request: Request,
    jwt_user: Optional[UserModel] = Depends(get_current_user_optional),
    api_key_user: Optional[UserModel] = Depends(get_user_from_api_key),
) -> UserModel:
    """
    Unified authentication that accepts either JWT token or API key.
    Tries API key first, then JWT token.

    Supports:
    - JWT: Authorization header with "Bearer <token>"
    - API Key: X-API-Key header or Authorization header with "ApiKey <key>"
    """
    # Try API key first
    if api_key_user:
        return api_key_user

    # Fall back to JWT token
    if jwt_user:
        return jwt_user

    # No valid authentication provided
    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Provide either a valid JWT token (Authorization: Bearer <token>) or API key (X-API-Key: <key> or Authorization: ApiKey <key>)",
    )


async def get_current_user_from_token(token: str) -> UserModel:
    """Get current user from token (for WebSocket authentication)."""
    return auth_service.get_current_user(token)


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency to get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Backward compatibility alias - get_current_user_flexible is now just an alias to get_current_user
# which handles both JWT and API keys
get_current_user_flexible = get_current_user
