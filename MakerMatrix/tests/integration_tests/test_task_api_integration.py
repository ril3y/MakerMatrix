"""
Integration tests for task API endpoints
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from MakerMatrix.main import app
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_user():
    """Get the admin user for authentication tests."""
    user_repo = UserRepository()
    user = user_repo.get_user_by_username("admin")
    if not user:
        raise ValueError("Admin user not found. Make sure setup_database fixture is running.")
    return user


@pytest.fixture
def auth_token(test_user):
    """Get an authentication token for the test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": test_user.username})
    return token


def test_part_enrichment_api_endpoint(auth_token):
    """Test that the part enrichment API endpoint works"""
    
    # Create a test part first
    with Session(engine) as session:
        test_part = PartModel(
            part_name="API Test Resistor",
            part_number="RES-API-TEST",
            part_vendor="LCSC"
        )
        session.add(test_part)
        session.commit()
        session.refresh(test_part)
        test_part_id = test_part.id
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test part enrichment task creation
        enrichment_data = {
            "part_id": test_part_id,
            "supplier": "LCSC"
        }
        
        response = client.post(
            "/api/tasks/quick/part_enrichment",
            json=enrichment_data,
            headers=headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["task_type"] == "part_enrichment"
        
        task_id = result["data"]["id"]
        
        # Check task status
        task_response = client.get(
            f"/api/tasks/{task_id}",
            headers=headers
        )
        
        assert task_response.status_code == 200
        task_data = task_response.json()
        assert task_data["status"] == "success"
        assert task_data["data"]["id"] == task_id
        
        # Task should be created successfully
        task_status = task_data["data"]["status"]
        assert task_status in ["pending", "running", "completed"]
        
    finally:
        # Clean up test part
        with Session(engine) as session:
            test_part = PartRepository.get_part_by_id(session, test_part_id)
            if test_part:
                session.delete(test_part)
                session.commit()


def test_task_stats_endpoint(auth_token):
    """Test that task stats endpoint works"""
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Get task stats
    response = client.get("/api/tasks/stats/summary", headers=headers)
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "data" in result
    
    stats = result["data"]
    assert "total_tasks" in stats
    assert "by_status" in stats
    assert "by_type" in stats
    assert "running_tasks" in stats
    assert isinstance(stats["total_tasks"], int)


def test_worker_status_endpoint(auth_token):
    """Test that worker status endpoint works"""
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Get worker status
    response = client.get("/api/tasks/worker/status", headers=headers)
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "data" in result
    
    worker_data = result["data"]
    assert "is_running" in worker_data
    assert "running_tasks_count" in worker_data
    assert "running_task_ids" in worker_data
    assert "registered_handlers" in worker_data
    assert isinstance(worker_data["is_running"], bool)
    assert isinstance(worker_data["running_tasks_count"], int)


def test_task_types_endpoint(auth_token):
    """Test that available task types endpoint works"""
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Get available task types
    response = client.get("/api/tasks/types/available", headers=headers)
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert "data" in result
    
    task_types = result["data"]
    assert isinstance(task_types, list)
    
    # Should include our part enrichment task
    task_type_names = [task["type"] for task in task_types]
    assert "part_enrichment" in task_type_names


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])