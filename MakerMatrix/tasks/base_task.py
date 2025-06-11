"""
Base task class for all background tasks
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from MakerMatrix.models.task_models import TaskModel, UpdateTaskRequest

logger = logging.getLogger(__name__)


class BaseTask(ABC):
    """Base class for all background tasks"""
    
    def __init__(self, task_service=None):
        self.task_service = task_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def task_type(self) -> str:
        """Return the task type identifier"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable task name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the task description"""
        pass
    
    @abstractmethod
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """
        Execute the task logic
        
        Args:
            task: The task model containing input data and metadata
            
        Returns:
            Dict containing the result data
        """
        pass
    
    async def update_progress(self, task: TaskModel, progress: int, step: Optional[str] = None):
        """Update task progress"""
        if self.task_service:
            await self.task_service.update_task(
                task.id,
                UpdateTaskRequest(
                    progress_percentage=progress,
                    current_step=step
                )
            )
    
    async def update_step(self, task: TaskModel, step: str):
        """Update current step without changing progress"""
        if self.task_service:
            await self.task_service.update_task(
                task.id,
                UpdateTaskRequest(current_step=step)
            )
    
    async def sleep(self, seconds: float):
        """Async sleep with logging"""
        await asyncio.sleep(seconds)
    
    def get_input_data(self, task: TaskModel) -> Dict[str, Any]:
        """Get input data from task"""
        return task.get_input_data() if task else {}
    
    def log_info(self, message: str, task: TaskModel = None):
        """Log info message"""
        if task:
            self.logger.info(f"Task {task.id}: {message}")
            # Send to WebSocket (import here to avoid circular imports)
            try:
                from MakerMatrix.services.websocket_service import websocket_manager
                asyncio.create_task(websocket_manager.broadcast_task_log(
                    task.id, "info", message, task.current_step
                ))
            except ImportError:
                pass  # WebSocket service not available
        else:
            self.logger.info(message)
    
    def log_error(self, message: str, task: TaskModel = None, exc_info: bool = False):
        """Log error message"""
        if task:
            self.logger.error(f"Task {task.id}: {message}", exc_info=exc_info)
            # Send to WebSocket
            try:
                from MakerMatrix.services.websocket_service import websocket_manager
                asyncio.create_task(websocket_manager.broadcast_task_log(
                    task.id, "error", message, task.current_step
                ))
            except ImportError:
                pass
        else:
            self.logger.error(message, exc_info=exc_info)
    
    def validate_input_data(self, task: TaskModel, required_fields: list) -> bool:
        """Validate that required fields are present in input data"""
        input_data = self.get_input_data(task)
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            self.log_error(f"Missing required fields: {missing_fields}", task)
            return False
        
        return True