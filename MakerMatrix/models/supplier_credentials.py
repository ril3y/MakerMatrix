"""
Supplier Credentials Model

Simple storage for supplier authentication credentials.
Supports any supplier with any credential schema without hardcoding.
"""

from sqlmodel import SQLModel, Field, Column, JSON
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Text


class SimpleSupplierCredentials(SQLModel, table=True):
    """
    Simple credential storage for any supplier.
    
    Stores credentials in a JSON field to support
    varying requirements without schema changes.
    """
    __tablename__ = "simple_supplier_credentials"
    
    id: Optional[str] = Field(default=None, primary_key=True)
    supplier_name: str = Field(index=True, description="Lowercase supplier name (e.g., 'digikey', 'lcsc')")
    
    # Flexible credential storage - supports any supplier's schema
    credentials: Dict[str, Any] = Field(
        default={}, 
        sa_column=Column(JSON),
        description="Credential data (client_id, client_secret, api_key, etc.)"
    )
    
    # Simple metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_tested_at: Optional[datetime] = Field(default=None)
    test_status: Optional[str] = Field(default=None, description="success, failed, never_tested")
    test_error_message: Optional[str] = Field(default=None, sa_column=Column(Text))