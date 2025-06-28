"""
WebSocket routes for real-time communication
"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
from MakerMatrix.services.system.websocket_service import websocket_manager
from MakerMatrix.auth.dependencies import get_current_user_from_token
from MakerMatrix.models.user_models import UserModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/tasks")
async def websocket_tasks_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for task monitoring"""
    user = None
    
    # Try to authenticate user if token provided
    if token:
        try:
            user = await get_current_user_from_token(token)
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
    
    user_id = user.id if user else None
    
    try:
        await websocket_manager.connect(websocket, "tasks", user_id)
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_task_websocket_message(websocket, message, user)
            except json.JSONDecodeError:
                await websocket_manager.send_to_connection(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket_manager.send_to_connection(websocket, {
                    "type": "error", 
                    "message": "Internal server error"
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/general")
async def websocket_general_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for general activity updates"""
    user = None
    
    # Try to authenticate user if token provided (optional for general updates)
    if token:
        try:
            user = await get_current_user_from_token(token)
        except Exception as e:
            logger.warning(f"General WebSocket authentication failed: {e}")
    
    user_id = user.id if user else None
    
    try:
        await websocket_manager.connect(websocket, "general", user_id)
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_general_websocket_message(websocket, message, user)
            except json.JSONDecodeError:
                await websocket_manager.send_to_connection(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling general WebSocket message: {e}")
                await websocket_manager.send_to_connection(websocket, {
                    "type": "error", 
                    "message": "Internal server error"
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"General WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/admin") 
async def websocket_admin_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for admin monitoring"""
    user = None
    
    # Require authentication for admin endpoint
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    try:
        user = await get_current_user_from_token(token)
        
        # Check if user has admin permissions
        if not user or "admin" not in [role.name for role in user.roles]:
            await websocket.close(code=4003, reason="Admin access required")
            return
            
    except Exception as e:
        logger.warning(f"Admin WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    try:
        await websocket_manager.connect(websocket, "admin", user.id)
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_admin_websocket_message(websocket, message, user)
            except json.JSONDecodeError:
                await websocket_manager.send_to_connection(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling admin WebSocket message: {e}")
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Admin WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


async def handle_task_websocket_message(websocket: WebSocket, message: dict, user: UserModel = None):
    """Handle incoming task WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket_manager.send_to_connection(websocket, {
            "type": "pong",
            "timestamp": message.get("timestamp")
        })
    
    elif message_type == "subscribe_task":
        task_id = message.get("task_id")
        if task_id:
            # Send current task status
            # This would fetch current task status from database
            await websocket_manager.send_to_connection(websocket, {
                "type": "task_subscription",
                "task_id": task_id,
                "status": "subscribed"
            })
    
    elif message_type == "unsubscribe_task":
        task_id = message.get("task_id")
        await websocket_manager.send_to_connection(websocket, {
            "type": "task_unsubscription", 
            "task_id": task_id,
            "status": "unsubscribed"
        })
    
    elif message_type == "get_connection_info":
        stats = websocket_manager.get_connection_stats()
        await websocket_manager.send_to_connection(websocket, {
            "type": "connection_info",
            "data": stats
        })


async def handle_general_websocket_message(websocket: WebSocket, message: dict, user: UserModel = None):
    """Handle incoming general WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "ping":
        await websocket_manager.send_to_connection(websocket, {
            "type": "pong",
            "timestamp": message.get("timestamp")
        })
    
    elif message_type == "subscribe_activities":
        # Subscribe to activity updates
        await websocket_manager.send_to_connection(websocket, {
            "type": "activity_subscription",
            "status": "subscribed"
        })
    
    elif message_type == "get_connection_info":
        stats = websocket_manager.get_connection_stats()
        await websocket_manager.send_to_connection(websocket, {
            "type": "connection_info",
            "data": stats
        })


async def handle_admin_websocket_message(websocket: WebSocket, message: dict, user: UserModel):
    """Handle incoming admin WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "get_system_stats":
        # Return system statistics
        stats = {
            "websocket_connections": websocket_manager.get_connection_stats(),
            "user_id": user.id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await websocket_manager.send_to_connection(websocket, {
            "type": "system_stats",
            "data": stats
        })
    
    elif message_type == "broadcast_notification":
        # Allow admin to broadcast notifications
        notification = message.get("notification", {})
        if notification:
            await websocket_manager.send_system_notification(
                notification,
                connection_types=["general", "tasks"]
            )