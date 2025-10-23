"""
Label Template Repository Module

Provides data access layer for label template management including CRUD operations,
search and filtering capabilities, and template validation methods.
"""

from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, or_, and_, func
from datetime import datetime

from .base_repository import BaseRepository
from MakerMatrix.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError
from MakerMatrix.models.label_template_models import (
    LabelTemplateModel,
    LabelTemplatePresetModel,
    TemplateCategory,
    LayoutType,
    TextRotation,
    QRPosition,
)


class LabelTemplateRepository(BaseRepository[LabelTemplateModel]):
    """Repository for managing label templates"""

    def __init__(self):
        super().__init__(LabelTemplateModel)

    def get_by_name(self, session: Session, name: str) -> Optional[LabelTemplateModel]:
        """Get template by name"""
        return session.exec(select(LabelTemplateModel).where(LabelTemplateModel.name == name)).first()

    def get_by_user(self, session: Session, user_id: str, include_public: bool = True) -> List[LabelTemplateModel]:
        """Get templates for a specific user"""
        if include_public:
            return session.exec(
                select(LabelTemplateModel)
                .where(
                    or_(
                        LabelTemplateModel.created_by_user_id == user_id,
                        LabelTemplateModel.is_public == True,
                        LabelTemplateModel.is_system_template == True,
                    )
                )
                .where(LabelTemplateModel.is_active == True)
                .order_by(LabelTemplateModel.is_system_template.desc(), LabelTemplateModel.name)
            ).all()
        else:
            return session.exec(
                select(LabelTemplateModel)
                .where(LabelTemplateModel.created_by_user_id == user_id)
                .where(LabelTemplateModel.is_active == True)
                .order_by(LabelTemplateModel.name)
            ).all()

    def get_by_category(self, session: Session, category: TemplateCategory) -> List[LabelTemplateModel]:
        """Get templates by category"""
        return session.exec(
            select(LabelTemplateModel)
            .where(LabelTemplateModel.category == category)
            .where(LabelTemplateModel.is_active == True)
            .order_by(LabelTemplateModel.name)
        ).all()

    def get_public_templates(self, session: Session) -> List[LabelTemplateModel]:
        """Get all public and system templates"""
        return session.exec(
            select(LabelTemplateModel)
            .where(or_(LabelTemplateModel.is_public == True, LabelTemplateModel.is_system_template == True))
            .where(LabelTemplateModel.is_active == True)
            .order_by(LabelTemplateModel.is_system_template.desc(), LabelTemplateModel.name)
        ).all()

    def get_system_templates(self, session: Session) -> List[LabelTemplateModel]:
        """Get only system templates"""
        return session.exec(
            select(LabelTemplateModel)
            .where(LabelTemplateModel.is_system_template == True)
            .where(LabelTemplateModel.is_active == True)
            .order_by(LabelTemplateModel.name)
        ).all()

    def search_templates(
        self,
        session: Session,
        search_term: Optional[str] = None,
        category: Optional[TemplateCategory] = None,
        layout_type: Optional[LayoutType] = None,
        user_id: Optional[str] = None,
        include_public: bool = True,
        label_size_range: Optional[tuple[float, float]] = None,
    ) -> List[LabelTemplateModel]:
        """Search templates with multiple filters"""

        query = select(LabelTemplateModel).where(LabelTemplateModel.is_active == True)

        # Text search
        if search_term:
            search_term = f"%{search_term}%"
            query = query.where(
                or_(
                    LabelTemplateModel.name.ilike(search_term),
                    LabelTemplateModel.display_name.ilike(search_term),
                    LabelTemplateModel.description.ilike(search_term),
                )
            )

        # Category filter
        if category:
            query = query.where(LabelTemplateModel.category == category)

        # Layout type filter
        if layout_type:
            query = query.where(LabelTemplateModel.layout_type == layout_type)

        # User access filter
        if user_id and include_public:
            query = query.where(
                or_(
                    LabelTemplateModel.created_by_user_id == user_id,
                    LabelTemplateModel.is_public == True,
                    LabelTemplateModel.is_system_template == True,
                )
            )
        elif user_id:
            query = query.where(LabelTemplateModel.created_by_user_id == user_id)

        # Label size range filter
        if label_size_range:
            min_size, max_size = label_size_range
            query = query.where(
                and_(LabelTemplateModel.label_height_mm >= min_size, LabelTemplateModel.label_height_mm <= max_size)
            )

        return session.exec(query.order_by(LabelTemplateModel.name)).all()

    def get_compatible_templates(
        self, session: Session, label_height_mm: float, label_width_mm: Optional[float] = None
    ) -> List[LabelTemplateModel]:
        """Get templates compatible with specific label dimensions"""

        query = select(LabelTemplateModel).where(LabelTemplateModel.is_active == True)

        # Match label height (exact or within tolerance)
        height_tolerance = 1.0  # 1mm tolerance
        query = query.where(
            and_(
                LabelTemplateModel.label_height_mm >= label_height_mm - height_tolerance,
                LabelTemplateModel.label_height_mm <= label_height_mm + height_tolerance,
            )
        )

        # If width is provided, match it too
        if label_width_mm:
            width_tolerance = 2.0  # 2mm tolerance for width
            query = query.where(
                and_(
                    LabelTemplateModel.label_width_mm >= label_width_mm - width_tolerance,
                    LabelTemplateModel.label_width_mm <= label_width_mm + width_tolerance,
                )
            )

        return session.exec(
            query.order_by(LabelTemplateModel.is_system_template.desc(), LabelTemplateModel.usage_count.desc())
        ).all()

    def get_popular_templates(self, session: Session, limit: int = 10) -> List[LabelTemplateModel]:
        """Get most popular templates by usage count"""
        return session.exec(
            select(LabelTemplateModel)
            .where(LabelTemplateModel.is_active == True)
            .order_by(LabelTemplateModel.usage_count.desc())
            .limit(limit)
        ).all()

    def create_template(self, session: Session, template: LabelTemplateModel) -> LabelTemplateModel:
        """Create a new template with validation"""

        # Check if name already exists
        existing = self.get_by_name(session, template.name)
        if existing:
            raise ResourceAlreadyExistsError(f"Template with name '{template.name}' already exists")

        # Validate template configuration
        validation_errors = template.validate_template()
        if validation_errors:
            raise ValueError(f"Template validation failed: {', '.join(validation_errors)}")

        return self.create(session, template)

    def update_template(self, session: Session, template_id: str, updates: Dict[str, Any]) -> LabelTemplateModel:
        """Update template with validation"""

        template = self.get_by_id(session, template_id)
        if not template:
            raise ResourceNotFoundError(f"Template with ID '{template_id}' not found")

        # Apply updates
        for field, value in updates.items():
            if hasattr(template, field):
                setattr(template, field, value)

        # Update timestamp
        template.updated_at = datetime.utcnow()

        # Validate updated template
        validation_errors = template.validate_template()
        if validation_errors:
            raise ValueError(f"Template validation failed: {', '.join(validation_errors)}")

        return self.update(session, template)

    def increment_usage(self, session: Session, template_id: str) -> None:
        """Increment usage count and update last used timestamp"""
        template = self.get_by_id(session, template_id)
        if template:
            template.update_usage()
            session.add(template)
            session.commit()

    def duplicate_template(self, session: Session, template_id: str, new_name: str, user_id: str) -> LabelTemplateModel:
        """Duplicate an existing template with new name and owner"""

        original = self.get_by_id(session, template_id)
        if not original:
            raise ResourceNotFoundError(f"Template with ID '{template_id}' not found")

        # Check if new name already exists
        existing = self.get_by_name(session, new_name)
        if existing:
            raise ResourceAlreadyExistsError(f"Template with name '{new_name}' already exists")

        # Create duplicate
        duplicate = LabelTemplateModel(
            name=new_name,
            display_name=f"{original.display_name} (Copy)",
            description=f"Copy of {original.description}" if original.description else None,
            category=original.category,
            is_system_template=False,  # User copies are never system templates
            is_public=False,  # User copies default to private
            created_by_user_id=user_id,
            # Copy all configuration
            label_width_mm=original.label_width_mm,
            label_height_mm=original.label_height_mm,
            layout_type=original.layout_type,
            layout_config=original.layout_config.copy(),
            qr_enabled=original.qr_enabled,
            qr_position=original.qr_position,
            qr_scale=original.qr_scale,
            qr_min_size_mm=original.qr_min_size_mm,
            qr_max_margin_mm=original.qr_max_margin_mm,
            text_template=original.text_template,
            text_rotation=original.text_rotation,
            text_alignment=original.text_alignment,
            enable_multiline=original.enable_multiline,
            enable_auto_sizing=original.enable_auto_sizing,
            font_config=original.font_config.copy(),
            spacing_config=original.spacing_config.copy(),
            supports_rotation=original.supports_rotation,
            supports_vertical_text=original.supports_vertical_text,
            custom_processing_rules=(
                original.custom_processing_rules.copy() if original.custom_processing_rules else None
            ),
        )

        return self.create(session, duplicate)

    def get_template_statistics(self, session: Session) -> Dict[str, Any]:
        """Get template usage statistics"""

        total_templates = session.exec(
            select(func.count()).select_from(LabelTemplateModel).where(LabelTemplateModel.is_active == True)
        ).first()

        system_templates = session.exec(
            select(func.count())
            .select_from(LabelTemplateModel)
            .where(and_(LabelTemplateModel.is_system_template == True, LabelTemplateModel.is_active == True))
        ).first()

        public_templates = session.exec(
            select(func.count())
            .select_from(LabelTemplateModel)
            .where(and_(LabelTemplateModel.is_public == True, LabelTemplateModel.is_active == True))
        ).first()

        # Category distribution
        category_stats = session.exec(
            select(LabelTemplateModel.category, func.count())
            .select_from(LabelTemplateModel)
            .where(LabelTemplateModel.is_active == True)
            .group_by(LabelTemplateModel.category)
        ).all()

        # Layout type distribution
        layout_stats = session.exec(
            select(LabelTemplateModel.layout_type, func.count())
            .select_from(LabelTemplateModel)
            .where(LabelTemplateModel.is_active == True)
            .group_by(LabelTemplateModel.layout_type)
        ).all()

        return {
            "total_templates": total_templates or 0,
            "system_templates": system_templates or 0,
            "public_templates": public_templates or 0,
            "user_templates": (total_templates or 0) - (system_templates or 0),
            "category_distribution": {category: count for category, count in category_stats},
            "layout_distribution": {layout: count for layout, count in layout_stats},
        }


class LabelTemplatePresetRepository(BaseRepository[LabelTemplatePresetModel]):
    """Repository for managing template presets"""

    def __init__(self):
        super().__init__(LabelTemplatePresetModel)

    def get_by_name(self, session: Session, name: str) -> Optional[LabelTemplatePresetModel]:
        """Get preset by name"""
        return session.exec(select(LabelTemplatePresetModel).where(LabelTemplatePresetModel.name == name)).first()

    def get_by_category(self, session: Session, category: TemplateCategory) -> List[LabelTemplatePresetModel]:
        """Get presets by category"""
        return session.exec(
            select(LabelTemplatePresetModel)
            .where(LabelTemplatePresetModel.category == category)
            .where(LabelTemplatePresetModel.is_active == True)
            .order_by(LabelTemplatePresetModel.sort_order, LabelTemplatePresetModel.name)
        ).all()

    def get_active_presets(self, session: Session) -> List[LabelTemplatePresetModel]:
        """Get all active presets ordered by sort order"""
        return session.exec(
            select(LabelTemplatePresetModel)
            .where(LabelTemplatePresetModel.is_active == True)
            .order_by(LabelTemplatePresetModel.sort_order, LabelTemplatePresetModel.name)
        ).all()

    def increment_usage(self, session: Session, preset_id: str) -> None:
        """Increment preset usage count"""
        preset = self.get_by_id(session, preset_id)
        if preset:
            preset.usage_count += 1
            session.add(preset)
            session.commit()

    def create_template_from_preset(
        self, session: Session, preset_id: str, template_name: str, user_id: str
    ) -> LabelTemplateModel:
        """Create a new template from a preset"""

        preset = self.get_by_id(session, preset_id)
        if not preset:
            raise ResourceNotFoundError(f"Preset with ID '{preset_id}' not found")

        # Increment preset usage
        self.increment_usage(session, preset_id)

        # Create template from preset configuration
        config = preset.template_config
        template = LabelTemplateModel(
            name=template_name,
            display_name=config.get("display_name", template_name),
            description=config.get("description", f"Template created from {preset.display_name} preset"),
            category=preset.category,
            created_by_user_id=user_id,
            # Apply preset configuration
            **{k: v for k, v in config.items() if k not in ["display_name", "description"]},
        )

        # Use template repository to create with validation
        template_repo = LabelTemplateRepository()
        return template_repo.create_template(session, template)
