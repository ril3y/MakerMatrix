import pytest
from sqlmodel import Session, SQLModel, create_engine
from MakerMatrix.models.models import PartModel, LocationModel, CategoryModel
from sqlmodel import select
import json


# Create an in-memory SQLite database engine for reuse
@pytest.fixture(scope="module")
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

    part = PartModel(part_number="12345", part_name="Resistor", quantity=100, location_id=location.id)
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.part_number == "12345"
    assert fetched_part.location.name == "Warehouse A"

    # Print the part as JSON
    print(fetched_part.model_dump_json(indent=2))


# Test function to verify if we can create and read a location model
def test_create_location(session):
    location = LocationModel(name="Storage Room B", description="Backup storage room")
    session.add(location)
    session.commit()
    session.refresh(location)

    fetched_location = session.get(LocationModel, location.id)

    assert fetched_location is not None
    assert fetched_location.name == "Storage Room B"

    # Print the location as JSON
    print(fetched_location.model_dump_json(indent=2))


# Test function to verify if we can create a category and assign it to a part
def test_create_category_and_assign_to_part(session):
    category = CategoryModel(name="Electronics", description="Electronic components")
    session.add(category)
    session.commit()
    session.refresh(category)

    part = PartModel(part_number="54321", part_name="Capacitor", quantity=200, categories=[category])
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert len(fetched_part.categories) > 0
    assert fetched_part.categories[0].name == "Electronics"

    # Print the part with category as JSON
    print(fetched_part.model_dump_json(indent=2))


# Test updating a part's quantity
def test_update_part_quantity(session):
    part = PartModel(part_number="11111", part_name="Inductor", quantity=50)
    session.add(part)
    session.commit()
    session.refresh(part)

    # Update the quantity
    part.quantity = 75
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.quantity == 75

    # Print the updated part as JSON
    print(fetched_part.model_dump_json(indent=2))


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

    # Print the location state as JSON (for demonstration, although it's deleted)
    # The following will raise an AttributeError since fetched_location is None.
    # Uncomment to observe behavior if required:
    # print(fetched_location.model_dump_json(indent=2)) if fetched_location else print("Location deleted.")


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

    # Print the entire nested structure as JSON
    from sqlmodel import select

    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "location_type": location.location_type,

            "children": []
        }
        statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))


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
    electronic_components_category = CategoryModel(name="Electronic Components",
                                                   description="Electronic components like resistors and microcontrollers")
    session.add_all([hardware_category, electronic_components_category])
    session.commit()
    session.refresh(hardware_category)
    session.refresh(electronic_components_category)

    # Create Parts
    screw = PartModel(part_number="S1234", part_name="Screw", quantity=500, location_id=drawer_1.id,
                      categories=[hardware_category])
    resistor = PartModel(part_number="R5678", part_name="Resistor", quantity=1000, location_id=drawer_2.id,
                         categories=[electronic_components_category])
    microcontroller = PartModel(part_number="MCU910", part_name="Microcontroller", quantity=50, location_id=desk.id,
                                categories=[electronic_components_category])
    session.add_all([screw, resistor, microcontroller])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Print the entire nested structure with categories and parts as JSON
    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "children": [],
            "parts": []
        }
        # Add parts in the current location
        part_statement = select(PartModel).where(PartModel.location_id == location.id)
        parts = session.exec(part_statement).all()
        for part in parts:
            serialized["parts"].append({
                "id": part.id,
                "part_number": part.part_number,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "categories": [category.name for category in part.categories]
            })

        # Add child locations
        location_statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(location_statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))


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
    electronic_components_category = CategoryModel(name="Electronic Components",
                                                   description="Electronic components like resistors and microcontrollers")
    session.add_all([hardware_category, electronic_components_category])
    session.commit()
    session.refresh(hardware_category)
    session.refresh(electronic_components_category)

    # Create Parts
    screw = PartModel(part_number="S1234", part_name="Screw", quantity=500, location_id=drawer_1.id,
                      categories=[hardware_category])
    resistor = PartModel(part_number="R5678", part_name="Resistor", quantity=1000, location_id=drawer_2.id,
                         categories=[electronic_components_category])
    microcontroller = PartModel(part_number="MCU910", part_name="Microcontroller", quantity=50, location_id=desk.id,
                                categories=[electronic_components_category])
    session.add_all([screw, resistor, microcontroller])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Print the entire nested structure with categories and parts as JSON
    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "children": [],
            "location_type": location.location_type,
            "parts": []
        }
        # Add parts in the current location
        part_statement = select(PartModel).where(PartModel.location_id == location.id)
        parts = session.exec(part_statement).all()
        for part in parts:
            serialized["parts"].append({
                "id": part.id,
                "part_number": part.part_number,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "categories": [category.name for category in part.categories]
            })

        # Add child locations
        location_statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(location_statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))
