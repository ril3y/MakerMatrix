"""
Supplier Configuration Models

Database models for storing supplier API configurations and encrypted credentials.
Supports user-managed supplier settings with secure credential storage.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlmodel import SQLModel, Field, Relationship
import json

import uuid


class SupplierConfigModel(SQLModel, table=True):
    """
    Supplier API configuration model
    
    Stores non-sensitive configuration data for supplier APIs including
    endpoints, rate limits, and feature flags.
    """
    __tablename__ = "supplier_configs"
    
    # Primary key
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Basic configuration
    supplier_name: str = Field(unique=True, index=True, max_length=100)
    display_name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    
    # API configuration
    api_type: str = Field(max_length=50, default="rest")  # "rest", "graphql", "scraping"
    base_url: str = Field(max_length=500)
    api_version: Optional[str] = Field(default=None, max_length=50)
    
    # Rate limiting and timeouts
    rate_limit_per_minute: Optional[int] = Field(default=None, gt=0)
    timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff: float = Field(default=1.0, gt=0)
    
    # Feature flags and capabilities
    enabled: bool = Field(default=True)
    supports_datasheet: bool = Field(default=False)
    supports_image: bool = Field(default=False)
    supports_pricing: bool = Field(default=False)
    supports_stock: bool = Field(default=False)
    supports_specifications: bool = Field(default=False)
    supports_alternatives: bool = Field(default=False)
    supports_lifecycle_status: bool = Field(default=False)
    supports_part_validation: bool = Field(default=False)
    
    # Custom headers and parameters (stored as JSON)
    custom_headers: Optional[str] = Field(default=None)  # JSON string
    custom_parameters: Optional[str] = Field(default=None)  # JSON string
    
    # Metadata
    created_by_user_id: Optional[str] = Field(foreign_key="usermodel.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_tested_at: Optional[datetime] = Field(default=None)
    test_status: Optional[str] = Field(default=None, max_length=50)  # "success", "failed", "pending"
    
    # Relationships
    credentials: Optional["SupplierCredentialsModel"] = Relationship(
        back_populates="config",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    
    def get_custom_headers(self) -> Dict[str, str]:
        """Parse custom headers from JSON string"""
        if not self.custom_headers:
            return {}
        try:
            return json.loads(self.custom_headers)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_custom_headers(self, headers: Dict[str, str]) -> None:
        """Set custom headers as JSON string"""
        self.custom_headers = json.dumps(headers) if headers else None
    
    def get_custom_parameters(self) -> Dict[str, Any]:
        """Parse custom parameters from JSON string"""
        if not self.custom_parameters:
            return {}
        try:
            return json.loads(self.custom_parameters)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_custom_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set custom parameters as JSON string"""
        self.custom_parameters = json.dumps(parameters) if parameters else None
    
    def get_capabilities(self) -> List[str]:
        """Get list of supported capabilities based on configuration flags"""
        capabilities = []
        if self.supports_datasheet:
            capabilities.append("fetch_datasheet")
        if self.supports_image:
            capabilities.append("fetch_image")
        if self.supports_pricing:
            capabilities.append("fetch_pricing")
        if self.supports_stock:
            capabilities.append("fetch_stock")
        if self.supports_specifications:
            capabilities.append("fetch_specifications")
        if self.supports_alternatives:
            capabilities.append("fetch_alternatives")
        if self.supports_lifecycle_status:
            capabilities.append("fetch_lifecycle_status")
        if self.supports_part_validation:
            capabilities.append("validate_part_number")
        
        # Always include fetch_details if any other capability is supported
        # Details enrichment is typically available whenever basic part info is accessible
        if capabilities:
            capabilities.append("fetch_details")
            
        return capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        # Check for credentials relationship safely
        has_credentials = False
        try:
            # Try to access the relationship
            has_credentials = self.credentials is not None
        except:
            # If relationship access fails (detached instance), assume no credentials
            has_credentials = False
        
        return {
            "id": self.id,
            "supplier_name": self.supplier_name,
            "display_name": self.display_name,
            "description": self.description,
            "api_type": self.api_type,
            "base_url": self.base_url,
            "api_version": self.api_version,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_backoff": self.retry_backoff,
            "enabled": self.enabled,
            "capabilities": self.get_capabilities(),
            "custom_headers": self.get_custom_headers(),
            "custom_parameters": self.get_custom_parameters(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "test_status": self.test_status,
            "has_credentials": has_credentials
        }


class SupplierCredentialsModel(SQLModel, table=True):
    """
    Encrypted supplier credentials model
    
    Stores sensitive authentication data with AES-256 encryption.
    Credentials are encrypted at rest and only decrypted when needed.
    """
    __tablename__ = "supplier_credentials"
    
    # Primary key
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign key to supplier config
    supplier_config_id: str = Field(foreign_key="supplier_configs.id", unique=True)
    
    # Encrypted credential fields (all stored as encrypted strings)
    api_key_encrypted: Optional[str] = Field(default=None)
    secret_key_encrypted: Optional[str] = Field(default=None)
    username_encrypted: Optional[str] = Field(default=None)
    password_encrypted: Optional[str] = Field(default=None)
    oauth_token_encrypted: Optional[str] = Field(default=None)
    refresh_token_encrypted: Optional[str] = Field(default=None)
    
    # Additional encrypted fields stored as JSON
    additional_data_encrypted: Optional[str] = Field(default=None)
    
    # Encryption metadata
    encryption_key_id: str = Field(max_length=100)  # ID of the encryption key used
    encryption_algorithm: str = Field(default="AES-256-GCM", max_length=50)
    salt: str = Field(max_length=200)  # Salt used for key derivation
    
    # Credential metadata
    created_by_user_id: Optional[str] = Field(foreign_key="usermodel.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)
    last_rotated_at: Optional[datetime] = Field(default=None)
    
    # Relationship
    config: "SupplierConfigModel" = Relationship(back_populates="credentials")
    
    def needs_rotation(self, rotation_days: int = 90) -> bool:
        """Check if credentials need rotation based on age"""
        if not self.last_rotated_at:
            # If never rotated, check creation date
            age = datetime.utcnow() - self.created_at
        else:
            age = datetime.utcnow() - self.last_rotated_at
        
        return age.days >= rotation_days
    
    def is_expired(self) -> bool:
        """Check if credentials are expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self, include_encrypted: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            "id": self.id,
            "supplier_config_id": self.supplier_config_id,
            "encryption_algorithm": self.encryption_algorithm,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_rotated_at": self.last_rotated_at.isoformat() if self.last_rotated_at else None,
            "needs_rotation": self.needs_rotation(),
            "is_expired": self.is_expired(),
            "has_api_key": self.api_key_encrypted is not None,
            "has_secret_key": self.secret_key_encrypted is not None,
            "has_username": self.username_encrypted is not None,
            "has_password": self.password_encrypted is not None,
            "has_oauth_token": self.oauth_token_encrypted is not None,
            "has_refresh_token": self.refresh_token_encrypted is not None
        }
        
        # Only include encrypted data if explicitly requested (for debugging/admin)
        if include_encrypted:
            data.update({
                "api_key_encrypted": self.api_key_encrypted,
                "secret_key_encrypted": self.secret_key_encrypted,
                "username_encrypted": self.username_encrypted,
                "password_encrypted": self.password_encrypted,
                "oauth_token_encrypted": self.oauth_token_encrypted,
                "refresh_token_encrypted": self.refresh_token_encrypted,
                "additional_data_encrypted": self.additional_data_encrypted,
                "encryption_key_id": self.encryption_key_id,
                "salt": self.salt
            })
        
        return data


class EnrichmentProfileModel(SQLModel, table=True):
    """
    User-defined enrichment workflow profiles
    
    Allows users to create custom enrichment workflows with supplier
    priority ordering and capability selection.
    """
    __tablename__ = "enrichment_profiles"
    
    # Primary key
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Profile identification
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None, max_length=1000)
    
    # Profile configuration
    supplier_priority: str = Field()  # JSON array of supplier names in priority order
    enabled_capabilities: str = Field()  # JSON array of capability names
    fallback_enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30, gt=0)
    
    # Custom field mappings and transformations
    field_mappings: Optional[str] = Field(default=None)  # JSON object
    data_transformations: Optional[str] = Field(default=None)  # JSON object
    
    # Profile metadata
    is_default: bool = Field(default=False)
    is_public: bool = Field(default=False)  # Can be shared with other users
    created_by_user_id: Optional[str] = Field(foreign_key="usermodel.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(default=None)
    usage_count: int = Field(default=0, ge=0)
    
    def get_supplier_priority(self) -> List[str]:
        """Parse supplier priority from JSON string"""
        try:
            return json.loads(self.supplier_priority) if self.supplier_priority else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_supplier_priority(self, suppliers: List[str]) -> None:
        """Set supplier priority as JSON string"""
        self.supplier_priority = json.dumps(suppliers)
    
    def get_enabled_capabilities(self) -> List[str]:
        """Parse enabled capabilities from JSON string"""
        try:
            return json.loads(self.enabled_capabilities) if self.enabled_capabilities else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_enabled_capabilities(self, capabilities: List[str]) -> None:
        """Set enabled capabilities as JSON string"""
        self.enabled_capabilities = json.dumps(capabilities)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Parse field mappings from JSON string"""
        try:
            return json.loads(self.field_mappings) if self.field_mappings else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_field_mappings(self, mappings: Dict[str, str]) -> None:
        """Set field mappings as JSON string"""
        self.field_mappings = json.dumps(mappings) if mappings else None
    
    def get_data_transformations(self) -> Dict[str, Any]:
        """Parse data transformations from JSON string"""
        try:
            return json.loads(self.data_transformations) if self.data_transformations else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_data_transformations(self, transformations: Dict[str, Any]) -> None:
        """Set data transformations as JSON string"""
        self.data_transformations = json.dumps(transformations) if transformations else None
    
    def increment_usage(self) -> None:
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "supplier_priority": self.get_supplier_priority(),
            "enabled_capabilities": self.get_enabled_capabilities(),
            "fallback_enabled": self.fallback_enabled,
            "timeout_seconds": self.timeout_seconds,
            "field_mappings": self.get_field_mappings(),
            "data_transformations": self.get_data_transformations(),
            "is_default": self.is_default,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count
        }