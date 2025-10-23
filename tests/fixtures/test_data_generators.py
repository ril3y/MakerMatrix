"""
Test Data Generators

Provides functions to populate test databases with realistic, predictable test data.
This enables data integrity verification after backup/restore operations.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from sqlmodel import Session

# Import all models needed for test data
from MakerMatrix.models.part_models import PartModel, DatasheetModel
from MakerMatrix.models.category_models import CategoryModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.models.api_key_models import APIKeyModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation
from passlib.hash import pbkdf2_sha256


def create_test_roles(session: Session) -> Tuple[RoleModel, RoleModel]:
    """
    Create test roles: admin and user.

    Args:
        session: Database session

    Returns:
        Tuple of (admin_role, user_role)
    """
    admin_role = RoleModel(
        id=str(uuid.uuid4()), name="admin", description="Administrator role for testing", permissions=["all"]
    )
    session.add(admin_role)

    user_role = RoleModel(
        id=str(uuid.uuid4()),
        name="user",
        description="Regular user role for testing",
        permissions=["parts:read", "parts:write", "locations:read"],
    )
    session.add(user_role)

    session.commit()
    return admin_role, user_role


def create_test_users(session: Session, admin_role: RoleModel, user_role: RoleModel) -> Tuple[UserModel, UserModel]:
    """
    Create test users: admin and regular user.

    Args:
        session: Database session
        admin_role: Admin role model
        user_role: User role model

    Returns:
        Tuple of (admin_user, regular_user)
    """
    # Create admin user
    admin_user = UserModel(
        id=str(uuid.uuid4()),
        username="test_admin",
        email="admin@test.local",
        hashed_password=pbkdf2_sha256.hash("AdminPass123!"),
        is_active=True,
        password_change_required=False,
        created_at=datetime.utcnow(),
    )
    admin_user.roles = [admin_role]
    session.add(admin_user)

    # Create regular user
    regular_user = UserModel(
        id=str(uuid.uuid4()),
        username="test_user",
        email="user@test.local",
        hashed_password=pbkdf2_sha256.hash("UserPass123!"),
        is_active=True,
        password_change_required=False,
        created_at=datetime.utcnow(),
    )
    regular_user.roles = [user_role]
    session.add(regular_user)

    session.commit()
    return admin_user, regular_user


def create_test_api_keys(session: Session, admin_user: UserModel, regular_user: UserModel) -> Tuple[str, str]:
    """
    Create test API keys for admin and regular user.

    Args:
        session: Database session
        admin_user: Admin user model
        regular_user: Regular user model

    Returns:
        Tuple of (admin_api_key, user_api_key) - the actual keys, not hashed
    """
    # Create admin API key
    admin_api_key = f"mm_test_admin_{uuid.uuid4().hex[:16]}"
    admin_key_hash = hashlib.sha256(admin_api_key.encode()).hexdigest()

    admin_key_model = APIKeyModel(
        id=str(uuid.uuid4()),
        name="Test Admin API Key",
        description="Admin API key for integration testing",
        key_hash=admin_key_hash,
        key_prefix=admin_api_key[:12],
        user_id=admin_user.id,
        permissions=["all"],
        role_names=["admin"],
        is_active=True,
        created_at=datetime.utcnow(),
        usage_count=0,
    )
    session.add(admin_key_model)

    # Create regular user API key
    user_api_key = f"mm_test_user_{uuid.uuid4().hex[:16]}"
    user_key_hash = hashlib.sha256(user_api_key.encode()).hexdigest()

    user_key_model = APIKeyModel(
        id=str(uuid.uuid4()),
        name="Test User API Key",
        description="Regular user API key for integration testing",
        key_hash=user_key_hash,
        key_prefix=user_api_key[:12],
        user_id=regular_user.id,
        permissions=["parts:read", "parts:write", "locations:read"],
        role_names=["user"],
        is_active=True,
        created_at=datetime.utcnow(),
        usage_count=0,
    )
    session.add(user_key_model)

    session.commit()
    return admin_api_key, user_api_key


def create_test_categories(session: Session) -> List[CategoryModel]:
    """
    Create hierarchical test categories.

    Structure:
    - Electronics
      - Resistors
        - SMD Resistors
      - Capacitors
        - Ceramic Capacitors
    - Hardware
      - Fasteners
        - Screws

    Args:
        session: Database session

    Returns:
        List of all created categories
    """
    categories = []

    # Top level: Electronics
    electronics = CategoryModel(id="cat_electronics", name="Electronics", description="Electronic components")
    session.add(electronics)
    categories.append(electronics)

    # Second level: Resistors, Capacitors
    resistors = CategoryModel(id="cat_resistors", name="Resistors", description="Resistive components")
    session.add(resistors)
    categories.append(resistors)

    capacitors = CategoryModel(id="cat_capacitors", name="Capacitors", description="Capacitive components")
    session.add(capacitors)
    categories.append(capacitors)

    # Third level: SMD Resistors, Ceramic Capacitors
    smd_resistors = CategoryModel(id="cat_smd_resistors", name="SMD Resistors", description="Surface mount resistors")
    session.add(smd_resistors)
    categories.append(smd_resistors)

    ceramic_caps = CategoryModel(id="cat_ceramic_caps", name="Ceramic Capacitors", description="Ceramic capacitors")
    session.add(ceramic_caps)
    categories.append(ceramic_caps)

    # Top level: Hardware
    hardware = CategoryModel(id="cat_hardware", name="Hardware", description="Mechanical hardware")
    session.add(hardware)
    categories.append(hardware)

    # Second level: Fasteners
    fasteners = CategoryModel(id="cat_fasteners", name="Fasteners", description="Screws, bolts, nuts")
    session.add(fasteners)
    categories.append(fasteners)

    # Third level: Screws
    screws = CategoryModel(id="cat_screws", name="Screws", description="Screw fasteners")
    session.add(screws)
    categories.append(screws)

    session.commit()
    return categories


def create_test_locations(session: Session) -> List[LocationModel]:
    """
    Create hierarchical test locations.

    Structure:
    - Warehouse A
      - Shelf 1
        - Bin A1
        - Bin A2
      - Shelf 2
        - Bin B1
    - SMD Storage
      - Cassette Rack
        - Cassette 01 (mobile)
        - Cassette 02 (mobile)

    Args:
        session: Database session

    Returns:
        List of all created locations
    """
    locations = []

    # Top level: Warehouse A
    warehouse_a = LocationModel(
        id="loc_warehouse_a",
        name="Warehouse A",
        description="Main warehouse storage",
        parent_id=None,
        location_type="warehouse",
        is_mobile=False,
    )
    session.add(warehouse_a)
    locations.append(warehouse_a)

    # Second level: Shelves
    shelf_1 = LocationModel(
        id="loc_shelf_1",
        name="Shelf 1",
        description="First shelf in warehouse",
        parent_id="loc_warehouse_a",
        location_type="shelf",
        is_mobile=False,
    )
    session.add(shelf_1)
    locations.append(shelf_1)

    shelf_2 = LocationModel(
        id="loc_shelf_2",
        name="Shelf 2",
        description="Second shelf in warehouse",
        parent_id="loc_warehouse_a",
        location_type="shelf",
        is_mobile=False,
    )
    session.add(shelf_2)
    locations.append(shelf_2)

    # Third level: Bins
    bin_a1 = LocationModel(
        id="loc_bin_a1",
        name="Bin A1",
        description="Bin A1 on Shelf 1",
        parent_id="loc_shelf_1",
        location_type="bin",
        is_mobile=False,
        container_capacity=1000,
    )
    session.add(bin_a1)
    locations.append(bin_a1)

    bin_a2 = LocationModel(
        id="loc_bin_a2",
        name="Bin A2",
        description="Bin A2 on Shelf 1",
        parent_id="loc_shelf_1",
        location_type="bin",
        is_mobile=False,
        container_capacity=1000,
    )
    session.add(bin_a2)
    locations.append(bin_a2)

    bin_b1 = LocationModel(
        id="loc_bin_b1",
        name="Bin B1",
        description="Bin B1 on Shelf 2",
        parent_id="loc_shelf_2",
        location_type="bin",
        is_mobile=False,
        container_capacity=500,
    )
    session.add(bin_b1)
    locations.append(bin_b1)

    # SMD Storage area
    smd_storage = LocationModel(
        id="loc_smd_storage",
        name="SMD Storage",
        description="Surface mount component storage",
        parent_id=None,
        location_type="storage_area",
        is_mobile=False,
    )
    session.add(smd_storage)
    locations.append(smd_storage)

    cassette_rack = LocationModel(
        id="loc_cassette_rack",
        name="Cassette Rack",
        description="Rack for SMD cassettes",
        parent_id="loc_smd_storage",
        location_type="rack",
        is_mobile=False,
    )
    session.add(cassette_rack)
    locations.append(cassette_rack)

    # Mobile cassettes
    cassette_01 = LocationModel(
        id="loc_cassette_01",
        name="Cassette 01",
        description="Mobile SMD cassette #1",
        parent_id="loc_cassette_rack",
        location_type="cassette",
        is_mobile=True,
        container_capacity=100,
    )
    session.add(cassette_01)
    locations.append(cassette_01)

    cassette_02 = LocationModel(
        id="loc_cassette_02",
        name="Cassette 02",
        description="Mobile SMD cassette #2",
        parent_id="loc_cassette_rack",
        location_type="cassette",
        is_mobile=True,
        container_capacity=100,
    )
    session.add(cassette_02)
    locations.append(cassette_02)

    session.commit()
    return locations


def create_test_parts(session: Session, categories: List[CategoryModel]) -> List[PartModel]:
    """
    Create test parts with various properties.

    Args:
        session: Database session
        categories: List of category models to assign to parts

    Returns:
        List of created parts
    """
    parts = []

    # Part 1: SMD Resistor
    part1 = PartModel(
        id="part_resistor_100k",
        part_name="Resistor 100K 0603",
        part_number="R100K-0603",
        description="100K ohm SMD resistor, 0603 package, 1%",
        manufacturer="Yageo",
        manufacturer_part_number="RC0603FR-07100KL",
        component_type="resistor",
        supplier="DigiKey",
        supplier_part_number="311-100KHRCT-ND",
        emoji="⚡",
    )
    # Link to SMD Resistors category
    if len(categories) > 3:
        part1.categories = [categories[3]]  # SMD Resistors
    session.add(part1)
    parts.append(part1)

    # Part 2: Ceramic Capacitor
    part2 = PartModel(
        id="part_cap_10uf",
        part_name="Capacitor 10uF 0805",
        part_number="C10UF-0805",
        description="10uF ceramic capacitor, 0805 package, 16V",
        manufacturer="Samsung",
        manufacturer_part_number="CL21A106KAYNNNE",
        component_type="capacitor",
        supplier="LCSC",
        supplier_part_number="C15850",
        emoji="🔋",
    )
    # Link to Ceramic Capacitors category
    if len(categories) > 4:
        part2.categories = [categories[4]]  # Ceramic Capacitors
    session.add(part2)
    parts.append(part2)

    # Part 3: Screw
    part3 = PartModel(
        id="part_screw_m3",
        part_name="M3 x 10mm Screw",
        part_number="SCR-M3-10",
        description="M3 x 10mm Phillips head screw, stainless steel",
        manufacturer="Generic",
        component_type="screw",
        supplier="McMaster-Carr",
        supplier_part_number="91290A115",
        emoji="🔩",
    )
    # Link to Screws category
    if len(categories) > 7:
        part3.categories = [categories[7]]  # Screws
    session.add(part3)
    parts.append(part3)

    # Part 4: IC without categories (test null handling)
    part4 = PartModel(
        id="part_ic_atmega328",
        part_name="ATmega328P-AU",
        part_number="IC-ATMEGA328P",
        description="8-bit AVR microcontroller, TQFP-32 package",
        manufacturer="Microchip",
        manufacturer_part_number="ATMEGA328P-AU",
        component_type="microcontroller",
        supplier="Mouser",
        supplier_part_number="556-ATMEGA328P-AU",
        emoji="🧠",
    )
    session.add(part4)
    parts.append(part4)

    # Part 5: Simple part for additional test coverage
    part5 = PartModel(
        id="part_led_red",
        part_name="LED Red 5mm",
        part_number="LED-RED-5MM",
        description="5mm red LED, 20mA, 2V forward voltage",
        manufacturer="Kingbright",
        component_type="led",
        supplier="DigiKey",
        emoji="💡",
    )
    session.add(part5)
    parts.append(part5)

    session.commit()
    return parts


def create_test_allocations(
    session: Session, parts: List[PartModel], locations: List[LocationModel]
) -> List[PartLocationAllocation]:
    """
    Create test part allocations across locations.

    Args:
        session: Database session
        parts: List of parts to allocate
        locations: List of locations to allocate to

    Returns:
        List of created allocations
    """
    allocations = []

    # Allocate Resistor: 5000 in Bin A1 (primary), 100 in Cassette 01
    if len(parts) > 0 and len(locations) > 3:
        alloc1 = PartLocationAllocation(
            id=str(uuid.uuid4()),
            part_id=parts[0].id,
            location_id=locations[3].id,  # Bin A1
            quantity_at_location=5000,
            is_primary_storage=True,
        )
        session.add(alloc1)
        allocations.append(alloc1)

        if len(locations) > 8:
            alloc2 = PartLocationAllocation(
                id=str(uuid.uuid4()),
                part_id=parts[0].id,
                location_id=locations[8].id,  # Cassette 01
                quantity_at_location=100,
                is_primary_storage=False,
            )
            session.add(alloc2)
            allocations.append(alloc2)

    # Allocate Capacitor: 3000 in Bin A2 (primary)
    if len(parts) > 1 and len(locations) > 4:
        alloc3 = PartLocationAllocation(
            id=str(uuid.uuid4()),
            part_id=parts[1].id,
            location_id=locations[4].id,  # Bin A2
            quantity_at_location=3000,
            is_primary_storage=True,
        )
        session.add(alloc3)
        allocations.append(alloc3)

    # Allocate Screws: 1000 in Bin B1 (primary)
    if len(parts) > 2 and len(locations) > 5:
        alloc4 = PartLocationAllocation(
            id=str(uuid.uuid4()),
            part_id=parts[2].id,
            location_id=locations[5].id,  # Bin B1
            quantity_at_location=1000,
            is_primary_storage=True,
        )
        session.add(alloc4)
        allocations.append(alloc4)

    session.commit()
    return allocations


def create_test_datasheet_files(static_files_dir: Path) -> List[Path]:
    """
    Create small test PDF files for datasheet testing.

    Args:
        static_files_dir: Base directory for static files

    Returns:
        List of created datasheet file paths
    """
    datasheets_dir = static_files_dir / "datasheets"
    datasheets_dir.mkdir(parents=True, exist_ok=True)

    datasheet_files = []

    # Create minimal PDF files (simplified PDF structure)
    # These are minimal but valid PDF files
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Datasheet) Tj
ET
endstream
endobj
5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000270 00000 n
0000000364 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
450
%%EOF
"""

    # Create test datasheets
    datasheet1 = datasheets_dir / f"{uuid.uuid4()}.pdf"
    datasheet1.write_bytes(pdf_content)
    datasheet_files.append(datasheet1)

    datasheet2 = datasheets_dir / f"{uuid.uuid4()}.pdf"
    datasheet2.write_bytes(pdf_content)
    datasheet_files.append(datasheet2)

    return datasheet_files


def create_test_image_files(static_files_dir: Path) -> List[Path]:
    """
    Create small test image files for image testing.

    Args:
        static_files_dir: Base directory for static files

    Returns:
        List of created image file paths
    """
    images_dir = static_files_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    image_files = []

    # Create minimal 1x1 PNG files
    # PNG header + 1x1 red pixel
    png_content = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "89000000d49444154789c62f8cf400000000000ffff030000060005a4a2b4dd"
        "00000000049454e44ae426082"
    )

    # Create test images
    image1 = images_dir / f"{uuid.uuid4()}.png"
    image1.write_bytes(png_content)
    image_files.append(image1)

    image2 = images_dir / f"{uuid.uuid4()}.png"
    image2.write_bytes(png_content)
    image_files.append(image2)

    return image_files


def populate_test_database(session: Session, static_files_dir: Path = None) -> dict:
    """
    Populate a test database with complete test data.

    This is a convenience function that creates all test data
    in the correct order and returns references to all created objects.

    Args:
        session: Database session
        static_files_dir: Optional directory for static files

    Returns:
        Dictionary containing all created test data:
        {
            "roles": (admin_role, user_role),
            "users": (admin_user, regular_user),
            "api_keys": (admin_api_key, user_api_key),
            "categories": [...],
            "locations": [...],
            "parts": [...],
            "allocations": [...],
            "datasheet_files": [...],  # if static_files_dir provided
            "image_files": [...]  # if static_files_dir provided
        }
    """
    # Create roles
    admin_role, user_role = create_test_roles(session)

    # Create users
    admin_user, regular_user = create_test_users(session, admin_role, user_role)

    # Create API keys
    admin_api_key, user_api_key = create_test_api_keys(session, admin_user, regular_user)

    # Create categories
    categories = create_test_categories(session)

    # Create locations
    locations = create_test_locations(session)

    # Create parts
    parts = create_test_parts(session, categories)

    # Create allocations
    allocations = create_test_allocations(session, parts, locations)

    result = {
        "roles": (admin_role, user_role),
        "users": (admin_user, regular_user),
        "api_keys": (admin_api_key, user_api_key),
        "categories": categories,
        "locations": locations,
        "parts": parts,
        "allocations": allocations,
    }

    # Create static files if directory provided
    if static_files_dir:
        datasheet_files = create_test_datasheet_files(static_files_dir)
        image_files = create_test_image_files(static_files_dir)
        result["datasheet_files"] = datasheet_files
        result["image_files"] = image_files

    return result
