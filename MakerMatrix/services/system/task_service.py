import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from MakerMatrix.database.db import get_session
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    CreateTaskRequest, UpdateTaskRequest, TaskFilterRequest
)
from MakerMatrix.repositories.task_repository import TaskRepository
from MakerMatrix.tasks import get_task_class, get_all_task_types, list_available_tasks
from MakerMatrix.services.system.websocket_service import websocket_manager
from MakerMatrix.services.base_service import BaseService, ServiceResponse
from MakerMatrix.services.activity_service import get_activity_service

logger = logging.getLogger(__name__)


class TaskService(BaseService):
    """
    Service for managing background tasks using repository pattern.
    
    ✅ ARCHITECTURE COMPLIANCE: This service uses TaskRepository for all database operations.
    All database access is properly delegated to the repository layer following the 
    established pattern where ONLY repositories handle database sessions and SQL operations.
    
    This migration eliminates all direct database access violations and ensures proper
    separation of concerns between service and repository layers.
    """
    
    def __init__(self):
        super().__init__()
        self.entity_name = "Task"
        self.task_repository = TaskRepository()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_instances: Dict[str, Any] = {}  # Cache task instances
        self.is_worker_running = False
        
        # Register modular task handlers
        self._register_modular_handlers()
    
    def _register_modular_handlers(self):
        """Register modular task handlers from the tasks directory"""
        available_tasks = get_all_task_types()
        
        for task_type, task_class in available_tasks.items():
            try:
                # Create task instance and cache it
                task_instance = task_class(task_service=self)
                self.task_instances[task_type] = task_instance
                logger.info(f"Registered task handler: {task_type} -> {task_class.__name__}")
            except Exception as e:
                logger.error(f"Failed to register task handler {task_type}: {e}")
    
    def get_available_task_types(self) -> List[Dict[str, str]]:
        """Get list of available task types with metadata"""
        task_types = []
        
        for task_type, task_instance in self.task_instances.items():
            task_types.append({
                "type": task_type,
                "name": task_instance.name,
                "description": task_instance.description
            })
        
        return task_types
    
    async def create_task(self, task_request: CreateTaskRequest, user_id: str = None) -> ServiceResponse[Dict[str, Any]]:
        """
        Create a new task using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        try:
            self.log_operation("create", self.entity_name, task_request.name)
            
            async with self.get_async_session() as session:
                task = TaskModel(
                    task_type=task_request.task_type,
                    name=task_request.name,
                    description=task_request.description,
                    priority=task_request.priority,
                    max_retries=task_request.max_retries,
                    timeout_seconds=task_request.timeout_seconds,
                    scheduled_at=task_request.scheduled_at,
                    created_by_user_id=user_id,
                    related_entity_type=task_request.related_entity_type,
                    related_entity_id=task_request.related_entity_id,
                    parent_task_id=task_request.parent_task_id
                )
                
                if task_request.input_data:
                    task.set_input_data(task_request.input_data)
                
                if task_request.depends_on_task_ids:
                    task.set_depends_on(task_request.depends_on_task_ids)
                
                # Use repository for database operations
                created_task = self.task_repository.create_task(session, task)
                
                # Convert to dict within session to prevent DetachedInstanceError
                task_dict = created_task.to_dict()
                
                # Send WebSocket notification for task creation
                asyncio.create_task(websocket_manager.broadcast_task_update(task_dict))
                
                return self.success_response(
                    f"{self.entity_name} '{created_task.name}' created successfully",
                    task_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")
    
    async def get_task(self, task_id: str) -> ServiceResponse[Dict[str, Any]]:
        """
        Get a task by ID using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        try:
            self.log_operation("get", self.entity_name, task_id)
            
            async with self.get_async_session() as session:
                task = self.task_repository.get_by_id(session, task_id)
                if not task:
                    return self.error_response(f"{self.entity_name} with ID {task_id} not found")
                
                # Convert to dict within session to prevent DetachedInstanceError
                task_dict = task.to_dict()
                
                return self.success_response(
                    f"{self.entity_name} retrieved successfully",
                    task_dict
                )
                
        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}")
    
    async def get_tasks(self, filter_request: TaskFilterRequest) -> List[Dict[str, Any]]:
        """
        Get tasks with filtering using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        async with self.get_async_session() as session:
            tasks = self.task_repository.get_tasks_with_filter(session, filter_request)
            # Convert to dict within session to prevent DetachedInstanceError
            return [task.to_dict() for task in tasks]
    
    async def update_task(self, task_id: str, update_request: UpdateTaskRequest) -> Optional[TaskModel]:
        """
        Update a task using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        async with self.get_async_session() as session:
            task = self.task_repository.get_by_id(session, task_id)
            if not task:
                return None
            
            if update_request.status is not None:
                task.status = update_request.status
                if update_request.status == TaskStatus.RUNNING and not task.started_at:
                    task.started_at = datetime.utcnow()
                elif update_request.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    task.completed_at = datetime.utcnow()
            
            if update_request.progress_percentage is not None:
                task.progress_percentage = update_request.progress_percentage
            
            if update_request.current_step is not None:
                task.current_step = update_request.current_step
            
            if update_request.result_data is not None:
                task.set_result_data(update_request.result_data)
            
            if update_request.error_message is not None:
                task.error_message = update_request.error_message
            
            # Use repository for database operations
            updated_task = self.task_repository.update_task(session, task)
            
            # Send WebSocket update
            asyncio.create_task(websocket_manager.broadcast_task_update(updated_task.to_dict()))
            
            return updated_task
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        # Cancel running task if exists
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Update database
        update_request = UpdateTaskRequest(
            status=TaskStatus.CANCELLED,
            current_step="Task cancelled by user"
        )
        task = await self.update_task(task_id, update_request)
        return task is not None
    
    async def retry_task(self, task_id: str) -> bool:
        """
        Retry a failed task using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        async with self.get_async_session() as session:
            task = self.task_repository.increment_retry_count(session, task_id)
            return task is not None
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a completed or failed task using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        try:
            async with self.get_async_session() as session:
                return self.task_repository.delete_task(session, task_id)
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
    
    async def start_worker(self):
        """Start the task worker with automatic restart on errors"""
        if self.is_worker_running:
            return
        
        self.is_worker_running = True
        logger.info("Starting task worker")
        
        while self.is_worker_running:
            try:
                await self._process_pending_tasks()
                await asyncio.sleep(1)  # Check for new tasks every second
            except Exception as e:
                logger.error(f"Task worker error: {e}", exc_info=True)
                logger.warning("Task worker encountered an error but will continue running...")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
        
        logger.info("Task worker stopped")
    
    async def stop_worker(self):
        """Stop the task worker"""
        self.is_worker_running = False
        
        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            task.cancel()
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.CANCELLED,
                current_step="Worker shutdown"
            ))
        
        self.running_tasks.clear()
    
    async def _process_pending_tasks(self):
        """
        Process pending tasks using repository pattern.
        
        ✅ REPOSITORY PATTERN: All database operations delegated to TaskRepository.
        """
        try:
            async with self.get_async_session() as session:
                pending_tasks = self.task_repository.get_pending_tasks_ready_to_run(session)
                
                # Extract task IDs while session is active to avoid DetachedInstanceError
                task_ids_to_start = []
                for task in pending_tasks:
                    if task.id not in self.running_tasks:
                        task_ids_to_start.append(task.id)
                
            # Start tasks using IDs (outside session to avoid conflicts)
            for task_id in task_ids_to_start:
                try:
                    await self._start_task_by_id(task_id)
                except Exception as e:
                    logger.error(f"Failed to start task {task_id}: {e}", exc_info=True)
                    # Continue processing other tasks
                        
        except Exception as e:
            logger.error(f"Error in _process_pending_tasks: {e}", exc_info=True)
            # Don't let database errors crash the worker
    
    async def _start_task(self, task: TaskModel):
        """Start executing a task"""
        if task.task_type not in self.task_instances:
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=f"No handler found for task type: {task.task_type}"
            ))
            return
        
        logger.info(f"Starting task {task.id}: {task.name}")
        
        # Create and start the task
        async_task = asyncio.create_task(self._execute_task(task))
        self.running_tasks[task.id] = async_task
    
    async def _start_task_by_id(self, task_id: str):
        """Start executing a task by ID (session-safe version) - Fixed DetachedInstanceError"""
        # Fetch fresh task instance in new session to avoid DetachedInstanceError
        async with self.get_async_session() as session:
            task = self.task_repository.get_by_id(session, task_id)
            if not task:
                logger.error(f"Task {task_id} not found when trying to start")
                return
                
            # Extract data while session is active
            task_type = task.task_type
            task_name = task.name
                
        # Check if task type has a handler
        if task_type not in self.task_instances:
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=f"No handler found for task type: {task_type}"
            ))
            return
        
        logger.info(f"Starting task {task_id}: {task_name}")
        
        # Create and start the task
        async_task = asyncio.create_task(self._execute_task_by_id(task_id))
        self.running_tasks[task_id] = async_task
    
    async def _execute_task(self, task: TaskModel):
        """Execute a task with error handling and timeout"""
        try:
            # Mark as running
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.RUNNING,
                current_step="Starting task execution"
            ))
            
            # Get the task instance and execute it
            task_instance = self.task_instances[task.task_type]
            
            if task.timeout_seconds:
                result_data = await asyncio.wait_for(
                    task_instance.execute(task), 
                    timeout=task.timeout_seconds
                )
            else:
                result_data = await task_instance.execute(task)
            
            # Mark as completed
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.COMPLETED,
                progress_percentage=100,
                current_step="Task completed successfully"
            ))

            logger.info(f"Task {task.id} completed successfully")

            # Log task completion activity
            try:
                activity_service = get_activity_service()
                user = await self._get_user_from_task(task)
                duration_seconds = (datetime.utcnow() - task.started_at).total_seconds() if task.started_at else None
                await activity_service.log_activity(
                    action="completed",
                    entity_type="task",
                    entity_id=task.id,
                    entity_name=task.name,
                    user=user,
                    details={
                        "task_type": task.task_type,
                        "duration_seconds": duration_seconds
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log task completion activity: {log_error}")
            
        except asyncio.TimeoutError:
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=f"Task timed out after {task.timeout_seconds} seconds"
            ))
            logger.error(f"Task {task.id} timed out")
            
        except asyncio.CancelledError:
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.CANCELLED,
                current_step="Task was cancelled"
            ))
            logger.info(f"Task {task.id} was cancelled")
            
        except Exception as e:
            await self.update_task(task.id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=str(e)
            ))
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)

            # Log task failure activity
            try:
                activity_service = get_activity_service()
                user = await self._get_user_from_task(task)
                await activity_service.log_activity(
                    action="failed",
                    entity_type="task",
                    entity_id=task.id,
                    entity_name=task.name,
                    user=user,
                    details={
                        "task_type": task.task_type,
                        "error": str(e)
                    }
                )
            except Exception as log_error:
                logger.warning(f"Failed to log task failure activity: {log_error}")
            
        finally:
            # Remove from running tasks
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

    async def _execute_task_by_id(self, task_id: str):
        """Execute a task by ID with error handling and timeout (session-safe version)"""
        try:
            # Mark as running
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.RUNNING,
                current_step="Starting task execution"
            ))
            
            # Fetch fresh task instance in new session
            task_type = None
            timeout_seconds = None
            async with self.get_async_session() as session:
                task = self.task_repository.get_by_id(session, task_id)
                if not task:
                    await self.update_task(task_id, UpdateTaskRequest(
                        status=TaskStatus.FAILED,
                        error_message="Task not found when executing"
                    ))
                    return
                
                # Extract data while session is active
                task_type = task.task_type
                timeout_seconds = task.timeout_seconds
            
            # Get the task instance and execute it
            task_instance = self.task_instances[task_type]
            
            # Fetch task again for execution (fresh session)
            async with self.get_async_session() as session:
                task = self.task_repository.get_by_id(session, task_id)
                if not task:
                    await self.update_task(task_id, UpdateTaskRequest(
                        status=TaskStatus.FAILED,
                        error_message="Task not found during execution"
                    ))
                    return
                
                if timeout_seconds:
                    result_data = await asyncio.wait_for(
                        task_instance.execute(task), 
                        timeout=timeout_seconds
                    )
                else:
                    result_data = await task_instance.execute(task)
            
            # Mark as completed
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.COMPLETED,
                progress_percentage=100,
                current_step="Task completed successfully"
            ))
            
            logger.info(f"Task {task_id} completed successfully")
            
        except asyncio.TimeoutError:
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=f"Task timed out after {timeout_seconds} seconds"
            ))
            logger.error(f"Task {task_id} timed out")
            
        except asyncio.CancelledError:
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.CANCELLED,
                error_message="Task was cancelled"
            ))
            logger.info(f"Task {task_id} was cancelled")
            
        except Exception as e:
            await self.update_task(task_id, UpdateTaskRequest(
                status=TaskStatus.FAILED,
                error_message=str(e)
            ))
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            
        finally:
            # Remove from running tasks
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    async def _get_user_from_task(self, task: TaskModel) -> Optional[Any]:
        """Get user object from task's created_by_user_id."""
        if not task.created_by_user_id:
            return None

        try:
            from MakerMatrix.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            async with self.get_async_session() as session:
                return user_repo.get_by_id(session, task.created_by_user_id)
        except Exception as e:
            logger.warning(f"Failed to get user for task: {e}")
            return None


# Global task service instance
task_service = TaskService()



async def create_file_import_enrichment_task(
    imported_part_ids: List[str], 
    supplier: str, 
    user_id: str,
    file_type: str = None
) -> TaskModel:
    """Create a file import enrichment task for imported parts"""
    from MakerMatrix.repositories.parts_repositories import PartRepository
    from MakerMatrix.models.models import engine
    from sqlmodel import Session
    
    # Prepare enrichment queue by fetching part data
    enrichment_queue = []
    
    with Session(engine) as session:
        part_repo = PartRepository(engine)
        
        for part_id in imported_part_ids:
            try:
                part = part_repo.get_part_by_id(session, part_id)
                if part:
                    # Convert part to dict format expected by the task
                    part_data = {
                        'part_id': part.id,
                        'part_name': part.part_name,
                        'part_number': part.part_number,
                        'supplier': part.supplier,
                        'description': part.description,
                        'additional_properties': part.additional_properties or {}
                    }
                    
                    # Set enrichment source and capabilities
                    if not part_data['additional_properties'].get('enrichment_source'):
                        part_data['additional_properties']['enrichment_source'] = supplier.upper()
                    
                    # Get actual capabilities supported by the supplier
                    from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
                    try:
                        supplier_service = SupplierConfigService()
                        supplier_config = supplier_service.get_supplier_config(supplier.upper())
                        available_capabilities = supplier_config.get('capabilities', [])
                        part_data['additional_properties']['available_capabilities'] = available_capabilities
                        logger.info(f"Using capabilities for {supplier}: {available_capabilities}")
                    except Exception as e:
                        logger.warning(f"Failed to get capabilities for {supplier}, using defaults: {e}")
                        # Fallback to standard enrichment capabilities
                        part_data['additional_properties']['available_capabilities'] = [
                            "fetch_datasheet", 
                            "fetch_image", 
                            "fetch_pricing", 
                            "fetch_specifications"
                        ]
                    
                    enrichment_queue.append({
                        'part_id': part_id,
                        'part_data': part_data
                    })
            except Exception as e:
                logger.error(f"Failed to prepare part {part_id} for enrichment: {e}")
    
    file_type_str = f" {file_type}" if file_type else ""
    task_request = CreateTaskRequest(
        task_type=TaskType.FILE_IMPORT_ENRICHMENT,
        name=f"File Import Enrichment - {supplier}{file_type_str}",
        description=f"Enrich {len(enrichment_queue)} parts imported from {supplier}{file_type_str} file",
        priority=TaskPriority.NORMAL,
        input_data={
            "enrichment_queue": enrichment_queue
        },
        created_by_user_id=user_id,
        max_retries=2,
        timeout_seconds=3600  # 1 hour timeout for large CSV imports
    )
    
    task = await task_service.create_task(task_request)
    return task