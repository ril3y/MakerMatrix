from typing import List, Dict, Any
from fastapi import Depends, HTTPException, status, APIRouter
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.auth.dependencies import get_current_user_flexible

auth_service = AuthService()

def require_permission(required_permission: str):
    """
    Dependency factory to check if the current user has the required permission.

    SECURITY FIX (CVE-001): Special handling for "admin" permission to check role name.
    """
    async def permission_dependency(current_user: UserModel = Depends(get_current_user_flexible)) -> UserModel:
        # CRITICAL SECURITY FIX (CVE-001): Admin permission requires admin role
        # Check BOTH role name and permissions for proper admin validation
        if required_permission == "admin":
            # For admin permission, check if user has admin ROLE (not just permission)
            has_admin_role = False
            for role in current_user.roles:
                if role.name == "admin" or "all" in role.permissions:
                    has_admin_role = True
                    break

            if not has_admin_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required. Only users with admin role can perform this action."
                )
        else:
            # For non-admin permissions, use standard permission check
            if not auth_service.has_permission(current_user, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_permission} required"
                )

        return current_user
    return permission_dependency


def require_admin(current_user: UserModel = Depends(get_current_user_flexible)) -> UserModel:
    """Dependency to check if the current user is an admin."""
    for role in current_user.roles:
        if role.name == "admin" or "all" in role.permissions:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


def secure_all_routes(router: APIRouter, exclude_paths: List[str] = None, permissions: Dict[str, Any] = None):
    """
    Apply authentication dependencies to all routes in a router.
    
    Args:
        router: The router to secure
        exclude_paths: List of path operations to exclude from authentication (e.g., ["/public-endpoint"])
        permissions: Dict mapping paths to required permissions (e.g., {"/admin-endpoint": "admin:access"})
                    Can also map paths to dicts of HTTP methods to permissions
        
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
        # Skip non-endpoint routes (like Mount)
        if not hasattr(route, 'path'):
            router.routes.append(route)
            continue
            
        path = route.path
        
        # Skip excluded paths
        if path in exclude_paths:
            router.routes.append(route)
            continue
        
        # Check if this path needs specific permissions
        if path in permissions:
            permission = permissions[path]
            
            # Handle method-specific permissions
            if isinstance(permission, dict) and hasattr(route, 'methods'):
                # Get the HTTP method for this route
                methods = route.methods if hasattr(route, 'methods') else []
                method = list(methods)[0] if methods else None
                
                if method in permission:
                    # Add method-specific permission dependency
                    route.dependencies.append(Depends(require_permission(permission[method])))
                else:
                    # Add general authentication dependency if method not specified
                    route.dependencies.append(Depends(get_current_user_flexible))
            else:
                # Add permission-specific dependency
                route.dependencies.append(Depends(require_permission(permission)))
        else:
            # Add general authentication dependency
            route.dependencies.append(Depends(get_current_user_flexible))
        
        router.routes.append(route)
    
    return router 
