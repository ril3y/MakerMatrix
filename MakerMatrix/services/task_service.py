import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from sqlmodel import select, and_, or_
from MakerMatrix.database.db import get_session
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    CreateTaskRequest, UpdateTaskRequest, TaskFilterRequest
)
from MakerMatrix.tasks import get_task_class, get_all_task_types, list_available_tasks
from MakerMatrix.services.websocket_service import websocket_manager

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing background tasks"""
    
    def __init__(self):
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
    
    async def create_task(self, task_request: CreateTaskRequest, user_id: str = None) -> TaskModel:
        """Create a new task"""
        session = next(get_session())
        try:
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
            
            session.add(task)
            session.commit()
            session.refresh(task)
            
            logger.info(f"Created task {task.id}: {task.name}")
            return task
            
        finally:
            session.close()
    
    async def get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID"""
        session = next(get_session())
        try:
            task = session.get(TaskModel, task_id)
            return task
        finally:
            session.close()
    
    async def get_tasks(self, filter_request: TaskFilterRequest) -> List[TaskModel]:
        """Get tasks with filtering"""
        session = next(get_session())
        try:
            query = select(TaskModel)
            
            # Apply filters
            conditions = []
            
            if filter_request.status:
                conditions.append(TaskModel.status.in_(filter_request.status))
            
            if filter_request.task_type:
                conditions.append(TaskModel.task_type.in_(filter_request.task_type))
            
            if filter_request.priority:
                conditions.append(TaskModel.priority.in_(filter_request.priority))
            
            if filter_request.created_by_user_id:
                conditions.append(TaskModel.created_by_user_id == filter_request.created_by_user_id)
            
            if filter_request.related_entity_type:
                conditions.append(TaskModel.related_entity_type == filter_request.related_entity_type)
            
            if filter_request.related_entity_id:
                conditions.append(TaskModel.related_entity_id == filter_request.related_entity_id)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            if filter_request.order_desc:
                query = query.order_by(getattr(TaskModel, filter_request.order_by).desc())
            else:
                query = query.order_by(getattr(TaskModel, filter_request.order_by))
            
            # Apply pagination
            query = query.offset(filter_request.offset).limit(filter_request.limit)
            
            tasks = session.exec(query).all()
            return list(tasks)
            
        finally:
            session.close()
    
    async def update_task(self, task_id: str, update_request: UpdateTaskRequest) -> Optional[TaskModel]:
        """Update a task"""
        session = next(get_session())
        try:
            task = session.get(TaskModel, task_id)
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
            
            session.add(task)
            session.commit()
            session.refresh(task)
            
            # Send WebSocket update
            asyncio.create_task(websocket_manager.broadcast_task_update(task.to_dict()))
            
            return task
            
        finally:
            session.close()
    
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
        """Retry a failed task"""
        session = next(get_session())
        try:
            task = session.get(TaskModel, task_id)
            if not task or not task.can_retry():
                return False
            
            task.status = TaskStatus.PENDING
            task.retry_count += 1
            task.error_message = None
            task.started_at = None
            task.completed_at = None
            task.progress_percentage = 0
            task.current_step = None
            
            session.add(task)
            session.commit()
            
            logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
            return True
            
        finally:
            session.close()
    
    async def start_worker(self):
        """Start the task worker"""
        if self.is_worker_running:
            return
        
        self.is_worker_running = True
        logger.info("Starting task worker")
        
        try:
            while self.is_worker_running:
                await self._process_pending_tasks()
                await asyncio.sleep(1)  # Check for new tasks every second
        except Exception as e:
            logger.error(f"Task worker error: {e}")
        finally:
            self.is_worker_running = False
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
        """Process pending tasks"""
        session = next(get_session())
        try:
            # Get ready-to-run tasks
            query = select(TaskModel).where(
                and_(
                    TaskModel.status == TaskStatus.PENDING,
                    or_(
                        TaskModel.scheduled_at.is_(None),
                        TaskModel.scheduled_at <= datetime.utcnow()
                    )
                )
            ).order_by(TaskModel.priority.desc(), TaskModel.created_at)
            
            pending_tasks = session.exec(query).all()
            
            for task in pending_tasks:
                if task.id not in self.running_tasks:
                    await self._start_task(task)
                    
        finally:
            session.close()
    
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
            
        finally:
            # Remove from running tasks
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
    


# Global task service instance
task_service = TaskService()