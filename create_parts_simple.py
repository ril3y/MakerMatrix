#!/usr/bin/env python3
"""
Simple script to create parts using the working API endpoints.
This uses the same approach as our successful tests.
"""

import sys
import requests
import json
sys.path.append('.')

# API Configuration
BASE_URL = "http://localhost:57891"
API_BASE = f"{BASE_URL}/api"

def get_admin_token():
    """Get admin authentication token"""
    login_data = {
        "username": "admin",
        "password": "Admin123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to login: {response.text}")

def get_all_categories(token):
    """Get all available categories"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/categories/get_all_categories", headers=headers)
    if response.status_code == 200:
        return response.json()["data"]["categories"]
    else:
        print(f"Failed to get categories: {response.text}")
        return []

def get_all_locations(token):
    """Get all available locations"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/locations/get_all_locations", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"DEBUG: Locations response: {data}")
        # Handle different possible response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "data" in data:
            return data["data"]
        else:
            return data
    else:
        print(f"Failed to get locations: {response.text}")
        return []

def create_part(token, part_data):
    """Create a single part using the API"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/parts/add_part", json=part_data, headers=headers)
    
    if response.status_code == 200:
        return response.json()["data"]
    else:
        print(f"Failed to create part {part_data['part_name']}: {response.text}")
        return None

def main():
    """Create parts with categories and locations"""
    print("🔧 MakerMatrix Simple Parts Creation Script")
    print("============================================")
    
    try:
        # Get authentication token
        print("🔐 Getting authentication token...")
        token = get_admin_token()
        print("✅ Authentication successful")
        
        # Get available categories and locations
        print("📋 Getting categories and locations...")
        categories = get_all_categories(token)
        locations = get_all_locations(token)
        
        print(f"Found {len(categories)} categories")
        print(f"Found {len(locations)} locations")
        
        # Create category and location lookup maps
        category_map = {cat["name"]: cat["name"] for cat in categories}
        location_map = {loc["name"]: loc["id"] for loc in locations}
        
        print("Available categories:", list(category_map.keys())[:5], "...")
        print("Available locations:", list(location_map.keys())[:5], "...")
        
        # Define parts to create (using the working API format)
        parts_to_create = [
            {
                "part_name": "Arduino Uno R3",
                "part_number": "ARD-UNO-R3",
                "description": "Microcontroller development board",
                "quantity": 5,
                "minimum_quantity": 2,
                "supplier": "Arduino",
                "location_id": location_map.get("Components Drawer 2"),
                "category_names": ["Electronics", "Microcontrollers"]
            },
            {
                "part_name": "Raspberry Pi 4 Model B",
                "part_number": "RPI-4B-4GB", 
                "description": "Single board computer, 4GB RAM",
                "quantity": 3,
                "minimum_quantity": 1,
                "supplier": "Raspberry Pi Foundation",
                "location_id": location_map.get("Components Drawer 2"),
                "category_names": ["Electronics", "Microcontrollers"]
            },
            {
                "part_name": "10kΩ Resistor (1/4W)",
                "part_number": "RES-10K-025W",
                "description": "Carbon film resistor, 5% tolerance",
                "quantity": 100,
                "minimum_quantity": 50,
                "supplier": "Vishay",
                "location_id": location_map.get("Components Drawer 1"),
                "category_names": ["Electronics", "Passive Components"]
            },
            {
                "part_name": "100µF Electrolytic Capacitor",
                "part_number": "CAP-100UF-25V",
                "description": "Aluminum electrolytic capacitor, 25V",
                "quantity": 25,
                "minimum_quantity": 10,
                "supplier": "Panasonic",
                "location_id": location_map.get("Components Drawer 1"),
                "category_names": ["Electronics", "Passive Components"]
            },
            {
                "part_name": "DHT22 Temperature Sensor",
                "part_number": "SENS-DHT22",
                "description": "Digital temperature and humidity sensor",
                "quantity": 8,
                "minimum_quantity": 3,
                "supplier": "Aosong",
                "location_id": location_map.get("Components Drawer 2"),
                "category_names": ["Electronics", "Sensors"]
            },
            {
                "part_name": "SG90 Servo Motor",
                "part_number": "SERVO-SG90", 
                "description": "Micro servo motor, 9g",
                "quantity": 12,
                "minimum_quantity": 5,
                "supplier": "TowerPro",
                "location_id": location_map.get("Shelf A2"),
                "category_names": ["Electronics", "Actuators"]
            },
            {
                "part_name": "ESP32 Development Board",
                "part_number": "ESP32-DEV",
                "description": "WiFi and Bluetooth microcontroller",
                "quantity": 6,
                "minimum_quantity": 2,
                "supplier": "Espressif",
                "location_id": location_map.get("Components Drawer 2"),
                "category_names": ["Electronics", "Microcontrollers", "Communication"]
            },
            {
                "part_name": "M3 x 10mm Socket Head Screw",
                "part_number": "SCR-M3-10-SHC",
                "description": "Stainless steel socket head cap screw",
                "quantity": 500,
                "minimum_quantity": 100,
                "supplier": "McMaster-Carr",
                "location_id": location_map.get("Bin 001"),
                "category_names": ["Mechanical", "Fasteners", "Hardware"]
            },
            {
                "part_name": "M3 Hex Nut",
                "part_number": "NUT-M3-HEX",
                "description": "Stainless steel hex nut",
                "quantity": 200,
                "minimum_quantity": 50,
                "supplier": "McMaster-Carr",
                "location_id": location_map.get("Bin 003"),
                "category_names": ["Mechanical", "Fasteners", "Hardware"]
            },
            {
                "part_name": "PLA Filament - Black",
                "part_number": "FIL-PLA-BLK-1KG",
                "description": "PLA 3D printer filament, 1.75mm, 1kg spool",
                "quantity": 3,
                "minimum_quantity": 1,
                "supplier": "eSUN",
                "location_id": location_map.get("Filament Storage"),
                "category_names": ["3D Printing", "Filament", "Consumables"]
            },
            {
                "part_name": "Digital Multimeter",
                "part_number": "DMM-FLUKE-117",
                "description": "HVAC digital multimeter with temperature",
                "quantity": 1,
                "minimum_quantity": 1,
                "supplier": "Fluke",
                "location_id": location_map.get("Tool Cabinet"),
                "category_names": ["Tools", "Measuring Tools", "Electronics"]
            },
            {
                "part_name": "Soldering Iron",
                "part_number": "IRON-HAKKO-FX888D",
                "description": "Digital soldering station, 70W",
                "quantity": 1,
                "minimum_quantity": 1,
                "supplier": "Hakko",
                "location_id": location_map.get("Electronics Bench"),
                "category_names": ["Tools", "Hand Tools", "Electronics"]
            },
            {
                "part_name": "Super Glue",
                "part_number": "GLUE-CA-20G",
                "description": "Cyanoacrylate adhesive, 20g tube",
                "quantity": 8,
                "minimum_quantity": 3,
                "supplier": "Loctite",
                "location_id": location_map.get("Shelf B"),
                "category_names": ["Consumables", "Adhesives"]
            },
            {
                "part_name": "Aluminum Sheet 1mm",
                "part_number": "AL-SHEET-1MM-300X200",
                "description": "Aluminum sheet, 1mm thick, 300x200mm",
                "quantity": 10,
                "minimum_quantity": 3,
                "supplier": "OnlineMetals",
                "location_id": location_map.get("Shelf A1"),
                "category_names": ["Raw Materials", "Metal Stock"]
            },
            {
                "part_name": "Isopropyl Alcohol 99%",
                "part_number": "IPA-99-500ML",
                "description": "Isopropyl alcohol, 99% pure, 500ml bottle",
                "quantity": 3,
                "minimum_quantity": 1,
                "supplier": "Generic",
                "location_id": location_map.get("Shelf B"),
                "category_names": ["Consumables", "Cleaning Supplies"]
            }
        ]
        
        # Create parts
        print(f"\n🔨 Creating {len(parts_to_create)} parts...")
        created_count = 0
        failed_count = 0
        
        for part_data in parts_to_create:
            # Filter out categories that don't exist
            valid_categories = []
            for cat_name in part_data["category_names"]:
                if cat_name in category_map:
                    valid_categories.append(cat_name)
                else:
                    print(f"  ⚠️  Category '{cat_name}' not found for {part_data['part_name']}")
            
            part_data["category_names"] = valid_categories
            
            # Remove location_id if location doesn't exist
            if part_data["location_id"] is None:
                print(f"  ⚠️  Location not found for {part_data['part_name']}, creating without location")
            
            # Create the part
            created_part = create_part(token, part_data)
            if created_part:
                created_count += 1
                print(f"  ✅ Created: {part_data['part_name']} ({len(valid_categories)} categories)")
            else:
                failed_count += 1
                print(f"  ❌ Failed: {part_data['part_name']}")
        
        print(f"\n📊 Summary:")
        print(f"  • Successfully created: {created_count} parts")
        print(f"  • Failed to create: {failed_count} parts")
        print(f"  • Total locations: {len(locations)}")
        print(f"  • Total categories: {len(categories)}")
        
        print(f"\n✅ Parts creation completed!")
        print(f"🌐 You can now view your inventory at: {BASE_URL}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()