"""
WebSocket service for real-time task monitoring and system events
"""

import json
import asyncio
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Store active connections by connection type
        self.connections: Dict[str, Set[WebSocket]] = {
            "tasks": set(),  # Task monitoring connections
            "general": set(),  # General system updates
            "admin": set(),  # Admin-only connections
        }
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, connection_type: str = "general", user_id: str = None):
        """Connect a new WebSocket client"""
        await websocket.accept()

        if connection_type not in self.connections:
            self.connections[connection_type] = set()

        self.connections[connection_type].add(websocket)
        self.connection_info[websocket] = {
            "type": connection_type,
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
        }

        logger.info(f"WebSocket connected: {connection_type} (user: {user_id})")

        # Send welcome message
        await self.send_to_connection(
            websocket,
            {
                "type": "connection",
                "status": "connected",
                "connection_type": connection_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        connection_info = self.connection_info.get(websocket, {})
        connection_type = connection_info.get("type", "unknown")
        user_id = connection_info.get("user_id", "unknown")

        # Remove from all connection sets
        for conn_set in self.connections.values():
            conn_set.discard(websocket)

        # Remove connection info
        self.connection_info.pop(websocket, None)

        logger.info(f"WebSocket disconnected: {connection_type} (user: {user_id})")

    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific connection"""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast_to_type(self, connection_type: str, message: Dict[str, Any]):
        """Broadcast message to all connections of a specific type"""
        if connection_type not in self.connections:
            return

        disconnected = set()
        for websocket in self.connections[connection_type].copy():
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Failed to broadcast to WebSocket: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_task_update(self, task_data: Dict[str, Any]):
        """Broadcast task update to task monitoring connections"""
        message = {"type": "task_update", "data": task_data, "timestamp": datetime.utcnow().isoformat()}
        await self.broadcast_to_type("tasks", message)

    async def broadcast_task_log(self, task_id: str, level: str, message: str, step: str = None):
        """Broadcast task log message"""
        log_message = {
            "type": "task_log",
            "data": {
                "task_id": task_id,
                "level": level,
                "message": message,
                "step": step,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
        await self.broadcast_to_type("tasks", log_message)

    async def broadcast_worker_status(self, status_data: Dict[str, Any]):
        """Broadcast worker status update"""
        message = {"type": "worker_status", "data": status_data, "timestamp": datetime.utcnow().isoformat()}
        await self.broadcast_to_type("tasks", message)
        await self.broadcast_to_type("admin", message)

    async def send_system_notification(self, notification: Dict[str, Any], connection_types: list = None):
        """Send system notification to specified connection types"""
        if connection_types is None:
            connection_types = ["general", "admin"]

        message = {"type": "system_notification", "data": notification, "timestamp": datetime.utcnow().isoformat()}

        for conn_type in connection_types:
            await self.broadcast_to_type(conn_type, message)

    async def broadcast_crud_event(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        user_id: str = None,
        username: str = None,
        changes: Dict[str, Any] = None,
        details: Dict[str, Any] = None,
        entity_data: Dict[str, Any] = None,
    ):
        """
        Broadcast CRUD event to general and admin connections

        Args:
            action: Action performed (created, updated, deleted, etc.)
            entity_type: Type of entity (part, location, category, etc.)
            entity_id: Unique identifier of the entity
            entity_name: Human-readable name of the entity
            user_id: ID of user who performed the action
            username: Username of user who performed the action
            changes: For updates, dict of what changed
            details: Additional action-specific details
            entity_data: Complete entity data after the action
        """
        message = {
            "type": f"entity_{action}",
            "data": {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_name": entity_name,
                "action": action,
                "user_id": user_id,
                "username": username,
                "changes": changes,
                "details": details or {},
                "entity_data": entity_data,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Broadcast to general and admin connections
        await self.broadcast_to_type("general", message)
        await self.broadcast_to_type("admin", message)

    async def ping_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = {"type": "ping", "timestamp": datetime.utcnow().isoformat()}

        for connection_type in self.connections:
            await self.broadcast_to_type(connection_type, ping_message)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = {
            "total_connections": sum(len(conns) for conns in self.connections.values()),
            "by_type": {conn_type: len(conns) for conn_type, conns in self.connections.items()},
            "active_users": len(
                set(info.get("user_id") for info in self.connection_info.values() if info.get("user_id"))
            ),
        }
        return stats


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def broadcast_message(message: Dict[str, Any], connection_types: list = None):
    """Broadcast message to specified connection types"""
    if connection_types is None:
        connection_types = ["general"]

    for connection_type in connection_types:
        await websocket_manager.broadcast_to_type(connection_type, message)


async def start_ping_task():
    """Start background task to ping connections periodically"""
    while True:
        try:
            await websocket_manager.ping_connections()
            await asyncio.sleep(30)  # Ping every 30 seconds
        except Exception as e:
            logger.error(f"Error in ping task: {e}")
            await asyncio.sleep(5)
