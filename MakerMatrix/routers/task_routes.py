from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from MakerMatrix.services.system.task_service import task_service
from MakerMatrix.services.system.task_security_service import task_security_service
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    CreateTaskRequest, UpdateTaskRequest, TaskFilterRequest
)
from MakerMatrix.models.task_security_model import get_user_allowed_task_types
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.models.user_models import UserModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Background Tasks"])


# Custom task creation removed for security reasons
# Only predefined quick task endpoints are allowed

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


# Quick task creation endpoints
@router.post("/quick/part_enrichment", response_model=Dict[str, Any])
async def quick_create_part_enrichment_task(
    request: Dict[str, Any],
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Quick create part enrichment task"""
    try:
        from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
        from MakerMatrix.suppliers.registry import SupplierRegistry
        
        # Extract request data
        part_id = request.get("part_id")
        supplier = request.get("supplier", "").lower()
        capabilities = request.get("capabilities", [])
        force_refresh = request.get("force_refresh", False)  # Accept but ignore for now
        
        if not part_id:
            raise HTTPException(status_code=400, detail="part_id is required")
        
        if not supplier:
            raise HTTPException(status_code=400, detail="supplier is required")
            
        if not capabilities:
            raise HTTPException(status_code=400, detail="capabilities are required")
        
        # Validate that the supplier has an actual enrichment implementation
        if not SupplierRegistry.is_supplier_available(supplier):
            available_suppliers = SupplierRegistry.get_available_suppliers()
            raise HTTPException(
                status_code=400, 
                detail=f"Supplier '{supplier}' has no enrichment implementation. Available suppliers: {', '.join(available_suppliers)}"
            )
        
        # Create task request
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name=f"Enrich part {part_id}",
            description=f"Enrich part using {supplier} with capabilities: {', '.join(capabilities)}",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_id": part_id,
                "supplier": supplier,
                "capabilities": capabilities
            },
            related_entity_type="part",
            related_entity_id=part_id
        )
        
        # Create the task
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        logger.info(f"Created part enrichment task {task.id} for part {part_id} with {supplier}")
        
        return {
            "status": "success",
            "message": "Part enrichment task created successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create part enrichment task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create part enrichment task: {str(e)}")


@router.post("/quick/datasheet_fetch", response_model=Dict[str, Any])  
async def quick_create_datasheet_fetch_task(
    request: Dict[str, Any],
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Quick create datasheet fetch task"""
    try:
        from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
        
        part_id = request.get("part_id")
        supplier = request.get("supplier", "").lower()
        
        if not part_id:
            raise HTTPException(status_code=400, detail="part_id is required")
        
        task_request = CreateTaskRequest(
            task_type=TaskType.DATASHEET_FETCH,
            name=f"Fetch datasheet for part {part_id}",
            description=f"Fetch datasheet using {supplier}",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_id": part_id,
                "supplier": supplier,
                "capabilities": ["fetch_datasheet"]
            },
            related_entity_type="part",
            related_entity_id=part_id
        )
        
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        return {
            "status": "success", 
            "message": "Datasheet fetch task created successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create datasheet fetch task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create datasheet fetch task: {str(e)}")


@router.post("/quick/image_fetch", response_model=Dict[str, Any])
async def quick_create_image_fetch_task(
    request: Dict[str, Any],
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Quick create image fetch task"""
    try:
        from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
        
        part_id = request.get("part_id")
        supplier = request.get("supplier", "").lower()
        
        if not part_id:
            raise HTTPException(status_code=400, detail="part_id is required")
        
        task_request = CreateTaskRequest(
            task_type=TaskType.IMAGE_FETCH,
            name=f"Fetch image for part {part_id}",
            description=f"Fetch image using {supplier}",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_id": part_id,
                "supplier": supplier,
                "capabilities": ["fetch_image"]
            },
            related_entity_type="part",
            related_entity_id=part_id
        )
        
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        return {
            "status": "success",
            "message": "Image fetch task created successfully", 
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create image fetch task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create image fetch task: {str(e)}")


@router.post("/quick/bulk_enrichment", response_model=Dict[str, Any])
async def quick_create_bulk_enrichment_task(
    request: Dict[str, Any],
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Quick create bulk enrichment task"""
    try:
        from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
        from MakerMatrix.suppliers.registry import SupplierRegistry
        
        part_ids = request.get("part_ids", [])
        supplier = request.get("supplier", "").lower()
        capabilities = request.get("capabilities", [])
        
        if not part_ids:
            raise HTTPException(status_code=400, detail="part_ids are required")
        
        # Validate that the supplier has an actual enrichment implementation
        if supplier and not SupplierRegistry.is_supplier_available(supplier):
            available_suppliers = SupplierRegistry.get_available_suppliers()
            raise HTTPException(
                status_code=400, 
                detail=f"Supplier '{supplier}' has no enrichment implementation. Available suppliers: {', '.join(available_suppliers)}"
            )
        
        task_request = CreateTaskRequest(
            task_type=TaskType.BULK_ENRICHMENT,
            name=f"Bulk enrich {len(part_ids)} parts",
            description=f"Bulk enrich parts using {supplier} with capabilities: {', '.join(capabilities)}",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_ids": part_ids,
                "supplier": supplier,
                "capabilities": capabilities
            }
        )
        
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        return {
            "status": "success",
            "message": "Bulk enrichment task created successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bulk enrichment task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create bulk enrichment task: {str(e)}")


@router.post("/quick/price_update", response_model=Dict[str, Any])
async def quick_create_price_update_task(
    request: Dict[str, Any],
    current_user: UserModel = Depends(require_permission("tasks:create"))
):
    """Quick create price update task"""
    try:
        from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
        
        part_ids = request.get("part_ids", [])
        supplier = request.get("supplier", "").lower()
        
        if not part_ids:
            raise HTTPException(status_code=400, detail="part_ids are required")
        
        task_request = CreateTaskRequest(
            task_type=TaskType.PRICE_UPDATE,
            name=f"Update prices for {len(part_ids)} parts",
            description=f"Update part prices using {supplier}",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_ids": part_ids,
                "supplier": supplier,
                "capabilities": ["fetch_pricing"]
            }
        )
        
        task = await task_service.create_task(task_request, user_id=current_user.id)
        
        return {
            "status": "success",
            "message": "Price update task created successfully",
            "data": task.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create price update task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create price update task: {str(e)}")


# Task capabilities endpoints
@router.get("/capabilities/suppliers", response_model=Dict[str, Any])
async def get_supplier_capabilities(
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get enrichment capabilities for all suppliers"""
    try:
        from MakerMatrix.suppliers.registry import SupplierRegistry
        
        capabilities = {}
        suppliers = SupplierRegistry.get_available_suppliers()
        
        for supplier_name in suppliers:
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name)
                supplier_capabilities = [cap.value for cap in supplier.get_capabilities()]
                capabilities[supplier_name] = supplier_capabilities
            except Exception as e:
                logger.warning(f"Failed to get capabilities for {supplier_name}: {e}")
                capabilities[supplier_name] = []
        
        return {
            "status": "success",
            "message": f"Retrieved capabilities for {len(capabilities)} suppliers",
            "data": capabilities
        }
    except Exception as e:
        logger.error(f"Failed to get supplier capabilities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get supplier capabilities: {str(e)}")


@router.get("/capabilities/suppliers/{supplier_name}", response_model=Dict[str, Any])
async def get_supplier_specific_capabilities(
    supplier_name: str,
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Get capabilities for a specific supplier"""
    try:
        from MakerMatrix.suppliers.registry import SupplierRegistry
        
        supplier = SupplierRegistry.get_supplier(supplier_name)
        capabilities = [cap.value for cap in supplier.get_capabilities()]
        
        return {
            "status": "success",
            "message": f"Retrieved capabilities for {supplier_name}",
            "data": capabilities
        }
    except Exception as e:
        logger.error(f"Failed to get capabilities for {supplier_name}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found or failed to get capabilities")


@router.get("/capabilities/find/{capability_type}", response_model=Dict[str, Any])
async def find_suppliers_with_capability(
    capability_type: str,
    current_user: UserModel = Depends(require_permission("tasks:read"))
):
    """Find suppliers that support a specific capability"""
    try:
        from MakerMatrix.suppliers.registry import SupplierRegistry
        
        matching_suppliers = []
        suppliers = SupplierRegistry.get_available_suppliers()
        
        for supplier_name in suppliers:
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name)
                capabilities = [cap.value for cap in supplier.get_capabilities()]
                if capability_type in capabilities:
                    matching_suppliers.append(supplier_name)
            except Exception as e:
                logger.warning(f"Failed to check capabilities for {supplier_name}: {e}")
        
        return {
            "status": "success",
            "message": f"Found {len(matching_suppliers)} suppliers with capability '{capability_type}'",
            "data": matching_suppliers
        }
    except Exception as e:
        logger.error(f"Failed to find suppliers with capability {capability_type}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find suppliers with capability: {str(e)}")


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


# Task creation validation endpoint removed - no longer needed without custom task creation

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