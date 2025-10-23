import pytest
from sqlmodel import Session, SQLModel, create_engine
from MakerMatrix.models.models import PartModel, LocationModel, CategoryModel
from sqlmodel import select
import json


# Create an in-memory SQLite database engine for reuse
@pytest.fixture(scope="function")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    return engine


# Create a test fixture for a session
@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


# Test function to verify if we can create and read a part model
def test_create_part(session):
    location = LocationModel(name="Warehouse A", description="Primary warehouse location")
    session.add(location)
    session.commit()
    session.refresh(location)

    # Create part (no longer has location_id and quantity fields)
    part = PartModel(part_number="12345", part_name="Resistor")
    session.add(part)
    session.commit()
    session.refresh(part)

    # Create allocation (replaces old location_id and quantity)
    from MakerMatrix.models.part_allocation_models import PartLocationAllocation

    allocation = PartLocationAllocation(
        part_id=part.id, location_id=location.id, quantity_at_location=100, is_primary_storage=True
    )
    session.add(allocation)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.part_number == "12345"
    assert fetched_part.primary_location.name == "Warehouse A"  # Use computed property
    assert fetched_part.total_quantity == 100  # Use computed property

    # Verify the part was properly created with allocation


# Test function to verify if we can create and read a location model
def test_create_location(session):
    location = LocationModel(name="Storage Room B", description="Backup storage room")
    session.add(location)
    session.commit()
    session.refresh(location)

    fetched_location = session.get(LocationModel, location.id)

    assert fetched_location is not None
    assert fetched_location.name == "Storage Room B"

    # Verify the location was properly created


# Test function to verify if we can create a category and assign it to a part
def test_create_category_and_assign_to_part(session):
    category = CategoryModel(name="Electronics", description="Electronic components")
    session.add(category)
    session.commit()
    session.refresh(category)

    # Create part without quantity (no longer a field)
    part = PartModel(part_number="54321", part_name="Capacitor", categories=[category])
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert len(fetched_part.categories) > 0
    assert fetched_part.categories[0].name == "Electronics"

    # Verify the category was properly assigned


# Test updating a part's quantity via allocation
def test_update_part_quantity(session):
    from MakerMatrix.models.part_allocation_models import PartLocationAllocation

    # Create location
    location = LocationModel(name="Test Location")
    session.add(location)
    session.commit()

    # Create part (no longer has quantity field)
    part = PartModel(part_number="11111", part_name="Inductor")
    session.add(part)
    session.commit()
    session.refresh(part)

    # Create allocation with initial quantity
    allocation = PartLocationAllocation(
        part_id=part.id, location_id=location.id, quantity_at_location=50, is_primary_storage=True
    )
    session.add(allocation)
    session.commit()
    session.refresh(part)

    # Verify initial quantity
    assert part.total_quantity == 50

    # Update the allocation quantity
    allocation.quantity_at_location = 75
    session.add(allocation)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.total_quantity == 75  # Use computed property

    # Verify the update was successful


# Test deleting a location
def test_delete_location(session):
    location = LocationModel(name="Temporary Storage", description="Temporary holding area")
    session.add(location)
    session.commit()
    session.refresh(location)

    # Delete the location
    session.delete(location)
    session.commit()

    fetched_location = session.get(LocationModel, location.id)

    assert fetched_location is None

    # Verify the location was properly deleted


# Test function to create nested locations (e.g., Building -> Room -> Desk -> Drawer)
def test_create_nested_locations(session):
    # Create the top-level building
    building = LocationModel(name="Building A", description="Main office building")
    session.add(building)
    session.commit()
    session.refresh(building)

    # Create a few rooms in the building
    room_101 = LocationModel(name="Room 101", description="Conference Room", parent_id=building.id)
    room_102 = LocationModel(name="Room 102", description="Office Room", parent_id=building.id)
    session.add_all([room_101, room_102])
    session.commit()
    session.refresh(room_101)
    session.refresh(room_102)

    # Create a desk inside Room 102
    desk = LocationModel(name="Desk A", description="Manager's Desk", parent_id=room_102.id)
    session.add(desk)
    session.commit()
    session.refresh(desk)

    # Create drawers inside the desk
    drawer_1 = LocationModel(name="Drawer 1", description="Top drawer", parent_id=desk.id)
    drawer_2 = LocationModel(name="Drawer 2", description="Bottom drawer", parent_id=desk.id)
    session.add_all([drawer_1, drawer_2])
    session.commit()
    session.refresh(drawer_1)
    session.refresh(drawer_2)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Verify the nested structure was created correctly
    statement = select(LocationModel).where(LocationModel.parent_id == building.id)
    rooms = session.exec(statement).all()
    assert len(rooms) == 2

    # Check that Room 102 has a desk
    room_102 = next(room for room in rooms if room.name == "Room 102")
    desk_statement = select(LocationModel).where(LocationModel.parent_id == room_102.id)
    desks = session.exec(desk_statement).all()
    assert len(desks) == 1
    assert desks[0].name == "Desk A"

    # Check that the desk has drawers
    drawer_statement = select(LocationModel).where(LocationModel.parent_id == desks[0].id)
    drawers = session.exec(drawer_statement).all()
    assert len(drawers) == 2
    assert any(drawer.name == "Drawer 1" for drawer in drawers)
    assert any(drawer.name == "Drawer 2" for drawer in drawers)


def test_create_nested_locations_with_categories_and_parts(session):
    # Create the top-level building
    building = LocationModel(name="Building A", description="Main office building")
    session.add(building)
    session.commit()
    session.refresh(building)

    # Create a few rooms in the building
    room_101 = LocationModel(name="Room 101", description="Conference Room", parent_id=building.id)
    room_102 = LocationModel(name="Room 102", description="Office Room", parent_id=building.id)
    session.add_all([room_101, room_102])
    session.commit()
    session.refresh(room_101)
    session.refresh(room_102)

    # Create a desk inside Room 102
    desk = LocationModel(name="Desk A", description="Manager's Desk", parent_id=room_102.id)
    session.add(desk)
    session.commit()
    session.refresh(desk)

    # Create drawers inside the desk
    drawer_1 = LocationModel(name="Drawer 1", description="Top drawer", parent_id=desk.id)
    drawer_2 = LocationModel(name="Drawer 2", description="Bottom drawer", parent_id=desk.id)
    session.add_all([drawer_1, drawer_2])
    session.commit()
    session.refresh(drawer_1)
    session.refresh(drawer_2)

    # Create Categories
    hardware_category = CategoryModel(name="Hardware", description="Mechanical parts like screws, bolts, etc.")
    electronic_components_category = CategoryModel(
        name="Electronic Components", description="Electronic components like resistors and microcontrollers"
    )
    session.add_all([hardware_category, electronic_components_category])
    session.commit()
    session.refresh(hardware_category)
    session.refresh(electronic_components_category)

    # Create Parts (without quantity and location_id - use allocations instead)
    from MakerMatrix.models.part_allocation_models import PartLocationAllocation

    screw = PartModel(part_number="S1234", part_name="Screw", categories=[hardware_category])
    resistor = PartModel(part_number="R5678", part_name="Resistor", categories=[electronic_components_category])
    microcontroller = PartModel(
        part_number="MCU910", part_name="Microcontroller", categories=[electronic_components_category]
    )
    session.add_all([screw, resistor, microcontroller])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Create allocations for parts
    screw_alloc = PartLocationAllocation(
        part_id=screw.id, location_id=drawer_1.id, quantity_at_location=500, is_primary_storage=True
    )
    resistor_alloc = PartLocationAllocation(
        part_id=resistor.id, location_id=drawer_2.id, quantity_at_location=1000, is_primary_storage=True
    )
    micro_alloc = PartLocationAllocation(
        part_id=microcontroller.id, location_id=desk.id, quantity_at_location=50, is_primary_storage=True
    )
    session.add_all([screw_alloc, resistor_alloc, micro_alloc])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Verify that the structure is properly created
    assert len(fetched_building.children) == 2
    assert any(room.name == "Room 101" for room in fetched_building.children)
    assert any(room.name == "Room 102" for room in fetched_building.children)

    # Check that parts are properly assigned to locations via allocations
    all_parts = session.exec(select(PartModel)).all()
    assert len(all_parts) == 3
    # Check using primary_location computed property instead of location_id
    assert any(
        part.part_name == "Screw" and part.primary_location and part.primary_location.id == drawer_1.id
        for part in all_parts
    )
    assert any(
        part.part_name == "Resistor" and part.primary_location and part.primary_location.id == drawer_2.id
        for part in all_parts
    )
    assert any(
        part.part_name == "Microcontroller" and part.primary_location and part.primary_location.id == desk.id
        for part in all_parts
    )
