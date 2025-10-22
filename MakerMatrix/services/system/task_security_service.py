"""
Task Security Service - Enforces security policies for task creation and execution
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from MakerMatrix.services.base_service import BaseService
from MakerMatrix.repositories.task_repository import TaskRepository
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus, CreateTaskRequest
from MakerMatrix.models.task_security_model import (
    get_task_security_policy,
    TaskSecurityPolicy,
    TaskSecurityLevel,
    is_task_allowed_for_user,
    get_user_allowed_task_types,
)
from MakerMatrix.models.user_models import UserModel

logger = logging.getLogger(__name__)


class TaskSecurityError(Exception):
    """Raised when task security validation fails"""

    pass


class TaskSecurityService(BaseService):
    """Service for enforcing task security policies"""

    def __init__(self):
        super().__init__()
        self._rate_limit_cache: Dict[str, List[datetime]] = {}
        self._concurrent_tasks_cache: Dict[str, int] = {}
        self.task_repo = TaskRepository()

    async def validate_task_creation(
        self, task_request: CreateTaskRequest, user: UserModel
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a user can create a specific task.

        Returns:
            Tuple of (is_allowed, error_message)
        """
        try:
            # Get security policy for task type
            policy = get_task_security_policy(task_request.task_type)
            if not policy:
                return False, (
                    f"Security policy not configured for task type: {task_request.task_type.value}. "
                    f"This task type may not be available or requires system configuration. "
                    f"Please contact your system administrator."
                )

            # Check user permissions
            user_permissions = await self._get_user_permissions(user)
            if not is_task_allowed_for_user(task_request.task_type, user_permissions):
                missing_perms = [p for p in policy.required_permissions if p not in user_permissions]
                # Enhanced error message with actionable information
                error_msg = (
                    f"Insufficient permissions to create {task_request.task_type.value} task. "
                    f"Missing: {', '.join(missing_perms)}. "
                    f"Current role(s): {', '.join([r.name for r in user.roles]) if user.roles else 'None'}. "
                    f"Contact your administrator to request the necessary permissions."
                )
                return False, error_msg

            # Check rate limits (admin users are exempt)
            rate_limit_ok, rate_limit_msg = await self._check_rate_limits(user, policy, task_request.task_type)
            if not rate_limit_ok:
                return False, rate_limit_msg

            # Check concurrent task limits
            concurrent_ok, concurrent_msg = await self._check_concurrent_limits(user.id, task_request.task_type, policy)
            if not concurrent_ok:
                return False, concurrent_msg

            # Check resource limits
            resource_ok, resource_msg = self._check_resource_limits(task_request, policy)
            if not resource_ok:
                return False, resource_msg

            # Check approval requirements
            if policy.requires_approval:
                approval_ok, approval_msg = await self._check_approval_status(task_request, user)
                if not approval_ok:
                    return False, approval_msg

            return True, None

        except Exception as e:
            logger.error(f"Error validating task creation: {e}", exc_info=True)
            return False, f"Security validation error: {str(e)}"

    async def _get_user_permissions(self, user: UserModel) -> List[str]:
        """Get user permissions (integrate with your auth system)"""
        permissions = []

        # Add role-based permissions
        if user.roles:
            for role in user.roles:
                if role.name == "admin":
                    permissions.extend(
                        [
                            "admin",
                            "tasks:admin",
                            "tasks:power_user",
                            "tasks:user",
                            "parts:write",
                            "parts:read",
                            "csv:import",
                            "pricing:update",
                            "database:cleanup",
                            "backup:create",
                            "backup:restore",
                            "backup:manage",
                            "reports:generate",
                        ]
                    )
                elif role.name == "power_user":
                    permissions.extend(
                        [
                            "tasks:power_user",
                            "tasks:user",
                            "parts:write",
                            "parts:read",
                            "csv:import",
                            "pricing:update",
                            "reports:generate",
                        ]
                    )
                elif role.name == "user":
                    permissions.extend(["tasks:user", "parts:write", "parts:read", "reports:generate"])
                elif role.name == "viewer":
                    permissions.extend(["parts:read", "tools:read", "dashboard:view"])
                else:
                    # For custom roles, use the role.permissions field
                    if hasattr(role, 'permissions') and role.permissions:
                        permissions.extend(role.permissions)

        # Add any specific user permissions here
        # You could extend this to check a user_permissions table

        return list(set(permissions))  # Remove duplicates

    async def _check_rate_limits(
        self, user: UserModel, policy: TaskSecurityPolicy, task_type: TaskType
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has exceeded rate limits.

        Admin users are exempt from rate limits.
        """
        # Admin users are exempt from rate limits
        if user.roles:
            for role in user.roles:
                if role.name == "admin":
                    logger.info(f"Admin user {user.username} exempt from rate limits for {task_type.value}")
                    return True, None

        if not policy.rate_limit_per_hour and not policy.rate_limit_per_day:
            return True, None

        with self.get_session() as session:
            now = datetime.utcnow()

            # Check hourly rate limit
            if policy.rate_limit_per_hour:
                hour_ago = now - timedelta(hours=1)
                hourly_count = self.task_repo.count_tasks_by_user_and_timeframe(session, user.id, task_type, hour_ago)

                if hourly_count >= policy.rate_limit_per_hour:
                    return (
                        False,
                        f"Hourly rate limit exceeded for {task_type.value} tasks. "
                        f"You've created {hourly_count} of {policy.rate_limit_per_hour} allowed tasks this hour. "
                        f"Try again in approximately {60 - now.minute} minutes, or wait for existing tasks to complete.",
                    )

            # Check daily rate limit
            if policy.rate_limit_per_day:
                day_ago = now - timedelta(days=1)
                daily_count = self.task_repo.count_tasks_by_user_and_timeframe(session, user.id, task_type, day_ago)

                if daily_count >= policy.rate_limit_per_day:
                    hours_until_reset = 24 - now.hour
                    return (
                        False,
                        f"Daily rate limit exceeded for {task_type.value} tasks. "
                        f"You've created {daily_count} of {policy.rate_limit_per_day} allowed tasks today. "
                        f"Limit will reset in approximately {hours_until_reset} hours.",
                    )

            return True, None

    async def _check_concurrent_limits(
        self, user_id: str, task_type: TaskType, policy: TaskSecurityPolicy
    ) -> Tuple[bool, Optional[str]]:
        """Check if user has too many concurrent tasks"""
        with self.get_session() as session:
            running_count = self.task_repo.count_concurrent_tasks_by_user_and_type(session, user_id, task_type)

            if running_count >= policy.max_concurrent_per_user:
                return (
                    False,
                    f"Concurrent task limit reached for {task_type.value} tasks. "
                    f"You currently have {running_count} active task(s), maximum allowed is {policy.max_concurrent_per_user}. "
                    f"Please wait for your existing tasks to complete before creating new ones, or check /api/tasks to monitor progress.",
                )

            return True, None

    def _check_resource_limits(
        self, task_request: CreateTaskRequest, policy: TaskSecurityPolicy
    ) -> Tuple[bool, Optional[str]]:
        """Check if task request exceeds resource limits"""
        if not policy.resource_limits:
            return True, None

        input_data = task_request.input_data or {}

        # Check max_parts limit
        if "max_parts" in policy.resource_limits:
            max_parts = policy.resource_limits["max_parts"]

            # Check different ways parts might be specified
            part_count = 0
            if "part_ids" in input_data:
                part_count = len(input_data["part_ids"])
            elif "part_id" in input_data:
                part_count = 1

            if part_count > max_parts:
                return False, (
                    f"Resource limit exceeded: You requested {part_count} part(s), but the maximum allowed is {max_parts}. "
                    f"Please reduce the number of parts in your request or split into multiple smaller tasks."
                )

        # Check batch_size limit
        if "batch_size" in policy.resource_limits:
            max_batch = policy.resource_limits["batch_size"]
            batch_size = input_data.get("batch_size", 1)

            if batch_size > max_batch:
                return False, (
                    f"Batch size limit exceeded: You requested batch size of {batch_size}, but the maximum allowed is {max_batch}. "
                    f"Please reduce your batch size parameter."
                )

        # Check max_capabilities limit
        if "max_capabilities" in policy.resource_limits:
            max_caps = policy.resource_limits["max_capabilities"]
            capabilities = input_data.get("capabilities", [])

            if len(capabilities) > max_caps:
                return False, (
                    f"Capabilities limit exceeded: You requested {len(capabilities)} capabilities, but the maximum allowed is {max_caps}. "
                    f"Please reduce the number of enrichment capabilities in your request."
                )

        return True, None

    async def _check_approval_status(
        self, task_request: CreateTaskRequest, user: UserModel
    ) -> Tuple[bool, Optional[str]]:
        """Check if task requires approval and if it's approved"""
        # For now, return True. In the future, implement approval workflow
        # You could have an approval_requests table and check status
        return True, None

    async def log_task_security_event(self, event_type: str, user: UserModel, task: TaskModel, details: Dict = None):
        """Log security events for audit purposes"""
        # Implement audit logging here
        # Could write to a security_audit_log table

        audit_entry = {
            "timestamp": datetime.utcnow(),
            "event_type": event_type,  # "task_created", "task_denied", "rate_limit_hit", etc.
            "user_id": user.id,
            "username": user.username,
            "task_id": task.id if task else None,
            "task_type": task.task_type if task else None,
            "details": details or {},
        }

        # For now, just log to application logs
        logger.info(f"Task Security Event: {event_type}", extra=audit_entry)

    def get_user_task_limits_summary(self, user: UserModel) -> Dict[str, any]:
        """Get summary of user's task limits and current usage"""
        # This would return current usage vs limits for the user
        # Useful for UI to show users their current status
        return {
            "allowed_task_types": [],  # Would be populated with actual data
            "current_usage": {},
            "limits": {},
            "time_until_reset": {},
        }


# Global instance
task_security_service = TaskSecurityService()
