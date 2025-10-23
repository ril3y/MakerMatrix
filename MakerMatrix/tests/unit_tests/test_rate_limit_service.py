"""
Tests for Rate Limiting Service

Comprehensive tests for the RateLimitService including usage tracking,
limit enforcement, and WebSocket integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock
from sqlmodel import Session, create_engine, SQLModel, select

from MakerMatrix.models.rate_limiting_models import (
    SupplierUsageTrackingModel,
    SupplierRateLimitModel,
    SupplierUsageSummaryModel,
)
from MakerMatrix.services.rate_limit_service import RateLimitService, RateLimitExceeded


@pytest.fixture
def memory_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def rate_limit_service(memory_engine):
    """Create RateLimitService instance with mock WebSocket manager"""
    websocket_manager = Mock()
    websocket_manager.broadcast_to_all = AsyncMock()
    return RateLimitService(memory_engine, websocket_manager)


@pytest.fixture
def sample_rate_limits(memory_engine):
    """Create sample rate limit configurations"""
    with Session(memory_engine) as session:
        limits = [
            SupplierRateLimitModel(
                supplier_name="MOUSER",
                requests_per_minute=30,
                requests_per_hour=1000,
                requests_per_day=1000,
                enabled=True,
            ),
            SupplierRateLimitModel(
                supplier_name="LCSC",
                requests_per_minute=60,
                requests_per_hour=3600,
                requests_per_day=10000,
                enabled=True,
            ),
            SupplierRateLimitModel(
                supplier_name="DISABLED",
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=1000,
                enabled=False,
            ),
        ]
        for limit in limits:
            session.add(limit)
        session.commit()
        return limits


class TestRateLimitService:
    """Test RateLimitService functionality"""

    @pytest.mark.asyncio
    async def test_initialize_default_limits(self, rate_limit_service, memory_engine):
        """Test initialization of default rate limits"""
        await rate_limit_service.initialize_default_limits()

        with Session(memory_engine) as session:
            # Check that default limits were created
            mouser_limit = session.exec(
                select(SupplierRateLimitModel).where(SupplierRateLimitModel.supplier_name == "mouser")
            ).first()
            assert mouser_limit is not None
            assert mouser_limit.requests_per_minute == 30
            assert mouser_limit.requests_per_hour == 1000
            assert mouser_limit.enabled is True

            lcsc_limit = session.exec(
                select(SupplierRateLimitModel).where(SupplierRateLimitModel.supplier_name == "lcsc")
            ).first()
            assert lcsc_limit is not None
            assert lcsc_limit.requests_per_minute == 60
            assert lcsc_limit.requests_per_hour == 3600

    @pytest.mark.asyncio
    async def test_check_rate_limit_no_config(self, rate_limit_service):
        """Test rate limit check when no configuration exists"""
        result = await rate_limit_service.check_rate_limit("UNKNOWN_SUPPLIER")

        assert result["allowed"] is True
        assert "No rate limits configured" in result["message"]

    @pytest.mark.asyncio
    async def test_check_rate_limit_disabled(self, rate_limit_service, sample_rate_limits):
        """Test rate limit check for disabled supplier"""
        result = await rate_limit_service.check_rate_limit("DISABLED")

        assert result["allowed"] is True
        assert "disabled" in result["message"]

    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limit_service, sample_rate_limits):
        """Test rate limit check when within limits"""
        result = await rate_limit_service.check_rate_limit("MOUSER")

        assert result["allowed"] is True
        assert result["supplier_name"] == "MOUSER"
        assert "current_usage" in result
        assert "limits" in result
        assert "next_reset" in result
        assert "usage_percentage" in result

        # Check limits match configuration
        assert result["limits"]["per_minute"] == 30
        assert result["limits"]["per_hour"] == 1000
        assert result["limits"]["per_day"] == 1000

        # Check usage is initially zero
        assert result["current_usage"]["per_minute"] == 0
        assert result["current_usage"]["per_hour"] == 0
        assert result["current_usage"]["per_day"] == 0

    @pytest.mark.asyncio
    async def test_record_request_success(self, rate_limit_service, memory_engine):
        """Test recording successful requests"""
        await rate_limit_service.record_request(
            "MOUSER", "search", True, response_time_ms=150, request_metadata={"query": "resistor"}
        )

        with Session(memory_engine) as session:
            # Check that usage was recorded
            usage_records = session.exec(
                select(SupplierUsageTrackingModel).where(SupplierUsageTrackingModel.supplier_name == "MOUSER")
            ).all()

            assert len(usage_records) == 1
            record = usage_records[0]
            assert record.supplier_name == "MOUSER"
            assert record.endpoint_type == "search"
            assert record.success is True
            assert record.response_time_ms == 150
            assert record.request_metadata["query"] == "resistor"

    @pytest.mark.asyncio
    async def test_record_request_failure(self, rate_limit_service, memory_engine):
        """Test recording failed requests"""
        await rate_limit_service.record_request(
            "MOUSER", "details", False, response_time_ms=5000, error_message="Timeout error"
        )

        with Session(memory_engine) as session:
            usage_records = session.exec(
                select(SupplierUsageTrackingModel).where(SupplierUsageTrackingModel.supplier_name == "MOUSER")
            ).all()

            assert len(usage_records) == 1
            record = usage_records[0]
            assert record.success is False
            assert record.error_message == "Timeout error"
            assert record.response_time_ms == 5000

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limit_service, sample_rate_limits, memory_engine):
        """Test that rate limits are enforced"""
        # Create 30 requests in the last minute (at the limit)
        now = datetime.now(timezone.utc)
        with Session(memory_engine) as session:
            for i in range(30):
                usage = SupplierUsageTrackingModel(
                    supplier_name="MOUSER",
                    endpoint_type="search",
                    request_timestamp=now - timedelta(seconds=i),
                    success=True,
                )
                session.add(usage)
            session.commit()

        # Next request should be rate limited
        result = await rate_limit_service.check_rate_limit("MOUSER")

        assert result["allowed"] is False
        assert "per_minute" in result["violations"]
        assert result["retry_after_seconds"] == 60
        assert result["current_usage"]["per_minute"] == 30

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, rate_limit_service, memory_engine):
        """Test usage statistics calculation"""
        # Create test data
        now = datetime.now(timezone.utc)
        with Session(memory_engine) as session:
            # 5 successful requests
            for i in range(5):
                usage = SupplierUsageTrackingModel(
                    supplier_name="MOUSER",
                    endpoint_type="search",
                    request_timestamp=now - timedelta(hours=i),
                    success=True,
                    response_time_ms=100 + i * 10,
                )
                session.add(usage)

            # 2 failed requests
            for i in range(2):
                usage = SupplierUsageTrackingModel(
                    supplier_name="MOUSER",
                    endpoint_type="details",
                    request_timestamp=now - timedelta(hours=i),
                    success=False,
                    response_time_ms=5000,
                )
                session.add(usage)
            session.commit()

        stats = await rate_limit_service.get_usage_stats("MOUSER", "24h")

        assert stats["supplier_name"] == "MOUSER"
        assert stats["total_requests"] == 7
        assert stats["successful_requests"] == 5
        assert stats["failed_requests"] == 2
        assert abs(stats["success_rate"] - 71.43) < 0.1  # ~71.43%
        assert stats["avg_response_time_ms"] is not None
        assert "search" in stats["endpoint_breakdown"]
        assert "details" in stats["endpoint_breakdown"]

    @pytest.mark.asyncio
    async def test_cleanup_old_tracking_data(self, rate_limit_service, memory_engine):
        """Test cleanup of old tracking data"""
        # Create old and new data
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=35)  # Older than 30 days
        recent_date = now - timedelta(days=5)

        with Session(memory_engine) as session:
            # Old data (should be cleaned up)
            old_usage = SupplierUsageTrackingModel(
                supplier_name="MOUSER", endpoint_type="search", request_timestamp=old_date, success=True
            )
            session.add(old_usage)

            # Recent data (should be kept)
            recent_usage = SupplierUsageTrackingModel(
                supplier_name="MOUSER", endpoint_type="search", request_timestamp=recent_date, success=True
            )
            session.add(recent_usage)
            session.commit()

        # Cleanup with 30 day retention
        await rate_limit_service.cleanup_old_tracking_data(keep_days=30)

        with Session(memory_engine) as session:
            remaining_records = session.exec(select(SupplierUsageTrackingModel)).all()

            # Only recent data should remain
            assert len(remaining_records) == 1
            # Compare without timezone info since SQLite stores naive datetimes
            assert remaining_records[0].request_timestamp.replace(tzinfo=timezone.utc) == recent_date

    @pytest.mark.asyncio
    async def test_rate_limited_request_context_success(self, rate_limit_service, sample_rate_limits):
        """Test rate limited request context manager for successful requests"""
        async with rate_limit_service.rate_limited_request("MOUSER", "search") as ctx:
            assert ctx.allowed is True
            assert ctx.supplier_name == "MOUSER"
            assert ctx.endpoint_type == "search"

            # Simulate successful API call
            await asyncio.sleep(0.01)  # Simulate processing time
            await ctx.record_success(response_time_ms=123)

        # Verify request was recorded
        stats = await rate_limit_service.get_usage_stats("MOUSER", "1h")
        assert stats["total_requests"] == 1
        assert stats["successful_requests"] == 1

    @pytest.mark.asyncio
    async def test_rate_limited_request_context_failure(self, rate_limit_service, sample_rate_limits):
        """Test rate limited request context manager for failed requests"""
        async with rate_limit_service.rate_limited_request("MOUSER", "search") as ctx:
            assert ctx.allowed is True

            # Simulate failed API call
            await ctx.record_failure("Connection timeout")

        # Verify failure was recorded
        stats = await rate_limit_service.get_usage_stats("MOUSER", "1h")
        assert stats["total_requests"] == 1
        assert stats["failed_requests"] == 1

    @pytest.mark.asyncio
    async def test_get_all_supplier_usage(self, rate_limit_service, sample_rate_limits):
        """Test getting usage statistics for all suppliers"""
        # Add some usage data
        await rate_limit_service.record_request("MOUSER", "search", True, 150)
        await rate_limit_service.record_request("LCSC", "details", True, 200)

        usage_data = await rate_limit_service.get_all_supplier_usage()

        # Should have data for enabled suppliers
        supplier_names = [data["supplier_name"] for data in usage_data]
        assert "MOUSER" in supplier_names
        assert "LCSC" in supplier_names
        assert "DISABLED" in supplier_names

        # Check data structure
        mouser_data = next(data for data in usage_data if data["supplier_name"] == "MOUSER")
        assert "limits" in mouser_data
        assert "current_usage" in mouser_data
        assert "usage_percentage" in mouser_data
        assert "stats_24h" in mouser_data
        assert mouser_data["enabled"] is True

    @pytest.mark.asyncio
    async def test_websocket_broadcast_on_record_request(self, rate_limit_service, sample_rate_limits):
        """Test that WebSocket updates are broadcast when recording requests"""
        await rate_limit_service.record_request("MOUSER", "search", True, 150)

        # Verify WebSocket manager was called
        rate_limit_service.websocket_manager.broadcast_to_all.assert_called_once()

        # Check the message structure
        call_args = rate_limit_service.websocket_manager.broadcast_to_all.call_args[0]
        message = call_args[0]

        assert message["type"] == "rate_limit_update"
        assert message["data"]["supplier_name"] == "MOUSER"
        assert "current_usage" in message["data"]
        assert "limits" in message["data"]


class TestRateLimitModels:
    """Test rate limiting models"""

    def test_supplier_rate_limit_model_to_dict(self):
        """Test SupplierRateLimitModel to_dict method"""
        model = SupplierRateLimitModel(
            supplier_name="TEST",
            requests_per_minute=30,
            requests_per_hour=1000,
            requests_per_day=5000,
            enabled=True,
            burst_allowance=5,
            custom_settings={"test": "value"},
        )

        result = model.to_dict()

        assert result["supplier_name"] == "TEST"
        assert result["requests_per_minute"] == 30
        assert result["requests_per_hour"] == 1000
        assert result["requests_per_day"] == 5000
        assert result["enabled"] is True
        assert result["burst_allowance"] == 5
        assert result["custom_settings"]["test"] == "value"
        assert "created_at" in result
        assert "updated_at" in result

    def test_supplier_usage_summary_model_to_dict(self):
        """Test SupplierUsageSummaryModel to_dict method"""
        model = SupplierUsageSummaryModel(
            supplier_name="TEST",
            summary_date=datetime.now(timezone.utc),
            summary_type="hourly",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            avg_response_time_ms=150.5,
            endpoint_breakdown={"search": 50, "details": 45, "pricing": 5},
        )

        result = model.to_dict()

        assert result["supplier_name"] == "TEST"
        assert result["summary_type"] == "hourly"
        assert result["total_requests"] == 100
        assert result["successful_requests"] == 95
        assert result["failed_requests"] == 5
        assert result["success_rate"] == 95.0
        assert result["avg_response_time_ms"] == 150.5
        assert result["endpoint_breakdown"]["search"] == 50


class TestRateLimitExceptions:
    """Test rate limiting exceptions"""

    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception"""
        exception = RateLimitExceeded("MOUSER", "per_minute", 60)

        assert exception.supplier_name == "MOUSER"
        assert exception.limit_type == "per_minute"
        assert exception.retry_after == 60
        assert "Rate limit exceeded for MOUSER" in str(exception)
        assert "Retry after 60 seconds" in str(exception)


@pytest.mark.asyncio
async def test_concurrent_rate_limit_checks(rate_limit_service, sample_rate_limits):
    """Test concurrent rate limit checks work correctly"""
    # Run multiple concurrent rate limit checks
    tasks = []
    for i in range(10):
        task = rate_limit_service.check_rate_limit("MOUSER", f"endpoint_{i}")
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # All should be allowed initially
    for result in results:
        assert result["allowed"] is True
        assert result["supplier_name"] == "MOUSER"


@pytest.mark.asyncio
async def test_multiple_supplier_rate_limiting(rate_limit_service, sample_rate_limits, memory_engine):
    """Test rate limiting works independently for different suppliers"""
    # Fill up MOUSER's rate limit
    now = datetime.now(timezone.utc)
    with Session(memory_engine) as session:
        for i in range(30):  # MOUSER limit is 30/minute
            usage = SupplierUsageTrackingModel(
                supplier_name="MOUSER",
                endpoint_type="search",
                request_timestamp=now - timedelta(seconds=i),
                success=True,
            )
            session.add(usage)
        session.commit()

    # MOUSER should be rate limited
    mouser_result = await rate_limit_service.check_rate_limit("MOUSER")
    assert mouser_result["allowed"] is False

    # LCSC should still be allowed (different supplier)
    lcsc_result = await rate_limit_service.check_rate_limit("LCSC")
    assert lcsc_result["allowed"] is True
