#!/usr/bin/env python3
"""
Initialize System Label Templates

Creates the 7 pre-designed system templates in the database.
These templates are available to all users and cover common use cases.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlmodel import Session
from MakerMatrix.models.models import engine
from MakerMatrix.models.label_template_models import (
    LabelTemplateModel,
    TemplateCategory,
    LayoutType,
    TextRotation,
    TextAlignment,
    QRPosition
)
from MakerMatrix.repositories.label_template_repository import LabelTemplateRepository


# Define the 7 system templates
SYSTEM_TEMPLATES = [
    {
        "name": "makermatrix_12mm_box",
        "display_name": "MakerMatrix 12mm Box Label",
        "description": "Standard box label with QR code and part name. Optimized for phone scanning with 8mm minimum QR size.",
        "category": TemplateCategory.COMPONENT,
        "label_width_mm": 39.0,
        "label_height_mm": 12.0,
        "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
        "text_template": "{part_name}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.CENTER,
        "qr_enabled": True,
        "qr_position": QRPosition.LEFT,
        "qr_scale": 0.95,
        "enable_multiline": False,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "component_vertical",
        "display_name": "Component Vertical Label",
        "description": "Rotated text for narrow components. 90° text rotation, vertical layout.",
        "category": TemplateCategory.COMPONENT,
        "label_width_mm": 62.0,
        "label_height_mm": 12.0,
        "layout_type": LayoutType.TEXT_ONLY,
        "text_template": "{part_name}\\n{part_number}",
        "text_rotation": TextRotation.QUARTER,
        "text_alignment": TextAlignment.CENTER,
        "qr_enabled": False,
        "qr_position": QRPosition.LEFT,
        "enable_multiline": True,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "location_label",
        "display_name": "Location Label",
        "description": "Multi-line location with QR code. For storage area labels.",
        "category": TemplateCategory.LOCATION,
        "label_width_mm": 29.0,
        "label_height_mm": 62.0,
        "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
        "text_template": "{location_name}\\n{description}\\nBin: {location_id}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.LEFT,
        "qr_enabled": True,
        "qr_position": QRPosition.TOP,
        "qr_scale": 0.90,
        "enable_multiline": True,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "inventory_tag",
        "display_name": "Inventory Tag",
        "description": "Quantity + description layouts for inventory management.",
        "category": TemplateCategory.INVENTORY,
        "label_width_mm": 25.0,
        "label_height_mm": 50.0,
        "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
        "text_template": "{part_name}\\nQty: {quantity}\\n{description}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.CENTER,
        "qr_enabled": True,
        "qr_position": QRPosition.BOTTOM,
        "qr_scale": 0.85,
        "enable_multiline": True,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "cable_label",
        "display_name": "Cable Label",
        "description": "Long, narrow cable identification. Horizontal layout for cable management.",
        "category": TemplateCategory.CABLE,
        "label_width_mm": 102.0,
        "label_height_mm": 12.0,
        "layout_type": LayoutType.TEXT_ONLY,
        "text_template": "{cable_name} | {source} → {destination} | {cable_type}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.CENTER,
        "qr_enabled": False,
        "qr_position": QRPosition.LEFT,
        "enable_multiline": False,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "storage_box",
        "display_name": "Storage Box Label",
        "description": "Large format storage container labels. Big container labels with detailed information.",
        "category": TemplateCategory.STORAGE,
        "label_width_mm": 51.0,
        "label_height_mm": 102.0,
        "layout_type": LayoutType.QR_TEXT_VERTICAL,
        "text_template": "{container_name}\\n{description}\\nContents: {contents}\\nLocation: {location}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.LEFT,
        "qr_enabled": True,
        "qr_position": QRPosition.TOP_RIGHT,
        "qr_scale": 0.90,
        "enable_multiline": True,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    },
    {
        "name": "small_parts",
        "display_name": "Small Parts Label",
        "description": "Tiny component labels (6mm height). Text-only for tiny labels.",
        "category": TemplateCategory.COMPONENT,
        "label_width_mm": 19.0,
        "label_height_mm": 6.0,
        "layout_type": LayoutType.TEXT_ONLY,
        "text_template": "{part_number}",
        "text_rotation": TextRotation.NONE,
        "text_alignment": TextAlignment.CENTER,
        "qr_enabled": False,
        "qr_position": QRPosition.LEFT,
        "enable_multiline": False,
        "enable_auto_sizing": True,
        "is_system_template": True,
        "is_public": True,
        "is_active": True
    }
]


def init_system_templates():
    """Initialize system templates in the database"""

    with Session(engine) as session:
        repo = LabelTemplateRepository()

        print("🎨 Initializing System Label Templates...")
        print("=" * 60)

        created_count = 0
        skipped_count = 0

        for template_data in SYSTEM_TEMPLATES:
            template_name = template_data["name"]

            # Check if template already exists
            existing = repo.get_by_name(session, template_name)
            if existing:
                print(f"⏭️  Skipping '{template_data['display_name']}' - already exists")
                skipped_count += 1
                continue

            # Create template
            try:
                template = LabelTemplateModel(**template_data)
                created = repo.create_template(session, template)
                print(f"✅ Created '{created.display_name}' ({created.label_width_mm}×{created.label_height_mm}mm)")
                created_count += 1
            except Exception as e:
                print(f"❌ Failed to create '{template_data['display_name']}': {e}")

        print("=" * 60)
        print(f"✨ Initialization complete!")
        print(f"   Created: {created_count} templates")
        print(f"   Skipped: {skipped_count} templates (already existed)")
        print(f"   Total system templates: {created_count + skipped_count}")


if __name__ == "__main__":
    init_system_templates()
