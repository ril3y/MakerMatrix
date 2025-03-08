from typing import Optional, Callable, List, Dict, Any
from fastapi import Depends, HTTPException, status, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.models.user_models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    """Dependency to get the current authenticated user."""
    return auth_service.get_current_user(token)


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency to get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permission(required_permission: str):
    """Dependency factory to check if the current user has the required permission."""
    async def permission_dependency(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
        if not auth_service.has_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required"
            )
        return current_user
    return permission_dependency


def require_admin(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Dependency to check if the current user is an admin."""
    for role in current_user.roles:
        if role.name == "admin" or "all" in role.permissions:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


def secure_all_routes(router: APIRouter, exclude_paths: List[str] = None, permissions: Dict[str, str] = None):
    """
    Apply authentication dependencies to all routes in a router.
    
    Args:
        router: The router to secure
        exclude_paths: List of path operations to exclude from authentication (e.g., ["/public-endpoint"])
        permissions: Dict mapping paths to required permissions (e.g., {"/admin-endpoint": "admin:access"})
        
    Returns:
        The secured router
    """
    if exclude_paths is None:
        exclude_paths = []
    
    if permissions is None:
        permissions = {}
    
    # Store the original routes
    original_routes = router.routes.copy()
    
    # Clear the router routes
    router.routes.clear()
    
    # Add the routes back with dependencies
    for route in original_routes:
        path = route.path
        
        # Skip excluded paths
        if path in exclude_paths:
            router.routes.append(route)
            continue
        
        # Check if this path needs specific permissions
        if path in permissions:
            # Add permission-specific dependency
            route.dependencies.append(Depends(require_permission(permissions[path])))
        else:
            # Add general authentication dependency
            route.dependencies.append(Depends(get_current_active_user))
        
        router.routes.append(route)
    
    return router 