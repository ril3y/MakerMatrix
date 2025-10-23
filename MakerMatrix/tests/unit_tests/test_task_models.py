import pytest
import json
from datetime import datetime, timedelta
from MakerMatrix.models.task_models import (
    TaskModel,
    TaskStatus,
    TaskPriority,
    TaskType,
    CreateTaskRequest,
    UpdateTaskRequest,
    TaskFilterRequest,
)


class TestTaskModel:
    """Test the TaskModel class"""

    def test_task_creation(self):
        """Test basic task creation"""
        task = TaskModel(task_type=TaskType.CSV_ENRICHMENT, name="Test Task", description="A test task")

        assert task.task_type == TaskType.CSV_ENRICHMENT
        assert task.name == "Test Task"
        assert task.description == "A test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.progress_percentage == 0
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.id is not None  # UUID should be generated

    def test_input_data_handling(self):
        """Test input data JSON serialization"""
        task = TaskModel(task_type=TaskType.PRICE_UPDATE, name="Price Update")

        test_data = {"parts": [1, 2, 3], "source": "test_api", "settings": {"timeout": 30}}

        task.set_input_data(test_data)
        assert task.input_data is not None
        assert task.get_input_data() == test_data

        # Test with None
        task.set_input_data(None)
        assert task.input_data is None
        assert task.get_input_data() == {}

    def test_result_data_handling(self):
        """Test result data JSON serialization"""
        task = TaskModel(task_type=TaskType.DATABASE_CLEANUP, name="DB Cleanup")

        result_data = {"records_deleted": 150, "space_freed": "50MB", "duration": 45.2}

        task.set_result_data(result_data)
        assert task.result_data is not None
        assert task.get_result_data() == result_data

    def test_dependencies_handling(self):
        """Test task dependencies"""
        task = TaskModel(task_type=TaskType.DATA_SYNC, name="Data Sync")

        dep_tasks = ["task-1", "task-2", "task-3"]
        task.set_depends_on(dep_tasks)
        assert task.depends_on_task_ids is not None
        assert task.get_depends_on() == dep_tasks

        # Test with empty list
        task.set_depends_on([])
        assert task.depends_on_task_ids is None
        assert task.get_depends_on() == []

    def test_is_ready_to_run(self):
        """Test ready-to-run logic"""
        task = TaskModel(task_type=TaskType.FILE_DOWNLOAD, name="Download Files")

        # Pending task should be ready
        assert task.is_ready_to_run() is True

        # Running task should not be ready
        task.status = TaskStatus.RUNNING
        assert task.is_ready_to_run() is False

        # Completed task should not be ready
        task.status = TaskStatus.COMPLETED
        assert task.is_ready_to_run() is False

        # Scheduled future task should not be ready
        task.status = TaskStatus.PENDING
        task.scheduled_at = datetime.utcnow() + timedelta(hours=1)
        assert task.is_ready_to_run() is False

        # Scheduled past task should be ready
        task.scheduled_at = datetime.utcnow() - timedelta(minutes=1)
        assert task.is_ready_to_run() is True

    def test_can_retry(self):
        """Test retry logic"""
        task = TaskModel(task_type=TaskType.PART_VALIDATION, name="Validate Parts", max_retries=3)

        # Failed task with retries available
        task.status = TaskStatus.FAILED
        task.retry_count = 1
        assert task.can_retry() is True

        # Failed task with no retries left
        task.retry_count = 3
        assert task.can_retry() is False

        # Completed task should not retry
        task.status = TaskStatus.COMPLETED
        task.retry_count = 0
        assert task.can_retry() is False

    def test_to_dict(self):
        """Test dictionary conversion"""
        task = TaskModel(
            task_type=TaskType.INVENTORY_AUDIT,
            name="Inventory Audit",
            description="Check inventory levels",
            priority=TaskPriority.HIGH,
            created_by_user_id="user-123",
            related_entity_type="inventory",
            related_entity_id="inv-456",
        )

        test_input = {"check_level": "full"}
        test_result = {"items_checked": 500}
        task.set_input_data(test_input)
        task.set_result_data(test_result)

        result_dict = task.to_dict()

        assert result_dict["id"] == task.id
        assert result_dict["task_type"] == TaskType.INVENTORY_AUDIT
        assert result_dict["name"] == "Inventory Audit"
        assert result_dict["description"] == "Check inventory levels"
        assert result_dict["priority"] == TaskPriority.HIGH
        assert result_dict["input_data"] == test_input
        assert result_dict["result_data"] == test_result
        assert result_dict["created_by_user_id"] == "user-123"
        assert result_dict["related_entity_type"] == "inventory"
        assert result_dict["related_entity_id"] == "inv-456"


class TestTaskRequestModels:
    """Test task request models"""

    def test_create_task_request(self):
        """Test CreateTaskRequest model"""
        request = CreateTaskRequest(
            task_type=TaskType.CSV_ENRICHMENT,
            name="Enrich CSV Data",
            description="Enrich parts from CSV import",
            priority=TaskPriority.HIGH,
            input_data={"parts_count": 100},
            max_retries=5,
            timeout_seconds=600,
            related_entity_type="csv_import",
            related_entity_id="import-123",
        )

        assert request.task_type == TaskType.CSV_ENRICHMENT
        assert request.name == "Enrich CSV Data"
        assert request.priority == TaskPriority.HIGH
        assert request.input_data == {"parts_count": 100}
        assert request.max_retries == 5
        assert request.timeout_seconds == 600

    def test_update_task_request(self):
        """Test UpdateTaskRequest model"""
        request = UpdateTaskRequest(
            status=TaskStatus.RUNNING,
            progress_percentage=75,
            current_step="Processing step 3 of 4",
            result_data={"processed": 75},
            error_message=None,
        )

        assert request.status == TaskStatus.RUNNING
        assert request.progress_percentage == 75
        assert request.current_step == "Processing step 3 of 4"
        assert request.result_data == {"processed": 75}
        assert request.error_message is None

    def test_task_filter_request(self):
        """Test TaskFilterRequest model"""
        request = TaskFilterRequest(
            status=[TaskStatus.PENDING, TaskStatus.RUNNING],
            task_type=[TaskType.CSV_ENRICHMENT],
            priority=[TaskPriority.HIGH, TaskPriority.URGENT],
            created_by_user_id="user-123",
            limit=25,
            offset=50,
            order_by="priority",
            order_desc=True,
        )

        assert request.status == [TaskStatus.PENDING, TaskStatus.RUNNING]
        assert request.task_type == [TaskType.CSV_ENRICHMENT]
        assert request.priority == [TaskPriority.HIGH, TaskPriority.URGENT]
        assert request.created_by_user_id == "user-123"
        assert request.limit == 25
        assert request.offset == 50
        assert request.order_by == "priority"
        assert request.order_desc is True

    def test_task_filter_defaults(self):
        """Test TaskFilterRequest default values"""
        request = TaskFilterRequest()

        assert request.status is None
        assert request.task_type is None
        assert request.priority is None
        assert request.limit == 50
        assert request.offset == 0
        assert request.order_by == "created_at"
        assert request.order_desc is True


class TestTaskEnums:
    """Test task enumerations"""

    def test_task_status_enum(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.RETRY == "retry"

    def test_task_priority_enum(self):
        """Test TaskPriority enum values"""
        assert TaskPriority.LOW == "low"
        assert TaskPriority.NORMAL == "normal"
        assert TaskPriority.HIGH == "high"
        assert TaskPriority.URGENT == "urgent"

    def test_task_type_enum(self):
        """Test TaskType enum values"""
        assert TaskType.CSV_ENRICHMENT == "csv_enrichment"
        assert TaskType.PRICE_UPDATE == "price_update"
        assert TaskType.DATABASE_CLEANUP == "database_cleanup"
        assert TaskType.FILE_DOWNLOAD == "file_download"
        assert TaskType.DATA_SYNC == "data_sync"
        assert TaskType.INVENTORY_AUDIT == "inventory_audit"
        assert TaskType.PART_VALIDATION == "part_validation"
        assert TaskType.BACKUP_CREATION == "backup_creation"
        assert TaskType.EMAIL_NOTIFICATION == "email_notification"
        assert TaskType.REPORT_GENERATION == "report_generation"
