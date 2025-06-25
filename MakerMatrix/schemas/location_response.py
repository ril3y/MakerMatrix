from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LocationResponse(BaseModel):
    """Response schema for location data"""
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: str = "standard"
    image_url: Optional[str] = None
    emoji: Optional[str] = None
    parent: Optional['LocationResponse'] = None
    children: List['LocationResponse'] = []
    parts_count: int = 0
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_model(cls, location_model) -> 'LocationResponse':
        """Convert LocationModel to LocationResponse"""
        data = {
            'id': location_model.id,
            'name': location_model.name,
            'description': location_model.description,
            'parent_id': location_model.parent_id,
            'location_type': location_model.location_type,
            'image_url': location_model.image_url,
            'emoji': getattr(location_model, 'emoji', None),
            'parts_count': len(location_model.parts) if location_model.parts else 0
        }
        
        # Handle parent recursively
        if location_model.parent:
            data['parent'] = cls.from_model(location_model.parent)
            
        # Handle children recursively
        if location_model.children:
            data['children'] = [cls.from_model(child) for child in location_model.children]
            
        return cls(**data)


# Update forward references
LocationResponse.model_rebuild()