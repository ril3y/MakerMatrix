from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.sqlite import JSON
from typing import Optional, Dict, Any
import json


class CSVImportConfigModel(SQLModel, table=True):
    """Model for storing CSV import configuration settings"""
    
    id: Optional[str] = Field(default="default", primary_key=True)
    
    # Download settings
    download_datasheets: bool = Field(default=True)
    download_images: bool = Field(default=True)
    overwrite_existing_files: bool = Field(default=False)
    
    # Performance settings
    download_timeout_seconds: int = Field(default=30, ge=5, le=300)
    
    # Import settings
    show_progress: bool = Field(default=True)
    
    # Enrichment settings
    enable_enrichment: bool = Field(default=True)
    auto_create_enrichment_tasks: bool = Field(default=True)
    
    # Additional settings as JSON
    additional_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "download_datasheets": self.download_datasheets,
            "download_images": self.download_images,
            "overwrite_existing_files": self.overwrite_existing_files,
            "download_timeout_seconds": self.download_timeout_seconds,
            "show_progress": self.show_progress,
            "enable_enrichment": self.enable_enrichment,
            "auto_create_enrichment_tasks": self.auto_create_enrichment_tasks,
            "additional_settings": self.additional_settings or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CSVImportConfigModel":
        """Create model from dictionary"""
        return cls(
            download_datasheets=data.get("download_datasheets", True),
            download_images=data.get("download_images", True),
            overwrite_existing_files=data.get("overwrite_existing_files", False),
            download_timeout_seconds=data.get("download_timeout_seconds", 30),
            show_progress=data.get("show_progress", True),
            enable_enrichment=data.get("enable_enrichment", True),
            auto_create_enrichment_tasks=data.get("auto_create_enrichment_tasks", True),
            additional_settings=data.get("additional_settings", {})
        )


class ImportProgressModel(SQLModel):
    """Model for tracking import progress (not stored in DB, used for API responses)"""
    
    total_parts: int = 0
    processed_parts: int = 0
    successful_parts: int = 0
    failed_parts: int = 0
    current_operation: str = "Initializing..."
    is_downloading: bool = False
    download_progress: Optional[Dict[str, Any]] = None
    errors: list[str] = Field(default_factory=list)
    start_time: str = ""
    estimated_completion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            "total_parts": self.total_parts,
            "processed_parts": self.processed_parts,
            "successful_parts": self.successful_parts,
            "failed_parts": self.failed_parts,
            "current_operation": self.current_operation,
            "is_downloading": self.is_downloading,
            "download_progress": self.download_progress,
            "errors": self.errors,
            "start_time": self.start_time,
            "estimated_completion": self.estimated_completion,
            "percentage_complete": round((self.processed_parts / max(1, self.total_parts)) * 100, 1)
        }