"""
Complete Enrichment Workflow Integration Test

This test validates the entire enrichment system end-to-end:
1. Database initialization with rate limiting tables
2. Mouser XLS file import 
3. Enrichment queue processing with rate limiting
4. WebSocket progress updates
5. Real-time supplier usage monitoring
"""

import pytest
import asyncio
import os
from pathlib import Path
from sqlmodel import create_engine, SQLModel
from unittest.mock import Mock, AsyncMock

from MakerMatrix.services.rate_limit_service import RateLimitService
from MakerMatrix.services.enrichment_queue_manager import EnrichmentQueueManager
from MakerMatrix.models.rate_limiting_models import (
    SupplierRateLimitModel,
    SupplierUsageTrackingModel,
    SupplierUsageSummaryModel
)
from MakerMatrix.models.models import PartModel, LocationModel, CategoryModel


@pytest.fixture
def test_engine():
    """Create test database engine with all tables"""
    engine = create_engine("sqlite:///test_enrichment_workflow.db")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for testing"""
    manager = Mock()
    manager.broadcast_to_all = AsyncMock()
    return manager


@pytest.fixture
def rate_limit_service(test_engine, mock_websocket_manager):
    """Create rate limit service"""
    return RateLimitService(test_engine, mock_websocket_manager)


@pytest.fixture
def enrichment_queue_manager(test_engine, rate_limit_service, mock_websocket_manager):
    """Create enrichment queue manager"""
    return EnrichmentQueueManager(test_engine, rate_limit_service, mock_websocket_manager)


@pytest.fixture
def mouser_xls_file():
    """Get path to Mouser XLS test file"""
    file_path = Path("/home/ril3y/MakerMatrix/MakerMatrix/tests/mouser_xls_test/271360826.xls")
    if not file_path.exists():
        pytest.skip(f"Mouser XLS test file not found at {file_path}")
    return file_path


class TestCompleteEnrichmentWorkflow:
    """Test the complete enrichment workflow"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, test_engine, rate_limit_service):
        """Test that all tables are created and rate limits initialized"""
        from sqlmodel import Session, select
        
        # Initialize the default limits first
        await rate_limit_service.initialize_default_limits()
        
        with Session(test_engine) as session:
            # Check rate limit tables exist and have data
            mouser_limits = session.exec(
                select(SupplierRateLimitModel).where(
                    SupplierRateLimitModel.supplier_name == "mouser"
                )
            ).first()
            
            assert mouser_limits is not None
            assert mouser_limits.requests_per_minute == 30
            assert mouser_limits.requests_per_hour == 1000
            assert mouser_limits.enabled is True
            
            # Check other suppliers
            lcsc_limits = session.exec(
                select(SupplierRateLimitModel).where(
                    SupplierRateLimitModel.supplier_name == "lcsc"
                )
            ).first()
            
            assert lcsc_limits is not None
            assert lcsc_limits.requests_per_minute == 60
            assert lcsc_limits.requests_per_hour == 3600
    
    @pytest.mark.asyncio
    async def test_enrichment_queue_initialization(self, enrichment_queue_manager):
        """Test that enrichment queues are properly initialized"""
        # Check that supplier queues are created
        assert "MOUSER" in enrichment_queue_manager.supplier_queues
        assert "LCSC" in enrichment_queue_manager.supplier_queues
        assert "DIGIKEY" in enrichment_queue_manager.supplier_queues
        
        # Check queue status
        status = enrichment_queue_manager.get_queue_status()
        assert isinstance(status, dict)
        assert len(status) > 0
        
        for supplier, queue_info in status.items():
            assert "queue_size" in queue_info
            assert "running_count" in queue_info
            assert "completed_count" in queue_info
            assert queue_info["queue_size"] == 0  # Should start empty
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limit_service):
        """Test rate limiting works correctly"""
        # Test that initial requests are allowed
        result = await rate_limit_service.check_rate_limit("MOUSER")
        assert result["allowed"] is True
        assert result["current_usage"]["per_minute"] == 0
        
        # Record some requests
        for i in range(5):
            await rate_limit_service.record_request("MOUSER", "search", True, 100)
        
        # Check usage tracking
        result = await rate_limit_service.check_rate_limit("MOUSER")
        assert result["allowed"] is True
        assert result["current_usage"]["per_minute"] == 5
        
        # Get usage stats
        stats = await rate_limit_service.get_usage_stats("MOUSER", "1h")
        assert stats["total_requests"] == 5
        assert stats["successful_requests"] == 5
        assert stats["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_websocket_integration(self, rate_limit_service, mock_websocket_manager):
        """Test WebSocket messages are sent for rate limit updates"""
        # Record a request which should trigger WebSocket broadcast
        await rate_limit_service.record_request("MOUSER", "search", True, 150)
        
        # Verify WebSocket broadcast was called
        mock_websocket_manager.broadcast_to_all.assert_called()
        
        # Check the message structure
        call_args = mock_websocket_manager.broadcast_to_all.call_args[0]
        message = call_args[0]
        
        assert message["type"] == "rate_limit_update"
        assert message["data"]["supplier_name"] == "MOUSER"
        assert "current_usage" in message["data"]
        assert "limits" in message["data"]
    
    @pytest.mark.asyncio
    async def test_part_enrichment_queuing(self, enrichment_queue_manager):
        """Test queuing parts for enrichment"""
        # Queue a part for enrichment
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="test-part-123",
            part_name="Test Resistor 1K",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet", "fetch_image", "fetch_pricing"]
        )
        
        assert task_id is not None
        assert task_id in enrichment_queue_manager.task_registry
        
        # Check task status
        task_status = enrichment_queue_manager.get_task_status(task_id)
        assert task_status is not None
        assert task_status["part_name"] == "Test Resistor 1K"
        assert task_status["supplier_name"] == "MOUSER"
        assert task_status["status"] == "pending"
        assert task_status["progress_percentage"] == 0
        
        # Check queue status
        mouser_status = enrichment_queue_manager.get_queue_status("MOUSER")
        assert mouser_status["queue_size"] == 1
        assert mouser_status["supplier_name"] == "MOUSER"
    
    @pytest.mark.asyncio
    async def test_priority_queuing(self, enrichment_queue_manager):
        """Test that priority queuing works correctly"""
        # Add tasks with different priorities
        normal_task = await enrichment_queue_manager.queue_part_enrichment(
            part_id="normal-part",
            part_name="Normal Priority Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        
        from MakerMatrix.services.enrichment_queue_manager import EnrichmentPriority
        
        urgent_task = await enrichment_queue_manager.queue_part_enrichment(
            part_id="urgent-part", 
            part_name="Urgent Priority Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"],
            priority=EnrichmentPriority.URGENT
        )
        
        high_task = await enrichment_queue_manager.queue_part_enrichment(
            part_id="high-part",
            part_name="High Priority Part", 
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"],
            priority=EnrichmentPriority.HIGH
        )
        
        # Check queue status
        mouser_queue = enrichment_queue_manager.supplier_queues["MOUSER"]
        assert mouser_queue.queue_size == 3
        
        # Get next task - should be urgent priority
        next_task = mouser_queue.get_next_task()
        assert next_task.part_name == "Urgent Priority Part"
        
        # Next should be high priority
        next_task = mouser_queue.get_next_task()
        assert next_task.part_name == "High Priority Part"
        
        # Finally normal priority
        next_task = mouser_queue.get_next_task()
        assert next_task.part_name == "Normal Priority Part"
    
    @pytest.mark.asyncio
    async def test_task_cancellation(self, enrichment_queue_manager):
        """Test task cancellation works"""
        # Queue a task
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="cancel-test",
            part_name="Cancellation Test Part",
            supplier_name="MOUSER", 
            capabilities=["fetch_datasheet"]
        )
        
        # Verify task is queued
        task_status = enrichment_queue_manager.get_task_status(task_id)
        assert task_status["status"] == "pending"
        
        # Cancel the task
        success = await enrichment_queue_manager.cancel_task(task_id)
        assert success is True
        
        # Verify task is cancelled
        task_status = enrichment_queue_manager.get_task_status(task_id)
        assert task_status["status"] == "cancelled"
        
        # Verify task removed from queue
        mouser_status = enrichment_queue_manager.get_queue_status("MOUSER")
        assert mouser_status["queue_size"] == 0
    
    @pytest.mark.asyncio 
    async def test_all_supplier_usage_tracking(self, rate_limit_service):
        """Test getting usage data for all suppliers"""
        # Add usage for multiple suppliers
        await rate_limit_service.record_request("MOUSER", "search", True, 100)
        await rate_limit_service.record_request("LCSC", "details", True, 200)
        await rate_limit_service.record_request("DIGIKEY", "pricing", False, 5000)
        
        # Get all supplier usage
        all_usage = await rate_limit_service.get_all_supplier_usage()
        
        assert len(all_usage) >= 3  # Should have at least 3 suppliers
        
        supplier_names = [data["supplier_name"] for data in all_usage]
        assert "MOUSER" in supplier_names
        assert "LCSC" in supplier_names
        assert "DIGIKEY" in supplier_names
        
        # Check data structure
        mouser_data = next(data for data in all_usage if data["supplier_name"] == "MOUSER")
        assert "limits" in mouser_data
        assert "current_usage" in mouser_data
        assert "usage_percentage" in mouser_data
        assert "stats_24h" in mouser_data
        assert mouser_data["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, enrichment_queue_manager):
        """Test comprehensive queue statistics"""
        # Add tasks to different queues
        await enrichment_queue_manager.queue_part_enrichment(
            part_id="stats-test-1",
            part_name="Stats Test Part 1",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        
        await enrichment_queue_manager.queue_part_enrichment(
            part_id="stats-test-2", 
            part_name="Stats Test Part 2",
            supplier_name="LCSC",
            capabilities=["fetch_image"]
        )
        
        # Get comprehensive statistics
        stats = await enrichment_queue_manager.get_queue_statistics()
        
        assert stats["total_pending"] == 2
        assert stats["total_running"] == 0
        assert stats["total_completed"] == 0
        assert stats["total_failed"] == 0
        assert stats["total_queues"] >= 3
        assert stats["active_queues"] == 0  # No processing yet
        assert "queue_details" in stats
        
        # Check individual queue details
        queue_details = stats["queue_details"]
        assert "MOUSER" in queue_details
        assert "LCSC" in queue_details
        assert queue_details["MOUSER"]["queue_size"] == 1
        assert queue_details["LCSC"]["queue_size"] == 1


@pytest.mark.integration
class TestMouserXLSWorkflow:
    """Test the complete workflow with actual Mouser XLS file"""
    
    def test_mouser_xls_file_exists(self, mouser_xls_file):
        """Verify the Mouser XLS test file exists"""
        assert mouser_xls_file.exists()
        assert mouser_xls_file.suffix == ".xls"
        assert mouser_xls_file.stat().st_size > 0
        print(f"Found Mouser XLS file: {mouser_xls_file} ({mouser_xls_file.stat().st_size} bytes)")
    
    @pytest.mark.asyncio
    async def test_simulated_mouser_import_workflow(self, enrichment_queue_manager, rate_limit_service):
        """Simulate importing Mouser XLS and enriching parts"""
        # Simulate importing multiple parts from Mouser XLS
        mouser_parts = [
            {"part_id": "mouser-part-1", "part_name": "Resistor 1K 0603", "part_number": "71-CRCW0603-1K-E3"},
            {"part_id": "mouser-part-2", "part_name": "Capacitor 10uF 16V", "part_number": "80-C0603C106M4PAC"},
            {"part_id": "mouser-part-3", "part_name": "LED Red 0805", "part_number": "720-150080RS75000"},
            {"part_id": "mouser-part-4", "part_name": "IC MCU ARM Cortex", "part_number": "511-STM32F103C8T6"},
            {"part_id": "mouser-part-5", "part_name": "Crystal 8MHz", "part_number": "815-ABL-8-B2"}
        ]
        
        # Queue all parts for enrichment
        task_ids = []
        for part in mouser_parts:
            task_id = await enrichment_queue_manager.queue_part_enrichment(
                part_id=part["part_id"],
                part_name=part["part_name"],
                supplier_name="MOUSER",
                capabilities=["fetch_datasheet", "fetch_image", "fetch_pricing"]
            )
            task_ids.append(task_id)
        
        # Verify all tasks are queued
        assert len(task_ids) == 5
        
        mouser_status = enrichment_queue_manager.get_queue_status("MOUSER")
        assert mouser_status["queue_size"] == 5
        
        # Check overall statistics
        stats = await enrichment_queue_manager.get_queue_statistics()
        assert stats["total_pending"] == 5
        
        # Simulate processing some tasks (mark as completed)
        mouser_queue = enrichment_queue_manager.supplier_queues["MOUSER"]
        
        for i in range(3):  # Process first 3 tasks
            task = mouser_queue.get_next_task()
            if task:
                mouser_queue.mark_task_running(task)
                
                # Simulate successful enrichment
                task.completed_capabilities = task.capabilities.copy()
                mouser_queue.mark_task_completed(task)
                
                # Record API usage for rate limiting
                for capability in task.capabilities:
                    await rate_limit_service.record_request("MOUSER", capability, True, 150)
        
        # Check updated statistics
        stats = await enrichment_queue_manager.get_queue_statistics()
        assert stats["total_pending"] == 2  # 2 remaining
        assert stats["total_completed"] == 3  # 3 completed
        
        # Check rate limit usage
        rate_status = await rate_limit_service.check_rate_limit("MOUSER")
        assert rate_status["allowed"] is True
        assert rate_status["current_usage"]["per_minute"] == 9  # 3 tasks * 3 capabilities each
        
        # Get usage statistics
        usage_stats = await rate_limit_service.get_usage_stats("MOUSER", "1h")
        assert usage_stats["total_requests"] == 9
        assert usage_stats["successful_requests"] == 9
        assert usage_stats["success_rate"] == 100.0
        
        print(f"Successfully processed 3/5 parts with rate limiting")
        print(f"Current MOUSER usage: {rate_status['current_usage']['per_minute']}/30 per minute")


if __name__ == "__main__":
    # Run the integration tests
    import subprocess
    subprocess.run([
        "python", "-m", "pytest", 
        "/home/ril3y/MakerMatrix/MakerMatrix/tests/integration_tests/test_complete_enrichment_workflow.py",
        "-v", "--tb=short"
    ])