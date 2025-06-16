#!/usr/bin/env python3
"""
Manual parts creation script that bypasses the service layer.
Creates parts directly in the database using SQLModel.
"""

import sys
sys.path.append('.')

from sqlmodel import Session, select
from MakerMatrix.models.models import engine, PartModel, CategoryModel, LocationModel, PartCategoryLink
from MakerMatrix.database.db import create_db_and_tables
import uuid

def get_category_by_name(session: Session, name: str):
    """Get category by name"""
    statement = select(CategoryModel).where(CategoryModel.name == name)
    return session.exec(statement).first()

def get_location_by_name(session: Session, name: str):
    """Get location by name"""
    statement = select(LocationModel).where(LocationModel.name == name)
    return session.exec(statement).first()

def create_part_manual(session: Session, part_data):
    """Create a part manually with direct database operations"""
    try:
        # Get location if specified
        location = None
        if part_data.get("location_name"):
            location = get_location_by_name(session, part_data["location_name"])
        
        # Create the part
        part = PartModel(
            id=str(uuid.uuid4()),
            part_name=part_data["part_name"],
            part_number=part_data["part_number"],
            description=part_data["description"],
            quantity=part_data["quantity"],
            minimum_quantity=part_data.get("minimum_quantity"),
            supplier=part_data.get("supplier"),
            location_id=location.id if location else None
        )
        
        session.add(part)
        session.flush()  # Get the ID
        
        # Add categories
        for category_name in part_data.get("category_names", []):
            category = get_category_by_name(session, category_name)
            if category:
                # Create the many-to-many link
                link = PartCategoryLink(part_id=part.id, category_id=category.id)
                session.add(link)
        
        session.commit()
        return part
        
    except Exception as e:
        session.rollback()
        print(f"Failed to create {part_data['part_name']}: {e}")
        return None

def main():
    """Create parts manually"""
    print("🔧 Manual Parts Creation Script")
    print("===============================")
    
    create_db_and_tables()
    
    # Simple parts data (fewer parts to start)
    parts_data = [
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
            "part_name": "Digital Multimeter",
            "part_number": "DMM-FLUKE-117",
            "description": "HVAC digital multimeter with temperature",
            "quantity": 1,
            "minimum_quantity": 1,
            "supplier": "Fluke",
            "location_name": "Tool Cabinet",
            "category_names": ["Tools", "Measuring Tools", "Electronics"]
        }
    ]
    
    with Session(engine) as session:
        created_count = 0
        
        for part_data in parts_data:
            part = create_part_manual(session, part_data)
            if part:
                created_count += 1
                categories_str = ", ".join(part_data.get("category_names", []))
                print(f"  ✅ Created: {part_data['part_name']} ({categories_str})")
            else:
                print(f"  ❌ Failed: {part_data['part_name']}")
    
    print(f"\n📊 Summary:")
    print(f"  • Successfully created: {created_count} parts")
    print(f"  • Parts will appear in the web interface!")
    print(f"  • Categories and locations are already assigned!")
    
    print(f"\n✅ Manual part creation completed!")
    print(f"🌐 Refresh your browser at: http://localhost:57891")

if __name__ == "__main__":
    main()