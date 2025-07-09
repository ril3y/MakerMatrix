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
from MakerMatrix.repositories.rate_limit_repository import RateLimitRepository
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    def __init__(self, supplier_name: str, limit_type: str, retry_after: int):
        self.supplier_name = supplier_name
        self.limit_type = limit_type
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {supplier_name} ({limit_type}). Retry after {retry_after} seconds.")


class RateLimitService(BaseService):
    """Service for managing supplier API rate limits"""
    
    def __init__(self, engine, websocket_manager=None):
        super().__init__()
        self.engine = engine
        self.websocket_manager = websocket_manager
        self.rate_limit_repo = RateLimitRepository()
        self._default_limits = {
            "mouser": {"per_minute": 30, "per_hour": 1000, "per_day": 1000},
            "lcsc": {"per_minute": 60, "per_hour": 3600, "per_day": 10000},
            "digikey": {"per_minute": 100, "per_hour": 6000, "per_day": 10000},
            "mcmaster-carr": {"per_minute": 24, "per_hour": 1000, "per_day": 5000},  # Conservative limits for both API and scraper
            "bolt-depot": {"per_minute": 20, "per_hour": 800, "per_day": 2000}  # Conservative for web scraping
        }
    
    async def initialize_default_limits(self):
        """Initialize default rate limits for known suppliers"""
        with self.get_session() as session:
            self.rate_limit_repo.initialize_default_limits(session, self._default_limits)
    
    async def check_rate_limit(self, supplier_name: str, endpoint_type: str = "general") -> Dict[str, Any]:
        """
        Check if supplier has capacity for new requests
        
        Returns:
            Dict with rate limit status and next available slot
        """
        supplier_name = supplier_name.upper()
        
        with self.get_session() as session:
            # Get rate limit configuration
            rate_limit = self.rate_limit_repo.get_rate_limit_config(session, supplier_name)
            
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
        
        with self.get_session() as session:
            # Convert response_time_ms to seconds for repository
            response_time_seconds = response_time_ms / 1000.0 if response_time_ms else None
            
            # Use repository to record the request
            usage_record = self.rate_limit_repo.record_request(
                session=session,
                supplier_name=supplier_name,
                endpoint_type=endpoint_type,
                response_time=response_time_seconds,
                success=success,
                response_time_ms=response_time_ms,
                error_message=error_message,
                request_metadata=request_metadata
            )
            
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
        
        with self.get_session() as session:
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
            
            # Use repository to get usage summary
            usage_summary = self.rate_limit_repo.get_usage_summary(
                session, supplier_name, start_time, now
            )
            
            # Convert to expected format and add time period info
            return {
                "supplier_name": supplier_name,
                "time_period": time_period,
                "start_time": start_time.isoformat(),
                "end_time": now.isoformat(),
                "total_requests": usage_summary["total_requests"],
                "successful_requests": usage_summary["successful_requests"],
                "failed_requests": usage_summary["failed_requests"],
                "success_rate": usage_summary["success_rate"] * 100,  # Convert to percentage
                "avg_response_time_ms": usage_summary["avg_response_time"] * 1000 if usage_summary["avg_response_time"] else None,
                "endpoint_breakdown": usage_summary["endpoint_breakdown"]
            }
    
    async def cleanup_old_tracking_data(self, keep_days: int = 30):
        """Clean up old tracking data to prevent database bloat"""
        with self.get_session() as session:
            deleted_count = self.rate_limit_repo.cleanup_old_tracking_data(session, keep_days)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old usage tracking records")
    
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
        
        # Use repository to get usage counts
        time_windows = [
            (minute_ago, "per_minute"),
            (hour_ago, "per_hour"),
            (day_ago, "per_day")
        ]
        
        return self.rate_limit_repo.get_usage_counts(session, supplier_name, time_windows)
    
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
        with self.get_session() as session:
            suppliers = self.rate_limit_repo.get_all_supplier_limits(session)
            
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