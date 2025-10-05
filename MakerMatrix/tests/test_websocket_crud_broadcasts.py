"""
Test WebSocket CRUD Broadcast Functionality

Tests the websocket broadcast system for all CRUD operations across
parts, locations, and categories entities.
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from MakerMatrix.services.system.websocket_service import WebSocketManager, websocket_manager
from MakerMatrix.models.user_models import UserModel
from fastapi import WebSocket


class MockWebSocket:
    """Mock WebSocket for testing"""

    def __init__(self):
        self.messages: List[str] = []
        self.is_connected = True

    async def accept(self):
        """Mock accept connection"""
        pass

    async def send_text(self, data: str):
        """Mock send text and store message"""
        if self.is_connected:
            self.messages.append(data)
        else:
            raise Exception("WebSocket disconnected")

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages as parsed JSON"""
        return [json.loads(msg) for msg in self.messages]

    def clear_messages(self):
        """Clear message history"""
        self.messages = []

    def disconnect(self):
        """Simulate disconnection"""
        self.is_connected = False


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    return MockWebSocket()


@pytest.fixture
def fresh_ws_manager():
    """Create a fresh WebSocketManager instance for each test"""
    manager = WebSocketManager()
    yield manager
    # Cleanup all connections after test
    manager.connections.clear()
    manager.connection_info.clear()


@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    user = Mock(spec=UserModel)
    user.id = "test-user-id-123"
    user.username = "testuser"
    return user


# ============================================================================
# WebSocket Manager Basic Tests
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_manager_connect(fresh_ws_manager, mock_websocket):
    """Test connecting a WebSocket client"""
    await fresh_ws_manager.connect(mock_websocket, "general", "user-123")

    assert mock_websocket in fresh_ws_manager.connections["general"]
    assert mock_websocket in fresh_ws_manager.connection_info
    assert fresh_ws_manager.connection_info[mock_websocket]["type"] == "general"
    assert fresh_ws_manager.connection_info[mock_websocket]["user_id"] == "user-123"

    # Check welcome message was sent
    messages = mock_websocket.get_messages()
    assert len(messages) == 1
    assert messages[0]["type"] == "connection"
    assert messages[0]["status"] == "connected"


@pytest.mark.asyncio
async def test_websocket_manager_disconnect(fresh_ws_manager, mock_websocket):
    """Test disconnecting a WebSocket client"""
    await fresh_ws_manager.connect(mock_websocket, "general", "user-123")
    assert mock_websocket in fresh_ws_manager.connections["general"]

    fresh_ws_manager.disconnect(mock_websocket)

    assert mock_websocket not in fresh_ws_manager.connections["general"]
    assert mock_websocket not in fresh_ws_manager.connection_info


@pytest.mark.asyncio
async def test_broadcast_to_multiple_connections(fresh_ws_manager):
    """Test broadcasting to multiple connected clients"""
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    await fresh_ws_manager.connect(ws1, "general", "user-1")
    await fresh_ws_manager.connect(ws2, "general", "user-2")
    await fresh_ws_manager.connect(ws3, "admin", "admin-1")

    # Clear welcome messages
    ws1.clear_messages()
    ws2.clear_messages()
    ws3.clear_messages()

    # Broadcast to general
    test_message = {"type": "test", "data": "hello"}
    await fresh_ws_manager.broadcast_to_type("general", test_message)

    # Check only general connections received the message
    assert len(ws1.get_messages()) == 1
    assert len(ws2.get_messages()) == 1
    assert len(ws3.get_messages()) == 0

    assert ws1.get_messages()[0]["type"] == "test"
    assert ws2.get_messages()[0]["data"] == "hello"


@pytest.mark.asyncio
async def test_broadcast_handles_disconnected_socket(fresh_ws_manager):
    """Test that broadcasting handles disconnected sockets gracefully"""
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await fresh_ws_manager.connect(ws1, "general", "user-1")
    await fresh_ws_manager.connect(ws2, "general", "user-2")

    # Disconnect ws1
    ws1.disconnect()

    # Broadcast should handle the disconnected socket
    test_message = {"type": "test", "data": "hello"}
    await fresh_ws_manager.broadcast_to_type("general", test_message)

    # ws2 should still receive the message
    ws2_messages = [msg for msg in ws2.get_messages() if msg.get("type") != "connection"]
    assert len(ws2_messages) == 1

    # ws1 should be removed from connections after failed broadcast
    assert ws1 not in fresh_ws_manager.connections["general"]


# ============================================================================
# CRUD Broadcast Tests - Parts
# ============================================================================

@pytest.mark.asyncio
async def test_broadcast_part_created(fresh_ws_manager, mock_user):
    """Test broadcasting part creation event"""
    ws_general = MockWebSocket()
    ws_admin = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    await fresh_ws_manager.connect(ws_admin, "admin", "admin-1")

    # Clear welcome messages
    ws_general.clear_messages()
    ws_admin.clear_messages()

    # Broadcast part creation
    part_data = {
        "id": "part-123",
        "part_name": "Test Resistor",
        "part_number": "R-1K-001",
        "quantity": 100
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Resistor",
        user_id=mock_user.id,
        username=mock_user.username,
        entity_data=part_data
    )

    # Both general and admin should receive the event
    general_msgs = ws_general.get_messages()
    admin_msgs = ws_admin.get_messages()

    assert len(general_msgs) == 1
    assert len(admin_msgs) == 1

    # Verify message structure
    msg = general_msgs[0]
    assert msg["type"] == "entity_created"
    assert msg["data"]["entity_type"] == "part"
    assert msg["data"]["entity_id"] == "part-123"
    assert msg["data"]["entity_name"] == "Test Resistor"
    assert msg["data"]["action"] == "created"
    assert msg["data"]["user_id"] == mock_user.id
    assert msg["data"]["username"] == mock_user.username
    assert msg["data"]["entity_data"] == part_data
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_broadcast_part_updated(fresh_ws_manager, mock_user):
    """Test broadcasting part update event with changes"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    # Broadcast part update with changes
    part_data = {
        "id": "part-123",
        "part_name": "Test Resistor",
        "quantity": 150
    }

    changes = {
        "quantity": {"from": 100, "to": 150},
        "location_id": {"from": "loc-1", "to": "loc-2"}
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="updated",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Resistor",
        user_id=mock_user.id,
        username=mock_user.username,
        changes=changes,
        entity_data=part_data
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_updated"
    assert msg["data"]["entity_type"] == "part"
    assert msg["data"]["changes"] == changes
    assert msg["data"]["entity_data"]["quantity"] == 150


@pytest.mark.asyncio
async def test_broadcast_part_deleted(fresh_ws_manager, mock_user):
    """Test broadcasting part deletion event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    await fresh_ws_manager.broadcast_crud_event(
        action="deleted",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Resistor",
        user_id=mock_user.id,
        username=mock_user.username
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_deleted"
    assert msg["data"]["entity_type"] == "part"
    assert msg["data"]["entity_id"] == "part-123"
    assert msg["data"]["action"] == "deleted"


@pytest.mark.asyncio
async def test_broadcast_parts_bulk_updated(fresh_ws_manager, mock_user):
    """Test broadcasting bulk part update event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    details = {
        "part_ids": ["part-1", "part-2", "part-3"],
        "updated_count": 3,
        "failed_count": 0,
        "changes": {
            "location_id": "new-location-123",
            "supplier": "LCSC"
        }
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="bulk_updated",
        entity_type="part",
        entity_id="bulk",
        entity_name="3 parts",
        user_id=mock_user.id,
        username=mock_user.username,
        details=details
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_bulk_updated"
    assert msg["data"]["entity_id"] == "bulk"
    assert msg["data"]["details"]["updated_count"] == 3
    assert msg["data"]["details"]["part_ids"] == ["part-1", "part-2", "part-3"]


# ============================================================================
# CRUD Broadcast Tests - Locations
# ============================================================================

@pytest.mark.asyncio
async def test_broadcast_location_created(fresh_ws_manager, mock_user):
    """Test broadcasting location creation event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    location_data = {
        "id": "loc-123",
        "name": "Shelf A",
        "description": "Top shelf in storage room",
        "location_type": "shelf"
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="location",
        entity_id="loc-123",
        entity_name="Shelf A",
        user_id=mock_user.id,
        username=mock_user.username,
        entity_data=location_data
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_created"
    assert msg["data"]["entity_type"] == "location"
    assert msg["data"]["entity_name"] == "Shelf A"
    assert msg["data"]["entity_data"]["location_type"] == "shelf"


@pytest.mark.asyncio
async def test_broadcast_location_updated(fresh_ws_manager, mock_user):
    """Test broadcasting location update event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    changes = {
        "name": "Shelf A-1",
        "description": "Updated description"
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="updated",
        entity_type="location",
        entity_id="loc-123",
        entity_name="Shelf A-1",
        user_id=mock_user.id,
        username=mock_user.username,
        changes=changes
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1
    assert msgs[0]["data"]["changes"] == changes


@pytest.mark.asyncio
async def test_broadcast_location_deleted(fresh_ws_manager, mock_user):
    """Test broadcasting location deletion event with details"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    details = {
        "deleted_location_name": "Shelf A",
        "affected_parts_count": 5,
        "child_locations_count": 2
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="deleted",
        entity_type="location",
        entity_id="loc-123",
        entity_name="Shelf A",
        user_id=mock_user.id,
        username=mock_user.username,
        details=details
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["data"]["details"]["affected_parts_count"] == 5
    assert msg["data"]["details"]["child_locations_count"] == 2


# ============================================================================
# CRUD Broadcast Tests - Categories
# ============================================================================

@pytest.mark.asyncio
async def test_broadcast_category_created(fresh_ws_manager, mock_user):
    """Test broadcasting category creation event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    category_data = {
        "id": "cat-123",
        "name": "Resistors",
        "description": "All types of resistors"
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="category",
        entity_id="cat-123",
        entity_name="Resistors",
        user_id=mock_user.id,
        username=mock_user.username,
        entity_data=category_data
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_created"
    assert msg["data"]["entity_type"] == "category"
    assert msg["data"]["entity_name"] == "Resistors"


@pytest.mark.asyncio
async def test_broadcast_category_updated(fresh_ws_manager, mock_user):
    """Test broadcasting category update event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    changes = {
        "name": "Passive Components - Resistors",
        "description": "Updated description for resistors"
    }

    await fresh_ws_manager.broadcast_crud_event(
        action="updated",
        entity_type="category",
        entity_id="cat-123",
        entity_name="Passive Components - Resistors",
        user_id=mock_user.id,
        username=mock_user.username,
        changes=changes
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1
    assert msgs[0]["data"]["changes"] == changes


@pytest.mark.asyncio
async def test_broadcast_category_deleted(fresh_ws_manager, mock_user):
    """Test broadcasting category deletion event"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    await fresh_ws_manager.broadcast_crud_event(
        action="deleted",
        entity_type="category",
        entity_id="cat-123",
        entity_name="Resistors",
        user_id=mock_user.id,
        username=mock_user.username
    )

    msgs = ws_general.get_messages()
    assert len(msgs) == 1

    msg = msgs[0]
    assert msg["type"] == "entity_deleted"
    assert msg["data"]["entity_type"] == "category"


# ============================================================================
# Connection Type Tests
# ============================================================================

@pytest.mark.asyncio
async def test_crud_events_sent_to_both_general_and_admin(fresh_ws_manager, mock_user):
    """Test that CRUD events are broadcast to both general and admin connections"""
    ws_general = MockWebSocket()
    ws_admin = MockWebSocket()
    ws_tasks = MockWebSocket()  # Should NOT receive CRUD events

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    await fresh_ws_manager.connect(ws_admin, "admin", "admin-1")
    await fresh_ws_manager.connect(ws_tasks, "tasks", "user-2")

    # Clear welcome messages
    ws_general.clear_messages()
    ws_admin.clear_messages()
    ws_tasks.clear_messages()

    # Broadcast a CRUD event
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Part",
        user_id=mock_user.id,
        username=mock_user.username
    )

    # General and admin should receive, tasks should not
    assert len(ws_general.get_messages()) == 1
    assert len(ws_admin.get_messages()) == 1
    assert len(ws_tasks.get_messages()) == 0


# ============================================================================
# Message Format Tests
# ============================================================================

@pytest.mark.asyncio
async def test_message_format_includes_timestamp(fresh_ws_manager, mock_user):
    """Test that all messages include ISO format timestamp"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Part",
        user_id=mock_user.id,
        username=mock_user.username
    )

    msgs = ws_general.get_messages()
    assert "timestamp" in msgs[0]

    # Verify timestamp is valid ISO format
    timestamp_str = msgs[0]["timestamp"]
    # Should not raise exception
    datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


@pytest.mark.asyncio
async def test_message_data_structure(fresh_ws_manager, mock_user):
    """Test that message data structure is consistent"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Part",
        user_id=mock_user.id,
        username=mock_user.username,
        changes={"test": "value"},
        details={"extra": "info"},
        entity_data={"id": "part-123"}
    )

    msgs = ws_general.get_messages()
    msg = msgs[0]

    # Verify top-level structure
    assert "type" in msg
    assert "data" in msg
    assert "timestamp" in msg

    # Verify data structure
    data = msg["data"]
    assert "entity_type" in data
    assert "entity_id" in data
    assert "entity_name" in data
    assert "action" in data
    assert "user_id" in data
    assert "username" in data
    assert "changes" in data
    assert "details" in data
    assert "entity_data" in data


@pytest.mark.asyncio
async def test_empty_optional_fields(fresh_ws_manager, mock_user):
    """Test that optional fields default to None or empty dict"""
    ws_general = MockWebSocket()

    await fresh_ws_manager.connect(ws_general, "general", "user-1")
    ws_general.clear_messages()

    # Call with minimal required parameters
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Part"
    )

    msgs = ws_general.get_messages()
    data = msgs[0]["data"]

    assert data["user_id"] is None
    assert data["username"] is None
    assert data["changes"] is None
    assert data["details"] == {}
    assert data["entity_data"] is None


# ============================================================================
# Connection Statistics Tests
# ============================================================================

@pytest.mark.asyncio
async def test_connection_stats(fresh_ws_manager):
    """Test getting connection statistics"""
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    await fresh_ws_manager.connect(ws1, "general", "user-1")
    await fresh_ws_manager.connect(ws2, "general", "user-2")
    await fresh_ws_manager.connect(ws3, "admin", "admin-1")

    stats = fresh_ws_manager.get_connection_stats()

    assert stats["total_connections"] == 3
    assert stats["by_type"]["general"] == 2
    assert stats["by_type"]["admin"] == 1
    assert stats["active_users"] == 3


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_send_to_connection_handles_errors(fresh_ws_manager):
    """Test that send_to_connection handles errors gracefully"""
    ws = MockWebSocket()

    await fresh_ws_manager.connect(ws, "general", "user-1")

    # Disconnect the websocket to cause send error
    ws.disconnect()

    # Should not raise exception, should disconnect gracefully
    await fresh_ws_manager.send_to_connection(ws, {"test": "message"})

    # WebSocket should be removed from connections
    assert ws not in fresh_ws_manager.connections["general"]


# ============================================================================
# Integration-like Tests
# ============================================================================

@pytest.mark.asyncio
async def test_sequential_crud_operations(fresh_ws_manager, mock_user):
    """Test sequential CRUD operations to simulate real workflow"""
    ws = MockWebSocket()

    await fresh_ws_manager.connect(ws, "general", "user-1")
    ws.clear_messages()

    # Create
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Resistor 1K",
        user_id=mock_user.id,
        username=mock_user.username,
        entity_data={"id": "part-123", "quantity": 100}
    )

    # Update
    await fresh_ws_manager.broadcast_crud_event(
        action="updated",
        entity_type="part",
        entity_id="part-123",
        entity_name="Resistor 1K",
        user_id=mock_user.id,
        username=mock_user.username,
        changes={"quantity": {"from": 100, "to": 150}}
    )

    # Delete
    await fresh_ws_manager.broadcast_crud_event(
        action="deleted",
        entity_type="part",
        entity_id="part-123",
        entity_name="Resistor 1K",
        user_id=mock_user.id,
        username=mock_user.username
    )

    msgs = ws.get_messages()
    assert len(msgs) == 3
    assert msgs[0]["type"] == "entity_created"
    assert msgs[1]["type"] == "entity_updated"
    assert msgs[2]["type"] == "entity_deleted"


@pytest.mark.asyncio
async def test_multiple_entity_types_in_sequence(fresh_ws_manager, mock_user):
    """Test broadcasting different entity types in sequence"""
    ws = MockWebSocket()

    await fresh_ws_manager.connect(ws, "general", "user-1")
    ws.clear_messages()

    # Part
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="part",
        entity_id="part-123",
        entity_name="Test Part",
        user_id=mock_user.id,
        username=mock_user.username
    )

    # Location
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="location",
        entity_id="loc-123",
        entity_name="Test Location",
        user_id=mock_user.id,
        username=mock_user.username
    )

    # Category
    await fresh_ws_manager.broadcast_crud_event(
        action="created",
        entity_type="category",
        entity_id="cat-123",
        entity_name="Test Category",
        user_id=mock_user.id,
        username=mock_user.username
    )

    msgs = ws.get_messages()
    assert len(msgs) == 3
    assert msgs[0]["data"]["entity_type"] == "part"
    assert msgs[1]["data"]["entity_type"] == "location"
    assert msgs[2]["data"]["entity_type"] == "category"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
