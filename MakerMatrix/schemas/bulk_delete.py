"""
Bulk Delete Schema

Schema for bulk deleting multiple parts at once
"""

from typing import List
from pydantic import BaseModel, Field


class BulkDeleteRequest(BaseModel):
    """Request model for bulk deleting parts"""

    part_ids: List[str] = Field(..., description="List of part IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operation"""

    deleted_count: int = Field(..., description="Number of parts successfully deleted")
    files_deleted: int = Field(default=0, description="Number of files deleted (images + datasheets)")
    failed_count: int = Field(default=0, description="Number of parts that failed to delete")
    errors: List[dict] = Field(default_factory=list, description="List of errors encountered")
