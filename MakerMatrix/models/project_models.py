"""
Project Models Module

Contains ProjectModel and related project-specific models for organizing parts into projects.
This module supports many-to-many relationships between parts and projects with tag-like functionality.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from pydantic import ConfigDict


class PartProjectLink(SQLModel, table=True):
    """Link table for many-to-many relationship between parts and projects"""
    __tablename__ = "part_project_link"

    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    project_id: str = Field(foreign_key="projectmodel.id", primary_key=True)
    added_at: datetime = Field(default_factory=datetime.utcnow, description="When the part was added to the project")
    notes: Optional[str] = Field(default=None, description="Notes about this part's use in the project")


class ProjectModel(SQLModel, table=True):
    """
    Model for organizing parts into projects.

    This model allows users to create projects and tag parts to them, similar to hashtags.
    Useful for tracking which parts are used in specific builds or designs.

    Examples:
    - "golfcart-harness"
    - "home-automation-system"
    - "robot-arm-prototype"
    """
    __tablename__ = "projectmodel"

    # === CORE IDENTIFICATION ===
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True, description="Project name (like a tag)")
    slug: str = Field(index=True, unique=True, description="URL-friendly version of name")

    # === PROJECT DETAILS ===
    description: Optional[str] = Field(default=None, description="Project description")
    status: str = Field(default="planning", description="Project status: planning, active, completed, archived")

    # === MEDIA ===
    image_url: Optional[str] = Field(default=None, description="Project image/thumbnail")

    # === METADATA ===
    links: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Project-related links (GitHub, docs, website, etc.)"
    )
    project_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional project metadata (tags, custom fields, etc.)"
    )

    # === STATISTICS ===
    parts_count: int = Field(default=0, description="Number of parts in this project")
    estimated_cost: Optional[float] = Field(default=None, description="Estimated total cost of parts")

    # === TIMESTAMPS ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None, description="When project was marked complete")

    # === RELATIONSHIPS ===
    # Many-to-many relationship with parts through link table
    parts: List["PartModel"] = Relationship(
        back_populates="projects",
        link_model=PartProjectLink
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        base_dict = self.model_dump(exclude={"parts"})

        # Convert datetime fields to ISO strings
        if self.created_at:
            base_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            base_dict["updated_at"] = self.updated_at.isoformat()
        if self.completed_at:
            base_dict["completed_at"] = self.completed_at.isoformat()

        return base_dict

    def update_stats(self, session):
        """Update project statistics (parts count, estimated cost)"""
        from MakerMatrix.models.part_models import PartModel
        from sqlmodel import select, func

        # Count parts
        parts_count_stmt = (
            select(func.count(PartProjectLink.part_id))
            .where(PartProjectLink.project_id == self.id)
        )
        self.parts_count = session.exec(parts_count_stmt).one()

        # Calculate estimated cost from current pricing
        # This would need to be implemented based on your pricing model
        # For now, we'll leave it as is

        self.updated_at = datetime.utcnow()
