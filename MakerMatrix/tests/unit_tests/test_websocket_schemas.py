"""
Tests for WebSocket Schemas

Tests for the unified WebSocket message schemas and helper functions.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from MakerMatrix.schemas.websocket_schemas import (
    WebSocketMessage,
    WebSocketEventType,
    ImportProgressData,
    EnrichmentProgressData,
    RateLimitData,
    TaskProgressData,
    NotificationData,
    ToastData,
    ConnectionStatusData,
    create_import_progress_message,
    create_enrichment_progress_message,
    create_rate_limit_update_message,
    create_notification_message,
    create_toast_message,
)


class TestWebSocketEventType:
    """Test WebSocket event type enum"""

    def test_all_event_types_defined(self):
        """Test that all expected event types are defined"""
        expected_types = [
            "ping",
            "pong",
            "error",
            "connection_status",
            "import_started",
            "import_progress",
            "import_completed",
            "import_failed",
            "enrichment_started",
            "enrichment_progress",
            "enrichment_completed",
            "enrichment_failed",
            "rate_limit_update",
            "rate_limit_warning",
            "rate_limit_exceeded",
            "task_created",
            "task_updated",
            "task_completed",
            "task_failed",
            "supplier_status_changed",
            "supplier_error",
            "notification",
            "toast",
        ]

        for event_type in expected_types:
            assert hasattr(WebSocketEventType, event_type.upper().replace("-", "_"))

    def test_event_type_values(self):
        """Test that event type values are correct"""
        assert WebSocketEventType.PING == "ping"
        assert WebSocketEventType.IMPORT_PROGRESS == "import_progress"
        assert WebSocketEventType.ENRICHMENT_PROGRESS == "enrichment_progress"
        assert WebSocketEventType.RATE_LIMIT_UPDATE == "rate_limit_update"
        assert WebSocketEventType.NOTIFICATION == "notification"


class TestWebSocketMessage:
    """Test base WebSocket message"""

    def test_create_basic_message(self):
        """Test creating a basic WebSocket message"""
        message = WebSocketMessage(type=WebSocketEventType.PING, data={"test": "value"})

        assert message.type == WebSocketEventType.PING
        assert message.data == {"test": "value"}
        assert isinstance(message.timestamp, datetime)
        assert message.correlation_id is None
        assert message.metadata is None

    def test_create_message_with_correlation_id(self):
        """Test creating message with correlation ID"""
        message = WebSocketMessage(type=WebSocketEventType.PONG, correlation_id="test-123", data={"response": "ok"})

        assert message.correlation_id == "test-123"
        assert message.data == {"response": "ok"}

    def test_create_message_with_metadata(self):
        """Test creating message with metadata"""
        metadata = {"user_id": "user-123", "session_id": "session-456"}
        message = WebSocketMessage(type=WebSocketEventType.NOTIFICATION, data={"title": "Test"}, metadata=metadata)

        assert message.metadata == metadata
        assert message.data == {"title": "Test"}


class TestImportProgressData:
    """Test import progress data schema"""

    def test_valid_import_progress_data(self):
        """Test creating valid import progress data"""
        data = ImportProgressData(
            task_id="task-123",
            filename="test.csv",
            parser_type="mouser",
            progress_percentage=50,
            current_step="Processing parts",
            parts_processed=25,
            total_parts=50,
        )

        assert data.task_id == "task-123"
        assert data.filename == "test.csv"
        assert data.parser_type == "mouser"
        assert data.progress_percentage == 50
        assert data.current_step == "Processing parts"
        assert data.parts_processed == 25
        assert data.total_parts == 50
        assert data.errors == []

    def test_invalid_progress_percentage(self):
        """Test validation of progress percentage"""
        with pytest.raises(ValidationError) as exc_info:
            ImportProgressData(
                task_id="task-123",
                filename="test.csv",
                parser_type="mouser",
                progress_percentage=150,  # Invalid: > 100
                current_step="Processing",
                parts_processed=10,
                total_parts=10,
            )

        assert "less than or equal to 100" in str(exc_info.value)

    def test_negative_parts_processed(self):
        """Test validation of negative parts processed"""
        with pytest.raises(ValidationError) as exc_info:
            ImportProgressData(
                task_id="task-123",
                filename="test.csv",
                parser_type="mouser",
                progress_percentage=0,
                current_step="Starting",
                parts_processed=-1,  # Invalid: negative
                total_parts=10,
            )

        assert "greater than or equal to 0" in str(exc_info.value)


class TestEnrichmentProgressData:
    """Test enrichment progress data schema"""

    def test_valid_enrichment_progress_data(self):
        """Test creating valid enrichment progress data"""
        data = EnrichmentProgressData(
            supplier_name="MOUSER",
            part_id="part-123",
            part_name="Test Resistor",
            capabilities_completed=["fetch_datasheet", "fetch_image"],
            capabilities_total=["fetch_datasheet", "fetch_image", "fetch_pricing"],
            progress_percentage=67,
            current_capability="fetch_pricing",
        )

        assert data.supplier_name == "MOUSER"
        assert data.part_id == "part-123"
        assert data.part_name == "Test Resistor"
        assert len(data.capabilities_completed) == 2
        assert len(data.capabilities_total) == 3
        assert data.progress_percentage == 67
        assert data.current_capability == "fetch_pricing"

    def test_enrichment_progress_with_task_id(self):
        """Test enrichment progress with task ID"""
        data = EnrichmentProgressData(
            task_id="task-456",
            supplier_name="LCSC",
            part_id="part-789",
            part_name="Test Capacitor",
            capabilities_completed=["fetch_details"],
            capabilities_total=["fetch_details", "fetch_image"],
            progress_percentage=50,
        )

        assert data.task_id == "task-456"
        assert data.supplier_name == "LCSC"


class TestRateLimitData:
    """Test rate limit data schema"""

    def test_valid_rate_limit_data(self):
        """Test creating valid rate limit data"""
        now = datetime.now(timezone.utc)
        data = RateLimitData(
            supplier_name="MOUSER",
            current_usage={"per_minute": 15, "per_hour": 500, "per_day": 750},
            limits={"per_minute": 30, "per_hour": 1000, "per_day": 1000},
            usage_percentage={"per_minute": 50.0, "per_hour": 50.0, "per_day": 75.0},
            next_reset={"per_minute": now, "per_hour": now, "per_day": now},
            queue_size=5,
        )

        assert data.supplier_name == "MOUSER"
        assert data.current_usage["per_minute"] == 15
        assert data.limits["per_minute"] == 30
        assert data.usage_percentage["per_minute"] == 50.0
        assert data.queue_size == 5


class TestNotificationData:
    """Test notification data schema"""

    def test_valid_notification_data(self):
        """Test creating valid notification data"""
        actions = [{"label": "View", "action": "view_details"}]
        data = NotificationData(
            level="info",
            title="Import Complete",
            message="Successfully imported 50 parts",
            duration=5000,
            actions=actions,
        )

        assert data.level == "info"
        assert data.title == "Import Complete"
        assert data.message == "Successfully imported 50 parts"
        assert data.duration == 5000
        assert data.actions == actions

    def test_notification_without_actions(self):
        """Test notification without actions"""
        data = NotificationData(
            level="warning", title="Rate Limit Warning", message="Approaching rate limit for MOUSER"
        )

        assert data.level == "warning"
        assert data.actions is None
        assert data.duration == 5000  # Default value


class TestToastData:
    """Test toast data schema"""

    def test_valid_toast_data(self):
        """Test creating valid toast data"""
        data = ToastData(level="success", message="Part enrichment completed", duration=4000, position="bottom-right")

        assert data.level == "success"
        assert data.message == "Part enrichment completed"
        assert data.duration == 4000
        assert data.position == "bottom-right"

    def test_toast_default_values(self):
        """Test toast with default values"""
        data = ToastData(level="error", message="Something went wrong")

        assert data.duration == 3000  # Default
        assert data.position == "top-right"  # Default


class TestHelperFunctions:
    """Test helper functions for creating messages"""

    def test_create_import_progress_message(self):
        """Test creating import progress message"""
        message = create_import_progress_message(
            task_id="task-123",
            filename="test.xls",
            parser_type="mouser",
            progress=75,
            current_step="Enriching parts",
            parts_processed=75,
            total_parts=100,
            correlation_id="corr-456",
        )

        assert isinstance(message, WebSocketMessage)
        assert message.type == WebSocketEventType.IMPORT_PROGRESS
        assert message.correlation_id == "corr-456"
        assert message.data["task_id"] == "task-123"
        assert message.data["filename"] == "test.xls"
        assert message.data["parser_type"] == "mouser"
        assert message.data["progress_percentage"] == 75
        assert message.data["current_step"] == "Enriching parts"
        assert message.data["parts_processed"] == 75
        assert message.data["total_parts"] == 100

    def test_create_enrichment_progress_message(self):
        """Test creating enrichment progress message"""
        message = create_enrichment_progress_message(
            supplier_name="LCSC",
            part_id="part-789",
            part_name="Test Part",
            capabilities_completed=["fetch_datasheet"],
            capabilities_total=["fetch_datasheet", "fetch_image", "fetch_pricing"],
            current_capability="fetch_image",
            task_id="task-456",
        )

        assert isinstance(message, WebSocketMessage)
        assert message.type == WebSocketEventType.ENRICHMENT_PROGRESS
        assert message.data["supplier_name"] == "LCSC"
        assert message.data["part_id"] == "part-789"
        assert message.data["part_name"] == "Test Part"
        assert message.data["progress_percentage"] == 33  # 1/3 * 100
        assert message.data["current_capability"] == "fetch_image"
        assert message.data["task_id"] == "task-456"

    def test_create_rate_limit_update_message(self):
        """Test creating rate limit update message"""
        now = datetime.now(timezone.utc)
        current_usage = {"per_minute": 20, "per_hour": 800}
        limits = {"per_minute": 30, "per_hour": 1000}
        next_reset = {"per_minute": now, "per_hour": now}

        message = create_rate_limit_update_message(
            supplier_name="MOUSER", current_usage=current_usage, limits=limits, next_reset=next_reset, queue_size=3
        )

        assert isinstance(message, WebSocketMessage)
        assert message.type == WebSocketEventType.RATE_LIMIT_UPDATE
        assert message.data["supplier_name"] == "MOUSER"
        assert message.data["current_usage"] == current_usage
        assert message.data["limits"] == limits
        assert message.data["queue_size"] == 3

        # Check calculated usage percentages
        usage_percentage = message.data["usage_percentage"]
        assert abs(usage_percentage["per_minute"] - 66.67) < 0.1  # 20/30 * 100
        assert usage_percentage["per_hour"] == 80.0  # 800/1000 * 100

    def test_create_notification_message(self):
        """Test creating notification message"""
        actions = [{"label": "Retry", "action": "retry_import"}]
        message = create_notification_message(
            level="error",
            title="Import Failed",
            message="Failed to import file due to format error",
            duration=10000,
            actions=actions,
            correlation_id="corr-789",
        )

        assert isinstance(message, WebSocketMessage)
        assert message.type == WebSocketEventType.NOTIFICATION
        assert message.correlation_id == "corr-789"
        assert message.data["level"] == "error"
        assert message.data["title"] == "Import Failed"
        assert message.data["message"] == "Failed to import file due to format error"
        assert message.data["duration"] == 10000
        assert message.data["actions"] == actions

    def test_create_toast_message(self):
        """Test creating toast message"""
        message = create_toast_message(
            level="success", message="✅ Enrichment completed successfully", duration=4000, position="bottom-center"
        )

        assert isinstance(message, WebSocketMessage)
        assert message.type == WebSocketEventType.TOAST
        assert message.data["level"] == "success"
        assert message.data["message"] == "✅ Enrichment completed successfully"
        assert message.data["duration"] == 4000
        assert message.data["position"] == "bottom-center"

    def test_create_toast_message_defaults(self):
        """Test creating toast message with defaults"""
        message = create_toast_message(level="info", message="Processing...")

        assert message.data["duration"] == 3000  # Default
        assert message.data["position"] == "top-right"  # Default


class TestConnectionStatusData:
    """Test connection status data schema"""

    def test_valid_connection_status_data(self):
        """Test creating valid connection status data"""
        data = ConnectionStatusData(
            connected=True,
            connection_id="conn-123",
            user_id="user-456",
            subscriptions=["import_progress", "enrichment_progress"],
        )

        assert data.connected is True
        assert data.connection_id == "conn-123"
        assert data.user_id == "user-456"
        assert "import_progress" in data.subscriptions
        assert "enrichment_progress" in data.subscriptions
        assert isinstance(data.server_time, datetime)

    def test_connection_status_without_user(self):
        """Test connection status without user ID"""
        data = ConnectionStatusData(connected=False, connection_id="conn-789")

        assert data.connected is False
        assert data.connection_id == "conn-789"
        assert data.user_id is None
        assert data.subscriptions == []


class TestTaskProgressData:
    """Test task progress data schema"""

    def test_valid_task_progress_data(self):
        """Test creating valid task progress data"""
        started_at = datetime.now(timezone.utc)
        estimated_completion = started_at.replace(hour=started_at.hour + 1)

        data = TaskProgressData(
            task_id="task-123",
            task_type="import",
            task_name="Import Mouser XLS",
            status="running",
            progress_percentage=45,
            current_step="Enriching parts",
            started_at=started_at,
            estimated_completion=estimated_completion,
            result_summary={"parts_imported": 45, "parts_total": 100},
        )

        assert data.task_id == "task-123"
        assert data.task_type == "import"
        assert data.task_name == "Import Mouser XLS"
        assert data.status == "running"
        assert data.progress_percentage == 45
        assert data.current_step == "Enriching parts"
        assert data.started_at == started_at
        assert data.estimated_completion == estimated_completion
        assert data.result_summary["parts_imported"] == 45

    def test_task_progress_invalid_percentage(self):
        """Test validation of task progress percentage"""
        with pytest.raises(ValidationError) as exc_info:
            TaskProgressData(
                task_id="task-123",
                task_type="import",
                task_name="Test Task",
                status="running",
                progress_percentage=120,  # Invalid: > 100
                current_step="Processing",
            )

        assert "less than or equal to 100" in str(exc_info.value)


@pytest.mark.parametrize(
    "event_type,expected_string",
    [
        (WebSocketEventType.PING, "ping"),
        (WebSocketEventType.IMPORT_PROGRESS, "import_progress"),
        (WebSocketEventType.ENRICHMENT_COMPLETED, "enrichment_completed"),
        (WebSocketEventType.RATE_LIMIT_WARNING, "rate_limit_warning"),
        (WebSocketEventType.NOTIFICATION, "notification"),
    ],
)
def test_event_type_string_values(event_type, expected_string):
    """Test that event types have correct string values"""
    assert event_type == expected_string


def test_websocket_message_serialization():
    """Test that WebSocket messages can be serialized to dict"""
    message = create_import_progress_message(
        task_id="task-123",
        filename="test.csv",
        parser_type="lcsc",
        progress=50,
        current_step="Processing",
        parts_processed=50,
        total_parts=100,
    )

    # Should be able to convert to dict for JSON serialization
    message_dict = message.model_dump()

    assert isinstance(message_dict, dict)
    assert message_dict["type"] == "import_progress"
    assert "timestamp" in message_dict
    assert "data" in message_dict
    assert message_dict["data"]["task_id"] == "task-123"
