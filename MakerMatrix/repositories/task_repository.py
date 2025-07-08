import logging
from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select, and_, or_
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    TaskFilterRequest
)
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class TaskRepository(BaseRepository[TaskModel]):
    """
    Repository for task database operations.
    
    Follows the established repository pattern where ONLY repositories
    handle database sessions and SQL operations. Services delegate all
    database operations to repositories.
    """
    
    def __init__(self):
        super().__init__(TaskModel)
    
    def create_task(self, session: Session, task: TaskModel) -> TaskModel:
        """Create a new task with proper session management."""
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    
    def update_task(self, session: Session, task: TaskModel) -> TaskModel:
        """Update an existing task with proper session management."""
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    
    def delete_task(self, session: Session, task_id: str) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""
        task = self.get_by_id(session, task_id)
        if not task:
            return False
            
        # Only allow deletion of completed, failed, or cancelled tasks
        if task.status in [TaskStatus.RUNNING, TaskStatus.PENDING, TaskStatus.RETRY]:
            return False
            
        session.delete(task)
        session.commit()
        logger.info(f"Deleted task {task_id} (status: {task.status})")
        return True
    
    def get_tasks_with_filter(self, session: Session, filter_request: TaskFilterRequest) -> List[TaskModel]:
        """Get tasks with filtering and pagination."""
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
    
    def get_pending_tasks_ready_to_run(self, session: Session) -> List[TaskModel]:
        """Get pending tasks that are ready to run (scheduled time has passed)."""
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
        return list(pending_tasks)
    
    def update_task_status(self, session: Session, task_id: str, status: TaskStatus, 
                          current_step: str = None, progress_percentage: int = None,
                          error_message: str = None, result_data: dict = None) -> Optional[TaskModel]:
        """Update task status and related fields in a single operation."""
        task = self.get_by_id(session, task_id)
        if not task:
            return None
        
        task.status = status
        
        # Update timestamps based on status
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.utcnow()
        
        # Update optional fields
        if current_step is not None:
            task.current_step = current_step
            
        if progress_percentage is not None:
            task.progress_percentage = progress_percentage
            
        if error_message is not None:
            task.error_message = error_message
            
        if result_data is not None:
            task.set_result_data(result_data)
        
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    
    def increment_retry_count(self, session: Session, task_id: str) -> Optional[TaskModel]:
        """Increment retry count and reset task for retry."""
        task = self.get_by_id(session, task_id)
        if not task or not task.can_retry():
            return None
        
        task.status = TaskStatus.PENDING
        task.retry_count += 1
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        task.progress_percentage = 0
        task.current_step = None
        
        session.add(task)
        session.commit()
        session.refresh(task)
        
        logger.info(f"Retrying task {task_id} (attempt {task.retry_count})")
        return task
    
    def get_tasks_by_user(self, session: Session, user_id: str, 
                         limit: int = 50, offset: int = 0) -> List[TaskModel]:
        """Get tasks created by a specific user."""
        query = select(TaskModel).where(
            TaskModel.created_by_user_id == user_id
        ).order_by(TaskModel.created_at.desc()).offset(offset).limit(limit)
        
        tasks = session.exec(query).all()
        return list(tasks)
    
    def get_running_tasks(self, session: Session) -> List[TaskModel]:
        """Get all currently running tasks."""
        query = select(TaskModel).where(TaskModel.status == TaskStatus.RUNNING)
        tasks = session.exec(query).all()
        return list(tasks)