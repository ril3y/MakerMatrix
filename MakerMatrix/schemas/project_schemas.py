from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "planning"
    image_url: Optional[str] = None
    links: Optional[Dict[str, Any]] = None
    project_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    image_url: Optional[str] = None
    links: Optional[Dict[str, Any]] = None
    project_metadata: Optional[str] = None
    estimated_cost: Optional[float] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    """Schema for project responses"""
    id: Optional[str] = None
    name: str
    slug: str
    description: Optional[str] = None
    status: str = "planning"
    image_url: Optional[str] = None
    links: Optional[Dict[str, Any]] = None
    project_metadata: Optional[Dict[str, Any]] = None
    parts_count: int = 0
    estimated_cost: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectsListResponse(BaseModel):
    """Schema for list of projects"""
    projects: List[ProjectResponse]

    model_config = ConfigDict(from_attributes=True)


class ProjectPartAssociation(BaseModel):
    """Schema for adding/removing parts from projects"""
    part_id: str
    project_id: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeleteProjectsResponse(BaseModel):
    """Schema for delete all projects response"""
    deleted_count: int

    model_config = ConfigDict(from_attributes=True)
