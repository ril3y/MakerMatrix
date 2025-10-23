#!/usr/bin/env python3
"""
Test data creation script for MakerMatrix

This script creates a comprehensive set of test data including:
- Nested location hierarchy
- Multiple categories
- Parts with various category assignments
- Realistic inventory data for testing

Usage: python create_test_data.py
"""

import asyncio
import sys
import os

sys.path.append(".")

from sqlmodel import Session
from MakerMatrix.models.models import engine, LocationModel, CategoryModel, PartModel
from MakerMatrix.services.data.location_service import LocationService
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.database.db import create_db_and_tables


def create_locations():
    """Create a nested hierarchy of storage locations"""
    print("Creating location hierarchy...")

    locations_data = [
        # Top level - Building areas
        {"name": "Workshop", "description": "Main workshop area", "parent": None},
        {"name": "Storage Room", "description": "General storage area", "parent": None},
        {"name": "Office", "description": "Office workspace", "parent": None},
        # Workshop subdivisions
        {"name": "Electronics Bench", "description": "Electronics workstation", "parent": "Workshop"},
        {"name": "3D Printer Area", "description": "3D printing station", "parent": "Workshop"},
        {"name": "Tool Cabinet", "description": "Hand tools storage", "parent": "Workshop"},
        # Electronics bench drawers
        {"name": "Components Drawer 1", "description": "Resistors and capacitors", "parent": "Electronics Bench"},
        {"name": "Components Drawer 2", "description": "ICs and microcontrollers", "parent": "Electronics Bench"},
        {"name": "Components Drawer 3", "description": "Connectors and cables", "parent": "Electronics Bench"},
        # Storage room sections
        {"name": "Shelf A", "description": "Metal shelving unit A", "parent": "Storage Room"},
        {"name": "Shelf B", "description": "Metal shelving unit B", "parent": "Storage Room"},
        {"name": "Parts Bins", "description": "Small parts organization", "parent": "Storage Room"},
        # Shelf subdivisions
        {"name": "Shelf A1", "description": "Top shelf - Raw materials", "parent": "Shelf A"},
        {"name": "Shelf A2", "description": "Middle shelf - Hardware", "parent": "Shelf A"},
        {"name": "Shelf A3", "description": "Bottom shelf - Tools", "parent": "Shelf A"},
        # 3D printer area
        {"name": "Filament Storage", "description": "3D printer filament", "parent": "3D Printer Area"},
        {"name": "Print Bed", "description": "Active printing area", "parent": "3D Printer Area"},
        # Parts bins
        {"name": "Bin 001", "description": "Small screws and fasteners", "parent": "Parts Bins"},
        {"name": "Bin 002", "description": "Washers and spacers", "parent": "Parts Bins"},
        {"name": "Bin 003", "description": "Nuts and bolts", "parent": "Parts Bins"},
    ]

    location_map = {}

    # Create locations in dependency order
    for location_data in locations_data:
        parent_id = None
        if location_data["parent"]:
            parent_id = location_map.get(location_data["parent"])
            if not parent_id:
                print(f"Warning: Parent '{location_data['parent']}' not found for '{location_data['name']}'")
                continue

        try:
            location_dict = {
                "name": location_data["name"],
                "description": location_data["description"],
                "parent_id": parent_id,
                "location_type": "storage",
            }
            location_service = LocationService()
            result = location_service.add_location(location_dict)

            if result.success:
                location_map[location_data["name"]] = result.data["id"]
                print(f"  ✓ Created location: {location_data['name']}")
            else:
                print(f"  ✗ Failed to create location {location_data['name']}: {result.message}")
        except Exception as e:
            print(f"  ✗ Failed to create location {location_data['name']}: {e}")

    return location_map


def create_categories():
    """Create a comprehensive set of part categories"""
    print("Creating categories...")

    categories = [
        "Electronics",
        "Passive Components",
        "Active Components",
        "Microcontrollers",
        "Sensors",
        "Actuators",
        "Power Management",
        "Communication",
        "Mechanical",
        "Fasteners",
        "Hardware",
        "3D Printing",
        "Filament",
        "Tools",
        "Hand Tools",
        "Measuring Tools",
        "Raw Materials",
        "Metal Stock",
        "Plastic Stock",
        "Consumables",
        "Adhesives",
        "Cleaning Supplies",
    ]

    category_map = {}

    category_service = CategoryService()

    for category_name in categories:
        try:
            category_model = CategoryModel(name=category_name)
            result = category_service.add_category(category_model)
            if result.success:
                category_map[category_name] = result.data["id"]
                print(f"  ✓ Created category: {category_name}")
            else:
                print(f"  ✗ Failed to create category {category_name}: {result.message}")
        except Exception as e:
            # If category already exists, try to get its ID
            try:
                existing_category = category_service.get_category(name=category_name)
                if existing_category.success:
                    category_map[category_name] = existing_category.data["id"]
                    print(f"  ○ Using existing category: {category_name}")
                else:
                    print(f"  ✗ Failed to get existing category {category_name}: {existing_category.message}")
            except Exception as get_error:
                print(f"  ✗ Failed to create or get category {category_name}: {e}")

    return category_map


def create_parts(location_map, category_map):
    """Create a variety of parts with different category assignments"""
    print("Creating parts...")

    parts_data = [
        # Electronics components
        {
            "name": "Arduino Uno R3",
            "part_number": "ARD-UNO-R3",
            "description": "Microcontroller development board",
            "quantity": 5,
            "minimum_quantity": 2,
            "supplier": "Arduino",
            "location": "Components Drawer 2",
            "categories": ["Electronics", "Microcontrollers"],
        },
        {
            "name": "Raspberry Pi 4 Model B",
            "part_number": "RPI-4B-4GB",
            "description": "Single board computer, 4GB RAM",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "Raspberry Pi Foundation",
            "location": "Components Drawer 2",
            "categories": ["Electronics", "Microcontrollers"],
        },
        {
            "name": "10kΩ Resistor (1/4W)",
            "part_number": "RES-10K-025W",
            "description": "Carbon film resistor, 5% tolerance",
            "quantity": 100,
            "minimum_quantity": 50,
            "supplier": "Vishay",
            "location": "Components Drawer 1",
            "categories": ["Electronics", "Passive Components"],
        },
        {
            "name": "100µF Electrolytic Capacitor",
            "part_number": "CAP-100UF-25V",
            "description": "Aluminum electrolytic capacitor, 25V",
            "quantity": 25,
            "minimum_quantity": 10,
            "supplier": "Panasonic",
            "location": "Components Drawer 1",
            "categories": ["Electronics", "Passive Components"],
        },
        {
            "name": "DHT22 Temperature Sensor",
            "part_number": "SENS-DHT22",
            "description": "Digital temperature and humidity sensor",
            "quantity": 8,
            "minimum_quantity": 3,
            "supplier": "Aosong",
            "location": "Components Drawer 2",
            "categories": ["Electronics", "Sensors"],
        },
        {
            "name": "SG90 Servo Motor",
            "part_number": "SERVO-SG90",
            "description": "Micro servo motor, 9g",
            "quantity": 12,
            "minimum_quantity": 5,
            "supplier": "TowerPro",
            "location": "Shelf A2",
            "categories": ["Electronics", "Actuators"],
        },
        {
            "name": "ESP32 Development Board",
            "part_number": "ESP32-DEV",
            "description": "WiFi and Bluetooth microcontroller",
            "quantity": 6,
            "minimum_quantity": 2,
            "supplier": "Espressif",
            "location": "Components Drawer 2",
            "categories": ["Electronics", "Microcontrollers", "Communication"],
        },
        # Mechanical components
        {
            "name": "M3 x 10mm Socket Head Screw",
            "part_number": "SCR-M3-10-SHC",
            "description": "Stainless steel socket head cap screw",
            "quantity": 500,
            "minimum_quantity": 100,
            "supplier": "McMaster-Carr",
            "location": "Bin 001",
            "categories": ["Mechanical", "Fasteners", "Hardware"],
        },
        {
            "name": "M3 Hex Nut",
            "part_number": "NUT-M3-HEX",
            "description": "Stainless steel hex nut",
            "quantity": 200,
            "minimum_quantity": 50,
            "supplier": "McMaster-Carr",
            "location": "Bin 003",
            "categories": ["Mechanical", "Fasteners", "Hardware"],
        },
        {
            "name": "M3 Washer",
            "part_number": "WASH-M3-FLAT",
            "description": "Stainless steel flat washer",
            "quantity": 150,
            "minimum_quantity": 30,
            "supplier": "McMaster-Carr",
            "location": "Bin 002",
            "categories": ["Mechanical", "Fasteners", "Hardware"],
        },
        # 3D Printing supplies
        {
            "name": "PLA Filament - Black",
            "part_number": "FIL-PLA-BLK-1KG",
            "description": "PLA 3D printer filament, 1.75mm, 1kg spool",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "eSUN",
            "location": "Filament Storage",
            "categories": ["3D Printing", "Filament", "Consumables"],
        },
        {
            "name": "PLA Filament - White",
            "part_number": "FIL-PLA-WHT-1KG",
            "description": "PLA 3D printer filament, 1.75mm, 1kg spool",
            "quantity": 2,
            "minimum_quantity": 1,
            "supplier": "eSUN",
            "location": "Filament Storage",
            "categories": ["3D Printing", "Filament", "Consumables"],
        },
        {
            "name": "PETG Filament - Clear",
            "part_number": "FIL-PETG-CLR-1KG",
            "description": "PETG 3D printer filament, 1.75mm, 1kg spool",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "eSUN",
            "location": "Filament Storage",
            "categories": ["3D Printing", "Filament", "Consumables"],
        },
        # Tools
        {
            "name": "Digital Multimeter",
            "part_number": "DMM-FLUKE-117",
            "description": "HVAC digital multimeter with temperature",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "Fluke",
            "location": "Tool Cabinet",
            "categories": ["Tools", "Measuring Tools", "Electronics"],
        },
        {
            "name": "Soldering Iron",
            "part_number": "IRON-HAKKO-FX888D",
            "description": "Digital soldering station, 70W",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "Hakko",
            "location": "Electronics Bench",
            "categories": ["Tools", "Hand Tools", "Electronics"],
        },
        {
            "name": "Wire Strippers",
            "part_number": "STRIP-KLEIN-11057",
            "description": "Wire stripper/cutter, 10-18 AWG",
            "quantity": 2,
            "minimum_quantity": 1,
            "supplier": "Klein Tools",
            "location": "Tool Cabinet",
            "categories": ["Tools", "Hand Tools", "Electronics"],
        },
        # Raw materials
        {
            "name": "Aluminum Sheet 1mm",
            "part_number": "AL-SHEET-1MM-300X200",
            "description": "Aluminum sheet, 1mm thick, 300x200mm",
            "quantity": 10,
            "minimum_quantity": 3,
            "supplier": "OnlineMetals",
            "location": "Shelf A1",
            "categories": ["Raw Materials", "Metal Stock"],
        },
        {
            "name": "Acrylic Sheet Clear 3mm",
            "part_number": "ACR-CLR-3MM-300X300",
            "description": "Clear acrylic sheet, 3mm thick, 300x300mm",
            "quantity": 5,
            "minimum_quantity": 2,
            "supplier": "TAP Plastics",
            "location": "Shelf A1",
            "categories": ["Raw Materials", "Plastic Stock"],
        },
        # Consumables
        {
            "name": "Super Glue",
            "part_number": "GLUE-CA-20G",
            "description": "Cyanoacrylate adhesive, 20g tube",
            "quantity": 8,
            "minimum_quantity": 3,
            "supplier": "Loctite",
            "location": "Shelf B",
            "categories": ["Consumables", "Adhesives"],
        },
        {
            "name": "Isopropyl Alcohol 99%",
            "part_number": "IPA-99-500ML",
            "description": "Isopropyl alcohol, 99% pure, 500ml bottle",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "Generic",
            "location": "Shelf B",
            "categories": ["Consumables", "Cleaning Supplies"],
        },
    ]

    created_parts = []
    part_service = PartService()

    for part_data in parts_data:
        try:
            # Get location ID
            location_id = None
            if part_data["location"] in location_map:
                location_id = location_map[part_data["location"]]

            # Get category names
            category_names = []
            for cat_name in part_data["categories"]:
                if cat_name in category_map:
                    category_names.append(cat_name)

            # Create part
            part_create_data = {
                "part_name": part_data["name"],
                "part_number": part_data["part_number"],
                "description": part_data["description"],
                "quantity": part_data["quantity"],
                "minimum_quantity": part_data["minimum_quantity"],
                "supplier": part_data["supplier"],
                "location_id": location_id,
                "category_names": category_names,
            }

            result = part_service.add_part(part_create_data)
            if result.success:
                created_parts.append(result.data)
                print(f"  ✓ Created part: {part_data['name']} with {len(category_names)} categories")
            else:
                print(f"  ✗ Failed to create part {part_data['name']}: {result.message}")

        except Exception as e:
            print(f"  ✗ Failed to create part {part_data['name']}: {e}")

    return created_parts


def main():
    """Main function to create all test data"""
    print("🔧 MakerMatrix Test Data Creation Script")
    print("========================================")

    # Ensure database tables exist
    print("Initializing database...")
    create_db_and_tables()

    # Create test data
    location_map = create_locations()
    category_map = create_categories()
    parts = create_parts(location_map, category_map)

    print("\n📊 Summary:")
    print(f"  • Created {len(location_map)} locations")
    print(f"  • Created {len(category_map)} categories")
    print(f"  • Created {len(parts)} parts")

    print("\n✅ Test data creation completed!")
    print("\nYou can now:")
    print("  • View parts in the web interface")
    print("  • Test search and filtering")
    print("  • Verify category assignments")
    print("  • Check nested location hierarchy")
    print("  • Test deletion and activity logging")


if __name__ == "__main__":
    main()
