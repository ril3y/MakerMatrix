#!/usr/bin/env python3
"""
Direct database script to create parts with categories and locations.
This bypasses the API and works directly with the service layer.
"""

import sys
sys.path.append('.')

from sqlmodel import Session
from MakerMatrix.models.models import engine
from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.database.db import create_db_and_tables

def get_categories_map():
    """Get all categories as a name-to-ID mapping"""
    try:
        result = CategoryService.get_all_categories()
        return {cat["name"]: cat["id"] for cat in result["data"]["categories"]}
    except Exception as e:
        print(f"Failed to get categories: {e}")
        return {}

def get_locations_map():
    """Get all locations as a name-to-ID mapping"""
    try:
        locations = LocationService.get_all_locations()
        return {loc.name: loc.id for loc in locations}
    except Exception as e:
        print(f"Failed to get locations: {e}")
        return {}

def create_part_direct(part_data, categories_map, locations_map):
    """Create a part using direct service calls"""
    try:
        # Validate categories exist
        valid_category_names = []
        for cat_name in part_data.get("category_names", []):
            if cat_name in categories_map:
                valid_category_names.append(cat_name)
            else:
                print(f"  ⚠️  Category '{cat_name}' not found")
        
        # Get location ID if specified
        location_id = None
        location_name = part_data.get("location_name")
        if location_name and location_name in locations_map:
            location_id = locations_map[location_name]
        elif location_name:
            print(f"  ⚠️  Location '{location_name}' not found")
        
        # Prepare part data for service
        service_data = {
            "part_name": part_data["part_name"],
            "part_number": part_data["part_number"],
            "description": part_data["description"],
            "quantity": part_data["quantity"],
            "minimum_quantity": part_data.get("minimum_quantity"),
            "supplier": part_data.get("supplier"),
            "location_id": location_id,
            "category_names": valid_category_names
        }
        
        # Create the part
        result = PartService.add_part(service_data)
        return result["data"]
        
    except Exception as e:
        print(f"  ❌ Failed to create {part_data['part_name']}: {e}")
        return None

def main():
    """Create parts with categories and locations"""
    print("🔧 MakerMatrix Direct Parts Creation Script")
    print("=============================================")
    
    # Ensure database is initialized
    create_db_and_tables()
    
    # Get available categories and locations
    print("📋 Getting categories and locations...")
    categories_map = get_categories_map()
    locations_map = get_locations_map()
    
    print(f"Found {len(categories_map)} categories")
    print(f"Found {len(locations_map)} locations")
    
    if len(categories_map) == 0 or len(locations_map) == 0:
        print("❌ No categories or locations found. Run create_test_data.py first!")
        return
    
    print("Sample categories:", list(categories_map.keys())[:5])
    print("Sample locations:", list(locations_map.keys())[:5])
    
    # Define parts to create
    parts_to_create = [
        {
            "part_name": "Arduino Uno R3",
            "part_number": "ARD-UNO-R3",
            "description": "Microcontroller development board",
            "quantity": 5,
            "minimum_quantity": 2,
            "supplier": "Arduino",
            "location_name": "Components Drawer 2",
            "category_names": ["Electronics", "Microcontrollers"]
        },
        {
            "part_name": "Raspberry Pi 4 Model B",
            "part_number": "RPI-4B-4GB", 
            "description": "Single board computer, 4GB RAM",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "Raspberry Pi Foundation",
            "location_name": "Components Drawer 2",
            "category_names": ["Electronics", "Microcontrollers"]
        },
        {
            "part_name": "10kΩ Resistor (1/4W)",
            "part_number": "RES-10K-025W",
            "description": "Carbon film resistor, 5% tolerance",
            "quantity": 100,
            "minimum_quantity": 50,
            "supplier": "Vishay",
            "location_name": "Components Drawer 1",
            "category_names": ["Electronics", "Passive Components"]
        },
        {
            "part_name": "100µF Electrolytic Capacitor",
            "part_number": "CAP-100UF-25V",
            "description": "Aluminum electrolytic capacitor, 25V",
            "quantity": 25,
            "minimum_quantity": 10,
            "supplier": "Panasonic",
            "location_name": "Components Drawer 1",
            "category_names": ["Electronics", "Passive Components"]
        },
        {
            "part_name": "DHT22 Temperature Sensor",
            "part_number": "SENS-DHT22",
            "description": "Digital temperature and humidity sensor",
            "quantity": 8,
            "minimum_quantity": 3,
            "supplier": "Aosong",
            "location_name": "Components Drawer 2",
            "category_names": ["Electronics", "Sensors"]
        },
        {
            "part_name": "SG90 Servo Motor",
            "part_number": "SERVO-SG90", 
            "description": "Micro servo motor, 9g",
            "quantity": 12,
            "minimum_quantity": 5,
            "supplier": "TowerPro",
            "location_name": "Shelf A2",
            "category_names": ["Electronics", "Actuators"]
        },
        {
            "part_name": "ESP32 Development Board",
            "part_number": "ESP32-DEV",
            "description": "WiFi and Bluetooth microcontroller",
            "quantity": 6,
            "minimum_quantity": 2,
            "supplier": "Espressif",
            "location_name": "Components Drawer 2",
            "category_names": ["Electronics", "Microcontrollers", "Communication"]
        },
        {
            "part_name": "M3 x 10mm Socket Head Screw",
            "part_number": "SCR-M3-10-SHC",
            "description": "Stainless steel socket head cap screw",
            "quantity": 500,
            "minimum_quantity": 100,
            "supplier": "McMaster-Carr",
            "location_name": "Bin 001",
            "category_names": ["Mechanical", "Fasteners", "Hardware"]
        },
        {
            "part_name": "M3 Hex Nut",
            "part_number": "NUT-M3-HEX",
            "description": "Stainless steel hex nut",
            "quantity": 200,
            "minimum_quantity": 50,
            "supplier": "McMaster-Carr",
            "location_name": "Bin 003",
            "category_names": ["Mechanical", "Fasteners", "Hardware"]
        },
        {
            "part_name": "M3 Washer",
            "part_number": "WASH-M3-FLAT",
            "description": "Stainless steel flat washer",
            "quantity": 150,
            "minimum_quantity": 30,
            "supplier": "McMaster-Carr",
            "location_name": "Bin 002",
            "category_names": ["Mechanical", "Fasteners", "Hardware"]
        },
        {
            "part_name": "PLA Filament - Black",
            "part_number": "FIL-PLA-BLK-1KG",
            "description": "PLA 3D printer filament, 1.75mm, 1kg spool",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "eSUN",
            "location_name": "Filament Storage",
            "category_names": ["3D Printing", "Filament", "Consumables"]
        },
        {
            "part_name": "PLA Filament - White",
            "part_number": "FIL-PLA-WHT-1KG", 
            "description": "PLA 3D printer filament, 1.75mm, 1kg spool",
            "quantity": 2,
            "minimum_quantity": 1,
            "supplier": "eSUN",
            "location_name": "Filament Storage",
            "category_names": ["3D Printing", "Filament", "Consumables"]
        },
        {
            "part_name": "Digital Multimeter",
            "part_number": "DMM-FLUKE-117",
            "description": "HVAC digital multimeter with temperature",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "Fluke",
            "location_name": "Tool Cabinet",
            "category_names": ["Tools", "Measuring Tools", "Electronics"]
        },
        {
            "part_name": "Soldering Iron",
            "part_number": "IRON-HAKKO-FX888D",
            "description": "Digital soldering station, 70W",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "Hakko",
            "location_name": "Electronics Bench",
            "category_names": ["Tools", "Hand Tools", "Electronics"]
        },
        {
            "part_name": "Wire Strippers",
            "part_number": "STRIP-KLEIN-11057",
            "description": "Wire stripper/cutter, 10-18 AWG",
            "quantity": 2,
            "minimum_quantity": 1,
            "supplier": "Klein Tools",
            "location_name": "Tool Cabinet",
            "category_names": ["Tools", "Hand Tools", "Electronics"]
        },
        {
            "part_name": "Aluminum Sheet 1mm",
            "part_number": "AL-SHEET-1MM-300X200",
            "description": "Aluminum sheet, 1mm thick, 300x200mm",
            "quantity": 10,
            "minimum_quantity": 3,
            "supplier": "OnlineMetals",
            "location_name": "Shelf A1",
            "category_names": ["Raw Materials", "Metal Stock"]
        },
        {
            "part_name": "Acrylic Sheet Clear 3mm",
            "part_number": "ACR-CLR-3MM-300X300",
            "description": "Clear acrylic sheet, 3mm thick, 300x300mm",
            "quantity": 5,
            "minimum_quantity": 2,
            "supplier": "TAP Plastics",
            "location_name": "Shelf A1",
            "category_names": ["Raw Materials", "Plastic Stock"]
        },
        {
            "part_name": "Super Glue",
            "part_number": "GLUE-CA-20G",
            "description": "Cyanoacrylate adhesive, 20g tube",
            "quantity": 8,
            "minimum_quantity": 3,
            "supplier": "Loctite",
            "location_name": "Shelf B",
            "category_names": ["Consumables", "Adhesives"]
        },
        {
            "part_name": "Isopropyl Alcohol 99%",
            "part_number": "IPA-99-500ML",
            "description": "Isopropyl alcohol, 99% pure, 500ml bottle",
            "quantity": 3,
            "minimum_quantity": 1,
            "supplier": "Generic",
            "location_name": "Shelf B",
            "category_names": ["Consumables", "Cleaning Supplies"]
        }
    ]
    
    # Create parts
    print(f"\n🔨 Creating {len(parts_to_create)} parts...")
    created_count = 0
    failed_count = 0
    
    for part_data in parts_to_create:
        created_part = create_part_direct(part_data, categories_map, locations_map)
        if created_part:
            created_count += 1
            category_count = len(part_data.get("category_names", []))
            print(f"  ✅ Created: {part_data['part_name']} ({category_count} categories)")
        else:
            failed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"  • Successfully created: {created_count} parts")
    print(f"  • Failed to create: {failed_count} parts")
    print(f"  • Total locations: {len(locations_map)}")
    print(f"  • Total categories: {len(categories_map)}")
    
    print(f"\n✅ Parts creation completed!")
    print(f"🌐 Start the API server to view your inventory in the web interface")

if __name__ == "__main__":
    main()