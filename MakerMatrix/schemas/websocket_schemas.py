"""
Unified WebSocket Message Schemas

Standardized message formats for real-time communication across the application.
"""

from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class WebSocketEventType(str, Enum):
    """Standard WebSocket event types"""
    # System events
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    CONNECTION_STATUS = "connection_status"
    
    # Import/Export events
    IMPORT_STARTED = "import_started"
    IMPORT_PROGRESS = "import_progress"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"
    
    # Enrichment events
    ENRICHMENT_STARTED = "enrichment_started"
    ENRICHMENT_PROGRESS = "enrichment_progress"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    ENRICHMENT_FAILED = "enrichment_failed"
    
    # Rate limiting events
    RATE_LIMIT_UPDATE = "rate_limit_update"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Task events
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # Supplier events
    SUPPLIER_STATUS_CHANGED = "supplier_status_changed"
    SUPPLIER_ERROR = "supplier_error"
    
    # General notifications
    NOTIFICATION = "notification"
    TOAST = "toast"


class WebSocketMessage(BaseModel):
    """Base WebSocket message format"""
    type: WebSocketEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(default=None, description="ID to correlate request/response")
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class ImportProgressData(BaseModel):
    """Data for import progress events"""
    task_id: str
    filename: str
    parser_type: str
    progress_percentage: int = Field(ge=0, le=100)
    current_step: str
    parts_processed: int = Field(ge=0)
    total_parts: int = Field(ge=0)
    estimated_completion: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)


class EnrichmentProgressData(BaseModel):
    """Data for enrichment progress events"""
    task_id: Optional[str] = None
    supplier_name: str
    part_id: str
    part_name: str
    capabilities_completed: List[str] = Field(default_factory=list)
    capabilities_total: List[str] = Field(default_factory=list)
    progress_percentage: int = Field(ge=0, le=100)
    estimated_completion: Optional[datetime] = None
    current_capability: Optional[str] = None


class RateLimitData(BaseModel):
    """Data for rate limit events"""
    supplier_name: str
    current_usage: Dict[str, int] = Field(description="Current usage counts")
    limits: Dict[str, int] = Field(description="Rate limit configuration")
    usage_percentage: Dict[str, float] = Field(description="Usage as percentage of limits")
    next_reset: Dict[str, datetime] = Field(description="When counters reset")
    queue_size: Optional[int] = Field(default=None, description="Pending requests in queue")


class TaskProgressData(BaseModel):
    """Data for task progress events"""
    task_id: str
    task_type: str
    task_name: str
    status: str
    progress_percentage: int = Field(ge=0, le=100)
    current_step: str
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    result_summary: Optional[Dict[str, Any]] = None


class NotificationData(BaseModel):
    """Data for notification events"""
    level: str = Field(description="info, warning, error, success")
    title: str
    message: str
    duration: Optional[int] = Field(default=5000, description="Duration in milliseconds")
    actions: Optional[List[Dict[str, str]]] = Field(default=None, description="Available actions")


class ToastData(BaseModel):
    """Data for toast notification events"""
    level: str = Field(description="info, warning, error, success")
    message: str
    duration: Optional[int] = Field(default=3000, description="Duration in milliseconds")
    position: str = Field(default="top-right", description="Toast position")


class ConnectionStatusData(BaseModel):
    """Data for connection status events"""
    connected: bool
    connection_id: str
    user_id: Optional[str] = None
    subscriptions: List[str] = Field(default_factory=list, description="Active subscriptions")
    server_time: datetime = Field(default_factory=datetime.utcnow)


# Helper functions for creating common messages

def create_import_progress_message(
    task_id: str,
    filename: str,
    parser_type: str,
    progress: int,
    current_step: str,
    parts_processed: int,
    total_parts: int,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create an import progress message"""
    return WebSocketMessage(
        type=WebSocketEventType.IMPORT_PROGRESS,
        correlation_id=correlation_id,
        data=ImportProgressData(
            task_id=task_id,
            filename=filename,
            parser_type=parser_type,
            progress_percentage=progress,
            current_step=current_step,
            parts_processed=parts_processed,
            total_parts=total_parts
        ).dict()
    )


def create_enrichment_progress_message(
    supplier_name: str,
    part_id: str,
    part_name: str,
    capabilities_completed: List[str],
    capabilities_total: List[str],
    current_capability: Optional[str] = None,
    task_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create an enrichment progress message"""
    progress = int((len(capabilities_completed) / len(capabilities_total)) * 100) if capabilities_total else 0
    
    return WebSocketMessage(
        type=WebSocketEventType.ENRICHMENT_PROGRESS,
        correlation_id=correlation_id,
        data=EnrichmentProgressData(
            task_id=task_id,
            supplier_name=supplier_name,
            part_id=part_id,
            part_name=part_name,
            capabilities_completed=capabilities_completed,
            capabilities_total=capabilities_total,
            progress_percentage=progress,
            current_capability=current_capability
        ).dict()
    )


def create_rate_limit_update_message(
    supplier_name: str,
    current_usage: Dict[str, int],
    limits: Dict[str, int],
    next_reset: Dict[str, datetime],
    queue_size: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a rate limit update message"""
    usage_percentage = {
        period: (current_usage.get(period, 0) / limits.get(period, 1)) * 100
        for period in limits.keys()
    }
    
    return WebSocketMessage(
        type=WebSocketEventType.RATE_LIMIT_UPDATE,
        correlation_id=correlation_id,
        data=RateLimitData(
            supplier_name=supplier_name,
            current_usage=current_usage,
            limits=limits,
            usage_percentage=usage_percentage,
            next_reset=next_reset,
            queue_size=queue_size
        ).dict()
    )


def create_notification_message(
    level: str,
    title: str,
    message: str,
    duration: Optional[int] = None,
    actions: Optional[List[Dict[str, str]]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a notification message"""
    return WebSocketMessage(
        type=WebSocketEventType.NOTIFICATION,
        correlation_id=correlation_id,
        data=NotificationData(
            level=level,
            title=title,
            message=message,
            duration=duration,
            actions=actions
        ).dict()
    )


def create_toast_message(
    level: str,
    message: str,
    duration: Optional[int] = None,
    position: str = "top-right",
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a toast message"""
    return WebSocketMessage(
        type=WebSocketEventType.TOAST,
        correlation_id=correlation_id,
        data=ToastData(
            level=level,
            message=message,
            duration=duration,
            position=position
        ).dict()
    )