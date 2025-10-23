"""
Backup Configuration Models

Models for managing backup schedules, retention policies, and backup metadata.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import uuid


class BackupConfigModel(SQLModel, table=True):
    """
    Configuration for automated backup system.

    Stores scheduling, retention, and encryption settings.
    """

    __tablename__ = "backup_config"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Scheduling configuration
    schedule_enabled: bool = Field(default=False, description="Whether scheduled backups are enabled")
    schedule_type: str = Field(default="nightly", description="Schedule type: 'nightly', 'weekly', or 'custom'")
    schedule_cron: Optional[str] = Field(default=None, description="Cron expression for custom schedules")

    # Retention policy
    retention_count: int = Field(default=7, description="Number of backups to retain")

    # Backup timestamps
    last_backup_at: Optional[datetime] = Field(default=None, description="Timestamp of last successful backup")
    next_backup_at: Optional[datetime] = Field(default=None, description="Timestamp of next scheduled backup")

    # Encryption settings
    encryption_required: bool = Field(default=True, description="Whether backups must be encrypted")
    encryption_password: Optional[str] = Field(
        default=None, description="Password for encrypting scheduled backups (stored encrypted)"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "schedule_enabled": True,
                "schedule_type": "nightly",
                "schedule_cron": "0 2 * * *",
                "retention_count": 7,
                "encryption_required": True,
            }
        }


class BackupConfigCreate(SQLModel):
    """Schema for creating backup configuration"""

    schedule_enabled: bool = False
    schedule_type: str = "nightly"
    schedule_cron: Optional[str] = None
    retention_count: int = 7
    encryption_required: bool = True


class BackupConfigUpdate(SQLModel):
    """Schema for updating backup configuration"""

    schedule_enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    retention_count: Optional[int] = None
    encryption_required: Optional[bool] = None
    encryption_password: Optional[str] = None
    last_backup_at: Optional[datetime] = None
    next_backup_at: Optional[datetime] = None
