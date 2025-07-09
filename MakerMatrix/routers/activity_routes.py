"""
API routes for activity logging and retrieval.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from MakerMatrix.services.activity_service import get_activity_service, ActivityService
from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.routers.base import BaseRouter, standard_error_handling
from MakerMatrix.schemas.response import ResponseSchema


router = APIRouter()
base_router = BaseRouter()


class ActivityResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: Optional[str]
    entity_name: Optional[str]
    username: Optional[str]
    timestamp: str
    details: dict


class ActivityListResponse(BaseModel):
    activities: List[ActivityResponse]
    total: int


@router.get("/recent")
@standard_error_handling
async def get_recent_activities(
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (part, printer, label, etc.)"),
    hours: int = Query(24, ge=1, le=168, description="Hours back to look for activities"),
    current_user: UserModel = Depends(get_current_user),
    activity_service: ActivityService = Depends(get_activity_service)
) -> ResponseSchema:
    """Get recent activities."""
    
    activities = activity_service.get_recent_activities(
        limit=limit,
        entity_type=entity_type,
        hours=hours
    )
    
    activity_responses = [
        ActivityResponse(
            id=activity.id,
            action=activity.action,
            entity_type=activity.entity_type,
            entity_id=activity.entity_id,
            entity_name=activity.entity_name,
            username=activity.username or "system",
            timestamp=activity.timestamp.isoformat(),
            details=activity.details or {}
        )
        for activity in activities
    ]
    
    return base_router.build_success_response(
        data={
            "activities": [r.model_dump() for r in activity_responses],
            "total": len(activity_responses)
        },
        message="Recent activities retrieved successfully"
    )


@router.get("/stats")
@standard_error_handling
async def get_activity_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours back to analyze"),
    current_user: UserModel = Depends(get_current_user),
    activity_service: ActivityService = Depends(get_activity_service)
) -> ResponseSchema:
    """Get activity statistics."""
    
    activities = activity_service.get_recent_activities(
        limit=1000,  # Get more for stats
        hours=hours
    )
    
    # Calculate stats
    stats = {
        "total_activities": len(activities),
        "by_action": {},
        "by_entity_type": {},
        "by_user": {},
        "most_active_hour": None
    }
    
    # Count by action type
    for activity in activities:
        action = activity.action
        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
        
        entity_type = activity.entity_type
        stats["by_entity_type"][entity_type] = stats["by_entity_type"].get(entity_type, 0) + 1
        
        username = activity.username or "system"
        stats["by_user"][username] = stats["by_user"].get(username, 0) + 1
    
    return base_router.build_success_response(
        data=stats,
        message="Activity statistics retrieved successfully"
    )


@router.post("/cleanup")
@standard_error_handling
async def cleanup_old_activities(
    keep_days: int = Query(90, ge=7, le=365, description="Days of activities to keep"),
    current_user: UserModel = Depends(get_current_user),
    activity_service: ActivityService = Depends(get_activity_service)
) -> ResponseSchema:
    """Clean up old activity records (admin only)."""
    
    # Check if user has admin permissions
    if not any(role.name == "admin" for role in current_user.roles):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    
    deleted_count = activity_service.cleanup_old_activities(keep_days=keep_days)
    
    return base_router.build_success_response(
        data={
            "deleted_count": deleted_count,
            "keep_days": keep_days
        },
        message=f"Cleaned up {deleted_count} old activity records"
    )