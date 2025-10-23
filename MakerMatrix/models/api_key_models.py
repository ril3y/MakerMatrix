"""
API Key Models

Provides API key authentication for programmatic access to the MakerMatrix API.
API keys can have different permissions based on roles and can expire.
"""

import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, String
from sqlalchemy import JSON
from pydantic import ConfigDict


def generate_api_key() -> str:
    """Generate a secure random API key"""
    return f"mm_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


class APIKeyModel(SQLModel, table=True):
    """Model for API key authentication"""

    __tablename__ = "api_keys"

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Key information
    name: str = Field(index=True, description="Human-readable name for the API key")
    description: Optional[str] = Field(default=None, description="Purpose/description of this key")
    key_hash: str = Field(index=True, unique=True, description="Hashed API key for secure storage")
    key_prefix: str = Field(index=True, description="First 8 chars of key for identification (mm_xxxxx)")

    # Owner
    user_id: str = Field(foreign_key="usermodel.id", index=True, description="User who owns this key")

    # Permissions - can be role-based or custom
    permissions: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="List of permissions")
    role_names: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="Associated role names")

    # Status and expiration
    is_active: bool = Field(default=True, description="Whether the key is active")
    expires_at: Optional[datetime] = Field(default=None, description="When the key expires (None = never)")

    # Usage tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(default=None, description="Last time key was used")
    usage_count: int = Field(default=0, description="Number of times key has been used")

    # IP restrictions (optional)
    allowed_ips: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSON), description="IP whitelist (None = all)"
    )

    # Relationships
    user: Optional["UserModel"] = Relationship(back_populates="api_keys")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)"""
        return self.is_active and not self.is_expired()

    def can_be_used_from_ip(self, ip_address: str) -> bool:
        """Check if the key can be used from the given IP address"""
        if not self.allowed_ips:
            return True  # No IP restriction
        return ip_address in self.allowed_ips

    def record_usage(self, ip_address: Optional[str] = None):
        """Record that the key was used"""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1

    def to_dict(self, include_key: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "key_prefix": self.key_prefix,
            "user_id": self.user_id,
            "permissions": self.permissions or [],
            "role_names": self.role_names or [],
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "allowed_ips": self.allowed_ips or [],
            "is_expired": self.is_expired(),
            "is_valid": self.is_valid(),
        }
        return data


# Request/Response schemas
class APIKeyCreate(SQLModel):
    """Schema for creating a new API key"""

    name: str = Field(description="Name for the API key")
    description: Optional[str] = None
    role_names: List[str] = Field(default_factory=list, description="Roles to assign to this key")
    permissions: List[str] = Field(default_factory=list, description="Custom permissions (optional)")
    expires_in_days: Optional[int] = Field(default=None, description="Days until expiration (None = never)")
    allowed_ips: Optional[List[str]] = Field(default=None, description="IP whitelist (None = all)")


class APIKeyUpdate(SQLModel):
    """Schema for updating an API key"""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    allowed_ips: Optional[List[str]] = None
    role_names: Optional[List[str]] = None
    permissions: Optional[List[str]] = None


class APIKeyResponse(SQLModel):
    """Schema for API key responses"""

    id: str
    name: str
    description: Optional[str]
    key_prefix: str
    user_id: str
    permissions: List[str]
    role_names: List[str]
    is_active: bool
    expires_at: Optional[str]  # ISO format
    created_at: str  # ISO format
    last_used_at: Optional[str]  # ISO format
    usage_count: int
    allowed_ips: List[str]
    is_expired: bool
    is_valid: bool


class APIKeyCreateResponse(APIKeyResponse):
    """Response when creating a new API key - includes the actual key"""

    api_key: str = Field(description="The actual API key - save this, it won't be shown again!")


# Forward reference for UserModel
if False:  # Type checking only
    from .user_models import UserModel
