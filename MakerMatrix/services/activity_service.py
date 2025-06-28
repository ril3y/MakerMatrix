"""
Activity logging service for tracking user actions and system events.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.engine import Engine
from sqlmodel import Session, select, desc
from datetime import datetime, timedelta
from fastapi import Request

from MakerMatrix.models.models import ActivityLogModel, engine
from MakerMatrix.models.user_models import UserModel


class ActivityService:
    """Service for logging and retrieving user activities."""
    
    def __init__(self, db_engine: Engine = engine):
        self.engine = db_engine
    
    async def log_activity(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        user: Optional[UserModel] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> ActivityLogModel:
        """
        Log an activity to the database.
        
        Args:
            action: What happened (created, updated, deleted, printed, etc.)
            entity_type: Type of entity (part, printer, label, location, etc.)
            entity_id: ID of the entity acted upon
            entity_name: Human-readable name
            user: User who performed the action
            details: Additional details about the action
            request: FastAPI request object for IP/user agent
        """
        try:
            # Extract request info
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            # Create activity record
            activity = ActivityLogModel(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                user_id=user.id if user else None,
                username=user.username if user else "system",
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Save to database
            with Session(self.engine) as session:
                session.add(activity)
                session.commit()
                session.refresh(activity)
            
            # Send real-time update via WebSocket
            await self._broadcast_activity(activity)
            
            return activity
            
        except Exception as e:
            print(f"Failed to log activity: {e}")
            # Don't fail the main operation if logging fails
            return None
    
    async def _broadcast_activity(self, activity: ActivityLogModel):
        """Broadcast activity to connected WebSocket clients using standardized schemas."""
        try:
            from MakerMatrix.services.system.websocket_service import broadcast_message
            from MakerMatrix.schemas.websocket_schemas import create_entity_event_message
            
            # Create standardized WebSocket message
            ws_message = create_entity_event_message(
                action=activity.action,
                entity_type=activity.entity_type,
                entity_id=activity.entity_id or "",
                entity_name=activity.entity_name or "",
                user_id=activity.user_id,
                username=activity.username,
                details=activity.details or {}
            )
            
            # Broadcast to general connections (for activity monitoring)
            await broadcast_message(ws_message.model_dump(), connection_types=["general"])
            
        except Exception as e:
            print(f"Failed to broadcast activity: {e}")
            # Don't fail if WebSocket broadcast fails
    
    def get_recent_activities(
        self,
        limit: int = 50,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> List[ActivityLogModel]:
        """
        Get recent activities from the database.
        
        Args:
            limit: Maximum number of activities to return
            entity_type: Filter by entity type
            user_id: Filter by user
            hours: Only activities from last N hours
        """
        try:
            with Session(self.engine) as session:
                # Build query
                statement = select(ActivityLogModel)
                
                # Filter by time
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                statement = statement.where(ActivityLogModel.timestamp >= cutoff_time)
                
                # Apply filters
                if entity_type:
                    statement = statement.where(ActivityLogModel.entity_type == entity_type)
                if user_id:
                    statement = statement.where(ActivityLogModel.user_id == user_id)
                
                # Order by most recent first
                statement = statement.order_by(desc(ActivityLogModel.timestamp))
                
                # Apply limit
                statement = statement.limit(limit)
                
                return list(session.exec(statement).all())
                
        except Exception as e:
            print(f"Failed to retrieve activities: {e}")
            return []
    
    def cleanup_old_activities(self, keep_days: int = 90) -> int:
        """
        Clean up old activity records to prevent database bloat.
        
        Args:
            keep_days: Number of days to keep activities
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
            
            with Session(self.engine) as session:
                # Get activities to delete
                statement = select(ActivityLogModel).where(
                    ActivityLogModel.timestamp < cutoff_date
                )
                activities_to_delete = session.exec(statement).all()
                
                # Delete them
                for activity in activities_to_delete:
                    session.delete(activity)
                
                session.commit()
                return len(activities_to_delete)
                
        except Exception as e:
            print(f"Failed to cleanup activities: {e}")
            return 0

    # Convenience methods for common activities
    async def log_part_created(self, part_id: str, part_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log part creation activity."""
        return await self.log_activity(
            action="created",
            entity_type="part",
            entity_id=part_id,
            entity_name=part_name,
            user=user,
            request=request
        )
    
    async def log_part_updated(self, part_id: str, part_name: str, changes: Dict[str, Any], user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log part update activity."""
        return await self.log_activity(
            action="updated",
            entity_type="part",
            entity_id=part_id,
            entity_name=part_name,
            details={"changes": changes},
            user=user,
            request=request
        )
    
    async def log_part_deleted(self, part_id: str, part_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log part deletion activity."""
        return await self.log_activity(
            action="deleted",
            entity_type="part",
            entity_id=part_id,
            entity_name=part_name,
            user=user,
            request=request
        )
    
    async def log_label_printed(self, printer_id: str, printer_name: str, label_type: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log label printing activity."""
        return await self.log_activity(
            action="printed",
            entity_type="label",
            entity_id=printer_id,
            entity_name=f"{label_type} on {printer_name}",
            details={"printer_id": printer_id, "label_type": label_type},
            user=user,
            request=request
        )
    
    async def log_printer_registered(self, printer_id: str, printer_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log printer registration activity."""
        return await self.log_activity(
            action="registered",
            entity_type="printer",
            entity_id=printer_id,
            entity_name=printer_name,
            user=user,
            request=request
        )
    
    async def log_printer_updated(self, printer_id: str, printer_name: str, changes: Dict[str, Any], user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log printer update activity."""
        return await self.log_activity(
            action="updated",
            entity_type="printer",
            entity_id=printer_id,
            entity_name=printer_name,
            details={"changes": changes},
            user=user,
            request=request
        )
    
    async def log_printer_deleted(self, printer_id: str, printer_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log printer deletion activity."""
        return await self.log_activity(
            action="deleted",
            entity_type="printer",
            entity_id=printer_id,
            entity_name=printer_name,
            user=user,
            request=request
        )
    
    async def log_printer_tested(self, printer_id: str, printer_name: str, test_result: bool, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log printer test activity."""
        return await self.log_activity(
            action="tested",
            entity_type="printer",
            entity_id=printer_id,
            entity_name=printer_name,
            details={"test_success": test_result},
            user=user,
            request=request
        )
    
    async def log_location_created(self, location_id: str, location_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log location creation activity."""
        return await self.log_activity(
            action="created",
            entity_type="location",
            entity_id=location_id,
            entity_name=location_name,
            user=user,
            request=request
        )
    
    async def log_location_updated(self, location_id: str, location_name: str, changes: Dict[str, Any], user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log location update activity."""
        return await self.log_activity(
            action="updated",
            entity_type="location",
            entity_id=location_id,
            entity_name=location_name,
            details={"changes": changes},
            user=user,
            request=request
        )
    
    async def log_location_deleted(self, location_id: str, location_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log location deletion activity."""
        return await self.log_activity(
            action="deleted",
            entity_type="location",
            entity_id=location_id,
            entity_name=location_name,
            user=user,
            request=request
        )
    
    async def log_category_created(self, category_id: str, category_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log category creation activity."""
        return await self.log_activity(
            action="created",
            entity_type="category",
            entity_id=category_id,
            entity_name=category_name,
            user=user,
            request=request
        )
    
    async def log_category_updated(self, category_id: str, category_name: str, changes: Dict[str, Any], user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log category update activity."""
        return await self.log_activity(
            action="updated",
            entity_type="category",
            entity_id=category_id,
            entity_name=category_name,
            details={"changes": changes},
            user=user,
            request=request
        )
    
    async def log_category_deleted(self, category_id: str, category_name: str, user: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log category deletion activity."""
        return await self.log_activity(
            action="deleted",
            entity_type="category",
            entity_id=category_id,
            entity_name=category_name,
            user=user,
            request=request
        )
    
    async def log_user_created(self, user_id: str, username: str, created_by: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log user creation activity."""
        return await self.log_activity(
            action="created",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
            user=created_by,
            request=request
        )
    
    async def log_user_updated(self, user_id: str, username: str, changes: Dict[str, Any], updated_by: Optional[UserModel] = None, request: Optional[Request] = None):
        """Log user update activity."""
        return await self.log_activity(
            action="updated",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
            details={"changes": changes},
            user=updated_by,
            request=request
        )
    
    async def log_login(self, user: UserModel, request: Optional[Request] = None):
        """Log user login activity."""
        return await self.log_activity(
            action="logged_in",
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            user=user,
            request=request
        )
    
    async def log_logout(self, user: UserModel, request: Optional[Request] = None):
        """Log user logout activity."""
        return await self.log_activity(
            action="logged_out",
            entity_type="user",
            entity_id=user.id,
            entity_name=user.username,
            user=user,
            request=request
        )


# Global service instance
_activity_service: Optional[ActivityService] = None


def get_activity_service() -> ActivityService:
    """Get the global activity service instance."""
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService()
    return _activity_service