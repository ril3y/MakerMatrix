import pytest
import asyncio
from datetime import datetime, timedelta
from sqlmodel import Session, select
from MakerMatrix.database.db import engine, get_session
from MakerMatrix.models.task_models import (
    TaskModel,
    TaskStatus,
    TaskPriority,
    TaskType,
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskFilterRequest,
)
from MakerMatrix.services.system.task_service import TaskService, task_service


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def clean_tasks(db_session):
    """Clean up tasks before and after tests"""
    # Clean before
    db_session.exec(select(TaskModel)).all()
    for task in db_session.exec(select(TaskModel)).all():
        db_session.delete(task)
    db_session.commit()

    yield

    # Clean after
    for task in db_session.exec(select(TaskModel)).all():
        db_session.delete(task)
    db_session.commit()


@pytest.mark.integration
class TestTaskSystemIntegration:
    """Integration tests for the task management system"""

    @pytest.mark.asyncio
    async def test_task_lifecycle_integration(self, clean_tasks):
        """Test complete task lifecycle with database operations"""
        service = TaskService()

        # Create a task
        request = CreateTaskRequest(
            task_type=TaskType.DATABASE_CLEANUP,
            name="Integration Test Cleanup",
            description="Test database cleanup task",
            priority=TaskPriority.HIGH,
            input_data={"cleanup_type": "full"},
            max_retries=2,
        )

        task = await service.create_task(request, user_id="test-user")

        # Verify task was created
        assert task.id is not None
        assert task.status == TaskStatus.PENDING

        # Get the task back from database
        retrieved_task = await service.get_task(task.id)
        assert retrieved_task is not None
        assert retrieved_task.name == "Integration Test Cleanup"
        assert retrieved_task.get_input_data() == {"cleanup_type": "full"}

        # Update the task
        update_request = UpdateTaskRequest(
            status=TaskStatus.RUNNING, progress_percentage=50, current_step="Halfway through cleanup"
        )

        updated_task = await service.update_task(task.id, update_request)
        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.progress_percentage == 50
        assert updated_task.started_at is not None

        # Complete the task
        completion_request = UpdateTaskRequest(
            status=TaskStatus.COMPLETED,
            progress_percentage=100,
            current_step="Cleanup completed",
            result_data={"records_cleaned": 150},
        )

        completed_task = await service.update_task(task.id, completion_request)
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.completed_at is not None
        assert completed_task.get_result_data() == {"records_cleaned": 150}

    @pytest.mark.asyncio
    async def test_task_filtering_integration(self, clean_tasks):
        """Test task filtering with real database"""
        service = TaskService()

        # Create multiple tasks
        tasks = []

        # High priority CSV enrichment task
        task1 = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.CSV_ENRICHMENT, name="High Priority Enrichment", priority=TaskPriority.HIGH
            ),
            user_id="user1",
        )
        tasks.append(task1)

        # Normal priority price update task
        task2 = await service.create_task(
            CreateTaskRequest(task_type=TaskType.PRICE_UPDATE, name="Price Update", priority=TaskPriority.NORMAL),
            user_id="user2",
        )
        tasks.append(task2)

        # Low priority cleanup task
        task3 = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.DATABASE_CLEANUP, name="Low Priority Cleanup", priority=TaskPriority.LOW
            ),
            user_id="user1",
        )
        tasks.append(task3)

        # Mark one as running
        await service.update_task(task2.id, UpdateTaskRequest(status=TaskStatus.RUNNING))

        # Test filtering by status
        filter_request = TaskFilterRequest(status=[TaskStatus.PENDING], limit=10)
        pending_tasks = await service.get_tasks(filter_request)
        assert len(pending_tasks) == 2  # task1 and task3

        # Test filtering by priority
        filter_request = TaskFilterRequest(priority=[TaskPriority.HIGH], limit=10)
        high_priority_tasks = await service.get_tasks(filter_request)
        assert len(high_priority_tasks) == 1
        assert high_priority_tasks[0].id == task1.id

        # Test filtering by user
        filter_request = TaskFilterRequest(created_by_user_id="user1", limit=10)
        user1_tasks = await service.get_tasks(filter_request)
        assert len(user1_tasks) == 2  # task1 and task3

        # Test filtering by task type
        filter_request = TaskFilterRequest(task_type=[TaskType.CSV_ENRICHMENT, TaskType.PRICE_UPDATE], limit=10)
        specific_type_tasks = await service.get_tasks(filter_request)
        assert len(specific_type_tasks) == 2  # task1 and task2

    @pytest.mark.asyncio
    async def test_task_retry_integration(self, clean_tasks):
        """Test task retry functionality with database"""
        service = TaskService()

        # Create a task that will fail
        task = await service.create_task(
            CreateTaskRequest(task_type=TaskType.PART_VALIDATION, name="Failing Task", max_retries=3)
        )

        # Mark it as failed
        await service.update_task(task.id, UpdateTaskRequest(status=TaskStatus.FAILED, error_message="Test failure"))

        # Retry the task
        retry_success = await service.retry_task(task.id)
        assert retry_success is True

        # Verify task was reset
        retried_task = await service.get_task(task.id)
        assert retried_task.status == TaskStatus.PENDING
        assert retried_task.retry_count == 1
        assert retried_task.error_message is None
        assert retried_task.started_at is None
        assert retried_task.completed_at is None

        # Fail it again and retry until max retries
        for i in range(2, 4):  # 2 more times to reach max retries
            await service.update_task(
                task.id, UpdateTaskRequest(status=TaskStatus.FAILED, error_message=f"Test failure {i}")
            )
            retry_success = await service.retry_task(task.id)
            assert retry_success is True

            retried_task = await service.get_task(task.id)
            assert retried_task.retry_count == i

        # Now it should be at max retries, so retry should fail
        await service.update_task(task.id, UpdateTaskRequest(status=TaskStatus.FAILED, error_message="Final failure"))
        retry_success = await service.retry_task(task.id)
        assert retry_success is False

    @pytest.mark.asyncio
    async def test_task_worker_integration(self, clean_tasks):
        """Test task worker with real tasks"""
        service = TaskService()

        # Create a task
        task = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.CSV_ENRICHMENT,
                name="Worker Test Task",
                input_data={
                    "enrichment_queue": [
                        {"part_data": {"part_name": "Test Part 1"}},
                        {"part_data": {"part_name": "Test Part 2"}},
                    ]
                },
            )
        )

        # Start the worker
        worker_task = asyncio.create_task(service.start_worker())

        # Wait for task to be processed
        max_wait = 10  # seconds
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < max_wait:
            current_task = await service.get_task(task.id)
            if current_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            await asyncio.sleep(0.1)

        # Stop the worker
        await service.stop_worker()
        worker_task.cancel()

        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Verify task was processed
        final_task = await service.get_task(task.id)
        assert final_task.status == TaskStatus.COMPLETED
        assert final_task.progress_percentage == 100
        assert final_task.started_at is not None
        assert final_task.completed_at is not None


@pytest.mark.integration
class TestCSVEnrichmentTaskIntegration:
    """Integration tests for CSV enrichment with task system"""

    @pytest.mark.asyncio
    async def test_csv_enrichment_creates_tasks(self, clean_tasks):
        """Test that CSV import creates background enrichment tasks"""
        # This would test the integration between CSV import and task system
        # For now, we'll test the task creation part

        service = TaskService()

        # Simulate creating a CSV enrichment task
        enrichment_queue = [
            {
                "part_id": "part-1",
                "part_data": {
                    "part_name": "Test Resistor",
                    "additional_properties": {
                        "lcsc_part_number": "C123456",
                        "needs_enrichment": True,
                        "enrichment_source": "LCSC",
                    },
                },
                "action": "create",
            },
            {
                "part_id": "part-2",
                "part_data": {
                    "part_name": "Test Capacitor",
                    "additional_properties": {
                        "lcsc_part_number": "C789012",
                        "needs_enrichment": True,
                        "enrichment_source": "LCSC",
                    },
                },
                "action": "create",
            },
        ]

        # Create CSV enrichment task
        task = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.CSV_ENRICHMENT,
                name="CSV Import Enrichment",
                description="Background enrichment for CSV imported parts",
                priority=TaskPriority.NORMAL,
                input_data={"enrichment_queue": enrichment_queue},
                related_entity_type="csv_import",
                related_entity_id="import-123",
            )
        )

        assert task.task_type == TaskType.CSV_ENRICHMENT
        assert task.related_entity_type == "csv_import"
        assert task.related_entity_id == "import-123"

        input_data = task.get_input_data()
        assert "enrichment_queue" in input_data
        assert len(input_data["enrichment_queue"]) == 2

    @pytest.mark.asyncio
    async def test_task_dependencies(self, clean_tasks):
        """Test task dependencies functionality"""
        service = TaskService()

        # Create a parent task
        parent_task = await service.create_task(
            CreateTaskRequest(task_type=TaskType.CSV_ENRICHMENT, name="Parent Enrichment Task")
        )

        # Create dependent tasks
        child_task1 = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.FILE_DOWNLOAD,
                name="Download Datasheets",
                parent_task_id=parent_task.id,
                depends_on_task_ids=[parent_task.id],
            )
        )

        child_task2 = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.PART_VALIDATION,
                name="Validate Parts",
                parent_task_id=parent_task.id,
                depends_on_task_ids=[parent_task.id],
            )
        )

        # Verify relationships
        assert child_task1.parent_task_id == parent_task.id
        assert child_task2.parent_task_id == parent_task.id
        assert child_task1.get_depends_on() == [parent_task.id]
        assert child_task2.get_depends_on() == [parent_task.id]

    @pytest.mark.asyncio
    async def test_scheduled_tasks(self, clean_tasks):
        """Test scheduled task execution"""
        service = TaskService()

        # Create a task scheduled for the future
        future_time = datetime.utcnow() + timedelta(hours=1)
        future_task = await service.create_task(
            CreateTaskRequest(task_type=TaskType.PRICE_UPDATE, name="Scheduled Price Update", scheduled_at=future_time)
        )

        # Should not be ready to run yet
        assert not future_task.is_ready_to_run()

        # Create a task scheduled for the past (should run immediately)
        past_time = datetime.utcnow() - timedelta(minutes=1)
        past_task = await service.create_task(
            CreateTaskRequest(
                task_type=TaskType.DATABASE_CLEANUP, name="Past Scheduled Cleanup", scheduled_at=past_time
            )
        )

        # Should be ready to run
        assert past_task.is_ready_to_run()


@pytest.mark.integration
class TestTaskSystemPerformance:
    """Performance tests for the task system"""

    @pytest.mark.asyncio
    async def test_bulk_task_creation(self, clean_tasks):
        """Test creating many tasks efficiently"""
        service = TaskService()

        num_tasks = 50
        start_time = datetime.utcnow()

        # Create many tasks
        tasks = []
        for i in range(num_tasks):
            task = await service.create_task(
                CreateTaskRequest(
                    task_type=TaskType.PART_VALIDATION,
                    name=f"Bulk Task {i}",
                    input_data={"batch_id": f"batch-{i // 10}"},
                )
            )
            tasks.append(task)

        creation_time = (datetime.utcnow() - start_time).total_seconds()

        # Should be able to create 50 tasks in reasonable time
        assert creation_time < 5.0  # Less than 5 seconds
        assert len(tasks) == num_tasks

        # Verify all tasks were created correctly
        for i, task in enumerate(tasks):
            assert task.name == f"Bulk Task {i}"
            assert task.get_input_data()["batch_id"] == f"batch-{i // 10}"

    @pytest.mark.asyncio
    async def test_concurrent_task_updates(self, clean_tasks):
        """Test concurrent task updates"""
        service = TaskService()

        # Create a task
        task = await service.create_task(CreateTaskRequest(task_type=TaskType.DATA_SYNC, name="Concurrent Update Test"))

        # Update the task concurrently
        async def update_progress(progress):
            await service.update_task(
                task.id, UpdateTaskRequest(progress_percentage=progress, current_step=f"Step {progress}")
            )

        # Run multiple updates concurrently
        update_tasks = [update_progress(25), update_progress(50), update_progress(75), update_progress(100)]

        await asyncio.gather(*update_tasks)

        # Verify final state
        final_task = await service.get_task(task.id)
        assert final_task.progress_percentage in [25, 50, 75, 100]  # One of the values
