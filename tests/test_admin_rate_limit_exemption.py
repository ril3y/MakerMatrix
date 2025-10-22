"""
Test that admin users are exempt from rate limits.

This test verifies the fix for the user's request:
- Rate limits should not return 500 (already fixed - returns 429)
- Admin users should be exempt from rate limits (this test)
"""

import pytest
from unittest.mock import Mock, patch
from MakerMatrix.services.system.task_security_service import TaskSecurityService
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.models.task_models import TaskType, CreateTaskRequest, TaskPriority
from MakerMatrix.models.task_security_model import get_task_security_policy


class TestAdminRateLimitExemption:
    """Test admin exemption from rate limits"""

    @pytest.mark.asyncio
    async def test_admin_user_exempt_from_rate_limits(self):
        """Test that admin users bypass rate limits"""
        # Create admin user
        admin_role = Mock(spec=RoleModel)
        admin_role.name = "admin"

        admin_user = Mock(spec=UserModel)
        admin_user.id = "admin-123"
        admin_user.username = "admin_user"
        admin_user.roles = [admin_role]

        # Create task security service
        service = TaskSecurityService()

        # Get policy for backup task (has strict rate limits)
        policy = get_task_security_policy(TaskType.BACKUP_CREATION)
        assert policy.rate_limit_per_hour == 2  # Backup has strict limits

        # Call rate limit check directly
        rate_limit_ok, rate_limit_msg = await service._check_rate_limits(admin_user, policy, TaskType.BACKUP_CREATION)

        # Admin should pass rate limit check
        assert rate_limit_ok is True
        assert rate_limit_msg is None

    @pytest.mark.asyncio
    async def test_regular_user_subject_to_rate_limits(self):
        """Test that regular users are still subject to rate limits"""
        # Create regular user
        user_role = Mock(spec=RoleModel)
        user_role.name = "user"

        regular_user = Mock(spec=UserModel)
        regular_user.id = "user-456"
        regular_user.username = "regular_user"
        regular_user.roles = [user_role]

        # Create task security service
        service = TaskSecurityService()

        # Get policy for backup task
        policy = get_task_security_policy(TaskType.BACKUP_CREATION)

        # Mock the task repository to simulate that user has exceeded rate limit
        with patch.object(service.task_repo, "count_tasks_by_user_and_timeframe") as mock_count:
            mock_count.return_value = 10  # Exceeds the hourly limit of 2

            # Call rate limit check
            rate_limit_ok, rate_limit_msg = await service._check_rate_limits(
                regular_user, policy, TaskType.BACKUP_CREATION
            )

            # Regular user should fail rate limit check
            assert rate_limit_ok is False
            assert "rate limit exceeded" in rate_limit_msg.lower()
            assert "2" in rate_limit_msg  # Should mention the limit

    @pytest.mark.asyncio
    async def test_admin_validation_still_works_end_to_end(self):
        """Test that admin users can create tasks that would be rate limited for others"""
        # Create admin user
        admin_role = Mock(spec=RoleModel)
        admin_role.name = "admin"

        admin_user = Mock(spec=UserModel)
        admin_user.id = "admin-789"
        admin_user.username = "admin_test"
        admin_user.roles = [admin_role]

        # Create task request
        task_request = CreateTaskRequest(
            task_type=TaskType.BACKUP_CREATION,
            name="Test Backup",
            description="Test backup task",
            priority=TaskPriority.HIGH,
            input_data={"backup_name": "test_backup"},
        )

        # Create task security service
        service = TaskSecurityService()

        # Mock task repository to simulate exceeding rate limits (but not concurrent limits)
        with patch.object(service.task_repo, "count_tasks_by_user_and_timeframe") as mock_count:
            with patch.object(service.task_repo, "count_concurrent_tasks_by_user_and_type") as mock_concurrent:
                # Simulate that admin has many tasks (would exceed rate limits for regular users)
                mock_count.return_value = 100  # Way over hourly rate limit
                mock_concurrent.return_value = 0  # No concurrent tasks (within limit)

                # Validate task creation
                is_allowed, error_msg = await service.validate_task_creation(task_request, admin_user)

                # Admin should be allowed despite high task count
                assert is_allowed is True
                assert error_msg is None

    @pytest.mark.asyncio
    async def test_regular_user_blocked_by_rate_limit(self):
        """Test that regular users are blocked when exceeding rate limits"""
        # Create regular user
        user_role = Mock(spec=RoleModel)
        user_role.name = "user"

        regular_user = Mock(spec=UserModel)
        regular_user.id = "user-999"
        regular_user.username = "regular_test"
        regular_user.roles = [user_role]

        # Create task request - use PART_ENRICHMENT which regular users CAN create
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test Enrichment",
            description="Test part enrichment task",
            priority=TaskPriority.NORMAL,
            input_data={"part_id": "test-part-123", "capabilities": ["GET_PART_DETAILS"]},
        )

        # Create task security service
        service = TaskSecurityService()

        # Mock task repository to simulate exceeding limits
        with patch.object(service.task_repo, "count_tasks_by_user_and_timeframe") as mock_count:
            with patch.object(service.task_repo, "count_concurrent_tasks_by_user_and_type") as mock_concurrent:
                # Simulate that user has exceeded hourly rate limit (30 is the limit)
                mock_count.return_value = 50  # Over the limit of 30
                mock_concurrent.return_value = 0  # No concurrent tasks

                # Validate task creation
                is_allowed, error_msg = await service.validate_task_creation(task_request, regular_user)

                # Regular user should be blocked
                assert is_allowed is False
                assert error_msg is not None
                assert "rate limit" in error_msg.lower()
