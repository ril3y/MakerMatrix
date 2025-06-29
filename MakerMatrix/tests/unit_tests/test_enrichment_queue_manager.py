"""
Tests for Enrichment Queue Manager

Tests for the intelligent enrichment queue system including supplier queues,
task management, and rate-limit-aware processing.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from sqlmodel import Session, create_engine, SQLModel


from MakerMatrix.services.rate_limit_service import RateLimitService
from MakerMatrix.models.rate_limiting_models import SupplierRateLimitModel


@pytest.fixture
def memory_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_rate_limit_service():
    """Create mock rate limit service"""
    service = Mock(spec=RateLimitService)
    service.check_rate_limit = AsyncMock(return_value={
        "allowed": True,
        "current_usage": {"per_minute": 5, "per_hour": 100, "per_day": 500},
        "limits": {"per_minute": 30, "per_hour": 1000, "per_day": 1000}
    })
    service.record_request = AsyncMock()
    return service


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    manager = Mock()
    manager.broadcast_to_all = AsyncMock()
    return manager


@pytest.fixture
def enrichment_queue_manager(memory_engine, mock_rate_limit_service, mock_websocket_manager):
    """Create EnrichmentQueueManager instance with mocks"""
    with patch('MakerMatrix.services.enrichment_queue_manager.get_available_suppliers') as mock_suppliers:
        mock_suppliers.return_value = ["mouser", "lcsc", "digikey"]
        
        manager = EnrichmentQueueManager(
            memory_engine,
            mock_rate_limit_service,
            mock_websocket_manager
        )
        return manager


@pytest.fixture
def sample_enrichment_task():
    """Create a sample enrichment task"""
    return EnrichmentTask(
        id="task-123",
        part_id="part-456",
        part_name="Test Resistor",
        supplier_name="MOUSER",
        capabilities=["fetch_datasheet", "fetch_image", "fetch_pricing"],
        priority=EnrichmentPriority.NORMAL
    )


class TestEnrichmentTask:
    """Test EnrichmentTask data class"""
    
    def test_create_enrichment_task(self, sample_enrichment_task):
        """Test creating an enrichment task"""
        task = sample_enrichment_task
        
        assert task.id == "task-123"
        assert task.part_id == "part-456"
        assert task.part_name == "Test Resistor"
        assert task.supplier_name == "MOUSER"
        assert task.capabilities == ["fetch_datasheet", "fetch_image", "fetch_pricing"]
        assert task.priority == EnrichmentPriority.NORMAL
        assert task.status == EnrichmentStatus.PENDING
        assert isinstance(task.created_at, datetime)
        assert task.started_at is None
        assert task.completed_at is None
        assert task.completed_capabilities == []
        assert task.failed_capabilities == []
        assert task.retry_count == 0
        assert task.max_retries == 3
    
    def test_progress_percentage_calculation(self, sample_enrichment_task):
        """Test progress percentage calculation"""
        task = sample_enrichment_task
        
        # Initially 0%
        assert task.progress_percentage == 0
        
        # Mark one capability as completed (33%)
        task.completed_capabilities = ["fetch_datasheet"]
        assert task.progress_percentage == 33
        
        # Mark two capabilities as completed (67%)
        task.completed_capabilities = ["fetch_datasheet", "fetch_image"]
        assert task.progress_percentage == 66
        
        # Mark all capabilities as completed (100%)
        task.completed_capabilities = ["fetch_datasheet", "fetch_image", "fetch_pricing"]
        assert task.progress_percentage == 100
    
    def test_remaining_capabilities(self, sample_enrichment_task):
        """Test remaining capabilities calculation"""
        task = sample_enrichment_task
        
        # Initially all capabilities remain
        assert task.remaining_capabilities == ["fetch_datasheet", "fetch_image", "fetch_pricing"]
        
        # Mark one as completed
        task.completed_capabilities = ["fetch_datasheet"]
        assert task.remaining_capabilities == ["fetch_image", "fetch_pricing"]
        
        # Mark all as completed
        task.completed_capabilities = ["fetch_datasheet", "fetch_image", "fetch_pricing"]
        assert task.remaining_capabilities == []
    
    def test_empty_capabilities_progress(self):
        """Test progress calculation with empty capabilities"""
        task = EnrichmentTask(
            id="task-empty",
            part_id="part-123",
            part_name="Empty Task",
            supplier_name="MOUSER",
            capabilities=[],  # Empty capabilities
            priority=EnrichmentPriority.NORMAL
        )
        
        assert task.progress_percentage == 100  # Should be 100% when no capabilities
        assert task.remaining_capabilities == []


class TestSupplierQueue:
    """Test SupplierQueue functionality"""
    
    @pytest.fixture
    def supplier_queue(self, mock_rate_limit_service):
        """Create a supplier queue"""
        with patch('MakerMatrix.services.enrichment_queue_manager.get_supplier') as mock_get_supplier:
            mock_supplier = Mock()
            mock_supplier.get_rate_limit_delay.return_value = 2.0
            mock_get_supplier.return_value = mock_supplier
            
            queue = SupplierQueue("MOUSER", mock_rate_limit_service)
            return queue
    
    def test_create_supplier_queue(self, supplier_queue):
        """Test creating a supplier queue"""
        assert supplier_queue.supplier_name == "MOUSER"
        assert supplier_queue.pending_tasks == []
        assert supplier_queue.running_tasks == set()
        assert supplier_queue.completed_tasks == []
        assert supplier_queue.failed_tasks == []
        assert supplier_queue.is_processing is False
        assert supplier_queue.rate_limit_delay == 2.0
    
    def test_add_task_normal_priority(self, supplier_queue, sample_enrichment_task):
        """Test adding normal priority task"""
        supplier_queue.add_task(sample_enrichment_task)
        
        assert supplier_queue.queue_size == 1
        assert supplier_queue.pending_tasks[0] == sample_enrichment_task
    
    def test_add_tasks_priority_ordering(self, supplier_queue):
        """Test that tasks are ordered by priority"""
        # Add tasks in mixed priority order
        normal_task = EnrichmentTask(
            id="normal", part_id="part-1", part_name="Normal", supplier_name="MOUSER",
            capabilities=["fetch_datasheet"], priority=EnrichmentPriority.NORMAL
        )
        urgent_task = EnrichmentTask(
            id="urgent", part_id="part-2", part_name="Urgent", supplier_name="MOUSER",
            capabilities=["fetch_datasheet"], priority=EnrichmentPriority.URGENT
        )
        high_task = EnrichmentTask(
            id="high", part_id="part-3", part_name="High", supplier_name="MOUSER",
            capabilities=["fetch_datasheet"], priority=EnrichmentPriority.HIGH
        )
        low_task = EnrichmentTask(
            id="low", part_id="part-4", part_name="Low", supplier_name="MOUSER",
            capabilities=["fetch_datasheet"], priority=EnrichmentPriority.LOW
        )
        
        # Add in random order
        supplier_queue.add_task(normal_task)
        supplier_queue.add_task(urgent_task)
        supplier_queue.add_task(high_task)
        supplier_queue.add_task(low_task)
        
        # Should be ordered: urgent, high, normal, low
        assert supplier_queue.pending_tasks[0].priority == EnrichmentPriority.URGENT
        assert supplier_queue.pending_tasks[1].priority == EnrichmentPriority.HIGH
        assert supplier_queue.pending_tasks[2].priority == EnrichmentPriority.NORMAL
        assert supplier_queue.pending_tasks[3].priority == EnrichmentPriority.LOW
    
    def test_get_next_task(self, supplier_queue, sample_enrichment_task):
        """Test getting next task from queue"""
        supplier_queue.add_task(sample_enrichment_task)
        
        next_task = supplier_queue.get_next_task()
        assert next_task == sample_enrichment_task
        assert supplier_queue.queue_size == 0  # Should be removed from queue
    
    def test_get_next_task_empty_queue(self, supplier_queue):
        """Test getting next task from empty queue"""
        next_task = supplier_queue.get_next_task()
        assert next_task is None
    
    def test_mark_task_running(self, supplier_queue, sample_enrichment_task):
        """Test marking task as running"""
        supplier_queue.mark_task_running(sample_enrichment_task)
        
        assert sample_enrichment_task.status == EnrichmentStatus.RUNNING
        assert isinstance(sample_enrichment_task.started_at, datetime)
        assert sample_enrichment_task.id in supplier_queue.running_tasks
        assert supplier_queue.running_count == 1
    
    def test_mark_task_completed(self, supplier_queue, sample_enrichment_task):
        """Test marking task as completed"""
        # First mark as running
        supplier_queue.mark_task_running(sample_enrichment_task)
        
        # Then mark as completed
        supplier_queue.mark_task_completed(sample_enrichment_task)
        
        assert sample_enrichment_task.status == EnrichmentStatus.COMPLETED
        assert isinstance(sample_enrichment_task.completed_at, datetime)
        assert sample_enrichment_task.id not in supplier_queue.running_tasks
        assert sample_enrichment_task in supplier_queue.completed_tasks
        assert supplier_queue.running_count == 0
    
    def test_mark_task_failed_with_retries(self, supplier_queue, sample_enrichment_task):
        """Test marking task as failed with retry logic"""
        # First mark as running
        supplier_queue.mark_task_running(sample_enrichment_task)
        
        # Mark as failed (should retry)
        supplier_queue.mark_task_failed(sample_enrichment_task, "Test error")
        
        assert sample_enrichment_task.status == EnrichmentStatus.PENDING  # Re-queued for retry
        assert sample_enrichment_task.retry_count == 1
        assert sample_enrichment_task.error_message == "Test error"
        assert sample_enrichment_task.id not in supplier_queue.running_tasks
        assert supplier_queue.queue_size == 1  # Re-added to queue
    
    def test_mark_task_failed_max_retries(self, supplier_queue, sample_enrichment_task):
        """Test marking task as failed after max retries"""
        # Set retry count to max
        sample_enrichment_task.retry_count = 3
        sample_enrichment_task.max_retries = 3
        
        # First mark as running
        supplier_queue.mark_task_running(sample_enrichment_task)
        
        # Mark as failed (should not retry)
        supplier_queue.mark_task_failed(sample_enrichment_task, "Final error")
        
        assert sample_enrichment_task.status == EnrichmentStatus.FAILED
        assert sample_enrichment_task in supplier_queue.failed_tasks
        assert supplier_queue.queue_size == 0  # Not re-added to queue
    
    def test_estimate_completion_time(self, supplier_queue):
        """Test completion time estimation"""
        # Empty queue should return None
        assert supplier_queue.estimate_completion_time() is None
        
        # Add tasks with capabilities
        task1 = EnrichmentTask(
            id="task1", part_id="part1", part_name="Part1", supplier_name="MOUSER",
            capabilities=["fetch_datasheet", "fetch_image"]  # 2 capabilities
        )
        task2 = EnrichmentTask(
            id="task2", part_id="part2", part_name="Part2", supplier_name="MOUSER",
            capabilities=["fetch_pricing"]  # 1 capability
        )
        
        supplier_queue.add_task(task1)
        supplier_queue.add_task(task2)
        
        # Should estimate based on total capabilities (3) * rate limit delay (2.0)
        estimated = supplier_queue.estimate_completion_time()
        assert estimated is not None
        assert isinstance(estimated, datetime)
        
        # Should be approximately 6 seconds from now (3 capabilities * 2 seconds)
        now = datetime.now(timezone.utc)
        time_diff = (estimated - now).total_seconds()
        assert 5.5 <= time_diff <= 6.5  # Allow some tolerance


class TestEnrichmentQueueManager:
    """Test EnrichmentQueueManager functionality"""
    
    def test_initialization(self, enrichment_queue_manager):
        """Test queue manager initialization"""
        manager = enrichment_queue_manager
        
        # Should have queues for all available suppliers
        assert "MOUSER" in manager.supplier_queues
        assert "LCSC" in manager.supplier_queues
        assert "DIGIKEY" in manager.supplier_queues
        assert len(manager.supplier_queues) == 3
        assert manager.is_running is False
        assert manager.task_registry == {}
    
    @pytest.mark.asyncio
    async def test_queue_part_enrichment(self, enrichment_queue_manager):
        """Test queuing a part for enrichment"""
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-123",
            part_name="Test Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet", "fetch_image"],
            priority=EnrichmentPriority.HIGH
        )
        
        assert task_id is not None
        assert task_id in enrichment_queue_manager.task_registry
        
        # Check task was added to correct queue
        mouser_queue = enrichment_queue_manager.supplier_queues["MOUSER"]
        assert mouser_queue.queue_size == 1
        
        # Check task details
        task = enrichment_queue_manager.task_registry[task_id]
        assert task.part_id == "part-123"
        assert task.part_name == "Test Part"
        assert task.supplier_name == "MOUSER"
        assert task.capabilities == ["fetch_datasheet", "fetch_image"]
        assert task.priority == EnrichmentPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_queue_part_enrichment_invalid_supplier(self, enrichment_queue_manager):
        """Test queuing with invalid supplier"""
        with pytest.raises(ValueError) as exc_info:
            await enrichment_queue_manager.queue_part_enrichment(
                part_id="part-123",
                part_name="Test Part",
                supplier_name="INVALID_SUPPLIER",
                capabilities=["fetch_datasheet"]
            )
        
        assert "Supplier INVALID_SUPPLIER not available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_queue_part_enrichment_with_custom_task_id(self, enrichment_queue_manager):
        """Test queuing with custom task ID"""
        custom_task_id = "custom-task-123"
        
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-456",
            part_name="Custom Task Part",
            supplier_name="LCSC",
            capabilities=["fetch_details"],
            task_id=custom_task_id
        )
        
        assert task_id == custom_task_id
        assert custom_task_id in enrichment_queue_manager.task_registry
    
    def test_get_queue_status_specific_supplier(self, enrichment_queue_manager):
        """Test getting queue status for specific supplier"""
        status = enrichment_queue_manager.get_queue_status("MOUSER")
        
        assert status["supplier_name"] == "MOUSER"
        assert status["queue_size"] == 0
        assert status["running_count"] == 0
        assert status["completed_count"] == 0
        assert status["failed_count"] == 0
        assert status["estimated_completion"] is None
        assert status["is_processing"] is False
    
    def test_get_queue_status_all_suppliers(self, enrichment_queue_manager):
        """Test getting queue status for all suppliers"""
        status = enrichment_queue_manager.get_queue_status()
        
        assert isinstance(status, dict)
        assert "MOUSER" in status
        assert "LCSC" in status
        assert "DIGIKEY" in status
        
        # Each supplier should have status info
        mouser_status = status["MOUSER"]
        assert "queue_size" in mouser_status
        assert "running_count" in mouser_status
        assert "completed_count" in mouser_status
        assert "failed_count" in mouser_status
        assert "is_processing" in mouser_status
    
    def test_get_queue_status_invalid_supplier(self, enrichment_queue_manager):
        """Test getting status for invalid supplier"""
        status = enrichment_queue_manager.get_queue_status("INVALID")
        assert status == {}
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, enrichment_queue_manager):
        """Test getting status of specific task"""
        # Queue a task first
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-789",
            part_name="Status Test Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet", "fetch_pricing"]
        )
        
        status = enrichment_queue_manager.get_task_status(task_id)
        
        assert status is not None
        assert status["id"] == task_id
        assert status["part_id"] == "part-789"
        assert status["part_name"] == "Status Test Part"
        assert status["supplier_name"] == "MOUSER"
        assert status["status"] == "pending"
        assert status["progress_percentage"] == 0
        assert status["capabilities"] == ["fetch_datasheet", "fetch_pricing"]
        assert status["completed_capabilities"] == []
        assert status["failed_capabilities"] == []
        assert status["retry_count"] == 0
        assert "created_at" in status
    
    def test_get_task_status_invalid_task(self, enrichment_queue_manager):
        """Test getting status for invalid task"""
        status = enrichment_queue_manager.get_task_status("invalid-task-id")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, enrichment_queue_manager):
        """Test cancelling a task"""
        # Queue a task first
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-cancel",
            part_name="Cancel Test Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        
        # Cancel the task
        success = await enrichment_queue_manager.cancel_task(task_id)
        
        assert success is True
        
        # Check task status
        task = enrichment_queue_manager.task_registry[task_id]
        assert task.status == EnrichmentStatus.CANCELLED
        
        # Check it was removed from queue
        mouser_queue = enrichment_queue_manager.supplier_queues["MOUSER"]
        assert mouser_queue.queue_size == 0
    
    @pytest.mark.asyncio
    async def test_cancel_invalid_task(self, enrichment_queue_manager):
        """Test cancelling invalid task"""
        success = await enrichment_queue_manager.cancel_task("invalid-task-id")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, enrichment_queue_manager):
        """Test cancelling already completed task"""
        # Queue and manually mark as completed
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-completed",
            part_name="Completed Part",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        
        task = enrichment_queue_manager.task_registry[task_id]
        task.status = EnrichmentStatus.COMPLETED
        
        # Try to cancel
        success = await enrichment_queue_manager.cancel_task(task_id)
        assert success is False  # Cannot cancel completed task
    
    @pytest.mark.asyncio
    async def test_get_queue_statistics(self, enrichment_queue_manager):
        """Test getting comprehensive queue statistics"""
        # Add some tasks to different queues
        await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-1", part_name="Part 1", supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-2", part_name="Part 2", supplier_name="LCSC",
            capabilities=["fetch_image"]
        )
        
        stats = await enrichment_queue_manager.get_queue_statistics()
        
        assert stats["total_pending"] == 2
        assert stats["total_running"] == 0
        assert stats["total_completed"] == 0
        assert stats["total_failed"] == 0
        assert stats["total_queues"] == 3
        assert stats["active_queues"] == 0  # No queues processing yet
        assert "queue_details" in stats
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_on_queue(self, enrichment_queue_manager, mock_websocket_manager):
        """Test that WebSocket updates are sent when queuing tasks"""
        await enrichment_queue_manager.queue_part_enrichment(
            part_id="part-ws",
            part_name="WebSocket Test Part", 
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"]
        )
        
        # Should have broadcast queue status update
        mock_websocket_manager.broadcast_to_all.assert_called()


class TestEnrichmentPriorityAndStatus:
    """Test priority and status enums"""
    
    def test_enrichment_priority_values(self):
        """Test EnrichmentPriority enum values"""
        assert EnrichmentPriority.LOW == "low"
        assert EnrichmentPriority.NORMAL == "normal"
        assert EnrichmentPriority.HIGH == "high"
        assert EnrichmentPriority.URGENT == "urgent"
    
    def test_enrichment_status_values(self):
        """Test EnrichmentStatus enum values"""
        assert EnrichmentStatus.PENDING == "pending"
        assert EnrichmentStatus.RUNNING == "running"
        assert EnrichmentStatus.COMPLETED == "completed"
        assert EnrichmentStatus.FAILED == "failed"
        assert EnrichmentStatus.RATE_LIMITED == "rate_limited"
        assert EnrichmentStatus.CANCELLED == "cancelled"


@pytest.mark.asyncio
async def test_multiple_tasks_same_supplier(enrichment_queue_manager):
    """Test queuing multiple tasks for the same supplier"""
    task_ids = []
    
    # Queue multiple tasks for MOUSER
    for i in range(3):
        task_id = await enrichment_queue_manager.queue_part_enrichment(
            part_id=f"part-{i}",
            part_name=f"Part {i}",
            supplier_name="MOUSER",
            capabilities=["fetch_datasheet"],
            priority=EnrichmentPriority.NORMAL if i != 1 else EnrichmentPriority.HIGH
        )
        task_ids.append(task_id)
    
    # Check queue size
    mouser_queue = enrichment_queue_manager.supplier_queues["MOUSER"]
    assert mouser_queue.queue_size == 3
    
    # High priority task should be first
    next_task = mouser_queue.get_next_task()
    assert next_task.part_name == "Part 1"  # The high priority one
    
    # Other tasks should follow
    assert mouser_queue.queue_size == 2


@pytest.mark.asyncio
async def test_rate_limit_service_integration(enrichment_queue_manager, mock_rate_limit_service):
    """Test integration with rate limit service"""
    await enrichment_queue_manager.queue_part_enrichment(
        part_id="part-rate-limit",
        part_name="Rate Limit Test",
        supplier_name="MOUSER",
        capabilities=["fetch_datasheet"]
    )
    
    # Queue manager should have initialized with rate limit service
    assert enrichment_queue_manager.rate_limit_service == mock_rate_limit_service