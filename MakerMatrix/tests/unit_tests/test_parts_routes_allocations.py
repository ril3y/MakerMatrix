"""
Comprehensive tests for parts API routes with allocation system

Tests that API endpoints correctly handle the allocation system through
the service and repository layers.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select
from sqlalchemy.pool import StaticPool

from MakerMatrix.main import app
from MakerMatrix.models.models import SQLModel
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.database.db import get_session
from MakerMatrix.auth.dependencies import get_current_user


@pytest.fixture(name="test_user")
def test_user_fixture():
    """Create a mock test user"""
    return UserModel(
        id="test-user-id",
        username="testuser",
        email="test@example.com",
        hashed_password="fake_hash",
        is_active=True
    )


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create a test database engine"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """Create a test session"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="test_client")
def test_client_fixture(test_session: Session, test_user: UserModel):
    """Create a test client with overridden dependencies"""
    def override_get_session():
        yield test_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="test_location")
def test_location_fixture(test_session: Session):
    """Create a test location"""
    location = LocationModel(name="Test Warehouse", location_type="warehouse")
    test_session.add(location)
    test_session.commit()
    test_session.refresh(location)
    return location


class TestPartsRoutesAddPart:
    """Test POST /parts/add_part endpoint"""

    def test_add_part_creates_allocation(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that adding a part via API creates an allocation"""
        part_data = {
            "part_name": "API Test Resistor",
            "part_number": "API-RES-001",
            "quantity": 100,
            "location_id": test_location.id,
            "supplier": "Test Supplier",
            "description": "Test part via API"
        }

        response = test_client.post("/api/parts/add_part", json=part_data)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["data"]["part_name"] == "API Test Resistor"
        assert data["data"]["quantity"] == 100

        # Verify allocation was created in database
        part_id = data["data"]["id"]
        part = test_session.get(PartModel, part_id)
        assert part is not None
        assert len(part.allocations) == 1
        assert part.allocations[0].quantity_at_location == 100
        assert part.allocations[0].location_id == test_location.id
        assert part.allocations[0].is_primary_storage is True

    def test_add_part_without_location(self, test_client: TestClient):
        """Test adding a part without location creates part but no allocation"""
        part_data = {
            "part_name": "API Test Capacitor",
            "part_number": "API-CAP-001",
            "description": "Test part without location"
        }

        response = test_client.post("/api/parts/add_part", json=part_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["quantity"] == 0  # No allocation means 0 quantity

    def test_add_part_with_zero_quantity(self, test_client: TestClient, test_location: LocationModel):
        """Test that adding a part with zero quantity doesn't create allocation"""
        part_data = {
            "part_name": "API Test LED",
            "part_number": "API-LED-001",
            "quantity": 0,
            "location_id": test_location.id
        }

        response = test_client.post("/api/parts/add_part", json=part_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["quantity"] == 0


class TestPartsRoutesUpdatePart:
    """Test PUT /parts/update_part/{part_id} endpoint"""

    def test_update_part_quantity(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that updating part quantity via API updates the allocation"""
        # Create part with allocation directly in database
        part = PartModel(part_name="Update Test Part", part_number="UPD-001")
        test_session.add(part)
        test_session.commit()
        test_session.refresh(part)

        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=test_location.id,
            quantity_at_location=50,
            is_primary_storage=True
        )
        test_session.add(allocation)
        test_session.commit()

        # Update via API
        update_data = {"quantity": 150}

        response = test_client.put(f"/api/parts/update_part/{part.id}", json=update_data)
        assert response.status_code == 200

        # Verify allocation was updated
        test_session.refresh(part)
        assert part.total_quantity == 150
        assert part.allocations[0].quantity_at_location == 150

    def test_update_part_location(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that updating part location via API moves the allocation"""
        # Create second location
        new_location = LocationModel(name="New Warehouse", location_type="warehouse")
        test_session.add(new_location)
        test_session.commit()
        test_session.refresh(new_location)

        # Create part with allocation at first location
        part = PartModel(part_name="Move Test Part", part_number="MOV-001")
        test_session.add(part)
        test_session.commit()
        test_session.refresh(part)

        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=test_location.id,
            quantity_at_location=75,
            is_primary_storage=True
        )
        test_session.add(allocation)
        test_session.commit()

        # Update location via API
        update_data = {"location_id": new_location.id}

        response = test_client.put(f"/api/parts/update_part/{part.id}", json=update_data)
        assert response.status_code == 200

        # Verify allocation location was updated
        test_session.refresh(part)
        assert part.primary_location.id == new_location.id
        assert part.allocations[0].location_id == new_location.id


class TestPartsRoutesGetPart:
    """Test GET /parts/get_part endpoint"""

    def test_get_part_returns_computed_quantity(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that getting a part returns quantity from allocations"""
        # Create part with allocation
        part = PartModel(part_name="Get Test Part", part_number="GET-001")
        test_session.add(part)
        test_session.commit()
        test_session.refresh(part)

        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=test_location.id,
            quantity_at_location=200,
            is_primary_storage=True
        )
        test_session.add(allocation)
        test_session.commit()

        # Get via API
        response = test_client.get(f"/api/parts/get_part?part_id={part.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["data"]["quantity"] == 200
        assert data["data"]["location"]["id"] == test_location.id


class TestPartsRoutesGetAllParts:
    """Test GET /parts/get_all_parts endpoint"""

    def test_get_all_parts_includes_allocations(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that get_all_parts returns parts with computed quantities"""
        # Create multiple parts with allocations
        for i in range(3):
            part = PartModel(part_name=f"List Part {i}", part_number=f"LIST-{i:03d}")
            test_session.add(part)
            test_session.commit()
            test_session.refresh(part)

            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=test_location.id,
                quantity_at_location=(i + 1) * 10,
                is_primary_storage=True
            )
            test_session.add(allocation)
            test_session.commit()

        # Get all parts via API
        response = test_client.get("/api/parts/get_all_parts?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()

        # Verify parts have quantities from allocations
        parts = data["data"]["items"]
        assert len(parts) >= 3

        # Find our test parts
        list_parts = [p for p in parts if p["part_name"].startswith("List Part")]
        assert len(list_parts) == 3

        # Verify quantities are correct
        for part in list_parts:
            assert part["quantity"] > 0  # Should have quantity from allocation


class TestPartsRoutesSearch:
    """Test POST /parts/search endpoint"""

    def test_search_by_location(self, test_client: TestClient, test_location: LocationModel, test_session: Session):
        """Test that searching by location uses allocations"""
        # Create parts at specific location
        for i in range(2):
            part = PartModel(part_name=f"Search Part {i}", part_number=f"SEARCH-{i:03d}")
            test_session.add(part)
            test_session.commit()
            test_session.refresh(part)

            allocation = PartLocationAllocation(
                part_id=part.id,
                location_id=test_location.id,
                quantity_at_location=50,
                is_primary_storage=True
            )
            test_session.add(allocation)
            test_session.commit()

        # Search by location
        search_data = {
            "location_id": test_location.id,
            "page": 1,
            "page_size": 10
        }

        response = test_client.post("/api/parts/search", json=search_data)
        assert response.status_code == 200
        data = response.json()

        # Verify results include our parts
        parts = data["data"]["items"]
        search_parts = [p for p in parts if p["part_name"].startswith("Search Part")]
        assert len(search_parts) >= 2
