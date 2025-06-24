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
    
    # Generic entity events (covers all entity types: parts, locations, categories, etc.)
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated" 
    ENTITY_DELETED = "entity_deleted"
    
    # Special action events
    ENTITY_PRINTED = "entity_printed"      # For labels, documents, etc.
    ENTITY_IMPORTED = "entity_imported"    # For CSV imports, etc.
    ENTITY_EXPORTED = "entity_exported"    # For exports
    ENTITY_TESTED = "entity_tested"        # For printer tests, etc.
    
    # User session events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"


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


class EntityEventData(BaseModel):
    """Generic entity event data for all CRUD operations"""
    # Entity identification
    entity_type: str = Field(description="Type of entity (part, location, category, printer, user, etc.)")
    entity_id: str = Field(description="Unique identifier of the entity")
    entity_name: str = Field(description="Human-readable name of the entity")
    
    # Action information
    action: str = Field(description="Action performed (created, updated, deleted, printed, etc.)")
    
    # User and timing
    user_id: Optional[str] = Field(default=None, description="ID of user who performed the action")
    username: Optional[str] = Field(default=None, description="Username of user who performed the action")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Change details (for updates)
    changes: Optional[Dict[str, Any]] = Field(default=None, description="What fields changed (before/after values)")
    
    # Additional context
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action-specific details")
    
    # Full entity data (optional, for frontend caching)
    entity_data: Optional[Dict[str, Any]] = Field(default=None, description="Complete entity data after the action")


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
        ).model_dump()
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
        ).model_dump()
    )


def create_rate_limit_event(
    supplier_name: str,
    current_usage: Dict[str, int],
    limits: Dict[str, int],
    next_reset: Dict[str, datetime],
    queue_size: Optional[int] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a rate limit event message (alias for create_rate_limit_update_message)"""
    return create_rate_limit_update_message(
        supplier_name=supplier_name,
        current_usage=current_usage,
        limits=limits,
        next_reset=next_reset,
        queue_size=queue_size,
        correlation_id=correlation_id
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
        ).model_dump()
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
        ).model_dump()
    )


def create_toast_message(
    level: str,
    message: str,
    duration: Optional[int] = None,
    position: str = "top-right",
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a toast message"""
    # Build ToastData kwargs, excluding None values to use defaults
    toast_kwargs = {
        "level": level,
        "message": message,
        "position": position
    }
    if duration is not None:
        toast_kwargs["duration"] = duration
    
    return WebSocketMessage(
        type=WebSocketEventType.TOAST,
        correlation_id=correlation_id,
        data=ToastData(**toast_kwargs).model_dump()
    )


def create_entity_event_message(
    action: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
    entity_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a generic entity event message"""
    
    # Map action to event type
    event_type_map = {
        "created": WebSocketEventType.ENTITY_CREATED,
        "updated": WebSocketEventType.ENTITY_UPDATED,
        "deleted": WebSocketEventType.ENTITY_DELETED,
        "printed": WebSocketEventType.ENTITY_PRINTED,
        "imported": WebSocketEventType.ENTITY_IMPORTED,
        "exported": WebSocketEventType.ENTITY_EXPORTED,
        "tested": WebSocketEventType.ENTITY_TESTED,
        "logged_in": WebSocketEventType.USER_LOGIN,
        "logged_out": WebSocketEventType.USER_LOGOUT,
    }
    
    event_type = event_type_map.get(action, WebSocketEventType.ENTITY_UPDATED)
    
    return WebSocketMessage(
        type=event_type,
        correlation_id=correlation_id,
        data=EntityEventData(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            user_id=user_id,
            username=username,
            changes=changes,
            details=details or {},
            entity_data=entity_data
        ).model_dump()
    )


# Convenience functions for common entity operations

def create_part_created_message(
    part_id: str,
    part_name: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    part_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a part created message"""
    return create_entity_event_message(
        action="created",
        entity_type="part",
        entity_id=part_id,
        entity_name=part_name,
        user_id=user_id,
        username=username,
        entity_data=part_data,
        correlation_id=correlation_id
    )


def create_part_updated_message(
    part_id: str,
    part_name: str,
    changes: Dict[str, Any],
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    part_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a part updated message"""
    return create_entity_event_message(
        action="updated",
        entity_type="part",
        entity_id=part_id,
        entity_name=part_name,
        user_id=user_id,
        username=username,
        changes=changes,
        entity_data=part_data,
        correlation_id=correlation_id
    )


def create_part_deleted_message(
    part_id: str,
    part_name: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a part deleted message"""
    return create_entity_event_message(
        action="deleted",
        entity_type="part",
        entity_id=part_id,
        entity_name=part_name,
        user_id=user_id,
        username=username,
        correlation_id=correlation_id
    )


def create_location_created_message(
    location_id: str,
    location_name: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    location_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a location created message"""
    return create_entity_event_message(
        action="created",
        entity_type="location",
        entity_id=location_id,
        entity_name=location_name,
        user_id=user_id,
        username=username,
        entity_data=location_data,
        correlation_id=correlation_id
    )


def create_category_created_message(
    category_id: str,
    category_name: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    category_data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> WebSocketMessage:
    """Create a category created message"""
    return create_entity_event_message(
        action="created",
        entity_type="category",
        entity_id=category_id,
        entity_name=category_name,
        user_id=user_id,
        username=username,
        entity_data=category_data,
        correlation_id=correlation_id
    )