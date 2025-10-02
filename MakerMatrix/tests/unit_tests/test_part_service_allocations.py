"""
Tests for PartService allocation integration

Verifies that PartService correctly creates and manages allocations when
creating and updating parts.
"""

import pytest
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
from MakerMatrix.services.data.part_service import PartService


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory database for each test"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    from MakerMatrix.models.models import SQLModel
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture(name="part_service")
def part_service_fixture():
    """Create PartService instance"""
    return PartService()


@pytest.fixture(name="test_location")
def test_location_fixture(session: Session):
    """Create a test location"""
    location = LocationModel(name="Test Shelf", location_type="shelf")
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


class TestPartServiceAddPart:
    """Test PartService.add_part() with allocation system"""

    def test_add_part_creates_allocation(self, part_service: PartService, test_location: LocationModel):
        """Test that adding a part creates an allocation"""
        part_data = {
            "part_name": "Test Resistor 10k",
            "part_number": "RES-10K",
            "description": "Test resistor",
            "quantity": 100,
            "location_id": test_location.id,
            "supplier": "Test Supplier"
        }

        response = part_service.add_part(part_data)

        assert response.success is True
        assert response.data is not None
        assert response.data["part_name"] == "Test Resistor 10k"
        assert response.data["quantity"] == 100  # From computed property
        assert response.data["location_id"] == test_location.id

    def test_add_part_without_quantity_creates_part(self, part_service: PartService, test_location: LocationModel):
        """Test that adding a part without quantity still works"""
        part_data = {
            "part_name": "Test Capacitor 100nF",
            "location_id": test_location.id
        }

        response = part_service.add_part(part_data)

        assert response.success is True
        assert response.data["quantity"] == 0  # No allocation created

    def test_add_part_zero_quantity_no_allocation(self, part_service: PartService, test_location: LocationModel):
        """Test that adding a part with zero quantity doesn't create allocation"""
        part_data = {
            "part_name": "Test LED Red",
            "quantity": 0,
            "location_id": test_location.id
        }

        response = part_service.add_part(part_data)

        assert response.success is True
        assert response.data["quantity"] == 0

    def test_add_part_allocation_marked_primary(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test that initial allocation is marked as primary storage"""
        part_data = {
            "part_name": "Test IC 555",
            "quantity": 50,
            "location_id": test_location.id
        }

        response = part_service.add_part(part_data)
        assert response.success is True

        # Verify allocation exists and is primary
        part_id = response.data["id"]
        part = session.get(PartModel, part_id)

        assert len(part.allocations) == 1
        assert part.allocations[0].is_primary_storage is True
        assert part.allocations[0].quantity_at_location == 50
        assert part.allocations[0].location_id == test_location.id

    def test_add_part_computed_properties_work(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test that computed properties return correct values"""
        part_data = {
            "part_name": "Test Transistor",
            "quantity": 200,
            "location_id": test_location.id
        }

        response = part_service.add_part(part_data)
        part_id = response.data["id"]

        # Get part and verify computed properties
        part = session.get(PartModel, part_id)
        assert part.total_quantity == 200
        assert part.primary_location is not None
        assert part.primary_location.id == test_location.id


class TestPartServiceUpdateQuantity:
    """Test PartService.update_quantity_service() with allocations"""

    def test_update_quantity_updates_primary_allocation(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test that updating quantity updates the primary allocation"""
        # Create part with initial quantity
        part_data = {
            "part_name": "Test Diode",
            "quantity": 100,
            "location_id": test_location.id
        }

        response = part_service.add_part(part_data)
        part_id = response.data["id"]

        # Update quantity
        update_response = part_service.update_quantity_service(
            new_quantity=250,
            part_id=part_id
        )

        assert update_response.success is True

        # Verify allocation was updated
        part = session.get(PartModel, part_id)
        assert part.total_quantity == 250
        assert part.allocations[0].quantity_at_location == 250

    def test_update_quantity_no_allocations_fails(self, part_service: PartService, session: Session):
        """Test that updating quantity on part without allocations fails gracefully"""
        # Create part without allocations (manually)
        part = PartModel(part_name="Test Part No Allocation")
        session.add(part)
        session.commit()

        response = part_service.update_quantity_service(
            new_quantity=100,
            part_id=part.id
        )

        assert response.success is False
        assert "no allocations" in response.message.lower()


class TestPartServiceUpdatePart:
    """Test PartService.update_part() with allocations"""

    def test_update_part_quantity(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test updating part quantity through update_part()"""
        # Create part
        part_data = {
            "part_name": "Test Component",
            "quantity": 50,
            "location_id": test_location.id
        }
        response = part_service.add_part(part_data)
        part_id = response.data["id"]

        # Update using PartUpdate schema
        from MakerMatrix.schemas.part_create import PartUpdate
        update_data = PartUpdate(quantity=150)

        update_response = part_service.update_part(part_id, update_data)

        assert update_response.success is True

        # Verify allocation updated
        part = session.get(PartModel, part_id)
        assert part.total_quantity == 150

    def test_update_part_location(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test updating part location through update_part()"""
        # Create second location
        new_location = LocationModel(name="New Shelf", location_type="shelf")
        session.add(new_location)
        session.commit()

        # Create part at first location
        part_data = {
            "part_name": "Test Movable Part",
            "quantity": 75,
            "location_id": test_location.id
        }
        response = part_service.add_part(part_data)
        part_id = response.data["id"]

        # Update location
        from MakerMatrix.schemas.part_create import PartUpdate
        update_data = PartUpdate(location_id=new_location.id)

        update_response = part_service.update_part(part_id, update_data)

        assert update_response.success is True

        # Verify allocation moved to new location
        part = session.get(PartModel, part_id)
        assert part.primary_location.id == new_location.id
        assert part.allocations[0].location_id == new_location.id

    def test_update_part_both_quantity_and_location(self, part_service: PartService, test_location: LocationModel, session: Session):
        """Test updating both quantity and location"""
        # Create second location
        new_location = LocationModel(name="Another Shelf", location_type="shelf")
        session.add(new_location)
        session.commit()

        # Create part
        part_data = {
            "part_name": "Test Multi Update",
            "quantity": 100,
            "location_id": test_location.id
        }
        response = part_service.add_part(part_data)
        part_id = response.data["id"]

        # Update both
        from MakerMatrix.schemas.part_create import PartUpdate
        update_data = PartUpdate(quantity=200, location_id=new_location.id)

        update_response = part_service.update_part(part_id, update_data)

        assert update_response.success is True

        # Verify both updated
        part = session.get(PartModel, part_id)
        assert part.total_quantity == 200
        assert part.primary_location.id == new_location.id
