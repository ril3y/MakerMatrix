"""
Rate Limiting and Usage Tracking Models

Models for tracking supplier API usage and enforcing rate limits.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, JSON, Column
import uuid


class SupplierUsageTrackingModel(SQLModel, table=True):
    """Track individual API requests to suppliers for rate limiting"""

    __tablename__ = "supplier_usage_tracking"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    supplier_name: str = Field(max_length=100, nullable=False, index=True)
    request_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    endpoint_type: str = Field(max_length=50, nullable=False)  # 'search', 'details', 'pricing', etc.
    success: bool = Field(default=True, nullable=False)
    response_time_ms: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=500)
    request_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class SupplierRateLimitModel(SQLModel, table=True):
    """Configuration for supplier rate limits"""

    __tablename__ = "supplier_rate_limits"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    supplier_name: str = Field(max_length=100, nullable=False, unique=True)
    requests_per_minute: int = Field(default=30, nullable=False)
    requests_per_hour: int = Field(default=1000, nullable=False)
    requests_per_day: int = Field(default=1000, nullable=False)
    enabled: bool = Field(default=True, nullable=False)

    # Burst allowance settings
    burst_allowance: int = Field(default=5, nullable=False)  # Allow small bursts above limit
    burst_window_seconds: int = Field(default=60, nullable=False)  # Window for burst detection

    # Custom settings per supplier
    custom_settings: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "supplier_name": self.supplier_name,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_day": self.requests_per_day,
            "enabled": self.enabled,
            "burst_allowance": self.burst_allowance,
            "burst_window_seconds": self.burst_window_seconds,
            "custom_settings": self.custom_settings,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SupplierUsageSummaryModel(SQLModel, table=True):
    """Pre-computed usage summaries for faster queries"""

    __tablename__ = "supplier_usage_summary"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    supplier_name: str = Field(max_length=100, nullable=False, index=True)
    summary_date: datetime = Field(nullable=False, index=True)  # Date this summary covers
    summary_type: str = Field(max_length=20, nullable=False)  # 'hourly', 'daily', 'monthly'

    total_requests: int = Field(default=0, nullable=False)
    successful_requests: int = Field(default=0, nullable=False)
    failed_requests: int = Field(default=0, nullable=False)
    avg_response_time_ms: Optional[float] = Field(default=None)

    # Breakdown by endpoint type
    endpoint_breakdown: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "supplier_name": self.supplier_name,
            "summary_date": self.summary_date.isoformat(),
            "summary_type": self.summary_type,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "avg_response_time_ms": self.avg_response_time_ms,
            "endpoint_breakdown": self.endpoint_breakdown,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "created_at": self.created_at.isoformat(),
        }
