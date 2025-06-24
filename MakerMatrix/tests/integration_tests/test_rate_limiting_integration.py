"""
Integration tests for rate limiting with supplier APIs

Tests the complete rate limiting flow with real supplier implementations.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

from MakerMatrix.services.rate_limit_service import RateLimitService
from MakerMatrix.suppliers.registry import get_supplier
from MakerMatrix.models.models import engine
from MakerMatrix.models.rate_limiting_models import SupplierRateLimitModel
from sqlalchemy.orm import Session


@pytest.fixture
async def rate_limit_service():
    """Create rate limit service for testing"""
    # Use the global engine instance
    service = RateLimitService(engine)
    await service._initialize_default_limits()
    return service


@pytest.fixture
def mock_mouser_supplier():
    """Mock Mouser supplier for controlled testing"""
    supplier = get_supplier("mouser")
    
    # Mock the HTTP session to avoid real API calls
    with patch.object(supplier, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "SearchResults": {
                "Parts": [
                    {
                        "MouserPartNumber": "TEST-PART-123",
                        "ManufacturerPartNumber": "TEST123",
                        "Description": "Test resistor",
                        "DataSheetUrl": "https://example.com/datasheet.pdf",
                        "ImagePath": "https://example.com/image.jpg",
                        "PriceBreaks": [{"Quantity": 1, "Price": "$0.10", "Currency": "USD"}]
                    }
                ]
            }
        }
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        yield supplier


@pytest.mark.asyncio
class TestRateLimitingIntegration:
    """Integration tests for rate limiting with suppliers"""
    
    async def test_rate_limit_enforcement_with_mouser(self, rate_limit_service, mock_mouser_supplier):
        """Test that rate limiting is enforced during Mouser API calls"""
        # Configure supplier with test credentials
        mock_mouser_supplier.configure(
            credentials={"api_key": "test-api-key"},
            config={"request_timeout": 30}
        )
        
        # Make multiple requests to trigger rate limiting
        results = []
        for i in range(35):  # Exceed Mouser's 30/minute limit
            try:
                async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                    if allowed:
                        result = await mock_mouser_supplier.fetch_datasheet("TEST-PART-123")
                        results.append(result)
                    else:
                        results.append(None)  # Rate limited
            except Exception as e:
                results.append(str(e))
        
        # Verify rate limiting was enforced
        successful_requests = len([r for r in results if r is not None and isinstance(r, str) and r.startswith("https")])
        rate_limited_requests = len([r for r in results if r is None])
        
        assert successful_requests <= 30, "Should not exceed rate limit"
        assert rate_limited_requests > 0, "Should have rate-limited some requests"
    
    async def test_rate_limit_reset_after_window(self, rate_limit_service, mock_mouser_supplier):
        """Test that rate limits reset after time window"""
        # Configure supplier
        mock_mouser_supplier.configure(
            credentials={"api_key": "test-api-key"},
            config={"request_timeout": 30}
        )
        
        # Use up rate limit
        for i in range(30):
            async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                if allowed:
                    await mock_mouser_supplier.fetch_datasheet(f"TEST-PART-{i}")
        
        # Check that we're at the limit
        status = await rate_limit_service.check_rate_limit("MOUSER", "datasheet")
        assert not status["allowed"], "Should be at rate limit"
        
        # Mock time advancement (simulate waiting 61 seconds)
        with patch('MakerMatrix.services.rate_limit_service.datetime') as mock_datetime:
            future_time = datetime.now(timezone.utc).timestamp() + 61
            mock_datetime.now.return_value.timestamp.return_value = future_time
            mock_datetime.now.return_value = datetime.fromtimestamp(future_time, tz=timezone.utc)
            
            # Rate limit should be reset
            status = await rate_limit_service.check_rate_limit("MOUSER", "datasheet")
            assert status["allowed"], "Rate limit should be reset after time window"
    
    async def test_websocket_rate_limit_events(self, rate_limit_service, mock_mouser_supplier):
        """Test WebSocket events are generated for rate limit violations"""
        # Configure supplier
        mock_mouser_supplier.configure(
            credentials={"api_key": "test-api-key"},
            config={"request_timeout": 30}
        )
        
        # Mock WebSocket manager
        websocket_events = []
        
        def mock_broadcast(event):
            websocket_events.append(event)
        
        with patch.object(rate_limit_service, '_broadcast_rate_limit_event', side_effect=mock_broadcast):
            # Trigger rate limit violation
            for i in range(31):  # One over the limit
                async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                    if allowed:
                        await mock_mouser_supplier.fetch_datasheet(f"TEST-PART-{i}")
        
        # Verify WebSocket events were generated
        assert len(websocket_events) > 0, "Should generate WebSocket events for rate limit violations"
        
        # Check event structure
        event = websocket_events[0]
        assert event["type"] == "rate_limit_violation"
        assert "MOUSER" in event["data"]["supplier_name"]
    
    async def test_supplier_usage_statistics_tracking(self, rate_limit_service, mock_mouser_supplier):
        """Test that supplier usage statistics are properly tracked"""
        # Configure supplier
        mock_mouser_supplier.configure(
            credentials={"api_key": "test-api-key"},
            config={"request_timeout": 30}
        )
        
        # Make some successful requests
        successful_count = 0
        for i in range(5):
            async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                if allowed:
                    await mock_mouser_supplier.fetch_datasheet(f"TEST-PART-{i}")
                    successful_count += 1
        
        # Check usage statistics
        stats = await rate_limit_service.get_supplier_usage_stats("MOUSER", hours=1)
        
        assert stats["supplier_name"] == "MOUSER"
        assert stats["total_requests"] >= successful_count
        assert stats["successful_requests"] >= successful_count
        assert stats["success_rate"] > 0
        assert "endpoint_breakdown" in stats
        assert stats["endpoint_breakdown"]["datasheet"] >= successful_count
    
    async def test_multiple_supplier_rate_limiting(self, rate_limit_service):
        """Test rate limiting across multiple suppliers"""
        # This would test LCSC, Mouser, DigiKey etc. simultaneously
        # For now, we'll test the framework with mock suppliers
        
        suppliers = ["MOUSER", "LCSC", "DIGIKEY"]
        results = {}
        
        for supplier in suppliers:
            results[supplier] = []
            for i in range(10):
                async with rate_limit_service.rate_limited_request(supplier, "search") as allowed:
                    results[supplier].append(allowed)
        
        # Each supplier should have independent rate limiting
        for supplier in suppliers:
            assert all(results[supplier]), f"All requests for {supplier} should be allowed initially"
    
    async def test_rate_limit_persistence(self, rate_limit_service):
        """Test that rate limit data persists across service restarts"""
        # Make some requests
        for i in range(5):
            async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                pass
        
        # Get current usage
        status_before = await rate_limit_service.check_rate_limit("MOUSER", "datasheet")
        
        # Create new service instance (simulating restart)
        # Use the global engine instance
        new_service = RateLimitService(engine)
        
        # Usage should be persisted
        status_after = await new_service.check_rate_limit("MOUSER", "datasheet")
        
        assert status_after["current_usage"]["per_minute"] >= status_before["current_usage"]["per_minute"]
    
    async def test_rate_limit_configuration_updates(self, rate_limit_service):
        """Test that rate limit configuration updates work correctly"""
        # Use the global engine instance
        
        # Update rate limits for Mouser
        with Session(engine) as session:
            rate_limit = session.query(SupplierRateLimitModel).filter_by(
                supplier_name="MOUSER"
            ).first()
            
            if rate_limit:
                rate_limit.requests_per_minute = 10  # Lower limit for testing
                session.commit()
        
        # Test with new limits
        successful_requests = 0
        for i in range(15):
            async with rate_limit_service.rate_limited_request("MOUSER", "datasheet") as allowed:
                if allowed:
                    successful_requests += 1
        
        # Should respect new lower limit
        assert successful_requests <= 10, "Should respect updated rate limits"


@pytest.mark.asyncio 
class TestRateLimitServiceMethods:
    """Test specific methods of the rate limit service"""
    
    async def test_get_all_supplier_limits(self, rate_limit_service):
        """Test retrieving all supplier rate limits"""
        limits = await rate_limit_service.get_all_supplier_limits()
        
        assert isinstance(limits, list)
        assert len(limits) > 0
        
        # Check structure
        for limit in limits:
            assert "supplier_name" in limit
            assert "requests_per_minute" in limit
            assert "requests_per_hour" in limit
            assert "requests_per_day" in limit
    
    async def test_get_supplier_limits(self, rate_limit_service):
        """Test retrieving specific supplier limits"""
        limits = await rate_limit_service.get_supplier_limits("MOUSER")
        
        assert limits is not None
        assert limits["supplier_name"] == "MOUSER"
        assert limits["requests_per_minute"] == 30
        assert limits["requests_per_hour"] == 1000
        assert limits["requests_per_day"] == 1000
    
    async def test_update_supplier_limits(self, rate_limit_service):
        """Test updating supplier rate limits"""
        new_limits = {
            "requests_per_minute": 25,
            "requests_per_hour": 800,
            "requests_per_day": 800
        }
        
        success = await rate_limit_service.update_supplier_limits("MOUSER", new_limits)
        assert success
        
        # Verify update
        updated_limits = await rate_limit_service.get_supplier_limits("MOUSER")
        assert updated_limits["requests_per_minute"] == 25
        assert updated_limits["requests_per_hour"] == 800
        assert updated_limits["requests_per_day"] == 800