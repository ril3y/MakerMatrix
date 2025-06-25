from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from MakerMatrix.services.task_service import task_service
from MakerMatrix.services.task_security_service import task_security_service
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    CreateTaskRequest, UpdateTaskRequest, TaskFilterRequest
)
from MakerMatrix.models.task_security_model import get_user_allowed_task_types
from MakerMatrix.dependencies.auth import require_permission
from MakerMatrix.models.user_models import UserModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Background Tasks"])


@router.post("/", response_model=Dict[str, Any])
async def create_task(
    task_request: CreateTaskRequest,
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Create a new background task with security validation"""
    try:
        # Validate task creation against security policies
        is_allowed, error_message = await task_security_service.validate_task_creation(task_request, current_user)
        
        if not is_allowed:
            # Log security denial
            await task_security_service.log_task_security_event(
                "task_denied", 
                current_user, 
                None,
                {"task_type": task_request.task_type.value, "reason": error_message}
            )
            raise HTTPException(status_code=403, detail=f"Task creation denied: {error_message}")
        
        # Create the task
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        # Log successful task creation
        await task_security_service.log_task_security_event(
            "task_created",
            current_user,
            task,
            {"task_type": task_request.task_type.value}
        )
        
        logger.info(f"Created task {task.id}: {task.name} by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task created successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/", response_model=Dict[str, Any])
async def get_tasks(
    status: Optional[List[TaskStatus]] = Query(None),
    task_type: Optional[List[TaskType]] = Query(None),
    priority: Optional[List[TaskPriority]] = Query(None),
    created_by_user_id: Optional[str] = Query(None),
    related_entity_type: Optional[str] = Query(None),
    related_entity_id: Optional[str] = Query(None),
    limit: int = Query(50, le=1000),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at"),
    order_desc: bool = Query(True),
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get tasks with filtering options"""
    try:
        filter_request = TaskFilterRequest(
            status=status,
            task_type=task_type,
            priority=priority,
            created_by_user_id=created_by_user_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc
        )
        
        tasks = await task_service.get_tasks(filter_request)
        
        return {
            "status": "success",
            "data": [task.to_dict() for task in tasks],
            "total": len(tasks),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.get("/my", response_model=Dict[str, Any])
async def get_my_tasks(
    status: Optional[List[TaskStatus]] = Query(None),
    task_type: Optional[List[TaskType]] = Query(None),
    priority: Optional[List[TaskPriority]] = Query(None),
    limit: int = Query(50, le=1000),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get tasks created by the current user"""
    try:
        filter_request = TaskFilterRequest(
            status=status,
            task_type=task_type,
            priority=priority,
            created_by_user_id=current_user.id,
            limit=limit,
            offset=offset,
            order_by="created_at",
            order_desc=True
        )
        
        tasks = await task_service.get_tasks(filter_request)
        
        return {
            "status": "success",
            "data": [task.to_dict() for task in tasks],
            "total": len(tasks)
        }
    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user tasks: {str(e)}")


# IMPORTANT: Place all specific routes BEFORE parameterized routes like /{task_id}
# This ensures FastAPI matches the specific paths first

@router.get("/types/available", response_model=Dict[str, Any])
async def get_available_task_types(
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get available task types and their descriptions"""
    try:
        # Get task types from the task service (dynamically discovered)
        task_types = task_service.get_available_task_types()
        
        return {
            "status": "success",
            "data": task_types
        }
    except Exception as e:
        logger.error(f"Failed to get task types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task types: {str(e)}")


@router.get("/stats/summary", response_model=Dict[str, Any])
async def get_task_stats(
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get task statistics summary"""
    try:
        # Get tasks grouped by status
        all_tasks_filter = TaskFilterRequest(limit=1000)  # Get up to 1000 tasks for stats
        tasks = await task_service.get_tasks(all_tasks_filter)
        
        stats = {
            "total_tasks": len(tasks),
            "by_status": {},
            "by_type": {},
            "by_priority": {},
            "running_tasks": 0,
            "failed_tasks": 0,
            "completed_today": 0
        }
        
        # Calculate stats
        today = datetime.utcnow().date()
        
        for task in tasks:
            # By status
            status = task.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # By type
            task_type = task.task_type
            stats["by_type"][task_type] = stats["by_type"].get(task_type, 0) + 1
            
            # By priority
            priority = task.priority
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            
            # Running tasks
            if task.status == TaskStatus.RUNNING:
                stats["running_tasks"] += 1
            
            # Failed tasks
            if task.status == TaskStatus.FAILED:
                stats["failed_tasks"] += 1
            
            # Completed today
            if (task.status == TaskStatus.COMPLETED and 
                task.completed_at and 
                task.completed_at.date() == today):
                stats["completed_today"] += 1
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task stats: {str(e)}")


@router.post("/worker/start", response_model=Dict[str, Any])
async def start_task_worker(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(require_permission("tasks:admin"))
):
    """Start the task worker (admin only)"""
    try:
        if task_service.is_worker_running:
            return {
                "status": "info",
                "message": "Task worker is already running"
            }
        
        # Start worker in background
        background_tasks.add_task(task_service.start_worker)
        
        logger.info(f"Task worker started by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task worker started successfully"
        }
    except Exception as e:
        logger.error(f"Failed to start task worker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start task worker: {str(e)}")


@router.post("/worker/stop", response_model=Dict[str, Any])
async def stop_task_worker(
    current_user: UserModel = Depends(require_permission("tasks:admin"))
):
    """Stop the task worker (admin only)"""
    try:
        if not task_service.is_worker_running:
            return {
                "status": "info",
                "message": "Task worker is not running"
            }
        
        await task_service.stop_worker()
        
        logger.info(f"Task worker stopped by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task worker stopped successfully"
        }
    except Exception as e:
        logger.error(f"Failed to stop task worker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop task worker: {str(e)}")


@router.get("/worker/status", response_model=Dict[str, Any])
async def get_worker_status(
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get task worker status"""
    try:
        return {
            "status": "success",
            "data": {
                "is_running": task_service.is_worker_running,
                "running_tasks_count": len(task_service.running_tasks),
                "running_task_ids": list(task_service.running_tasks.keys()),
                "registered_handlers": len(task_service.task_instances)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get worker status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")


# Quick task endpoints removed - use enrichment_routes.py for enrichment tasks


# Removed - use /api/enrichment/tasks/part


# Removed - use /api/enrichment/tasks/part with datasheet capability


# Removed - use /api/enrichment/tasks/part with image capability


# Removed - use /api/enrichment/tasks/bulk


# Removed - use /api/enrichment/tasks/part with pricing capability


# Removed - database cleanup should use generic task creation


# Enrichment capabilities endpoints moved to enrichment_routes.py


# Security and permissions endpoints
@router.get("/security/permissions", response_model=Dict[str, Any])
async def get_user_task_permissions(
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Get user's task permissions and allowed task types"""
    try:
        # Get user permissions
        user_permissions = await task_security_service._get_user_permissions(current_user)
        allowed_task_types = get_user_allowed_task_types(user_permissions)
        
        # Get security summary
        from MakerMatrix.models.task_security_model import get_task_security_summary
        security_summary = get_task_security_summary()
        
        return {
            "status": "success",
            "data": {
                "user_permissions": user_permissions,
                "allowed_task_types": [task_type.value for task_type in allowed_task_types],
                "security_levels": security_summary,
                "user_role": current_user.role.name if current_user.role else "no_role"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get user task permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task permissions: {str(e)}")


@router.get("/security/limits", response_model=Dict[str, Any])
async def get_user_task_limits(
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Get user's current task usage and limits"""
    try:
        from MakerMatrix.models.task_security_model import TASK_SECURITY_POLICIES
        from MakerMatrix.database.db import get_session
        from sqlmodel import select, func, and_
        from datetime import datetime, timedelta
        
        session = next(get_session())
        try:
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Get current usage statistics
            current_usage = {}
            
            for task_type, policy in TASK_SECURITY_POLICIES.items():
                # Check if user can access this task type
                user_permissions = await task_security_service._get_user_permissions(current_user)
                if not all(perm in user_permissions for perm in policy.required_permissions):
                    continue
                
                # Get current running tasks
                running_count = session.exec(
                    select(func.count(TaskModel.id))
                    .where(
                        and_(
                            TaskModel.created_by_user_id == current_user.id,
                            TaskModel.task_type == task_type,
                            TaskModel.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
                        )
                    )
                ).one()
                
                # Get hourly usage
                hourly_count = session.exec(
                    select(func.count(TaskModel.id))
                    .where(
                        and_(
                            TaskModel.created_by_user_id == current_user.id,
                            TaskModel.task_type == task_type,
                            TaskModel.created_at >= hour_ago
                        )
                    )
                ).one()
                
                # Get daily usage
                daily_count = session.exec(
                    select(func.count(TaskModel.id))
                    .where(
                        and_(
                            TaskModel.created_by_user_id == current_user.id,
                            TaskModel.task_type == task_type,
                            TaskModel.created_at >= day_ago
                        )
                    )
                ).one()
                
                current_usage[task_type.value] = {
                    "concurrent_running": running_count,
                    "max_concurrent": policy.max_concurrent_per_user,
                    "hourly_usage": hourly_count,
                    "hourly_limit": policy.rate_limit_per_hour,
                    "daily_usage": daily_count,
                    "daily_limit": policy.rate_limit_per_day,
                    "security_level": policy.security_level.value,
                    "risk_level": policy.risk_level.value
                }
            
            return {
                "status": "success",
                "data": {
                    "current_usage": current_usage,
                    "time_until_hourly_reset": 60 - now.minute,
                    "time_until_daily_reset": (24 - now.hour) * 60 - now.minute
                }
            }
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to get user task limits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task limits: {str(e)}")


@router.post("/security/validate", response_model=Dict[str, Any])
async def validate_task_creation_security(
    task_request: CreateTaskRequest,
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Validate if a task can be created without actually creating it"""
    try:
        is_allowed, error_message = await task_security_service.validate_task_creation(task_request, current_user)
        
        return {
            "status": "success",
            "data": {
                "allowed": is_allowed,
                "error_message": error_message,
                "task_type": task_request.task_type.value
            }
        }
    except Exception as e:
        logger.error(f"Failed to validate task creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate task creation: {str(e)}")


# PARAMETERIZED ROUTES MUST COME LAST to avoid conflicts
@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: str,
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get a specific task by ID"""
    try:
        task = await task_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "status": "success",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_id: str,
    update_request: UpdateTaskRequest,
    current_user: UserModel = Depends(require_permission("tasks:update"))
):
    """Update a task"""
    try:
        task = await task_service.update_task(task_id, update_request)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Updated task {task_id} by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task updated successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.post("/{task_id}/cancel", response_model=Dict[str, Any])
async def cancel_task(
    task_id: str,
    current_user: UserModel = Depends(require_permission("tasks:update"))
):
    """Cancel a running or pending task"""
    try:
        success = await task_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        logger.info(f"Cancelled task {task_id} by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


@router.post("/{task_id}/retry", response_model=Dict[str, Any])
async def retry_task(
    task_id: str,
    current_user: UserModel = Depends(require_permission("tasks:update"))
):
    """Retry a failed task"""
    try:
        success = await task_service.retry_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Task cannot be retried (not failed or max retries reached)")
        
        logger.info(f"Retried task {task_id} by user {current_user.username}")
        
        return {
            "status": "success",
            "message": "Task retry scheduled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retry task: {str(e)}")