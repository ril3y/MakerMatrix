from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    # Import and processing tasks
    FILE_IMPORT_ENRICHMENT = "file_import_enrichment"  # Handles CSV, XLS, etc.

    # General maintenance tasks
    PRICE_UPDATE = "price_update"
    DATABASE_CLEANUP = "database_cleanup"
    FILE_DOWNLOAD = "file_download"
    DATA_SYNC = "data_sync"
    INVENTORY_AUDIT = "inventory_audit"
    PART_VALIDATION = "part_validation"

    # Backup and restore tasks
    BACKUP_CREATION = "backup_creation"
    BACKUP_RESTORE = "backup_restore"
    BACKUP_SCHEDULED = "backup_scheduled"
    BACKUP_RETENTION = "backup_retention"

    # Notification and reporting
    EMAIL_NOTIFICATION = "email_notification"
    REPORT_GENERATION = "report_generation"
    
    # Enrichment task types
    PART_ENRICHMENT = "part_enrichment"  # Enrich a single part with all available data
    BULK_ENRICHMENT = "bulk_enrichment"  # Enrich multiple parts
    
    # Specific enrichment capabilities (usually part of PART_ENRICHMENT)
    DATASHEET_FETCH = "fetch_datasheet"
    IMAGE_FETCH = "fetch_image"
    PRICING_FETCH = "fetch_pricing"
    STOCK_FETCH = "fetch_stock"
    SPECIFICATIONS_FETCH = "fetch_specifications"
    
    # Other enrichment-related tasks
    PART_VALIDATION_ENRICHMENT = "part_validation_enrichment"
    SUPPLIER_DATA_SYNC = "supplier_data_sync"

    # Datasheet download task
    DATASHEET_DOWNLOAD = "datasheet_download"

    # Printer management task types
    PRINTER_DISCOVERY = "printer_discovery"


class TaskModel(SQLModel, table=True):
    """Background task management model"""
    __tablename__ = "tasks"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Task identification
    task_type: TaskType = Field(index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = None
    
    # Task status and progress
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, index=True)
    progress_percentage: int = Field(default=0, ge=0, le=100)
    current_step: Optional[str] = None
    
    # Task data and results
    input_data: Optional[str] = Field(default=None)  # JSON string
    result_data: Optional[str] = Field(default=None)  # JSON string
    error_message: Optional[str] = None
    
    # Execution tracking
    max_retries: int = Field(default=3)
    retry_count: int = Field(default=0)
    timeout_seconds: Optional[int] = Field(default=300)  # 5 minutes default
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None  # For delayed execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # User and context
    created_by_user_id: Optional[str] = Field(default=None, index=True)
    related_entity_type: Optional[str] = None  # e.g., "part", "order", "user"
    related_entity_id: Optional[str] = None
    
    # Task dependencies
    parent_task_id: Optional[str] = Field(default=None)
    depends_on_task_ids: Optional[str] = Field(default=None)  # JSON array of task IDs
    
    def set_input_data(self, data: Dict[str, Any]):
        """Set input data as JSON"""
        self.input_data = json.dumps(data) if data else None
    
    def get_input_data(self) -> Dict[str, Any]:
        """Get input data from JSON"""
        return json.loads(self.input_data) if self.input_data else {}
    
    def set_result_data(self, data: Dict[str, Any]):
        """Set result data as JSON"""
        self.result_data = json.dumps(data) if data else None
    
    def get_result_data(self) -> Dict[str, Any]:
        """Get result data from JSON"""
        return json.loads(self.result_data) if self.result_data else {}
    
    def set_depends_on(self, task_ids: List[str]):
        """Set task dependencies"""
        self.depends_on_task_ids = json.dumps(task_ids) if task_ids else None
    
    def get_depends_on(self) -> List[str]:
        """Get task dependencies"""
        return json.loads(self.depends_on_task_ids) if self.depends_on_task_ids else []
    
    def is_ready_to_run(self) -> bool:
        """Check if task is ready to run (dependencies completed)"""
        if self.status != TaskStatus.PENDING:
            return False
        
        if self.scheduled_at and self.scheduled_at > datetime.utcnow():
            return False
            
        return True
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return (self.status == TaskStatus.FAILED and 
                self.retry_count < self.max_retries)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "task_type": self.task_type,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "input_data": self.get_input_data(),
            "result_data": self.get_result_data(),
            "error_message": self.error_message,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by_user_id": self.created_by_user_id,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "parent_task_id": self.parent_task_id,
            "depends_on_task_ids": self.get_depends_on()
        }


class CreateTaskRequest(SQLModel):
    """Request model for creating tasks"""
    task_type: TaskType
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    input_data: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    timeout_seconds: Optional[int] = 300
    scheduled_at: Optional[datetime] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    depends_on_task_ids: Optional[List[str]] = None


class UpdateTaskRequest(SQLModel):
    """Request model for updating tasks"""
    status: Optional[TaskStatus] = None
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskFilterRequest(SQLModel):
    """Request model for filtering tasks"""
    status: Optional[List[TaskStatus]] = None
    task_type: Optional[List[TaskType]] = None
    priority: Optional[List[TaskPriority]] = None
    created_by_user_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    limit: int = Field(default=50, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="created_at")
    order_desc: bool = Field(default=True)