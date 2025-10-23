"""
Rate Limit Repository

Repository for rate limiting database operations.
Handles supplier API rate limit tracking and enforcement.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, func, and_, or_, delete

from MakerMatrix.models.rate_limiting_models import (
    SupplierUsageTrackingModel,
    SupplierRateLimitModel,
    SupplierUsageSummaryModel,
)
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RateLimitRepository(BaseRepository[SupplierRateLimitModel]):
    """
    Repository for rate limiting database operations.

    Handles all database operations for rate limiting,
    usage tracking, and enforcement.
    """

    def __init__(self):
        super().__init__(SupplierRateLimitModel)

    def initialize_default_limits(self, session: Session, default_limits: Dict[str, Dict[str, int]]):
        """
        Initialize default rate limits for known suppliers.

        Args:
            session: Database session
            default_limits: Dictionary of supplier limits
        """
        for supplier_name, limits in default_limits.items():
            existing = session.exec(
                select(SupplierRateLimitModel).where(SupplierRateLimitModel.supplier_name == supplier_name)
            ).first()

            if not existing:
                rate_limit = SupplierRateLimitModel(
                    supplier_name=supplier_name,
                    requests_per_minute=limits["per_minute"],
                    requests_per_hour=limits["per_hour"],
                    requests_per_day=limits["per_day"],
                    enabled=True,
                )
                session.add(rate_limit)
                logger.info(f"Created default rate limits for {supplier_name}")

        session.commit()

    def get_rate_limit_config(self, session: Session, supplier_name: str) -> Optional[SupplierRateLimitModel]:
        """
        Get rate limit configuration for a supplier.

        Args:
            session: Database session
            supplier_name: Supplier name

        Returns:
            Rate limit configuration or None if not found
        """
        return session.exec(
            select(SupplierRateLimitModel).where(SupplierRateLimitModel.supplier_name == supplier_name)
        ).first()

    def get_usage_counts(
        self, session: Session, supplier_name: str, time_windows: List[Tuple[datetime, str]]
    ) -> Dict[str, int]:
        """
        Get usage counts for different time windows.

        Args:
            session: Database session
            supplier_name: Supplier name
            time_windows: List of (start_time, window_type) tuples

        Returns:
            Dictionary mapping window types to usage counts
        """
        usage_counts = {}

        for start_time, window_type in time_windows:
            count = session.exec(
                select(func.count(SupplierUsageTrackingModel.id)).where(
                    and_(
                        SupplierUsageTrackingModel.supplier_name == supplier_name,
                        SupplierUsageTrackingModel.request_timestamp >= start_time,
                    )
                )
            ).first()
            usage_counts[window_type] = count or 0

        return usage_counts

    def record_request(
        self,
        session: Session,
        supplier_name: str,
        endpoint_type: str = "general",
        success: bool = True,
        response_time_ms: Optional[int] = None,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> SupplierUsageTrackingModel:
        """
        Record a request for rate limiting tracking.

        Args:
            session: Database session
            supplier_name: Supplier name
            endpoint_type: Type of endpoint called
            response_time: Request response time in seconds
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds (alternative to response_time)
            error_message: Error message if request failed
            request_metadata: Additional request metadata

        Returns:
            Created usage tracking record
        """
        # Convert response_time (seconds) to milliseconds if provided
        final_response_time_ms = response_time_ms
        if response_time is not None and final_response_time_ms is None:
            final_response_time_ms = int(response_time * 1000)

        usage_record = SupplierUsageTrackingModel(
            supplier_name=supplier_name,
            endpoint_type=endpoint_type,
            request_timestamp=datetime.now(timezone.utc),
            response_time_ms=final_response_time_ms,
            success=success,
            error_message=error_message,
            request_metadata=request_metadata,
        )

        session.add(usage_record)
        session.commit()
        session.refresh(usage_record)

        return usage_record

    def get_usage_summary(
        self, session: Session, supplier_name: str, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get usage summary for a supplier within a time range.

        Args:
            session: Database session
            supplier_name: Supplier name
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary containing usage summary
        """
        # Get usage records
        usage_records = session.exec(
            select(SupplierUsageTrackingModel).where(
                and_(
                    SupplierUsageTrackingModel.supplier_name == supplier_name,
                    SupplierUsageTrackingModel.request_timestamp >= start_time,
                    SupplierUsageTrackingModel.request_timestamp <= end_time,
                )
            )
        ).all()

        # Calculate summary statistics
        total_requests = len(usage_records)
        successful_requests = sum(1 for r in usage_records if r.success)
        failed_requests = total_requests - successful_requests

        response_times = [r.response_time_ms for r in usage_records if r.response_time_ms is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None

        # Group by endpoint type
        endpoint_counts = {}
        for record in usage_records:
            endpoint_type = record.endpoint_type or "general"
            endpoint_counts[endpoint_type] = endpoint_counts.get(endpoint_type, 0) + 1

        return {
            "supplier_name": supplier_name,
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "avg_response_time": avg_response_time,
            "endpoint_breakdown": endpoint_counts,
        }

    def cleanup_old_tracking_data(self, session: Session, days_to_keep: int = 30) -> int:
        """
        Clean up old tracking data to prevent database bloat.

        Args:
            session: Database session
            days_to_keep: Number of days to keep tracking data

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Delete old tracking records
        delete_result = session.exec(
            delete(SupplierUsageTrackingModel).where(SupplierUsageTrackingModel.request_timestamp < cutoff_date)
        )

        session.commit()
        deleted_count = delete_result.rowcount

        logger.info(f"Cleaned up {deleted_count} old rate limit tracking records")
        return deleted_count

    def get_all_supplier_limits(self, session: Session) -> List[SupplierRateLimitModel]:
        """
        Get all supplier rate limit configurations.

        Args:
            session: Database session

        Returns:
            List of all supplier rate limit configurations
        """
        return list(session.exec(select(SupplierRateLimitModel)).all())

    def update_supplier_limits(
        self, session: Session, supplier_name: str, limits: Dict[str, int]
    ) -> Optional[SupplierRateLimitModel]:
        """
        Update rate limits for a supplier.

        Args:
            session: Database session
            supplier_name: Supplier name
            limits: Dictionary of new limits

        Returns:
            Updated rate limit configuration or None if not found
        """
        rate_limit = self.get_rate_limit_config(session, supplier_name)
        if not rate_limit:
            return None

        # Update limits
        if "per_minute" in limits:
            rate_limit.requests_per_minute = limits["per_minute"]
        if "per_hour" in limits:
            rate_limit.requests_per_hour = limits["per_hour"]
        if "per_day" in limits:
            rate_limit.requests_per_day = limits["per_day"]
        if "enabled" in limits:
            rate_limit.enabled = limits["enabled"]

        session.add(rate_limit)
        session.commit()
        session.refresh(rate_limit)

        return rate_limit
