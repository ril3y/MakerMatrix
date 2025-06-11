"""
Unit tests for Task Security Service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from MakerMatrix.services.task_security_service import TaskSecurityService, TaskSecurityError
from MakerMatrix.models.task_models import TaskType, TaskStatus, CreateTaskRequest, TaskPriority
from MakerMatrix.models.task_security_model import TaskSecurityLevel, TaskRiskLevel
from MakerMatrix.models.user_models import UserModel, RoleModel


@pytest.fixture
def security_service():
    """Create a TaskSecurityService instance for testing"""
    return TaskSecurityService()


@pytest.fixture
def admin_user():
    """Create an admin user for testing"""
    role = RoleModel(id="admin_role", name="admin")
    user = UserModel(
        id="admin_user_id",
        username="admin",
        email="admin@test.com",
        hashed_password="fake_hash",
        is_active=True
    )
    user.roles = [role]
    return user


@pytest.fixture
def regular_user():
    """Create a regular user for testing"""
    role = RoleModel(id="user_role", name="user")
    user = UserModel(
        id="user_id",
        username="user",
        email="user@test.com",
        hashed_password="fake_hash",
        is_active=True
    )
    user.roles = [role]
    return user


@pytest.fixture
def power_user():
    """Create a power user for testing"""
    role = RoleModel(id="power_user_role", name="power_user")
    user = UserModel(
        id="power_user_id",
        username="power_user",
        email="power_user@test.com",
        hashed_password="fake_hash",
        is_active=True
    )
    user.roles = [role]
    return user


class TestTaskSecurityService:
    """Test cases for TaskSecurityService"""

    @pytest.mark.asyncio
    async def test_get_user_permissions_admin(self, security_service, admin_user):
        """Test that admin users get all permissions"""
        permissions = await security_service._get_user_permissions(admin_user)
        
        assert "admin" in permissions
        assert "tasks:admin" in permissions
        assert "tasks:power_user" in permissions
        assert "tasks:user" in permissions
        assert "parts:write" in permissions
        assert "parts:read" in permissions

    @pytest.mark.asyncio
    async def test_get_user_permissions_regular_user(self, security_service, regular_user):
        """Test that regular users get limited permissions"""
        permissions = await security_service._get_user_permissions(regular_user)
        
        assert "admin" not in permissions
        assert "tasks:admin" not in permissions
        assert "tasks:power_user" not in permissions
        assert "tasks:user" in permissions
        assert "parts:write" in permissions
        assert "parts:read" in permissions

    @pytest.mark.asyncio
    async def test_get_user_permissions_power_user(self, security_service, power_user):
        """Test that power users get elevated permissions"""
        permissions = await security_service._get_user_permissions(power_user)
        
        assert "admin" not in permissions
        assert "tasks:admin" not in permissions
        assert "tasks:power_user" in permissions
        assert "tasks:user" in permissions
        assert "parts:write" in permissions
        assert "csv:import" in permissions

    @pytest.mark.asyncio
    async def test_validate_task_creation_success(self, security_service, regular_user):
        """Test successful task creation validation"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={"part_id": "test_part"}
        )
        
        with patch.object(security_service, '_check_rate_limits', return_value=(True, None)), \
             patch.object(security_service, '_check_concurrent_limits', return_value=(True, None)):
            
            is_allowed, error_message = await security_service.validate_task_creation(task_request, regular_user)
            
            assert is_allowed is True
            assert error_message is None

    @pytest.mark.asyncio
    async def test_validate_task_creation_insufficient_permissions(self, security_service, regular_user):
        """Test task creation validation with insufficient permissions"""
        task_request = CreateTaskRequest(
            task_type=TaskType.DATABASE_CLEANUP,  # Admin-only task
            name="Test cleanup",
            description="Test description",
            priority=TaskPriority.NORMAL
        )
        
        is_allowed, error_message = await security_service.validate_task_creation(task_request, regular_user)
        
        assert is_allowed is False
        assert "Insufficient permissions" in error_message
        assert "admin" in error_message

    @pytest.mark.asyncio
    async def test_validate_task_creation_rate_limit_exceeded(self, security_service, regular_user):
        """Test task creation validation with rate limit exceeded"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={"part_id": "test_part"}
        )
        
        with patch.object(security_service, '_check_rate_limits', return_value=(False, "Rate limit exceeded")), \
             patch.object(security_service, '_check_concurrent_limits', return_value=(True, None)):
            
            is_allowed, error_message = await security_service.validate_task_creation(task_request, regular_user)
            
            assert is_allowed is False
            assert "Rate limit exceeded" in error_message

    @pytest.mark.asyncio
    async def test_validate_task_creation_concurrent_limit_exceeded(self, security_service, regular_user):
        """Test task creation validation with concurrent limit exceeded"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={"part_id": "test_part"}
        )
        
        with patch.object(security_service, '_check_rate_limits', return_value=(True, None)), \
             patch.object(security_service, '_check_concurrent_limits', return_value=(False, "Too many concurrent tasks")):
            
            is_allowed, error_message = await security_service.validate_task_creation(task_request, regular_user)
            
            assert is_allowed is False
            assert "Too many concurrent tasks" in error_message

    def test_check_resource_limits_success(self, security_service):
        """Test resource limits checking with valid input"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={"part_id": "test_part", "capabilities": ["fetch_datasheet"]}
        )
        
        from MakerMatrix.models.task_security_model import get_task_security_policy
        policy = get_task_security_policy(TaskType.PART_ENRICHMENT)
        
        is_allowed, error_message = security_service._check_resource_limits(task_request, policy)
        
        assert is_allowed is True
        assert error_message is None

    def test_check_resource_limits_too_many_parts(self, security_service):
        """Test resource limits checking with too many parts"""
        task_request = CreateTaskRequest(
            task_type=TaskType.BULK_ENRICHMENT,
            name="Test bulk enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={"part_ids": ["part_" + str(i) for i in range(150)]}  # Over limit
        )
        
        from MakerMatrix.models.task_security_model import get_task_security_policy
        policy = get_task_security_policy(TaskType.BULK_ENRICHMENT)
        
        is_allowed, error_message = security_service._check_resource_limits(task_request, policy)
        
        assert is_allowed is False
        assert "Too many parts requested" in error_message

    def test_check_resource_limits_too_many_capabilities(self, security_service):
        """Test resource limits checking with too many capabilities"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL,
            input_data={
                "part_id": "test_part",
                "capabilities": ["cap_" + str(i) for i in range(10)]  # Over limit
            }
        )
        
        from MakerMatrix.models.task_security_model import get_task_security_policy
        policy = get_task_security_policy(TaskType.PART_ENRICHMENT)
        
        is_allowed, error_message = security_service._check_resource_limits(task_request, policy)
        
        assert is_allowed is False
        assert "Too many capabilities requested" in error_message

    @pytest.mark.asyncio
    async def test_log_task_security_event(self, security_service, regular_user):
        """Test security event logging"""
        with patch('MakerMatrix.services.task_security_service.logger') as mock_logger:
            await security_service.log_task_security_event(
                "task_created",
                regular_user,
                None,
                {"task_type": "PART_ENRICHMENT"}
            )
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Task Security Event: task_created" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_check_rate_limits_mock_database(self, security_service, regular_user):
        """Test rate limits checking with mocked database"""
        from MakerMatrix.models.task_security_model import get_task_security_policy
        policy = get_task_security_policy(TaskType.PART_ENRICHMENT)
        
        # Mock the database session and query results
        with patch('MakerMatrix.services.task_security_service.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            # Mock query results - return count of 5 (under hourly limit of 10)
            mock_session.exec.return_value.one.return_value = 5
            
            is_allowed, error_message = await security_service._check_rate_limits(regular_user.id, policy)
            
            assert is_allowed is True
            assert error_message is None

    @pytest.mark.asyncio
    async def test_check_concurrent_limits_mock_database(self, security_service, regular_user):
        """Test concurrent limits checking with mocked database"""
        from MakerMatrix.models.task_security_model import get_task_security_policy
        policy = get_task_security_policy(TaskType.PART_ENRICHMENT)
        
        # Mock the database session and query results
        with patch('MakerMatrix.services.task_security_service.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            
            # Mock query results - return count of 1 (under limit of 2)
            mock_session.exec.return_value.one.return_value = 1
            
            is_allowed, error_message = await security_service._check_concurrent_limits(
                regular_user.id, TaskType.PART_ENRICHMENT, policy
            )
            
            assert is_allowed is True
            assert error_message is None

    @pytest.mark.asyncio
    async def test_approval_status_check(self, security_service, regular_user):
        """Test approval status checking"""
        task_request = CreateTaskRequest(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test enrichment",
            description="Test description",
            priority=TaskPriority.NORMAL
        )
        
        is_allowed, error_message = await security_service._check_approval_status(task_request, regular_user)
        
        # Currently returns True by default
        assert is_allowed is True
        assert error_message is None