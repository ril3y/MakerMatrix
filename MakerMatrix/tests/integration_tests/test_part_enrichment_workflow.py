"""
Integration tests for Part Enrichment Workflow
Tests the complete enrichment process from API to database
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from MakerMatrix.main import app
from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import PartModel
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus
from MakerMatrix.services.task_service import task_service


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user with appropriate permissions"""
    role = RoleModel(id="user_role", name="user")
    return UserModel(
        id="test_user_id",
        username="testuser",
        email="test@example.com",
        hashed_password="fake_hash",
        role=role,
        is_active=True
    )


@pytest.fixture
def test_part():
    """Create a test part for enrichment"""
    return PartModel(
        id="test_part_id",
        name="Test Resistor 1k",
        part_number="RES-1K-0603",
        description="1k ohm resistor, 0603 package",
        quantity=100,
        supplier="LCSC",
        part_vendor="LCSC",
        properties={"value": "1k", "package": "0603", "tolerance": "5%"}
    )


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test requests"""
    # Mock JWT token for the test user
    return {"Authorization": "Bearer fake_jwt_token"}


class TestPartEnrichmentWorkflow:
    """Integration tests for the complete part enrichment workflow"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_enrichment_workflow(self, client, test_user, test_part, auth_headers):
        """Test the complete enrichment workflow from API call to completion"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.database.db.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            # Setup mocks
            mock_require_permission.return_value = lambda: test_user
            
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = test_part
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.perform_enrichment_task.return_value = {
                "fetch_datasheet": {
                    "success": True,
                    "data": {
                        "datasheet_url": "https://lcsc.com/datasheet/resistor_1k.pdf",
                        "file_path": "/static/datasheets/resistor_1k.pdf"
                    }
                },
                "fetch_image": {
                    "success": True,
                    "data": {
                        "image_url": "https://lcsc.com/images/resistor_1k.jpg",
                        "file_path": "/static/images/resistor_1k.jpg"
                    }
                },
                "enrich_basic_info": {
                    "success": True,
                    "data": {
                        "manufacturer": "Yageo",
                        "manufacturer_part_number": "RC0603FR-071KL",
                        "category": "Resistors",
                        "detailed_description": "1 kOhms ±1% 0.1W, 1/10W Chip Resistor 0603"
                    }
                }
            }
            
            # Step 1: Create enrichment task via API
            enrichment_data = {
                "part_id": test_part.id,
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet", "fetch_image", "enrich_basic_info"],
                "force_refresh": True
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=enrichment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            task_data = response.json()
            assert task_data["status"] == "success"
            assert "data" in task_data
            
            task_id = task_data["data"]["id"]
            
            # Step 2: Verify task was created correctly
            response = client.get(f"/tasks/{task_id}", headers=auth_headers)
            assert response.status_code == 200
            
            task_info = response.json()["data"]
            assert task_info["task_type"] == "PART_ENRICHMENT"
            assert task_info["status"] == "PENDING"
            assert task_info["input_data"]["part_id"] == test_part.id
            
            # Step 3: Simulate task processing
            # In a real scenario, the task worker would pick this up
            # For testing, we'll manually execute the task handler
            
            with patch('MakerMatrix.services.task_service.task_service.get_task') as mock_get_task:
                mock_task = TaskModel(
                    id=task_id,
                    task_type=TaskType.PART_ENRICHMENT,
                    name="Test Enrichment",
                    status=TaskStatus.PENDING,
                    created_by_user_id=test_user.id,
                    input_data=enrichment_data
                )
                mock_get_task.return_value = mock_task
                
                # Execute the enrichment
                from MakerMatrix.services.enrichment_task_handlers import handle_part_enrichment
                
                progress_callback = AsyncMock()
                result = await handle_part_enrichment(mock_task, progress_callback)
                
                # Verify enrichment results
                assert result["success"] is True
                assert "enrichment_summary" in result
                
                enrichment_summary = result["enrichment_summary"]
                assert enrichment_summary["successful_count"] == 3
                assert enrichment_summary["failed_count"] == 0
                
                # Verify individual capability results
                results = enrichment_summary["results"]
                assert "fetch_datasheet" in results
                assert "fetch_image" in results
                assert "enrich_basic_info" in results
                
                assert results["fetch_datasheet"]["success"] is True
                assert results["fetch_image"]["success"] is True
                assert results["enrich_basic_info"]["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_enrichment_with_security_validation(self, client, test_user, test_part, auth_headers):
        """Test enrichment with security validation"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
            
            mock_require_permission.return_value = lambda: test_user
            
            # Test successful validation
            mock_validate.return_value = (True, None)
            
            enrichment_data = {
                "part_id": test_part.id,
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"],
                "force_refresh": True
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=enrichment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_validate.assert_called_once()
            
            # Test failed validation (rate limit exceeded)
            mock_validate.return_value = (False, "Rate limit exceeded")
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=enrichment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert "Rate limit exceeded" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_supplier_capabilities_discovery(self, client, auth_headers, test_user):
        """Test supplier capabilities discovery via API"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission:
            
            mock_require_permission.return_value = lambda: test_user
            
            # Test getting all supplier capabilities
            response = client.get("/tasks/capabilities/suppliers", headers=auth_headers)
            assert response.status_code == 200
            
            capabilities_data = response.json()["data"]
            assert "LCSC" in capabilities_data
            assert "Mouser" in capabilities_data
            assert "DigiKey" in capabilities_data
            assert "BoltDepot" in capabilities_data
            
            # Verify LCSC capabilities structure
            lcsc_caps = capabilities_data["LCSC"]
            assert "supplier_name" in lcsc_caps
            assert "supported_capabilities" in lcsc_caps
            assert "total_capabilities" in lcsc_caps
            assert lcsc_caps["supplier_name"] == "LCSC"
            
            # Test getting specific supplier capabilities
            response = client.get("/tasks/capabilities/suppliers/LCSC", headers=auth_headers)
            assert response.status_code == 200
            
            lcsc_specific = response.json()["data"]
            assert lcsc_specific["supplier_name"] == "LCSC"
            assert len(lcsc_specific["supported_capabilities"]) > 0
            
            # Test finding suppliers with specific capability
            response = client.get("/tasks/capabilities/find/fetch_datasheet", headers=auth_headers)
            assert response.status_code == 200
            
            suppliers_with_datasheet = response.json()["data"]
            assert "capability" in suppliers_with_datasheet
            assert "suppliers" in suppliers_with_datasheet
            assert suppliers_with_datasheet["capability"] == "fetch_datasheet"
            
            # Electronic suppliers should support datasheets
            assert "LCSC" in suppliers_with_datasheet["suppliers"]
            assert "Mouser" in suppliers_with_datasheet["suppliers"]
            assert "DigiKey" in suppliers_with_datasheet["suppliers"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_bulk_enrichment_workflow(self, client, test_user, auth_headers):
        """Test bulk enrichment workflow"""
        
        # Create multiple test parts
        test_parts = [
            PartModel(id=f"part_{i}", name=f"Part {i}", part_number=f"P{i:03d}")
            for i in range(1, 4)
        ]
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.database.db.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_require_permission.return_value = lambda: test_user
            
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            
            # Mock session.get to return different parts for different IDs
            def mock_get(model_class, part_id):
                for part in test_parts:
                    if part.id == part_id:
                        return part
                return None
                
            mock_session.get.side_effect = mock_get
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.perform_enrichment_task.return_value = {
                "fetch_datasheet": {"success": True, "data": {"datasheet_url": "test.pdf"}},
                "enrich_basic_info": {"success": True, "data": {"manufacturer": "Test Corp"}}
            }
            
            # Create bulk enrichment task
            bulk_data = {
                "part_ids": [part.id for part in test_parts],
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet", "enrich_basic_info"],
                "batch_size": 2
            }
            
            response = client.post(
                "/tasks/quick/bulk-enrichment",
                json=bulk_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            task_data = response.json()
            assert task_data["status"] == "success"
            
            # Verify task details
            task_info = task_data["data"]
            assert task_info["task_type"] == "BULK_ENRICHMENT"
            assert task_info["input_data"]["batch_size"] == 2
            assert len(task_info["input_data"]["part_ids"]) == 3

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_progress_tracking(self, client, test_user, test_part, auth_headers):
        """Test task progress tracking functionality"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.database.db.get_session') as mock_get_session:
            
            mock_require_permission.return_value = lambda: test_user
            
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = test_part
            
            # Create enrichment task
            enrichment_data = {
                "part_id": test_part.id,
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"],
                "force_refresh": True
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=enrichment_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            task_id = response.json()["data"]["id"]
            
            # Test getting task details
            response = client.get(f"/tasks/{task_id}", headers=auth_headers)
            assert response.status_code == 200
            
            task_info = response.json()["data"]
            assert "progress_percentage" in task_info
            assert "current_step" in task_info
            assert "status" in task_info
            
            # Test getting user's tasks
            response = client.get("/tasks/my", headers=auth_headers)
            assert response.status_code == 200
            
            user_tasks = response.json()["data"]
            assert len(user_tasks) >= 1
            
            # Find our task in the user's tasks
            our_task = next((task for task in user_tasks if task["id"] == task_id), None)
            assert our_task is not None
            assert our_task["task_type"] == "PART_ENRICHMENT"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_enrichment_error_handling(self, client, test_user, auth_headers):
        """Test enrichment error handling scenarios"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission, \
             patch('MakerMatrix.database.db.get_session') as mock_get_session:
            
            mock_require_permission.return_value = lambda: test_user
            
            mock_session = AsyncMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = None  # Part not found
            
            # Test enrichment with non-existent part
            enrichment_data = {
                "part_id": "non_existent_part",
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"],
                "force_refresh": True
            }
            
            response = client.post(
                "/tasks/quick/part-enrichment",
                json=enrichment_data,
                headers=auth_headers
            )
            
            # Task should be created but will fail during execution
            assert response.status_code == 200
            task_id = response.json()["data"]["id"]
            
            # Manually execute the task to test error handling
            with patch('MakerMatrix.services.task_service.task_service.get_task') as mock_get_task:
                mock_task = TaskModel(
                    id=task_id,
                    task_type=TaskType.PART_ENRICHMENT,
                    name="Test Enrichment",
                    status=TaskStatus.PENDING,
                    created_by_user_id=test_user.id,
                    input_data=enrichment_data
                )
                mock_get_task.return_value = mock_task
                
                from MakerMatrix.services.enrichment_task_handlers import handle_part_enrichment
                
                progress_callback = AsyncMock()
                result = await handle_part_enrichment(mock_task, progress_callback)
                
                # Should fail gracefully
                assert result["success"] is False
                assert "Part not found" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_security_endpoints(self, client, test_user, auth_headers):
        """Test task security-related endpoints"""
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=test_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission:
            
            mock_require_permission.return_value = lambda: test_user
            
            # Test getting user permissions
            response = client.get("/tasks/security/permissions", headers=auth_headers)
            assert response.status_code == 200
            
            permissions_data = response.json()["data"]
            assert "user_permissions" in permissions_data
            assert "allowed_task_types" in permissions_data
            assert "security_levels" in permissions_data
            assert "user_role" in permissions_data
            
            # Regular user should have basic permissions
            assert "tasks:user" in permissions_data["user_permissions"]
            assert "PART_ENRICHMENT" in permissions_data["allowed_task_types"]
            
            # Test getting user limits
            with patch('MakerMatrix.routers.task_routes.get_session') as mock_get_session, \
                 patch('MakerMatrix.services.task_security_service.task_security_service._get_user_permissions') as mock_get_perms:
                
                mock_session = AsyncMock()
                mock_get_session.return_value = mock_session
                mock_session.__enter__.return_value = mock_session
                mock_session.__exit__.return_value = None
                mock_session.exec.return_value.one.return_value = 0  # No current usage
                
                mock_get_perms.return_value = ["tasks:user", "parts:write", "parts:read"]
                
                response = client.get("/tasks/security/limits", headers=auth_headers)
                assert response.status_code == 200
                
                limits_data = response.json()["data"]
                assert "current_usage" in limits_data
                assert "time_until_hourly_reset" in limits_data
                assert "time_until_daily_reset" in limits_data
            
            # Test task validation
            validation_request = {
                "task_type": "PART_ENRICHMENT",
                "name": "Test Validation",
                "description": "Test task validation",
                "priority": "NORMAL",
                "input_data": {"part_id": "test_part"}
            }
            
            with patch('MakerMatrix.services.task_security_service.task_security_service.validate_task_creation') as mock_validate:
                mock_validate.return_value = (True, None)
                
                response = client.post(
                    "/tasks/security/validate",
                    json=validation_request,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                validation_data = response.json()["data"]
                assert validation_data["allowed"] is True
                assert validation_data["error_message"] is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_worker_management(self, client, auth_headers):
        """Test task worker management endpoints"""
        
        # Create admin user for worker management
        admin_role = RoleModel(id="admin_role", name="admin")
        admin_user = UserModel(
            id="admin_user_id",
            username="admin",
            email="admin@test.com",
            hashed_password="fake_hash",
            role=admin_role,
            is_active=True
        )
        
        with patch('MakerMatrix.dependencies.auth.get_current_user', return_value=admin_user), \
             patch('MakerMatrix.routers.task_routes.require_permission') as mock_require_permission:
            
            mock_require_permission.return_value = lambda: admin_user
            
            # Test getting worker status
            response = client.get("/tasks/worker/status", headers=auth_headers)
            assert response.status_code == 200
            
            worker_status = response.json()["data"]
            assert "is_running" in worker_status
            assert "running_tasks_count" in worker_status
            assert "registered_handlers" in worker_status
            
            # Test starting worker
            with patch('MakerMatrix.services.task_service.task_service.is_worker_running', False):
                response = client.post("/tasks/worker/start", headers=auth_headers)
                assert response.status_code == 200
                assert "started successfully" in response.json()["message"]
            
            # Test stopping worker
            with patch('MakerMatrix.services.task_service.task_service.is_worker_running', True):
                response = client.post("/tasks/worker/stop", headers=auth_headers)
                assert response.status_code == 200
                assert "stopped successfully" in response.json()["message"]