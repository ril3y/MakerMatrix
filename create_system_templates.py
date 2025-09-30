#!/usr/bin/env python3
"""
System Template Library Creator

Creates the pre-designed template library as specified in Phase 5 of the
Enhanced Label Template System plan. These templates provide out-of-the-box
functionality for common labeling scenarios.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def create_system_templates():
    """Create all pre-designed system templates"""
    print("🏗️ Creating MakerMatrix System Template Library")
    print("=" * 50)

    try:
        from sqlmodel import Session
        from MakerMatrix.models.models import engine
        from MakerMatrix.models.label_template_models import (
            LabelTemplateModel,
            TemplateCategory,
            LayoutType,
            TextRotation,
            QRPosition,
            TextAlignment
        )
        from MakerMatrix.repositories.label_template_repository import LabelTemplateRepository

        repo = LabelTemplateRepository()

        # System templates as specified in the plan
        system_templates = [
            {
                "name": "MakerMatrix12mmBox",
                "display_name": "MakerMatrix 12mm Box Label",
                "description": "QR + part name for 12mm × 39mm labels - optimized for phone scanning",
                "category": TemplateCategory.COMPONENT,
                "label_width_mm": 39.0,
                "label_height_mm": 12.0,
                "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
                "text_template": "{part_name}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.LEFT,
                "qr_position": QRPosition.LEFT,
                "qr_scale": 0.95,
                "qr_min_size_mm": 8.0,
                "enable_multiline": True,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5},
                    "spacing": {"qr_text_gap": 1, "line_spacing": 1.0}
                },
                "font_config": {
                    "family": "DejaVu Sans",
                    "weight": "bold",
                    "auto_size": True,
                    "min_size": 6,
                    "max_size": 12
                }
            },
            {
                "name": "ComponentVertical",
                "display_name": "Component Vertical Label",
                "description": "Rotated text for narrow components - vertical text layout",
                "category": TemplateCategory.COMPONENT,
                "label_width_mm": 12.0,
                "label_height_mm": 62.0,
                "layout_type": LayoutType.QR_TEXT_VERTICAL,
                "text_template": "{part_name}\\n{part_number}",
                "text_rotation": TextRotation.QUARTER,  # 90 degrees
                "text_alignment": TextAlignment.CENTER,
                "qr_position": QRPosition.BOTTOM,
                "qr_scale": 0.8,
                "qr_min_size_mm": 8.0,
                "enable_multiline": True,
                "enable_auto_sizing": True,
                "supports_rotation": True,
                "supports_vertical_text": True,
                "layout_config": {
                    "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
                    "spacing": {"qr_text_gap": 2, "line_spacing": 1.2}
                }
            },
            {
                "name": "LocationLabel",
                "display_name": "Multi-line Location Label",
                "description": "Multi-line location with QR for storage areas",
                "category": TemplateCategory.LOCATION,
                "label_width_mm": 62.0,
                "label_height_mm": 29.0,
                "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
                "text_template": "{location_name}\\n{description}\\nBin: {location_id}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.LEFT,
                "qr_position": QRPosition.RIGHT,
                "qr_scale": 0.85,
                "qr_min_size_mm": 10.0,
                "enable_multiline": True,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 2, "bottom": 2, "left": 2, "right": 2},
                    "spacing": {"qr_text_gap": 3, "line_spacing": 1.3}
                },
                "font_config": {
                    "family": "DejaVu Sans",
                    "weight": "normal",
                    "auto_size": True,
                    "min_size": 8,
                    "max_size": 16
                }
            },
            {
                "name": "InventoryTag",
                "display_name": "Inventory Tag Label",
                "description": "Quantity + description layouts for inventory management",
                "category": TemplateCategory.INVENTORY,
                "label_width_mm": 50.0,
                "label_height_mm": 25.0,
                "layout_type": LayoutType.QR_TEXT_COMBINED,
                "text_template": "{part_name}\\nQty: {quantity}\\n{description}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.LEFT,
                "qr_position": QRPosition.TOP_RIGHT,
                "qr_scale": 0.7,
                "qr_min_size_mm": 8.0,
                "enable_multiline": True,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 1.5, "bottom": 1.5, "left": 1.5, "right": 1.5},
                    "spacing": {"qr_text_gap": 2, "line_spacing": 1.2}
                }
            },
            {
                "name": "CableLabel",
                "display_name": "Cable Identification Label",
                "description": "Long, narrow cable identification - horizontal layout",
                "category": TemplateCategory.CABLE,
                "label_width_mm": 102.0,
                "label_height_mm": 12.0,
                "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
                "text_template": "{cable_name} | {source} → {destination} | {cable_type}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.CENTER,
                "qr_position": QRPosition.LEFT,
                "qr_scale": 0.9,
                "qr_min_size_mm": 8.0,
                "enable_multiline": False,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 0.5, "bottom": 0.5, "left": 1, "right": 1},
                    "spacing": {"qr_text_gap": 2, "line_spacing": 1.0}
                },
                "font_config": {
                    "family": "DejaVu Sans Mono",
                    "weight": "normal",
                    "auto_size": True,
                    "min_size": 6,
                    "max_size": 10
                }
            },
            {
                "name": "StorageBox",
                "display_name": "Storage Box Label",
                "description": "Large format storage container labels",
                "category": TemplateCategory.STORAGE,
                "label_width_mm": 102.0,
                "label_height_mm": 51.0,
                "layout_type": LayoutType.QR_TEXT_HORIZONTAL,
                "text_template": "{container_name}\\n{description}\\nContents: {contents}\\nLocation: {location}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.LEFT,
                "qr_position": QRPosition.RIGHT,
                "qr_scale": 0.8,
                "qr_min_size_mm": 15.0,
                "enable_multiline": True,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 3, "bottom": 3, "left": 3, "right": 3},
                    "spacing": {"qr_text_gap": 5, "line_spacing": 1.4}
                },
                "font_config": {
                    "family": "DejaVu Sans",
                    "weight": "bold",
                    "auto_size": True,
                    "min_size": 10,
                    "max_size": 24
                }
            },
            {
                "name": "SmallParts",
                "display_name": "Small Parts Label (6mm)",
                "description": "Tiny component labels for 6mm height labels",
                "category": TemplateCategory.COMPONENT,
                "label_width_mm": 19.0,
                "label_height_mm": 6.0,
                "layout_type": LayoutType.TEXT_ONLY,
                "text_template": "{part_number}",
                "text_rotation": TextRotation.NONE,
                "text_alignment": TextAlignment.CENTER,
                "qr_enabled": False,  # Too small for QR code
                "qr_position": QRPosition.CENTER,
                "qr_scale": 0.5,
                "enable_multiline": False,
                "enable_auto_sizing": True,
                "layout_config": {
                    "margins": {"top": 0.2, "bottom": 0.2, "left": 0.5, "right": 0.5},
                    "spacing": {"line_spacing": 1.0}
                },
                "font_config": {
                    "family": "DejaVu Sans",
                    "weight": "bold",
                    "auto_size": True,
                    "min_size": 4,
                    "max_size": 8
                }
            }
        ]

        created_count = 0
        updated_count = 0

        with Session(engine) as session:
            for template_data in system_templates:
                # Check if template already exists
                existing = repo.get_by_name(session, template_data["name"])

                if existing:
                    print(f"🔄 Updating existing template: {template_data['display_name']}")

                    # Update existing template with new data
                    for key, value in template_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)

                    existing.updated_at = datetime.utcnow()
                    existing.is_system_template = True
                    existing.is_public = True
                    existing.is_active = True

                    session.add(existing)
                    updated_count += 1
                else:
                    print(f"✨ Creating new template: {template_data['display_name']}")

                    # Create new template
                    template = LabelTemplateModel(
                        **template_data,
                        is_system_template=True,
                        is_public=True,
                        is_active=True,
                        created_by_user_id=None  # System templates have no owner
                    )

                    session.add(template)
                    created_count += 1

            # Commit all changes
            session.commit()

        print("\n" + "=" * 50)
        print("📊 System Template Library Creation Complete!")
        print("-" * 30)
        print(f"✨ New templates created: {created_count}")
        print(f"🔄 Templates updated: {updated_count}")
        print(f"📋 Total system templates: {created_count + updated_count}")

        # Validate all templates
        print("\n🔍 Validating system templates...")
        validation_errors = 0

        with Session(engine) as session:
            system_templates_db = session.exec(
                repo.model.select().where(repo.model.is_system_template == True)
            ).all()

            for template in system_templates_db:
                errors = template.validate_template()
                if errors:
                    print(f"⚠️ {template.display_name}: {', '.join(errors)}")
                    validation_errors += 1
                else:
                    print(f"✅ {template.display_name}: Valid")

        if validation_errors == 0:
            print(f"\n🎉 All {len(system_templates_db)} system templates are valid!")
        else:
            print(f"\n⚠️ {validation_errors} templates have validation warnings")

        return True

    except Exception as e:
        print(f"❌ System template creation failed: {e}")
        return False

def main():
    """Main execution function"""
    success = create_system_templates()

    if success:
        print("\n🚀 Next Steps:")
        print("   • Test templates with the printer")
        print("   • Implement template preview functionality")
        print("   • Build frontend template selection UI")
        print("   • Add template export/import features")

        print("\n💡 Template Usage Examples:")
        print("   GET /api/templates/ - List all templates")
        print("   GET /api/templates/categories - Get template categories")
        print("   POST /api/templates/preview - Preview template with sample data")
    else:
        print("\n❌ System template creation failed. Check the errors above.")

if __name__ == "__main__":
    main()