"""
Comprehensive tests for Part Allocation Models

Tests the multi-location allocation system including:
- PartLocationAllocation model
- Part-Location relationship
- Quantity tracking across locations
- Primary storage designation
- Computed properties on PartModel
"""

import pytest
from sqlmodel import Session, select, create_engine
from sqlalchemy.pool import StaticPool

from MakerMatrix.models.part_models import PartModel, PartCategoryLink
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.category_models import CategoryModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation


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


class TestPartLocationAllocationModel:
    """Test PartLocationAllocation model functionality"""

    def test_create_allocation(self, session: Session):
        """Test creating a basic allocation"""
        # Create location
        location = LocationModel(name="Test Shelf", location_type="shelf")
        session.add(location)

        # Create part
        part = PartModel(part_name="Test Part", part_number="TEST001")
        session.add(part)
        session.commit()

        # Create allocation
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=100,
            is_primary_storage=True,
            notes="Primary storage location"
        )
        session.add(allocation)
        session.commit()

        # Verify
        assert allocation.id is not None
        assert allocation.part_id == part.id
        assert allocation.location_id == location.id
        assert allocation.quantity_at_location == 100
        assert allocation.is_primary_storage is True
        assert allocation.notes == "Primary storage location"

    def test_allocation_unique_constraint(self, session: Session):
        """Test that part-location pairs must be unique"""
        location = LocationModel(name="Test Shelf")
        part = PartModel(part_name="Test Part")
        session.add_all([location, part])
        session.commit()

        # Create first allocation
        alloc1 = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=50
        )
        session.add(alloc1)
        session.commit()

        # Attempt to create duplicate allocation
        alloc2 = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=100
        )
        session.add(alloc2)

        with pytest.raises(Exception):  # SQLAlchemy integrity error
            session.commit()

    def test_allocation_relationships(self, session: Session):
        """Test that allocation relationships load correctly"""
        location = LocationModel(name="Storage Bin")
        part = PartModel(part_name="Resistor 10k")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=200
        )

        session.add_all([location, part, allocation])
        session.commit()
        session.refresh(allocation)

        # Verify relationships load
        assert allocation.part is not None
        assert allocation.part.part_name == "Resistor 10k"
        assert allocation.location is not None
        assert allocation.location.name == "Storage Bin"

    def test_allocation_to_dict(self, session: Session):
        """Test allocation serialization"""
        location = LocationModel(name="Test Location", emoji="📦")
        part = PartModel(part_name="Test Part")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=50,
            is_primary_storage=True,
            notes="Test notes"
        )

        session.add_all([location, part, allocation])
        session.commit()
        session.refresh(allocation)

        data = allocation.to_dict()

        assert data["id"] == allocation.id
        assert data["part_id"] == part.id
        assert data["location_id"] == location.id
        assert data["quantity_at_location"] == 50
        assert data["is_primary_storage"] is True
        assert data["notes"] == "Test notes"
        assert "location" in data
        assert data["location"]["name"] == "Test Location"
        assert data["location"]["emoji"] == "📦"

    def test_allocation_cascade_delete_part(self, session: Session):
        """Test that deleting a part cascades to allocations"""
        location = LocationModel(name="Test Location")
        part = PartModel(part_name="Test Part")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=100
        )

        session.add_all([location, part, allocation])
        session.commit()

        part_id = part.id
        allocation_id = allocation.id

        # Delete part
        session.delete(part)
        session.commit()

        # Verify allocation was also deleted
        remaining_alloc = session.get(PartLocationAllocation, allocation_id)
        assert remaining_alloc is None

    def test_allocation_cascade_delete_location(self, session: Session):
        """Test that deleting a location cascades to allocations"""
        location = LocationModel(name="Test Location")
        part = PartModel(part_name="Test Part")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=100
        )

        session.add_all([location, part, allocation])
        session.commit()

        allocation_id = allocation.id

        # Delete location
        session.delete(location)
        session.commit()

        # Verify allocation was also deleted
        remaining_alloc = session.get(PartLocationAllocation, allocation_id)
        assert remaining_alloc is None


class TestPartModelAllocationIntegration:
    """Test PartModel integration with allocations"""

    def test_part_with_no_allocations(self, session: Session):
        """Test part with no allocations has zero quantity"""
        part = PartModel(part_name="Empty Part")
        session.add(part)
        session.commit()
        session.refresh(part)

        assert part.total_quantity == 0
        assert part.primary_location is None

        summary = part.get_allocations_summary()
        assert summary["total_quantity"] == 0
        assert summary["location_count"] == 0
        assert summary["primary_location"] is None
        assert summary["allocations"] == []

    def test_part_with_single_allocation(self, session: Session):
        """Test part with single allocation"""
        location = LocationModel(name="Bin A1")
        part = PartModel(part_name="Capacitor 100nF")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=500,
            is_primary_storage=True
        )

        session.add_all([location, part, allocation])
        session.commit()
        session.refresh(part)

        assert part.total_quantity == 500
        assert part.primary_location is not None
        assert part.primary_location.name == "Bin A1"

        summary = part.get_allocations_summary()
        assert summary["total_quantity"] == 500
        assert summary["location_count"] == 1
        assert summary["primary_location"]["name"] == "Bin A1"

    def test_part_with_multiple_allocations(self, session: Session):
        """Test part distributed across multiple locations"""
        # Create locations
        reel_storage = LocationModel(name="Reel Storage", location_type="shelf")
        cassette1 = LocationModel(name="SMD Cassette #1", location_type="cassette", is_mobile=True)
        cassette2 = LocationModel(name="SMD Cassette #2", location_type="cassette", is_mobile=True)

        # Create part
        part = PartModel(part_name="Resistor 10k 0603")

        # Create allocations
        alloc_reel = PartLocationAllocation(
            part_id=part.id,
            location_id=reel_storage.id,
            quantity_at_location=3800,
            is_primary_storage=True,
            notes="Main reel storage"
        )
        alloc_cass1 = PartLocationAllocation(
            part_id=part.id,
            location_id=cassette1.id,
            quantity_at_location=100,
            is_primary_storage=False,
            notes="Working stock - Project A"
        )
        alloc_cass2 = PartLocationAllocation(
            part_id=part.id,
            location_id=cassette2.id,
            quantity_at_location=100,
            is_primary_storage=False,
            notes="Working stock - Project B"
        )

        session.add_all([reel_storage, cassette1, cassette2, part, alloc_reel, alloc_cass1, alloc_cass2])
        session.commit()
        session.refresh(part)

        # Verify total quantity
        assert part.total_quantity == 4000  # 3800 + 100 + 100

        # Verify primary location
        assert part.primary_location is not None
        assert part.primary_location.name == "Reel Storage"

        # Verify summary
        summary = part.get_allocations_summary()
        assert summary["total_quantity"] == 4000
        assert summary["location_count"] == 3
        assert summary["primary_location"]["name"] == "Reel Storage"
        assert len(summary["allocations"]) == 3

    def test_part_allocations_no_primary(self, session: Session):
        """Test part allocations when no primary is marked"""
        location1 = LocationModel(name="Location 1")
        location2 = LocationModel(name="Location 2")
        part = PartModel(part_name="Test Part")

        alloc1 = PartLocationAllocation(
            part_id=part.id,
            location_id=location1.id,
            quantity_at_location=50,
            is_primary_storage=False  # Not primary
        )
        alloc2 = PartLocationAllocation(
            part_id=part.id,
            location_id=location2.id,
            quantity_at_location=50,
            is_primary_storage=False  # Not primary
        )

        session.add_all([location1, location2, part, alloc1, alloc2])
        session.commit()
        session.refresh(part)

        # Should return first allocation's location
        assert part.primary_location is not None
        assert part.primary_location.name == "Location 1"

    def test_part_to_dict_with_allocations(self, session: Session):
        """Test that part.to_dict() includes computed quantity and location"""
        location = LocationModel(name="Storage")
        part = PartModel(part_name="LED Red 5mm")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=location.id,
            quantity_at_location=250,
            is_primary_storage=True
        )

        session.add_all([location, part, allocation])
        session.commit()
        session.refresh(part)

        data = part.to_dict()

        # Verify quantity is computed from allocations
        assert data["quantity"] == 250

        # Verify location is from primary allocation
        assert data["location"] is not None
        assert data["location"]["name"] == "Storage"

    def test_part_to_dict_no_allocations(self, session: Session):
        """Test that part.to_dict() handles missing allocations"""
        part = PartModel(part_name="Unallocated Part")
        session.add(part)
        session.commit()
        session.refresh(part)

        data = part.to_dict()

        assert data["quantity"] == 0
        assert data["location"] is None


class TestLocationModelAllocationIntegration:
    """Test LocationModel integration with allocations"""

    def test_location_with_allocations(self, session: Session):
        """Test location with multiple part allocations"""
        location = LocationModel(name="Bin A1", is_mobile=False)
        part1 = PartModel(part_name="Part 1")
        part2 = PartModel(part_name="Part 2")

        alloc1 = PartLocationAllocation(
            part_id=part1.id,
            location_id=location.id,
            quantity_at_location=100
        )
        alloc2 = PartLocationAllocation(
            part_id=part2.id,
            location_id=location.id,
            quantity_at_location=200
        )

        session.add_all([location, part1, part2, alloc1, alloc2])
        session.commit()
        session.refresh(location)

        # Verify location has allocations
        assert len(location.allocations) == 2

    def test_container_capacity_tracking(self, session: Session):
        """Test container capacity calculation"""
        cassette = LocationModel(
            name="SMD Cassette #5",
            location_type="cassette",
            is_mobile=True,
            container_capacity=200
        )
        part = PartModel(part_name="Capacitor 10uF")
        allocation = PartLocationAllocation(
            part_id=part.id,
            location_id=cassette.id,
            quantity_at_location=150
        )

        session.add_all([cassette, part, allocation])
        session.commit()
        session.refresh(cassette)

        # Get capacity info
        capacity_info = cassette.get_capacity_info()

        assert capacity_info is not None
        assert capacity_info["capacity"] == 200
        assert capacity_info["used"] == 150
        assert capacity_info["available"] == 50
        assert capacity_info["usage_percentage"] == 75.0

    def test_non_container_capacity_info(self, session: Session):
        """Test that non-containers return None for capacity_info"""
        shelf = LocationModel(name="Shelf", is_mobile=False)
        session.add(shelf)
        session.commit()

        capacity_info = shelf.get_capacity_info()
        assert capacity_info is None
