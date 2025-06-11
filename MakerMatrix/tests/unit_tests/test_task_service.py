import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from MakerMatrix.services.task_service import TaskService, task_service
from MakerMatrix.models.task_models import (
    TaskModel, TaskStatus, TaskPriority, TaskType,
    CreateTaskRequest, UpdateTaskRequest, TaskFilterRequest
)


@pytest.fixture
def service():
    """Create a fresh TaskService instance for testing"""
    return TaskService()


@pytest.fixture
def mock_session():
    """Mock database session"""
    with patch('MakerMatrix.services.task_service.get_session') as mock_get_session:
        mock_session = Mock()
        mock_get_session.return_value.__next__ = Mock(return_value=mock_session)
        yield mock_session


class TestTaskServiceCRUD:
    """Test CRUD operations for tasks"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, service, mock_session):
        """Test task creation"""
        request = CreateTaskRequest(
            task_type=TaskType.CSV_ENRICHMENT,
            name="Test Enrichment",
            description="Test CSV enrichment task",
            priority=TaskPriority.HIGH,
            input_data={"parts_count": 50},
            max_retries=5
        )
        
        # Mock the database operations
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        task = await service.create_task(request, user_id="test-user")
        
        assert task.task_type == TaskType.CSV_ENRICHMENT
        assert task.name == "Test Enrichment"
        assert task.description == "Test CSV enrichment task"
        assert task.priority == TaskPriority.HIGH
        assert task.created_by_user_id == "test-user"
        assert task.max_retries == 5
        assert task.get_input_data() == {"parts_count": 50}
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task(self, service, mock_session):
        """Test getting a task by ID"""
        task_id = "test-task-id"
        mock_task = TaskModel(
            task_type=TaskType.PRICE_UPDATE,
            name="Price Update Task"
        )
        mock_session.get.return_value = mock_task
        
        result = await service.get_task(task_id)
        
        assert result == mock_task
        mock_session.get.assert_called_once_with(TaskModel, task_id)
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, service, mock_session):
        """Test getting a non-existent task"""
        mock_session.get.return_value = None
        
        result = await service.get_task("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_task(self, service, mock_session):
        """Test updating a task"""
        task_id = "test-task-id"
        mock_task = TaskModel(
            task_type=TaskType.DATABASE_CLEANUP,
            name="Cleanup Task",
            status=TaskStatus.PENDING,
            progress_percentage=0
        )
        mock_session.get.return_value = mock_task
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        update_request = UpdateTaskRequest(
            status=TaskStatus.RUNNING,
            progress_percentage=50,
            current_step="Halfway done"
        )
        
        result = await service.update_task(task_id, update_request)
        
        assert result.status == TaskStatus.RUNNING
        assert result.progress_percentage == 50
        assert result.current_step == "Halfway done"
        assert result.started_at is not None  # Should be set when status becomes RUNNING
    
    @pytest.mark.asyncio
    async def test_update_task_completion(self, service, mock_session):
        """Test updating task to completed status"""
        mock_task = TaskModel(
            task_type=TaskType.FILE_DOWNLOAD,
            name="Download Task",
            status=TaskStatus.RUNNING
        )
        mock_session.get.return_value = mock_task
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        update_request = UpdateTaskRequest(
            status=TaskStatus.COMPLETED,
            progress_percentage=100,
            result_data={"files_downloaded": 5}
        )
        
        result = await service.update_task("task-id", update_request)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.completed_at is not None
        assert result.get_result_data() == {"files_downloaded": 5}
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, service, mock_session):
        """Test cancelling a task"""
        task_id = "test-task-id"
        
        # Mock running task
        mock_async_task = Mock()
        mock_async_task.cancel = Mock()
        service.running_tasks[task_id] = mock_async_task
        
        # Mock database task
        mock_task = TaskModel(
            task_type=TaskType.DATA_SYNC,
            name="Sync Task",
            status=TaskStatus.RUNNING
        )
        mock_session.get.return_value = mock_task
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        result = await service.cancel_task(task_id)
        
        assert result is True
        assert task_id not in service.running_tasks
        mock_async_task.cancel.assert_called_once()
        assert mock_task.status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_retry_task(self, service, mock_session):
        """Test retrying a failed task"""
        task_id = "test-task-id"
        mock_task = TaskModel(
            task_type=TaskType.PART_VALIDATION,
            name="Validation Task",
            status=TaskStatus.FAILED,
            retry_count=1,
            max_retries=3,
            error_message="Previous error"
        )
        mock_session.get.return_value = mock_task
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        result = await service.retry_task(task_id)
        
        assert result is True
        assert mock_task.status == TaskStatus.PENDING
        assert mock_task.retry_count == 2
        assert mock_task.error_message is None
        assert mock_task.started_at is None
        assert mock_task.completed_at is None
    
    @pytest.mark.asyncio
    async def test_retry_task_max_retries(self, service, mock_session):
        """Test retrying a task that has reached max retries"""
        mock_task = TaskModel(
            task_type=TaskType.INVENTORY_AUDIT,
            name="Audit Task",
            status=TaskStatus.FAILED,
            retry_count=3,
            max_retries=3
        )
        mock_session.get.return_value = mock_task
        
        result = await service.retry_task("task-id")
        
        assert result is False


class TestTaskServiceWorker:
    """Test task worker functionality"""
    
    @pytest.mark.asyncio
    async def test_start_stop_worker(self, service):
        """Test starting and stopping the worker"""
        assert service.is_worker_running is False
        
        # Start worker in background
        worker_task = asyncio.create_task(service.start_worker())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        assert service.is_worker_running is True
        
        # Stop worker
        await service.stop_worker()
        assert service.is_worker_running is False
        
        # Cancel the worker task
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_process_pending_tasks(self, service, mock_session):
        """Test processing pending tasks"""
        # Mock pending tasks
        pending_task = TaskModel(
            task_type=TaskType.CSV_ENRICHMENT,
            name="Enrichment Task",
            status=TaskStatus.PENDING
        )
        pending_task.id = "pending-task-1"
        
        mock_result = Mock()
        mock_result.all.return_value = [pending_task]
        mock_session.exec.return_value = mock_result
        
        # Mock the _start_task method
        service._start_task = AsyncMock()
        
        await service._process_pending_tasks()
        
        service._start_task.assert_called_once_with(pending_task)
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, service):
        """Test successful task execution"""
        task = TaskModel(
            task_type=TaskType.CSV_ENRICHMENT,
            name="Test Task"
        )
        task.id = "test-task"
        
        # Mock the handler
        mock_handler = AsyncMock()
        service.task_handlers[TaskType.CSV_ENRICHMENT] = mock_handler
        
        # Mock update_task
        service.update_task = AsyncMock()
        
        await service._execute_task(task)
        
        # Verify handler was called
        mock_handler.assert_called_once_with(task)
        
        # Verify status updates
        assert service.update_task.call_count >= 2  # At least start and completion
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(self, service):
        """Test task execution failure"""
        task = TaskModel(
            task_type=TaskType.PRICE_UPDATE,
            name="Failing Task"
        )
        task.id = "failing-task"
        
        # Mock the handler to raise an exception
        mock_handler = AsyncMock(side_effect=Exception("Test error"))
        service.task_handlers[TaskType.PRICE_UPDATE] = mock_handler
        
        # Mock update_task
        service.update_task = AsyncMock()
        
        await service._execute_task(task)
        
        # Verify failure was handled
        mock_handler.assert_called_once_with(task)
        
        # Check that task was marked as failed
        update_calls = service.update_task.call_args_list
        failed_call = next((call for call in update_calls 
                          if call[0][1].status == TaskStatus.FAILED), None)
        assert failed_call is not None
    
    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, service):
        """Test task execution timeout"""
        task = TaskModel(
            task_type=TaskType.DATABASE_CLEANUP,
            name="Slow Task",
            timeout_seconds=1
        )
        task.id = "slow-task"
        
        # Mock handler that takes too long
        async def slow_handler(task):
            await asyncio.sleep(2)
        
        service.task_handlers[TaskType.DATABASE_CLEANUP] = slow_handler
        service.update_task = AsyncMock()
        
        await service._execute_task(task)
        
        # Check that task was marked as failed due to timeout
        update_calls = service.update_task.call_args_list
        failed_call = next((call for call in update_calls 
                          if call[0][1].status == TaskStatus.FAILED), None)
        assert failed_call is not None
        assert "timed out" in failed_call[0][1].error_message


class TestTaskHandlers:
    """Test built-in task handlers"""
    
    @pytest.mark.asyncio
    async def test_csv_enrichment_handler(self, service):
        """Test CSV enrichment handler"""
        task = TaskModel(
            task_type=TaskType.CSV_ENRICHMENT,
            name="CSV Enrichment"
        )
        task.id = "csv-task"
        
        # Set input data
        enrichment_queue = [
            {"part_data": {"part_name": "Part 1"}},
            {"part_data": {"part_name": "Part 2"}},
            {"part_data": {"part_name": "Part 3"}}
        ]
        task.set_input_data({"enrichment_queue": enrichment_queue})
        
        # Mock update_task
        service.update_task = AsyncMock()
        
        await service._handle_csv_enrichment(task)
        
        # Verify progress updates
        assert service.update_task.call_count >= 2  # At least start and end
        
        # Check final update
        final_call = service.update_task.call_args_list[-1]
        assert final_call[0][1].progress_percentage == 100
        assert "Enrichment completed" in final_call[0][1].current_step
    
    @pytest.mark.asyncio
    async def test_price_update_handler(self, service):
        """Test price update handler"""
        task = TaskModel(
            task_type=TaskType.PRICE_UPDATE,
            name="Price Update"
        )
        task.id = "price-task"
        
        service.update_task = AsyncMock()
        
        await service._handle_price_update(task)
        
        # Verify progress updates
        assert service.update_task.call_count >= 3  # Multiple progress steps
        
        # Check final result
        final_call = service.update_task.call_args_list[-1]
        assert final_call[0][1].progress_percentage == 100
        assert final_call[0][1].result_data == {"parts_updated": 150}
    
    @pytest.mark.asyncio
    async def test_database_cleanup_handler(self, service):
        """Test database cleanup handler"""
        task = TaskModel(
            task_type=TaskType.DATABASE_CLEANUP,
            name="DB Cleanup"
        )
        task.id = "cleanup-task"
        
        service.update_task = AsyncMock()
        
        await service._handle_database_cleanup(task)
        
        # Verify all cleanup steps were executed
        assert service.update_task.call_count == 5  # One for each cleanup step
        
        # Verify final progress
        final_call = service.update_task.call_args_list[-1]
        assert final_call[0][1].progress_percentage == 100


class TestTaskServiceFiltering:
    """Test task filtering functionality"""
    
    @pytest.mark.asyncio
    async def test_get_tasks_with_filters(self, service, mock_session):
        """Test getting tasks with various filters"""
        filter_request = TaskFilterRequest(
            status=[TaskStatus.PENDING, TaskStatus.RUNNING],
            task_type=[TaskType.CSV_ENRICHMENT],
            priority=[TaskPriority.HIGH],
            created_by_user_id="test-user",
            limit=10,
            offset=0
        )
        
        # Mock query result
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result
        
        await service.get_tasks(filter_request)
        
        # Verify query was executed
        mock_session.exec.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_tasks_no_filters(self, service, mock_session):
        """Test getting tasks without filters"""
        filter_request = TaskFilterRequest()
        
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result
        
        await service.get_tasks(filter_request)
        
        mock_session.exec.assert_called_once()


class TestTaskServiceSingleton:
    """Test the global task service singleton"""
    
    def test_singleton_instance(self):
        """Test that task_service is a TaskService instance"""
        assert isinstance(task_service, TaskService)
        assert hasattr(task_service, 'create_task')
        assert hasattr(task_service, 'start_worker')
        assert hasattr(task_service, 'task_handlers')
    
    def test_handlers_registered(self):
        """Test that built-in handlers are registered"""
        assert TaskType.CSV_ENRICHMENT in task_service.task_handlers
        assert TaskType.PRICE_UPDATE in task_service.task_handlers
        assert TaskType.DATABASE_CLEANUP in task_service.task_handlers
        assert TaskType.FILE_DOWNLOAD in task_service.task_handlers
        assert TaskType.DATA_SYNC in task_service.task_handlers
        assert TaskType.INVENTORY_AUDIT in task_service.task_handlers
        assert TaskType.PART_VALIDATION in task_service.task_handlers