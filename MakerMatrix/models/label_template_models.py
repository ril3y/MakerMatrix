"""
Label Template Models Module

Contains LabelTemplate and related models for managing custom label templates.
This module enables users to create, save, and reuse label templates with various
configurations including text rotation, multi-line layouts, and QR positioning.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, String, JSON
from pydantic import field_serializer, model_validator, ConfigDict
from enum import Enum


class TemplateCategory(str, Enum):
    """Categories for organizing label templates"""

    GENERAL = "GENERAL"
    COMPONENT = "COMPONENT"
    STORAGE = "STORAGE"
    CABLE = "CABLE"
    LOCATION = "LOCATION"
    INVENTORY = "INVENTORY"
    CUSTOM = "CUSTOM"


class LayoutType(str, Enum):
    """Layout types for label templates"""

    QR_ONLY = "qr_only"
    TEXT_ONLY = "text_only"
    QR_TEXT_HORIZONTAL = "qr_text_horizontal"
    QR_TEXT_VERTICAL = "qr_text_vertical"
    QR_TEXT_COMBINED = "qr_text_combined"
    CUSTOM = "custom"


class TextRotation(str, Enum):
    """Text rotation options"""

    NONE = "NONE"
    QUARTER = "90"
    HALF = "180"
    THREE_QUARTER = "270"


class QRPosition(str, Enum):
    """QR code positioning options"""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    CENTER = "CENTER"
    TOP_LEFT = "TOP_LEFT"
    TOP_RIGHT = "TOP_RIGHT"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"


class TextAlignment(str, Enum):
    """Text alignment options"""

    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"


class LabelTemplateModel(SQLModel, table=True):
    """Model for storing custom label templates"""

    __tablename__ = "label_templates"

    # Primary identification
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, description="Unique template name")
    display_name: str = Field(description="Human-readable template name")
    description: Optional[str] = Field(default=None, description="Template description")

    # Template metadata
    category: TemplateCategory = Field(default=TemplateCategory.CUSTOM, description="Template category")
    is_system_template: bool = Field(default=False, description="Whether this is a built-in system template")
    is_active: bool = Field(default=True, description="Whether template is available for use")

    # User ownership
    created_by_user_id: Optional[str] = Field(default=None, description="User who created this template")
    is_public: bool = Field(default=False, description="Whether template is available to all users")

    # Label dimensions
    label_width_mm: float = Field(description="Label width in millimeters")
    label_height_mm: float = Field(description="Label height in millimeters")

    # Layout configuration
    layout_type: LayoutType = Field(default=LayoutType.QR_TEXT_HORIZONTAL, description="Overall layout type")
    layout_config: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Detailed layout configuration"
    )

    # QR code configuration
    qr_enabled: bool = Field(default=True, description="Whether QR code is included")
    qr_position: QRPosition = Field(default=QRPosition.LEFT, description="QR code position")
    qr_scale: float = Field(default=0.95, description="QR code scale factor (0.1-1.0)")
    qr_min_size_mm: float = Field(default=8.0, description="Minimum QR size in mm for phone scanning")
    qr_max_margin_mm: float = Field(default=1.0, description="Maximum margin around QR code in mm")

    # Text configuration
    text_template: str = Field(description="Text template with placeholders (e.g., '{part_name}\\n{part_number}')")
    text_rotation: TextRotation = Field(default=TextRotation.NONE, description="Text rotation angle")
    text_alignment: TextAlignment = Field(default=TextAlignment.LEFT, description="Text alignment")
    enable_multiline: bool = Field(default=True, description="Whether to support multi-line text")
    enable_auto_sizing: bool = Field(default=True, description="Whether to automatically size text to fit")

    # Font and styling
    font_config: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON), description="Font configuration")
    spacing_config: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Spacing and margin configuration"
    )

    # Advanced features
    supports_rotation: bool = Field(default=True, description="Whether template supports text rotation")
    supports_vertical_text: bool = Field(
        default=False, description="Whether template supports vertical character layout"
    )
    custom_processing_rules: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Custom processing rules"
    )

    # Usage tracking
    usage_count: int = Field(default=0, description="Number of times this template has been used")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time template was used")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Template validation
    is_validated: bool = Field(default=False, description="Whether template has been validated")
    validation_errors: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="Validation error messages"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "MakerMatrix12mmBox",
                "display_name": "MakerMatrix 12mm Box Label",
                "description": "Standard box label with QR code and part name",
                "category": "component",
                "label_width_mm": 39.0,
                "label_height_mm": 12.0,
                "layout_type": "qr_text_horizontal",
                "text_template": "{part_name}",
                "qr_position": "left",
                "text_alignment": "center",
            }
        }
    )

    @field_serializer("layout_config", "font_config", "spacing_config", "custom_processing_rules", "validation_errors")
    def serialize_json_fields(self, value):
        """Serialize JSON fields for API responses"""
        return value or {}

    @model_validator(mode="before")
    def set_defaults(cls, values):
        """Set default values for complex fields"""
        if isinstance(values, dict):
            # Set default layout_config
            if "layout_config" not in values or not values["layout_config"]:
                values["layout_config"] = {
                    "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
                    "spacing": {"qr_text_gap": 2, "line_spacing": 1.2},
                    "alignment": {"horizontal": "center", "vertical": "center"},
                }

            # Set default font_config
            if "font_config" not in values or not values["font_config"]:
                values["font_config"] = {
                    "family": "DejaVu Sans",
                    "weight": "normal",
                    "style": "normal",
                    "min_size": 8,
                    "max_size": 72,
                    "auto_size": True,
                }

            # Set default spacing_config
            if "spacing_config" not in values or not values["spacing_config"]:
                values["spacing_config"] = {
                    "margin_mm": 1.0,
                    "padding_mm": 0.5,
                    "line_spacing_factor": 1.2,
                    "character_spacing": 0,
                }

        return values

    def update_usage(self):
        """Update usage tracking when template is used"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def validate_template(self) -> List[str]:
        """Validate template configuration and return any errors"""
        errors = []

        # Validate dimensions
        if self.label_width_mm <= 0 or self.label_height_mm <= 0:
            errors.append("Label dimensions must be positive values")

        # Validate QR configuration
        if self.qr_enabled:
            if self.qr_scale <= 0 or self.qr_scale > 1:
                errors.append("QR scale must be between 0.1 and 1.0")
            if self.qr_min_size_mm <= 0:
                errors.append("QR minimum size must be positive")
            if self.qr_min_size_mm > self.label_height_mm:
                errors.append("QR minimum size cannot exceed label height")

        # Validate text template
        if not self.text_template or not self.text_template.strip():
            if self.layout_type in [LayoutType.TEXT_ONLY, LayoutType.QR_TEXT_HORIZONTAL, LayoutType.QR_TEXT_VERTICAL]:
                errors.append("Text template is required for text-based layouts")

        # Update validation status
        self.validation_errors = errors if errors else None
        self.is_validated = len(errors) == 0

        return errors


class LabelTemplatePresetModel(SQLModel, table=True):
    """Model for storing template presets and system templates"""

    __tablename__ = "label_template_presets"

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(unique=True, index=True, description="Preset name")
    display_name: str = Field(description="Human-readable preset name")
    description: str = Field(description="Preset description")

    # Template reference
    template_config: Dict[str, Any] = Field(sa_column=Column(JSON), description="Complete template configuration")

    # Preset metadata
    category: TemplateCategory = Field(description="Preset category")
    is_system_preset: bool = Field(default=True, description="Whether this is a built-in preset")
    sort_order: int = Field(default=0, description="Display sort order")

    # Usage
    is_active: bool = Field(default=True)
    usage_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "component_vertical",
                "display_name": "Component Vertical",
                "description": "Rotated text for narrow components",
                "category": "component",
                "template_config": {
                    "label_width_mm": 12.0,
                    "label_height_mm": 50.0,
                    "layout_type": "qr_text_vertical",
                    "text_rotation": "90",
                    "text_template": "{part_name}",
                },
            }
        }
    )


# Request/Response models for API
class LabelTemplateCreate(SQLModel):
    """Schema for creating new label templates"""

    name: str
    display_name: str
    description: Optional[str] = None
    category: TemplateCategory = TemplateCategory.CUSTOM

    label_width_mm: float
    label_height_mm: float
    layout_type: LayoutType = LayoutType.QR_TEXT_HORIZONTAL

    text_template: str
    text_rotation: TextRotation = TextRotation.NONE
    text_alignment: TextAlignment = TextAlignment.LEFT

    qr_enabled: bool = True
    qr_position: QRPosition = QRPosition.LEFT
    qr_scale: float = 0.95

    is_public: bool = False
    layout_config: Optional[Dict[str, Any]] = None
    font_config: Optional[Dict[str, Any]] = None
    spacing_config: Optional[Dict[str, Any]] = None


class LabelTemplateUpdate(SQLModel):
    """Schema for updating label templates"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TemplateCategory] = None

    label_width_mm: Optional[float] = None
    label_height_mm: Optional[float] = None
    layout_type: Optional[LayoutType] = None

    text_template: Optional[str] = None
    text_rotation: Optional[TextRotation] = None
    text_alignment: Optional[TextAlignment] = None

    qr_enabled: Optional[bool] = None
    qr_position: Optional[QRPosition] = None
    qr_scale: Optional[float] = None

    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    layout_config: Optional[Dict[str, Any]] = None
    font_config: Optional[Dict[str, Any]] = None
    spacing_config: Optional[Dict[str, Any]] = None


class LabelTemplateResponse(SQLModel):
    """Schema for label template API responses"""

    id: str
    name: str
    display_name: str
    description: Optional[str]
    category: TemplateCategory
    is_system_template: bool
    is_active: bool

    label_width_mm: float
    label_height_mm: float
    layout_type: LayoutType

    text_template: str
    text_rotation: TextRotation
    text_alignment: TextAlignment

    qr_enabled: bool
    qr_position: QRPosition
    qr_scale: float

    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    is_validated: bool
    validation_errors: Optional[List[str]]

    layout_config: Dict[str, Any] = Field(default_factory=dict)
    font_config: Dict[str, Any] = Field(default_factory=dict)
    spacing_config: Dict[str, Any] = Field(default_factory=dict)


class TemplatePreviewRequest(SQLModel):
    """Schema for template preview requests"""

    template_id: Optional[str] = None
    template_config: Optional[LabelTemplateCreate] = None
    sample_data: Dict[str, Any] = Field(default_factory=dict, description="Sample data for preview")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_id": "template_uuid",
                "sample_data": {"part_name": "Sample Part", "part_number": "SP001", "id": "sample_id"},
            }
        }
    )
