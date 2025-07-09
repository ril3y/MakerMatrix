"""
Activity Repository

Repository for activity log database operations.
Handles logging user activities and system events.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, desc

from MakerMatrix.models.models import ActivityLogModel
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ActivityRepository(BaseRepository[ActivityLogModel]):
    """
    Repository for activity log database operations.
    
    Handles all database operations for activity logging,
    retrieval, and cleanup.
    """
    
    def __init__(self):
        super().__init__(ActivityLogModel)
    
    def log_activity(self, session: Session, activity: ActivityLogModel) -> ActivityLogModel:
        """
        Log an activity to the database.
        
        Args:
            session: Database session
            activity: Activity to log
            
        Returns:
            Created activity log entry
        """
        session.add(activity)
        session.commit()
        session.refresh(activity)
        
        logger.debug(f"Logged activity: {activity.action} on {activity.entity_type} by {activity.username}")
        return activity
    
    def get_recent_activities(
        self,
        session: Session,
        limit: int = 50,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        hours: int = 24
    ) -> List[ActivityLogModel]:
        """
        Get recent activities with optional filtering.
        
        Args:
            session: Database session
            limit: Maximum number of activities to return
            entity_type: Filter by entity type
            user_id: Filter by user ID
            hours: Only activities from last N hours
            
        Returns:
            List of recent activities
        """
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
        
        activities = session.exec(statement).all()
        return list(activities)
    
    def cleanup_old_activities(self, session: Session, keep_days: int = 90) -> int:
        """
        Clean up old activity records to prevent database bloat.
        
        Args:
            session: Database session
            keep_days: Number of days to keep activities
            
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        # Get activities to delete
        statement = select(ActivityLogModel).where(
            ActivityLogModel.timestamp < cutoff_date
        )
        activities_to_delete = session.exec(statement).all()
        
        # Delete them
        for activity in activities_to_delete:
            session.delete(activity)
        
        session.commit()
        deleted_count = len(activities_to_delete)
        
        logger.info(f"Cleaned up {deleted_count} old activity records (older than {keep_days} days)")
        return deleted_count
    
    def get_activity_statistics(
        self,
        session: Session,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get activity statistics for the specified time period.
        
        Args:
            session: Database session
            hours: Time period in hours to analyze
            
        Returns:
            Dictionary containing activity statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get total activities
        total_activities = session.exec(
            select(ActivityLogModel).where(ActivityLogModel.timestamp >= cutoff_time)
        ).all()
        
        # Group by action type
        action_counts = {}
        entity_counts = {}
        user_counts = {}
        
        for activity in total_activities:
            # Count by action
            action_counts[activity.action] = action_counts.get(activity.action, 0) + 1
            
            # Count by entity type
            entity_counts[activity.entity_type] = entity_counts.get(activity.entity_type, 0) + 1
            
            # Count by user
            username = activity.username or "system"
            user_counts[username] = user_counts.get(username, 0) + 1
        
        return {
            "total_activities": len(total_activities),
            "time_period_hours": hours,
            "actions": action_counts,
            "entities": entity_counts,
            "users": user_counts
        }