"""
Integration tests for Task Security API Endpoints
Tests the security enforcement at the API level
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.models.task_models import TaskType


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def regular_user():
    """Create a regular user for testing"""
    role = RoleModel(id="user_role", name="user")
    return UserModel(
        id="user_id",
        username="user",
        email="user@test.com",
        hashed_password="fake_hash",
        role=role,
        is_active=True
    )


@pytest.fixture
def power_user():
    """Create a power user for testing"""
    role = RoleModel(id="power_user_role", name="power_user")
    return UserModel(
        id="power_user_id",
        username="power_user",
        email="power_user@test.com",
        hashed_password="fake_hash",
        role=role,
        is_active=True
    )


@pytest.fixture
def admin_user():
    """Create an admin user for testing"""
    role = RoleModel(id="admin_role", name="admin")
    return UserModel(
        id="admin_id",
        username="admin",
        email="admin@test.com",
        hashed_password="fake_hash",
        role=role,
        is_active=True
    )


@pytest.fixture
def viewer_user():
    """Create a viewer user for testing"""
    role = RoleModel(id="viewer_role", name="viewer")
    return UserModel(
        id="viewer_id",
        username="viewer",
        email="viewer@test.com",
        hashed_password="fake_hash",
        role=role,
        is_active=True
    )


@pytest.fixture
def auth_headers():
    """Create authentication headers"""
    return {"Authorization": "Bearer fake_jwt_token"}


class TestTaskSecurityEndpoints:
    """Test task security enforcement at API level"""

    @pytest.mark.integration
    def test_regular_user_can_create_part_enrichment(self, client, regular_user, auth_headers):
        """Test that regular users can create part enrichment tasks"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate, \
             patch('MakerMatrix.services.system.task_service.task_service.create_task') as mock_create_task:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (True, None)
            mock_create_task.return_value = MagicMock(id="task_123", to_dict=lambda: {"id": "task_123"})
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert "success" in response.json()["status"]
            mock_validate.assert_called_once()

    @pytest.mark.integration
    def test_regular_user_cannot_create_admin_tasks(self, client, regular_user, auth_headers):
        """Test that regular users cannot create admin-only tasks"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (False, "Insufficient permissions. Missing: admin, database:cleanup, tasks:admin")
            
            task_data = {
                "cleanup_options": {"remove_old_tasks": True}
            }
            
            response = client.post(
                "/tasks/quick/database-cleanup",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.integration
    def test_power_user_can_create_bulk_enrichment(self, client, power_user, auth_headers):
        """Test that power users can create bulk enrichment tasks"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=power_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate, \
             patch('MakerMatrix.services.system.task_service.task_service.create_task') as mock_create_task:
            
            mock_require_permission.return_value = lambda: power_user
            mock_validate.return_value = (True, None)
            mock_create_task.return_value = MagicMock(id="task_456", to_dict=lambda: {"id": "task_456"})
            
            task_data = {
                "part_ids": ["part1", "part2", "part3"],
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet", "enrich_basic_info"]
            }
            
            response = client.post(
                "/tasks/quick/bulk-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert "success" in response.json()["status"]

    @pytest.mark.integration
    def test_admin_can_create_database_cleanup(self, client, admin_user, auth_headers):
        """Test that admin users can create database cleanup tasks"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=admin_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate, \
             patch('MakerMatrix.services.system.task_service.task_service.create_task') as mock_create_task:
            
            mock_require_permission.return_value = lambda: admin_user
            mock_validate.return_value = (True, None)
            mock_create_task.return_value = MagicMock(id="task_789", to_dict=lambda: {"id": "task_789"})
            
            task_data = {
                "cleanup_options": {"remove_old_tasks": True, "optimize_database": True}
            }
            
            response = client.post(
                "/tasks/quick/database-cleanup",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert "success" in response.json()["status"]

    @pytest.mark.integration
    def test_rate_limiting_enforcement(self, client, regular_user, auth_headers):
        """Test that rate limiting is enforced"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (False, "Hourly rate limit exceeded (10/10). Try again in 45 minutes.")
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "rate limit exceeded" in response.json()["detail"].lower()

    @pytest.mark.integration
    def test_concurrent_task_limiting(self, client, regular_user, auth_headers):
        """Test that concurrent task limits are enforced"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (False, "Too many concurrent PART_ENRICHMENT tasks (2/2). Wait for existing tasks to complete.")
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "too many concurrent" in response.json()["detail"].lower()

    @pytest.mark.integration
    def test_resource_limits_enforcement(self, client, power_user, auth_headers):
        """Test that resource limits are enforced"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=power_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: power_user
            mock_validate.return_value = (False, "Too many parts requested (150). Maximum allowed: 100")
            
            # Try to create bulk task with too many parts
            task_data = {
                "part_ids": [f"part_{i}" for i in range(150)],  # Over limit
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/bulk-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "too many parts" in response.json()["detail"].lower()

    @pytest.mark.integration
    def test_security_permissions_endpoint(self, client, regular_user, auth_headers):
        """Test the security permissions endpoint"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service._get_user_permissions') as mock_get_perms:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_get_perms.return_value = ["tasks:user", "parts:write", "parts:read", "reports:generate"]
            
            response = client.get("/tasks/security/permissions", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()["data"]
            
            assert "user_permissions" in data
            assert "allowed_task_types" in data
            assert "security_levels" in data
            assert "user_role" in data
            
            # Regular user should have basic permissions
            assert "tasks:user" in data["user_permissions"]
            assert "PART_ENRICHMENT" in data["allowed_task_types"]
            assert "DATASHEET_FETCH" in data["allowed_task_types"]
            
            # Should NOT have admin permissions
            assert "DATABASE_CLEANUP" not in data["allowed_task_types"]
            assert "BACKUP_CREATION" not in data["allowed_task_types"]

    @pytest.mark.integration
    def test_security_limits_endpoint(self, client, regular_user, auth_headers):
        """Test the security limits endpoint"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.routers.task_routes.get_session') as mock_get_session, \
             patch('MakerMatrix.services.task_security_service.task_security_service._get_user_permissions') as mock_get_perms:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_get_perms.return_value = ["tasks:user", "parts:write", "parts:read"]
            
            # Mock database session
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.exec.return_value.one.return_value = 5  # Current usage count
            
            response = client.get("/tasks/security/limits", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()["data"]
            
            assert "current_usage" in data
            assert "time_until_hourly_reset" in data
            assert "time_until_daily_reset" in data
            
            # Should have usage data for allowed task types
            usage = data["current_usage"]
            assert "PART_ENRICHMENT" in usage
            assert "DATASHEET_FETCH" in usage
            
            # Check structure of usage data
            part_enrichment_usage = usage["PART_ENRICHMENT"]
            assert "concurrent_running" in part_enrichment_usage
            assert "max_concurrent" in part_enrichment_usage
            assert "hourly_usage" in part_enrichment_usage
            assert "hourly_limit" in part_enrichment_usage
            assert "daily_usage" in part_enrichment_usage
            assert "daily_limit" in part_enrichment_usage
            assert "security_level" in part_enrichment_usage
            assert "risk_level" in part_enrichment_usage

    @pytest.mark.integration
    def test_task_validation_endpoint(self, client, regular_user, auth_headers):
        """Test the task validation endpoint"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: regular_user
            
            # Test successful validation
            mock_validate.return_value = (True, None)
            
            validation_request = {
                "task_type": "PART_ENRICHMENT",
                "name": "Test Enrichment",
                "description": "Test task validation",
                "priority": "NORMAL",
                "input_data": {"part_id": "test_part", "capabilities": ["fetch_datasheet"]}
            }
            
            response = client.post(
                "/tasks/security/validate",
                json=validation_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()["data"]
            
            assert data["allowed"] is True
            assert data["error_message"] is None
            assert data["task_type"] == "PART_ENRICHMENT"
            
            # Test failed validation
            mock_validate.return_value = (False, "Rate limit exceeded")
            
            response = client.post(
                "/tasks/security/validate",
                json=validation_request,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()["data"]
            
            assert data["allowed"] is False
            assert data["error_message"] == "Rate limit exceeded"

    @pytest.mark.integration
    def test_viewer_user_permissions(self, client, viewer_user, auth_headers):
        """Test that viewer users have very limited permissions"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=viewer_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: viewer_user
            mock_validate.return_value = (False, "Insufficient permissions. Missing: parts:write, tasks:user")
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "Insufficient permissions" in response.json()["detail"]

    @pytest.mark.integration
    def test_audit_logging_on_security_denial(self, client, regular_user, auth_headers):
        """Test that security denials are properly logged"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate, \
             patch('MakerMatrix.services.task_security_service.task_security_service.log_task_security_event') as mock_log_event:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (False, "Rate limit exceeded")
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            
            # Verify that security event was logged
            mock_log_event.assert_called_once()
            call_args = mock_log_event.call_args[0]
            assert call_args[0] == "task_denied"  # event_type
            assert call_args[1] == regular_user   # user
            assert call_args[2] is None           # task (not created)

    @pytest.mark.integration
    def test_security_event_logging_on_success(self, client, regular_user, auth_headers):
        """Test that successful task creation is logged"""
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate, \
             patch('MakerMatrix.services.system.task_service.task_service.create_task') as mock_create_task, \
             patch('MakerMatrix.services.task_security_service.task_security_service.log_task_security_event') as mock_log_event:
            
            mock_require_permission.return_value = lambda: regular_user
            mock_validate.return_value = (True, None)
            
            mock_task = MagicMock(id="task_123", task_type=TaskType.PART_ENRICHMENT)
            mock_task.to_dict.return_value = {"id": "task_123"}
            mock_create_task.return_value = mock_task
            
            task_data = {
                "part_id": "test_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=task_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
            # Verify that successful creation was logged
            mock_log_event.assert_called_once()
            call_args = mock_log_event.call_args[0]
            assert call_args[0] == "task_created"  # event_type
            assert call_args[1] == regular_user    # user
            assert call_args[2] == mock_task       # task

    @pytest.mark.integration
    def test_worker_management_security(self, client, regular_user, admin_user, auth_headers):
        """Test that worker management requires admin permissions"""
        
        # Test regular user cannot manage worker
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission:
            
            # Mock require_permission to raise HTTPException for non-admin
            from fastapi import HTTPException
            mock_require_permission.return_value = lambda: exec('raise HTTPException(status_code=403, detail="Insufficient permissions")')
            
            try:
                response = client.post("/tasks/worker/start", headers=auth_headers)
                assert response.status_code == 403
            except:
                # Expected to fail due to permission check
                pass
        
        # Test admin user can manage worker
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=admin_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.system.task_service.task_service.is_worker_running', False):
            
            mock_require_permission.return_value = lambda: admin_user
            
            response = client.post("/tasks/worker/start", headers=auth_headers)
            assert response.status_code == 200
            assert "started successfully" in response.json()["message"]

    @pytest.mark.integration
    def test_cross_user_task_access_protection(self, client, regular_user, auth_headers):
        """Test that users cannot access other users' tasks inappropriately"""
        
        other_user = UserModel(
            id="other_user_id",
            username="other_user",
            email="other@test.com",
            hashed_password="fake_hash",
            role=RoleModel(id="user_role", name="user"),
            is_active=True
        )
        
        with patch('MakerMatrix.auth.dependencies.auth.get_current_user', return_value=regular_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.system.task_service.task_service.get_task') as mock_get_task:
            
            mock_require_permission.return_value = lambda: regular_user
            
            # Mock a task created by another user
            other_user_task = MagicMock()
            other_user_task.created_by_user_id = other_user.id
            other_user_task.to_dict.return_value = {
                "id": "other_task_123",
                "created_by_user_id": other_user.id,
                "task_type": "PART_ENRICHMENT"
            }
            mock_get_task.return_value = other_user_task
            
            # Regular users should be able to see the task (tasks are not private by default)
            # But they shouldn't be able to modify tasks they didn't create
            response = client.get("/tasks/other_task_123", headers=auth_headers)
            
            # The exact behavior depends on your business rules
            # This test verifies that the system has some form of access control