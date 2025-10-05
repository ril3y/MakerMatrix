"""
End-to-End WebSocket CRUD Broadcast Tests

Tests the complete flow of CRUD operations with websocket broadcasts,
verifying that backend API changes trigger correct websocket messages.
"""

import pytest
import asyncio
import json
import websockets
from typing import List, Dict, Any
from datetime import datetime
import time

from MakerMatrix.tests.conftest import test_client, admin_auth_headers


# Test configuration
BACKEND_URL = "https://192.168.1.58:8443"
WS_URL = "wss://192.168.1.58:8443"


class WebSocketMessageCollector:
    """Collects websocket messages for testing"""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.websocket = None

    async def connect(self, endpoint: str, token: str):
        """Connect to websocket endpoint"""
        ws_url = f"{WS_URL}{endpoint}?token={token}"

        # Disable SSL verification for testing with self-signed certificates
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        self.websocket = await websockets.connect(ws_url, ssl=ssl_context)
        return self.websocket

    async def collect_messages(self, duration: float = 2.0):
        """Collect messages for a specified duration"""
        self.messages = []
        end_time = time.time() + duration

        while time.time() < end_time:
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=max(0.1, end_time - time.time())
                )
                data = json.loads(message)
                self.messages.append(data)
                print(f"📨 Received WS message: {data.get('type')}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    async def disconnect(self):
        """Disconnect from websocket"""
        if self.websocket:
            await self.websocket.close()

    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get all messages of a specific type"""
        return [msg for msg in self.messages if msg.get("type") == message_type]

    def get_entity_events(self, entity_type: str = None, action: str = None) -> List[Dict[str, Any]]:
        """Get entity events, optionally filtered by type and action"""
        events = []
        for msg in self.messages:
            if msg.get("type", "").startswith("entity_"):
                data = msg.get("data", {})
                if entity_type and data.get("entity_type") != entity_type:
                    continue
                if action and data.get("action") != action:
                    continue
                events.append(msg)
        return events


@pytest.fixture
def api_token(test_client):
    """Get API authentication token"""
    response = test_client.post("/auth/login", json={
        "username": "admin",
        "password": "Admin123!"
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def ws_collector():
    """Create a websocket message collector"""
    collector = WebSocketMessageCollector()
    yield collector
    await collector.disconnect()


# ============================================================================
# Parts CRUD E2E Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_part_create_broadcasts(test_client, api_token, ws_collector):
    """Test that creating a part triggers websocket broadcast"""
    # Connect to websocket
    await ws_collector.connect("/ws/general", api_token)

    # Start collecting messages in background
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=3.0))

    # Wait for connection message
    await asyncio.sleep(0.5)

    # Create a part via API
    part_data = {
        "part_name": f"Test Part {datetime.now().timestamp()}",
        "part_number": f"TP-{int(datetime.now().timestamp())}",
        "quantity": 100,
        "description": "Test part for websocket",
        "supplier": "Test Supplier"
    }

    response = test_client.post(
        "/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )

    assert response.status_code == 200
    created_part = response.json()["data"]
    part_id = created_part["id"]

    # Wait for messages to be collected
    await collect_task

    # Verify websocket broadcast was received
    entity_created_events = ws_collector.get_messages_by_type("entity_created")
    assert len(entity_created_events) > 0, "Should receive entity_created message"

    # Find our specific part creation event
    part_events = [
        e for e in entity_created_events
        if e["data"]["entity_id"] == part_id
    ]
    assert len(part_events) == 1, "Should receive exactly one part creation event"

    event_data = part_events[0]["data"]
    assert event_data["entity_type"] == "part"
    assert event_data["entity_name"] == part_data["part_name"]
    assert event_data["action"] == "created"
    assert "timestamp" in part_events[0]
    assert event_data.get("username") == "admin"

    # Cleanup
    test_client.delete(
        f"/parts/delete_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_part_update_broadcasts(test_client, api_token, ws_collector):
    """Test that updating a part triggers websocket broadcast with changes"""
    # Create a test part first
    part_data = {
        "part_name": f"Test Part Update {datetime.now().timestamp()}",
        "part_number": f"TPU-{int(datetime.now().timestamp())}",
        "quantity": 50
    }

    response = test_client.post(
        "/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )
    part_id = response.json()["data"]["id"]

    # Connect to websocket
    await ws_collector.connect("/ws/general", api_token)
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=3.0))
    await asyncio.sleep(0.5)

    # Update the part
    update_data = {
        "quantity": 100,
        "description": "Updated description"
    }

    response = test_client.put(
        f"/parts/update_part/{part_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )

    assert response.status_code == 200

    # Wait for messages
    await collect_task

    # Verify websocket broadcast
    entity_updated_events = ws_collector.get_messages_by_type("entity_updated")
    part_events = [
        e for e in entity_updated_events
        if e["data"]["entity_id"] == part_id
    ]

    assert len(part_events) == 1
    event_data = part_events[0]["data"]
    assert event_data["entity_type"] == "part"
    assert event_data["action"] == "updated"
    assert event_data["changes"] is not None
    assert "quantity" in event_data["changes"] or len(event_data["changes"]) > 0

    # Cleanup
    test_client.delete(
        f"/parts/delete_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_part_delete_broadcasts(test_client, api_token, ws_collector):
    """Test that deleting a part triggers websocket broadcast"""
    # Create a test part
    part_data = {
        "part_name": f"Test Part Delete {datetime.now().timestamp()}",
        "part_number": f"TPD-{int(datetime.now().timestamp())}",
        "quantity": 25
    }

    response = test_client.post(
        "/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )
    part_id = response.json()["data"]["id"]

    # Connect to websocket
    await ws_collector.connect("/ws/general", api_token)
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=3.0))
    await asyncio.sleep(0.5)

    # Delete the part
    response = test_client.delete(
        f"/parts/delete_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )

    assert response.status_code == 200

    # Wait for messages
    await collect_task

    # Verify websocket broadcast
    entity_deleted_events = ws_collector.get_messages_by_type("entity_deleted")
    part_events = [
        e for e in entity_deleted_events
        if e["data"]["entity_id"] == part_id
    ]

    assert len(part_events) == 1
    event_data = part_events[0]["data"]
    assert event_data["entity_type"] == "part"
    assert event_data["action"] == "deleted"


# ============================================================================
# Location CRUD E2E Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_location_create_broadcasts(test_client, api_token, ws_collector):
    """Test that creating a location triggers websocket broadcast"""
    await ws_collector.connect("/ws/general", api_token)
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=3.0))
    await asyncio.sleep(0.5)

    # Create a location
    location_data = {
        "name": f"Test Location {datetime.now().timestamp()}",
        "description": "Test location for websocket",
        "location_type": "shelf"
    }

    response = test_client.post(
        "/locations/add_location",
        json=location_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )

    assert response.status_code == 200
    location_id = response.json()["data"]["id"]

    await collect_task

    # Verify broadcast
    location_events = ws_collector.get_entity_events(entity_type="location", action="created")
    assert len(location_events) > 0

    event_data = location_events[0]["data"]
    assert event_data["entity_name"] == location_data["name"]

    # Cleanup
    test_client.delete(
        f"/locations/delete_location/{location_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )


# ============================================================================
# Category CRUD E2E Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_category_create_broadcasts(test_client, api_token, ws_collector):
    """Test that creating a category triggers websocket broadcast"""
    await ws_collector.connect("/ws/general", api_token)
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=3.0))
    await asyncio.sleep(0.5)

    # Create a category
    category_data = {
        "name": f"Test Category {datetime.now().timestamp()}",
        "description": "Test category for websocket"
    }

    response = test_client.post(
        "/categories/add_category",
        json=category_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )

    assert response.status_code == 200
    category_id = response.json()["data"]["id"]

    await collect_task

    # Verify broadcast
    category_events = ws_collector.get_entity_events(entity_type="category", action="created")
    assert len(category_events) > 0

    event_data = category_events[0]["data"]
    assert event_data["entity_name"] == category_data["name"]

    # Cleanup
    test_client.delete(
        f"/categories/remove_category?cat_id={category_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )


# ============================================================================
# Message Format Validation
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_message_format_validation(test_client, api_token, ws_collector):
    """Test that all websocket messages have correct format"""
    await ws_collector.connect("/ws/general", api_token)
    collect_task = asyncio.create_task(ws_collector.collect_messages(duration=4.0))
    await asyncio.sleep(0.5)

    # Perform multiple CRUD operations
    part_data = {
        "part_name": f"Format Test {datetime.now().timestamp()}",
        "part_number": f"FT-{int(datetime.now().timestamp())}",
        "quantity": 10
    }

    response = test_client.post(
        "/parts/add_part",
        json=part_data,
        headers={"Authorization": f"Bearer {api_token}"}
    )
    part_id = response.json()["data"]["id"]

    # Update
    test_client.put(
        f"/parts/update_part/{part_id}",
        json={"quantity": 20},
        headers={"Authorization": f"Bearer {api_token}"}
    )

    # Delete
    test_client.delete(
        f"/parts/delete_part?part_id={part_id}",
        headers={"Authorization": f"Bearer {api_token}"}
    )

    await collect_task

    # Validate all entity events have correct structure
    entity_events = ws_collector.get_entity_events()

    for event in entity_events:
        # Top-level structure
        assert "type" in event
        assert "data" in event
        assert "timestamp" in event

        # Data structure
        data = event["data"]
        assert "entity_type" in data
        assert "entity_id" in data
        assert "entity_name" in data
        assert "action" in data
        assert "details" in data

        # Timestamp format validation
        timestamp_str = event["timestamp"]
        # Should not raise exception
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
