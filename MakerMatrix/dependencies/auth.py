from typing import Optional, Callable, List
from fastapi import Depends, HTTPException, status, APIRouter
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


def secure_router(router: APIRouter, dependencies: List[Callable] = None, exclude_paths: List[str] = None):
    """
    Apply authentication dependencies to all routes in a router.
    
    Args:
        router: The router to secure
        dependencies: List of dependencies to apply to all routes
        exclude_paths: List of path operations to exclude from authentication
        
    Returns:
        The secured router
    """
    if dependencies is None:
        dependencies = [Depends(get_current_active_user)]
    
    if exclude_paths is None:
        exclude_paths = []
    
    # Store the original routes
    original_routes = router.routes.copy()
    
    # Clear the router routes
    router.routes.clear()
    
    # Add the routes back with dependencies
    for route in original_routes:
        path = route.path
        if path in exclude_paths:
            router.routes.append(route)
        else:
            # Add the dependencies to the route
            route.dependencies.extend(dependencies)
            router.routes.append(route)
    
    return router 