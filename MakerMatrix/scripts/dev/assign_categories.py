#!/usr/bin/env python3
"""
Script to assign categories to existing parts in the database.
"""

import sys
sys.path.append('.')

from sqlmodel import Session
from MakerMatrix.models.models import engine
from MakerMatrix.services.data.category_service import CategoryService
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.schemas.part_create import PartUpdate


def assign_categories_to_parts():
    """Assign categories to existing parts based on their names and descriptions"""
    
    # Get all categories first
    try:
        categories_result = CategoryService.get_all_categories()
        categories = {cat["name"]: cat["id"] for cat in categories_result["data"]["categories"]}
        print(f"Found {len(categories)} categories")
    except Exception as e:
        print(f"Failed to get categories: {e}")
        return
    
    # Get all parts
    try:
        parts_result = PartService.get_all_parts()
        parts = parts_result["data"]
        print(f"Found {len(parts)} parts")
    except Exception as e:
        print(f"Failed to get parts: {e}")
        return
    
    # Part to category mappings based on part names/descriptions
    part_category_mappings = {
        "Arduino Uno R3": ["Electronics", "Microcontrollers"],
        "Raspberry Pi 4 Model B": ["Electronics", "Microcontrollers"],
        "10kΩ Resistor (1/4W)": ["Electronics", "Passive Components"],
        "100µF Electrolytic Capacitor": ["Electronics", "Passive Components"],
        "DHT22 Temperature Sensor": ["Electronics", "Sensors"],
        "SG90 Servo Motor": ["Electronics", "Actuators"],
        "ESP32 Development Board": ["Electronics", "Microcontrollers", "Communication"],
        "M3 x 10mm Socket Head Screw": ["Mechanical", "Fasteners", "Hardware"],
        "M3 Hex Nut": ["Mechanical", "Fasteners", "Hardware"],
        "M3 Washer": ["Mechanical", "Fasteners", "Hardware"],
        "PLA Filament - Black": ["3D Printing", "Filament", "Consumables"],
        "PLA Filament - White": ["3D Printing", "Filament", "Consumables"],
        "PETG Filament - Clear": ["3D Printing", "Filament", "Consumables"],
        "Digital Multimeter": ["Tools", "Measuring Tools", "Electronics"],
        "Soldering Iron": ["Tools", "Hand Tools", "Electronics"],
        "Wire Strippers": ["Tools", "Hand Tools", "Electronics"],
        "Aluminum Sheet 1mm": ["Raw Materials", "Metal Stock"],
        "Acrylic Sheet Clear 3mm": ["Raw Materials", "Plastic Stock"],
        "Super Glue": ["Consumables", "Adhesives"],
        "Isopropyl Alcohol 99%": ["Consumables", "Cleaning Supplies"]
    }
    
    # Assign categories to parts
    for part in parts:
        part_name = part["part_name"]
        if part_name in part_category_mappings:
            category_names = part_category_mappings[part_name]
            
            # Get category IDs
            valid_category_names = []
            for cat_name in category_names:
                if cat_name in categories:
                    valid_category_names.append(cat_name)
                else:
                    print(f"  Warning: Category '{cat_name}' not found for part '{part_name}'")
            
            if valid_category_names:
                try:
                    # Update part with categories
                    update_data = PartUpdate(category_names=valid_category_names)
                    PartService.update_part(part["id"], update_data)
                    print(f"  ✓ Assigned {len(valid_category_names)} categories to: {part_name}")
                except Exception as e:
                    print(f"  ✗ Failed to assign categories to {part_name}: {e}")
            else:
                print(f"  ! No valid categories found for: {part_name}")
        else:
            print(f"  ? No category mapping defined for: {part_name}")


def main():
    print("🏷️  MakerMatrix Category Assignment Script")
    print("==========================================")
    assign_categories_to_parts()
    print("\n✅ Category assignment completed!")


if __name__ == "__main__":
    main()