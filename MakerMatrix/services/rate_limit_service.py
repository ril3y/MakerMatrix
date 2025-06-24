"""
Rate Limiting Service

Manages supplier API rate limits, tracks usage, and enforces limits.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, func, and_, or_, delete
from contextlib import asynccontextmanager

from MakerMatrix.models.rate_limiting_models import (
    SupplierUsageTrackingModel,
    SupplierRateLimitModel,
    SupplierUsageSummaryModel
)
from MakerMatrix.schemas.websocket_schemas import (
    create_rate_limit_update_message,
    WebSocketEventType
)

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, supplier_name: str, limit_type: str, retry_after: int):
        self.supplier_name = supplier_name
        self.limit_type = limit_type
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {supplier_name} ({limit_type}). Retry after {retry_after} seconds.")


class RateLimitService:
    """Service for managing supplier API rate limits"""
    
    def __init__(self, engine, websocket_manager=None):
        self.engine = engine
        self.websocket_manager = websocket_manager
        self._default_limits = {
            "mouser": {"per_minute": 30, "per_hour": 1000, "per_day": 1000},
            "lcsc": {"per_minute": 60, "per_hour": 3600, "per_day": 10000},
            "digikey": {"per_minute": 100, "per_hour": 6000, "per_day": 10000},
            "mcmaster-carr": {"per_minute": 24, "per_hour": 1000, "per_day": 5000},  # Conservative limits for both API and scraper
            "bolt-depot": {"per_minute": 20, "per_hour": 800, "per_day": 2000}  # Conservative for web scraping
        }
    
    async def initialize_default_limits(self):
        """Initialize default rate limits for known suppliers"""
        with Session(self.engine) as session:
            for supplier_name, limits in self._default_limits.items():
                existing = session.exec(
                    select(SupplierRateLimitModel).where(
                        SupplierRateLimitModel.supplier_name == supplier_name
                    )
                ).first()
                
                if not existing:
                    rate_limit = SupplierRateLimitModel(
                        supplier_name=supplier_name,
                        requests_per_minute=limits["per_minute"],
                        requests_per_hour=limits["per_hour"],
                        requests_per_day=limits["per_day"],
                        enabled=True
                    )
                    session.add(rate_limit)
                    logger.info(f"Created default rate limits for {supplier_name}")
            
            session.commit()
    
    async def check_rate_limit(self, supplier_name: str, endpoint_type: str = "general") -> Dict[str, Any]:
        """
        Check if supplier has capacity for new requests
        
        Returns:
            Dict with rate limit status and next available slot
        """
        supplier_name = supplier_name.upper()
        
        with Session(self.engine) as session:
            # Get rate limit configuration
            rate_limit = session.exec(
                select(SupplierRateLimitModel).where(
                    SupplierRateLimitModel.supplier_name == supplier_name
                )
            ).first()
            
            if not rate_limit or not rate_limit.enabled:
                return {
                    "allowed": True,
                    "supplier_name": supplier_name,
                    "message": "No rate limits configured or disabled"
                }
            
            now = datetime.now(timezone.utc)
            
            # Check each time window
            usage_stats = await self._get_current_usage(session, supplier_name, now)
            
            # Check for violations
            violations = []
            retry_after = 0
            
            if usage_stats["per_minute"] >= rate_limit.requests_per_minute:
                violations.append("per_minute")
                retry_after = max(retry_after, 60)
            
            if usage_stats["per_hour"] >= rate_limit.requests_per_hour:
                violations.append("per_hour")
                retry_after = max(retry_after, 3600)
            
            if usage_stats["per_day"] >= rate_limit.requests_per_day:
                violations.append("per_day")
                retry_after = max(retry_after, 86400)
            
            if violations:
                return {
                    "allowed": False,
                    "supplier_name": supplier_name,
                    "violations": violations,
                    "retry_after_seconds": retry_after,
                    "current_usage": usage_stats,
                    "limits": {
                        "per_minute": rate_limit.requests_per_minute,
                        "per_hour": rate_limit.requests_per_hour,
                        "per_day": rate_limit.requests_per_day
                    }
                }
            
            # Calculate next reset times
            next_reset = {
                "per_minute": now.replace(second=0, microsecond=0) + timedelta(minutes=1),
                "per_hour": now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
                "per_day": now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            }
            
            return {
                "allowed": True,
                "supplier_name": supplier_name,
                "current_usage": usage_stats,
                "limits": {
                    "per_minute": rate_limit.requests_per_minute,
                    "per_hour": rate_limit.requests_per_hour,
                    "per_day": rate_limit.requests_per_day
                },
                "next_reset": next_reset,
                "usage_percentage": {
                    "per_minute": (usage_stats["per_minute"] / rate_limit.requests_per_minute) * 100,
                    "per_hour": (usage_stats["per_hour"] / rate_limit.requests_per_hour) * 100,
                    "per_day": (usage_stats["per_day"] / rate_limit.requests_per_day) * 100
                }
            }
    
    async def record_request(
        self,
        supplier_name: str,
        endpoint_type: str,
        success: bool,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a supplier API request for tracking"""
        supplier_name = supplier_name.upper()
        
        with Session(self.engine) as session:
            usage_record = SupplierUsageTrackingModel(
                supplier_name=supplier_name,
                endpoint_type=endpoint_type,
                success=success,
                response_time_ms=response_time_ms,
                error_message=error_message,
                request_metadata=request_metadata
            )
            session.add(usage_record)
            session.commit()
            
            logger.debug(f"Recorded {endpoint_type} request for {supplier_name}: success={success}")
        
        # Broadcast rate limit update via WebSocket
        if self.websocket_manager:
            try:
                rate_status = await self.check_rate_limit(supplier_name, endpoint_type)
                if rate_status.get("allowed") and "current_usage" in rate_status:
                    message = create_rate_limit_update_message(
                        supplier_name=supplier_name,
                        current_usage=rate_status["current_usage"],
                        limits=rate_status["limits"],
                        next_reset=rate_status.get("next_reset", {}),
                        queue_size=0  # TODO: Add queue size tracking
                    )
                    await self.websocket_manager.broadcast_to_all(message.model_dump())
            except Exception as e:
                logger.warning(f"Failed to broadcast rate limit update: {e}")
    
    async def get_usage_stats(
        self,
        supplier_name: str,
        time_period: str = "24h"
    ) -> Dict[str, Any]:
        """Get detailed usage statistics for a supplier"""
        supplier_name = supplier_name.upper()
        
        with Session(self.engine) as session:
            now = datetime.now(timezone.utc)
            
            # Determine time window
            if time_period == "1h":
                start_time = now - timedelta(hours=1)
            elif time_period == "24h":
                start_time = now - timedelta(days=1)
            elif time_period == "7d":
                start_time = now - timedelta(days=7)
            elif time_period == "30d":
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(days=1)
            
            # Get usage records
            usage_records = session.exec(
                select(SupplierUsageTrackingModel).where(
                    and_(
                        SupplierUsageTrackingModel.supplier_name == supplier_name,
                        SupplierUsageTrackingModel.request_timestamp >= start_time
                    )
                ).order_by(SupplierUsageTrackingModel.request_timestamp.desc())
            ).all()
            
            # Calculate statistics
            total_requests = len(usage_records)
            successful_requests = len([r for r in usage_records if r.success])
            failed_requests = total_requests - successful_requests
            
            # Response time statistics
            response_times = [r.response_time_ms for r in usage_records if r.response_time_ms is not None]
            avg_response_time = sum(response_times) / len(response_times) if response_times else None
            
            # Endpoint breakdown
            endpoint_breakdown = {}
            for record in usage_records:
                endpoint_breakdown[record.endpoint_type] = endpoint_breakdown.get(record.endpoint_type, 0) + 1
            
            return {
                "supplier_name": supplier_name,
                "time_period": time_period,
                "start_time": start_time.isoformat(),
                "end_time": now.isoformat(),
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "endpoint_breakdown": endpoint_breakdown
            }
    
    async def cleanup_old_tracking_data(self, keep_days: int = 30):
        """Clean up old tracking data to prevent database bloat"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=keep_days)
        
        with Session(self.engine) as session:
            # Count records to be deleted
            count = session.exec(
                select(func.count(SupplierUsageTrackingModel.id)).where(
                    SupplierUsageTrackingModel.request_timestamp < cutoff_date
                )
            ).first()
            
            if count and count > 0:
                # Delete old records
                session.exec(
                    delete(SupplierUsageTrackingModel).where(
                        SupplierUsageTrackingModel.request_timestamp < cutoff_date
                    )
                )
                session.commit()
                
                logger.info(f"Cleaned up {count} old usage tracking records")
    
    async def _get_current_usage(
        self,
        session: Session,
        supplier_name: str,
        now: datetime
    ) -> Dict[str, int]:
        """Get current usage counts for different time windows"""
        
        # Calculate time windows
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count requests in each window
        per_minute = session.exec(
            select(func.count(SupplierUsageTrackingModel.id)).where(
                and_(
                    SupplierUsageTrackingModel.supplier_name == supplier_name,
                    SupplierUsageTrackingModel.request_timestamp >= minute_ago
                )
            )
        ).first() or 0
        
        per_hour = session.exec(
            select(func.count(SupplierUsageTrackingModel.id)).where(
                and_(
                    SupplierUsageTrackingModel.supplier_name == supplier_name,
                    SupplierUsageTrackingModel.request_timestamp >= hour_ago
                )
            )
        ).first() or 0
        
        per_day = session.exec(
            select(func.count(SupplierUsageTrackingModel.id)).where(
                and_(
                    SupplierUsageTrackingModel.supplier_name == supplier_name,
                    SupplierUsageTrackingModel.request_timestamp >= day_ago
                )
            )
        ).first() or 0
        
        return {
            "per_minute": per_minute,
            "per_hour": per_hour,
            "per_day": per_day
        }
    
    @asynccontextmanager
    async def rate_limited_request(self, supplier_name: str, endpoint_type: str):
        """
        Context manager for rate-limited requests
        
        Usage:
            async with rate_limit_service.rate_limited_request("mouser", "search") as ctx:
                if ctx.allowed:
                    result = await make_api_call()
                    ctx.record_success(response_time_ms=123)
                else:
                    raise RateLimitExceeded(...)
        """
        
        class RequestContext:
            def __init__(self, service, supplier_name, endpoint_type):
                self.service = service
                self.supplier_name = supplier_name
                self.endpoint_type = endpoint_type
                self.allowed = False
                self.rate_status = None
                self.start_time = None
            
            async def record_success(self, response_time_ms: Optional[int] = None):
                await self.service.record_request(
                    self.supplier_name,
                    self.endpoint_type,
                    True,
                    response_time_ms
                )
            
            async def record_failure(self, error_message: str):
                await self.service.record_request(
                    self.supplier_name,
                    self.endpoint_type,
                    False,
                    error_message=error_message
                )
        
        ctx = RequestContext(self, supplier_name, endpoint_type)
        ctx.start_time = datetime.now(timezone.utc)
        
        # Check rate limit
        ctx.rate_status = await self.check_rate_limit(supplier_name, endpoint_type)
        ctx.allowed = ctx.rate_status.get("allowed", False)
        
        try:
            yield ctx
        except Exception as e:
            # Record the failure
            if ctx.start_time:
                response_time = int((datetime.now(timezone.utc) - ctx.start_time).total_seconds() * 1000)
                await ctx.record_failure(str(e))
            raise
    
    async def get_all_supplier_usage(self) -> List[Dict[str, Any]]:
        """Get usage statistics for all suppliers"""
        with Session(self.engine) as session:
            suppliers = session.exec(select(SupplierRateLimitModel)).all()
            
            usage_data = []
            for supplier in suppliers:
                stats = await self.get_usage_stats(supplier.supplier_name, "24h")
                rate_status = await self.check_rate_limit(supplier.supplier_name)
                
                usage_data.append({
                    "supplier_name": supplier.supplier_name,
                    "enabled": supplier.enabled,
                    "limits": {
                        "per_minute": supplier.requests_per_minute,
                        "per_hour": supplier.requests_per_hour,
                        "per_day": supplier.requests_per_day
                    },
                    "current_usage": rate_status.get("current_usage", {}),
                    "usage_percentage": rate_status.get("usage_percentage", {}),
                    "stats_24h": stats
                })
            
            return usage_data