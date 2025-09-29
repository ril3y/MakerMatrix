"""
Supplier Configuration API Routes

RESTful endpoints for managing supplier configurations, credentials,
and enrichment profiles with proper authentication and validation.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
import json

from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    SupplierConfigAlreadyExistsError,
    InvalidReferenceError
)
from MakerMatrix.models.user_models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# Pydantic schemas for request/response validation

class SupplierConfigCreate(BaseModel):
    """Schema for creating supplier configuration"""
    supplier_name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    api_type: str = Field(default="rest", max_length=50)
    base_url: str = Field(..., max_length=500)
    api_version: Optional[str] = Field(None, max_length=50)
    api_documentation_url: Optional[str] = Field(None, max_length=500)
    rate_limit_per_minute: Optional[int] = Field(None, gt=0)
    timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_backoff: float = Field(default=1.0, gt=0)
    enabled: bool = Field(default=True)
    supports_datasheet: bool = Field(default=False)
    supports_image: bool = Field(default=False)
    supports_pricing: bool = Field(default=False)
    supports_stock: bool = Field(default=False)
    supports_specifications: bool = Field(default=False)
    custom_headers: Optional[Dict[str, str]] = Field(default=None)
    custom_parameters: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('supplier_name')
    def validate_supplier_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Supplier name cannot be empty')
        return v.strip()
    
    @validator('api_type')
    def validate_api_type(cls, v):
        allowed_types = ['rest', 'graphql', 'scraping']
        if v not in allowed_types:
            raise ValueError(f'API type must be one of: {allowed_types}')
        return v


class SupplierConfigUpdate(BaseModel):
    """Schema for updating supplier configuration"""
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    api_type: Optional[str] = Field(None, max_length=50)
    base_url: Optional[str] = Field(None, max_length=500)
    api_version: Optional[str] = Field(None, max_length=50)
    api_documentation_url: Optional[str] = Field(None, max_length=500)
    rate_limit_per_minute: Optional[int] = Field(None, gt=0)
    timeout_seconds: Optional[int] = Field(None, gt=0)
    max_retries: Optional[int] = Field(None, ge=0)
    retry_backoff: Optional[float] = Field(None, gt=0)
    enabled: Optional[bool] = Field(None)
    supports_datasheet: Optional[bool] = Field(None)
    supports_image: Optional[bool] = Field(None)
    supports_pricing: Optional[bool] = Field(None)
    supports_stock: Optional[bool] = Field(None)
    supports_specifications: Optional[bool] = Field(None)
    capabilities: Optional[List[str]] = Field(None)  # Modern flexible capabilities list
    custom_headers: Optional[Dict[str, str]] = Field(None)
    custom_parameters: Optional[Dict[str, Any]] = Field(None)


class SupplierCredentials(BaseModel):
    """Schema for supplier credentials"""
    api_key: Optional[str] = Field(None)
    secret_key: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    oauth_token: Optional[str] = Field(None)
    refresh_token: Optional[str] = Field(None)
    additional_data: Optional[Dict[str, str]] = Field(None)


class ConnectionTestResult(BaseModel):
    """Schema for connection test results"""
    supplier_name: str
    success: bool
    test_duration_seconds: float
    tested_at: str
    error_message: Optional[str] = None


# API Routes

@router.get("/suppliers", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_all_suppliers(
    enabled_only: bool = False,
    current_user: UserModel = Depends(get_current_user)
):
    """Get all supplier configurations"""
    try:
        service = SupplierConfigService()
        config_dicts = service.get_all_supplier_configs(enabled_only=enabled_only)
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved {len(config_dicts)} supplier configurations",
            data=config_dicts
        )
        
    except Exception as e:
        logger.error(f"Error retrieving supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supplier configurations"
        )


@router.post("/suppliers", response_model=ResponseSchema[Dict[str, Any]])
async def create_supplier(
    config_data: SupplierConfigCreate,
    current_user: UserModel = Depends(require_permission("supplier_config:create"))
):
    """Create a new supplier configuration"""
    try:
        # Additional validation beyond Pydantic
        if not config_data.supplier_name or not config_data.supplier_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier name cannot be empty or whitespace only"
            )
        
        if not config_data.display_name or not config_data.display_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Display name cannot be empty or whitespace only"
            )
        
        # Validate supplier name format
        supplier_name = config_data.supplier_name.strip().lower()
        if not supplier_name.replace('_', '').replace('-', '').isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier name must contain only letters, numbers, hyphens, and underscores"
            )
        
        service = SupplierConfigService()
        config = service.create_supplier_config(
            config_data.dict(exclude_unset=True),
            user_id=current_user.id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Created supplier configuration: {config.supplier_name}",
            data=config.to_dict()
        )
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except SupplierConfigAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating supplier configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create supplier configuration"
        )


@router.get("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier(
    supplier_name: str,
    include_credentials: bool = False,
    current_user: UserModel = Depends(get_current_user)
):
    """Get specific supplier configuration"""
    try:
        service = SupplierConfigService()
        config = service.get_supplier_config(supplier_name, include_credentials=include_credentials)
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved supplier configuration: {supplier_name}",
            data=config.to_dict()
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supplier configuration"
        )


@router.put("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, Any]])
async def update_supplier(
    supplier_name: str,
    update_data: SupplierConfigUpdate,
    current_user: UserModel = Depends(require_permission("supplier_config:update"))
):
    """Update supplier configuration"""
    try:
        service = SupplierConfigService()
        config = service.update_supplier_config(
            supplier_name,
            update_data.dict(exclude_unset=True)
        )
        
        return ResponseSchema(
            status="success",
            message=f"Updated supplier configuration: {supplier_name}",
            data=config
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update supplier configuration"
        )


@router.delete("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def delete_supplier(
    supplier_name: str,
    current_user: UserModel = Depends(require_permission("supplier_config:delete"))
):
    """Delete supplier configuration"""
    try:
        if not supplier_name or not supplier_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier name is required"
            )
            
        service = SupplierConfigService()
        service.delete_supplier_config(supplier_name)
        
        return ResponseSchema(
            status="success",
            message=f"Deleted supplier configuration: {supplier_name}",
            data={"supplier_name": supplier_name, "deleted": "true"}
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete supplier configuration"
        )


# Test endpoint removed - use /api/suppliers/{supplier_name}/test from supplier_routes.py


# Capabilities endpoint removed - use /api/suppliers/{supplier_name}/capabilities from supplier_routes.py


@router.get("/suppliers/{supplier_name}/credential-fields", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supplier_credential_fields(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get credential field definitions for a supplier"""
    try:
        from MakerMatrix.config.suppliers import get_supplier_credential_fields
        
        fields = get_supplier_credential_fields(supplier_name)
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved credential fields for {supplier_name}",
            data=fields
        )
        
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving credential fields {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credential fields"
        )


@router.get("/suppliers/{supplier_name}/config-fields", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supplier_config_fields(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get configuration field definitions for a supplier"""
    try:
        from MakerMatrix.config.suppliers import get_supplier_config_fields, has_custom_config_fields
        
        fields = get_supplier_config_fields(supplier_name)
        has_custom = has_custom_config_fields(supplier_name)
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration fields for {supplier_name}",
            data={
                "fields": fields,
                "has_custom_fields": has_custom,
                "supplier_name": supplier_name
            }
        )
        
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier '{supplier_name}' not found"
        )
    except Exception as e:
        logger.error(f"Error retrieving config fields {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration fields"
        )


@router.get("/suppliers/{supplier_name}/config-options", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supplier_config_options(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get all configuration options for a supplier (e.g., sandbox vs production for DigiKey)"""
    try:
        service = SupplierConfigService()
        
        # Get the supplier instance to call get_configuration_options()
        try:
            supplier_config = service.get_supplier_config(supplier_name.upper())
        except ResourceNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Supplier '{supplier_name}' not found"
            )
        
        # Create supplier instance to get configuration options
        credentials = service.get_supplier_credentials(supplier_name.upper())
        supplier_instance = service._create_api_client(supplier_config, credentials)
        
        # Get all configuration options from the supplier
        config_options = supplier_instance.get_configuration_options()
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration options for {supplier_name}",
            data={
                "supplier_name": supplier_name,
                "options": config_options
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving config options for {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration options: {str(e)}"
        )


# Credential Management Routes

@router.post("/credentials", response_model=ResponseSchema[Dict[str, str]])
async def store_credentials(
    supplier_name: str,
    credentials: SupplierCredentials,
    current_user: UserModel = Depends(require_permission("supplier_config:credentials"))
):
    """Store encrypted credentials for a supplier"""
    try:
        service = SupplierConfigService()
        
        # Filter out None values
        creds_dict = {k: v for k, v in credentials.dict().items() if v is not None}
        
        if not creds_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No credentials provided"
            )
        
        creds_model = service.set_supplier_credentials(
            supplier_name,
            creds_dict,
            user_id=current_user.id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Stored credentials for {supplier_name}",
            data={
                "supplier_name": supplier_name,
                "credentials_id": creds_model.id,
                "encrypted": "true"
            }
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error storing credentials for {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store credentials"
        )


@router.put("/credentials/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def update_credentials(
    supplier_name: str,
    credentials: SupplierCredentials,
    current_user: UserModel = Depends(require_permission("supplier_config:credentials"))
):
    """Update encrypted credentials for a supplier"""
    try:
        service = SupplierConfigService()
        
        # Filter out None values
        creds_dict = {k: v for k, v in credentials.dict().items() if v is not None}
        
        if not creds_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No credentials provided"
            )
        
        creds_model = service.set_supplier_credentials(
            supplier_name,
            creds_dict,
            user_id=current_user.id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Updated credentials for {supplier_name}",
            data={
                "supplier_name": supplier_name,
                "credentials_id": creds_model.id,
                "updated": "true"
            }
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating credentials for {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credentials"
        )


@router.delete("/credentials/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def delete_credentials(
    supplier_name: str,
    current_user: UserModel = Depends(require_permission("supplier_config:credentials"))
):
    """Delete credentials for a supplier"""
    try:
        service = SupplierConfigService()
        
        # Delete by setting empty credentials
        service.set_supplier_credentials(supplier_name, {}, user_id=current_user.id)
        
        return ResponseSchema(
            status="success",
            message=f"Deleted credentials for {supplier_name}",
            data={"supplier_name": supplier_name, "deleted": "true"}
        )
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting credentials for {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete credentials"
        )


# Import/Export Routes

@router.post("/import", response_model=ResponseSchema[List[str]])
async def import_configurations(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(require_permission("supplier_config:import"))
):
    """Import supplier configurations from JSON file"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a JSON file"
            )
        
        content = await file.read()
        import_data = json.loads(content)
        
        service = SupplierConfigService()
        imported_suppliers = service.import_supplier_configs(import_data, user_id=current_user.id)
        
        return ResponseSchema(
            status="success",
            message=f"Imported {len(imported_suppliers)} supplier configurations",
            data=imported_suppliers
        )
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON file"
        )
    except Exception as e:
        logger.error(f"Error importing supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import supplier configurations"
        )


@router.get("/export", response_model=ResponseSchema[Dict[str, Any]])
async def export_configurations(
    include_credentials: bool = False,
    current_user: UserModel = Depends(require_permission("supplier_config:export"))
):
    """Export all supplier configurations to JSON"""
    try:
        service = SupplierConfigService()
        export_data = service.export_supplier_configs(include_credentials=include_credentials)
        
        return ResponseSchema(
            status="success",
            message=f"Exported {len(export_data['suppliers'])} supplier configurations",
            data=export_data
        )
        
    except Exception as e:
        logger.error(f"Error exporting supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export supplier configurations"
        )


@router.post("/initialize-defaults", response_model=ResponseSchema[List[str]])
async def initialize_default_suppliers(
    current_user: UserModel = Depends(require_permission("supplier_config:create"))
):
    """Initialize default supplier configurations"""
    try:
        service = SupplierConfigService()
        configs = service.initialize_default_suppliers()
        
        supplier_names = [config.supplier_name for config in configs]
        
        return ResponseSchema(
            status="success",
            message=f"Initialized {len(configs)} default supplier configurations",
            data=supplier_names
        )
        
    except Exception as e:
        logger.error(f"Error initializing default suppliers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default suppliers"
        )