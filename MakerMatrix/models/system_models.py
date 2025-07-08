"""
System Models Module

Contains system-level models for activity logging, printer management, and other
system functionality extracted from models.py.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON
from pydantic import ConfigDict


class ActivityLogModel(SQLModel, table=True):
    """
    Model for tracking user activities and system events.
    
    Provides comprehensive audit trail for all system operations
    including part management, printing, and configuration changes.
    """
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # What happened
    action: str = Field(index=True)  # "created", "updated", "deleted", "printed", etc.
    entity_type: str = Field(index=True)  # "part", "printer", "label", "location", etc.
    entity_id: Optional[str] = Field(index=True)  # ID of the entity acted upon
    entity_name: Optional[str] = None  # Human-readable name (part name, printer name, etc.)
    
    # Who did it
    user_id: Optional[str] = Field(foreign_key="usermodel.id", index=True)
    username: Optional[str] = None  # Cached for performance
    
    # When and details
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump()
        if self.timestamp:
            base_dict["timestamp"] = self.timestamp.isoformat()
        return base_dict


class PrinterModel(SQLModel, table=True):
    """
    Model for printer configuration and management.
    
    Stores printer settings, connection details, and status information
    for label printing functionality.
    """
    
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    printer_id: str = Field(unique=True, index=True)  # The internal printer ID
    name: str = Field(index=True)
    driver_type: str  # e.g., "brother_ql", "mock"
    model: str  # e.g., "QL-800", "QL-820NWB"
    backend: str  # e.g., "network", "usb", "serial"
    identifier: str  # e.g., "tcp://192.168.1.71", "/dev/usb/lp0"
    dpi: int = Field(default=300)
    scaling_factor: float = Field(default=1.0)
    
    # Status and metadata
    is_active: bool = Field(default=True)
    last_seen: Optional[datetime] = None
    
    # Configuration JSON for driver-specific settings
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization method"""
        base_dict = self.model_dump()
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            base_dict["updated_at"] = self.updated_at.isoformat()
        if self.last_seen:
            base_dict["last_seen"] = self.last_seen.isoformat()
        return base_dict