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
    InvalidReferenceError,
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
    website_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    supplier_type: str = Field(
        default="advanced",
        max_length=50,
        description="Supplier type: advanced (API enrichment), basic (limited features), simple (URL-only)",
    )
    api_type: str = Field(default="rest", max_length=50)
    base_url: Optional[str] = Field(None, max_length=500, description="Optional for simple suppliers")
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

    @validator("supplier_name")
    def validate_supplier_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Supplier name cannot be empty")
        return v.strip()

    @validator("supplier_type")
    def validate_supplier_type(cls, v):
        allowed_types = ["advanced", "basic", "simple"]
        if v not in allowed_types:
            raise ValueError(f"Supplier type must be one of: {allowed_types}")
        return v

    @validator("base_url")
    def validate_base_url(cls, v, values):
        # base_url is only required for advanced suppliers
        supplier_type = values.get("supplier_type", "advanced")
        if supplier_type in ["advanced", "basic"] and not v:
            raise ValueError("base_url is required for advanced and basic suppliers")
        return v if v else ""  # Set empty string for simple suppliers

    @validator("api_type")
    def validate_api_type(cls, v):
        allowed_types = ["rest", "graphql", "scraping"]
        if v not in allowed_types:
            raise ValueError(f"API type must be one of: {allowed_types}")
        return v


class SupplierConfigUpdate(BaseModel):
    """Schema for updating supplier configuration"""

    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    website_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    supplier_type: Optional[str] = Field(None, max_length=50)
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
async def get_all_suppliers(enabled_only: bool = False, current_user: UserModel = Depends(get_current_user)):
    """Get all supplier configurations"""
    try:
        service = SupplierConfigService()
        config_dicts = service.get_all_supplier_configs(enabled_only=enabled_only)

        return ResponseSchema(
            status="success", message=f"Retrieved {len(config_dicts)} supplier configurations", data=config_dicts
        )

    except Exception as e:
        logger.error(f"Error retrieving supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve supplier configurations"
        )


@router.post("/suppliers", response_model=ResponseSchema[Dict[str, Any]])
async def create_supplier(
    config_data: SupplierConfigCreate, current_user: UserModel = Depends(require_permission("supplier_config:create"))
):
    """Create a new supplier configuration - automatically fetches favicon if website_url is set"""
    try:
        # Additional validation beyond Pydantic
        if not config_data.supplier_name or not config_data.supplier_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier name cannot be empty or whitespace only"
            )

        if not config_data.display_name or not config_data.display_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Display name cannot be empty or whitespace only"
            )

        # Validate supplier name format
        supplier_name = config_data.supplier_name.strip().lower()
        if not supplier_name.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier name must contain only letters, numbers, hyphens, and underscores",
            )

        # Convert config to dict for modification
        config_dict = config_data.dict(exclude_unset=True)

        # Auto-fetch favicon if website_url is set but no image_url provided
        if config_dict.get("website_url") and not config_dict.get("image_url"):
            try:
                from MakerMatrix.services.utility.favicon_fetcher import FaviconFetcherService

                favicon_service = FaviconFetcherService()
                favicon_url = await favicon_service.fetch_and_store_favicon(config_dict["website_url"], supplier_name)
                if favicon_url:
                    config_dict["image_url"] = favicon_url
                    logger.info(f"Auto-fetched favicon for {supplier_name}: {favicon_url}")
            except Exception as e:
                logger.warning(f"Failed to auto-fetch favicon for {supplier_name}: {e}")
                # Continue with creation even if favicon fetch fails

        service = SupplierConfigService()
        config = service.create_supplier_config(config_dict, user_id=current_user.id)

        # Fetch the supplier again to get a fresh instance with all data
        # This avoids detached instance errors
        # Use the already-normalized supplier_name variable instead of accessing the detached config object
        config_data = service.get_supplier_config(supplier_name)

        return ResponseSchema(
            status="success", message=f"Created supplier configuration: {supplier_name}", data=config_data
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except SupplierConfigAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating supplier configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create supplier configuration"
        )


@router.get("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier(
    supplier_name: str, include_credentials: bool = False, current_user: UserModel = Depends(get_current_user)
):
    """Get specific supplier configuration"""
    try:
        service = SupplierConfigService()
        config = service.get_supplier_config(supplier_name, include_credentials=include_credentials)

        return ResponseSchema(
            status="success", message=f"Retrieved supplier configuration: {supplier_name}", data=config.to_dict()
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve supplier configuration"
        )


@router.put("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, Any]])
async def update_supplier(
    supplier_name: str,
    update_data: SupplierConfigUpdate,
    current_user: UserModel = Depends(require_permission("supplier_config:update")),
):
    """Update supplier configuration - automatically fetches favicon if website_url is set"""
    try:
        service = SupplierConfigService()
        update_dict = update_data.dict(exclude_unset=True)

        # Get current config to check for existing website_url
        current_config = service.get_supplier_config(supplier_name)

        # Determine the website_url (new or existing)
        website_url = update_dict.get("website_url") or current_config.get("website_url")

        # Auto-fetch favicon if:
        # 1. We have a website_url (new or existing)
        # 2. AND no image_url is set (neither in update nor in current config)
        if website_url:
            has_image = update_dict.get("image_url") or current_config.get("image_url")
            if not has_image:
                try:
                    from MakerMatrix.services.utility.favicon_fetcher import FaviconFetcherService

                    favicon_service = FaviconFetcherService()
                    favicon_url = await favicon_service.fetch_and_store_favicon(website_url, supplier_name)
                    if favicon_url:
                        update_dict["image_url"] = favicon_url
                        logger.info(f"Auto-fetched favicon for {supplier_name}: {favicon_url}")
                except Exception as e:
                    logger.warning(f"Failed to auto-fetch favicon for {supplier_name}: {e}")
                    # Continue with update even if favicon fetch fails

        config = service.update_supplier_config(supplier_name, update_dict)

        return ResponseSchema(status="success", message=f"Updated supplier configuration: {supplier_name}", data=config)

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update supplier configuration"
        )


@router.delete("/suppliers/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def delete_supplier(
    supplier_name: str, current_user: UserModel = Depends(require_permission("supplier_config:delete"))
):
    """Delete supplier configuration"""
    try:
        if not supplier_name or not supplier_name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier name is required")

        service = SupplierConfigService()
        service.delete_supplier_config(supplier_name)

        return ResponseSchema(
            status="success",
            message=f"Deleted supplier configuration: {supplier_name}",
            data={"supplier_name": supplier_name, "deleted": "true"},
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting supplier configuration {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete supplier configuration"
        )


# Test endpoint removed - use /api/suppliers/{supplier_name}/test from supplier_routes.py


# Capabilities endpoint removed - use /api/suppliers/{supplier_name}/capabilities from supplier_routes.py


@router.get("/suppliers/{supplier_name}/credential-fields", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supplier_credential_fields(supplier_name: str, current_user: UserModel = Depends(get_current_user)):
    """Get credential field definitions for a supplier"""
    try:
        from MakerMatrix.config.suppliers import get_supplier_credential_fields

        fields = get_supplier_credential_fields(supplier_name)

        return ResponseSchema(status="success", message=f"Retrieved credential fields for {supplier_name}", data=fields)

    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        logger.error(f"Error retrieving credential fields {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve credential fields"
        )


@router.get("/suppliers/{supplier_name}/config-fields", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_config_fields(supplier_name: str, current_user: UserModel = Depends(get_current_user)):
    """Get configuration field definitions for a supplier"""
    from MakerMatrix.suppliers.registry import get_supplier
    from MakerMatrix.exceptions import SupplierNotFoundError

    try:
        # Get the supplier instance
        supplier = get_supplier(supplier_name)

        # Get configuration schema
        field_definitions = supplier.get_configuration_schema()

        # Convert FieldDefinition objects to dicts
        fields = []
        for field_def in field_definitions:
            field_dict = {
                "field": field_def.name,
                "label": field_def.label,
                "type": (
                    field_def.field_type.value if hasattr(field_def.field_type, "value") else str(field_def.field_type)
                ),
                "required": field_def.required,
            }

            # Add optional fields if present
            if field_def.description:
                field_dict["description"] = field_def.description
            if field_def.placeholder:
                field_dict["placeholder"] = field_def.placeholder
            if field_def.help_text:
                field_dict["help_text"] = field_def.help_text
            if field_def.default_value is not None:
                field_dict["default_value"] = field_def.default_value
            if field_def.options:
                field_dict["options"] = field_def.options
            if field_def.validation:
                field_dict["validation"] = field_def.validation

            fields.append(field_dict)

        # Check if supplier has custom configuration fields
        # (suppliers with get_configuration_options returning more than default)
        has_custom = len(supplier.get_configuration_options()) > 1

        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration fields for {supplier_name}",
            data={"fields": fields, "has_custom_fields": has_custom, "supplier_name": supplier_name},
        )

    except SupplierNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        logger.error(f"Error retrieving config fields {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration fields: {str(e)}",
        )


@router.get("/suppliers/{supplier_name}/config-options", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supplier_config_options(supplier_name: str, current_user: UserModel = Depends(get_current_user)):
    """Get all configuration options for a supplier (e.g., sandbox vs production for DigiKey)"""
    try:
        service = SupplierConfigService()

        # Get the supplier instance to call get_configuration_options()
        try:
            supplier_config = service.get_supplier_config(supplier_name.upper())
        except ResourceNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Supplier '{supplier_name}' not found")

        # Create supplier instance to get configuration options
        credentials = service.get_supplier_credentials(supplier_name.upper())
        supplier_instance = service._create_api_client(supplier_config, credentials)

        # Get all configuration options from the supplier
        config_options = supplier_instance.get_configuration_options()

        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration options for {supplier_name}",
            data={"supplier_name": supplier_name, "options": config_options},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving config options for {supplier_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration options: {str(e)}",
        )


# Credential Management Routes


@router.post("/credentials", response_model=ResponseSchema[Dict[str, str]])
async def store_credentials(
    supplier_name: str,
    credentials: SupplierCredentials,
    current_user: UserModel = Depends(require_permission("supplier_config:credentials")),
):
    """Store encrypted credentials for a supplier"""
    try:
        service = SupplierConfigService()

        # Filter out None values
        creds_dict = {k: v for k, v in credentials.dict().items() if v is not None}

        if not creds_dict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credentials provided")

        creds_model = service.set_supplier_credentials(supplier_name, creds_dict, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message=f"Stored credentials for {supplier_name}",
            data={"supplier_name": supplier_name, "credentials_id": creds_model.id, "encrypted": "true"},
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing credentials for {supplier_name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store credentials")


@router.put("/credentials/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def update_credentials(
    supplier_name: str,
    credentials: SupplierCredentials,
    current_user: UserModel = Depends(require_permission("supplier_config:credentials")),
):
    """Update encrypted credentials for a supplier"""
    try:
        service = SupplierConfigService()

        # Filter out None values
        creds_dict = {k: v for k, v in credentials.dict().items() if v is not None}

        if not creds_dict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credentials provided")

        creds_model = service.set_supplier_credentials(supplier_name, creds_dict, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message=f"Updated credentials for {supplier_name}",
            data={"supplier_name": supplier_name, "credentials_id": creds_model.id, "updated": "true"},
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating credentials for {supplier_name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update credentials")


@router.delete("/credentials/{supplier_name}", response_model=ResponseSchema[Dict[str, str]])
async def delete_credentials(
    supplier_name: str, current_user: UserModel = Depends(require_permission("supplier_config:credentials"))
):
    """Delete credentials for a supplier"""
    try:
        service = SupplierConfigService()

        # Delete by setting empty credentials
        service.set_supplier_credentials(supplier_name, {}, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message=f"Deleted credentials for {supplier_name}",
            data={"supplier_name": supplier_name, "deleted": "true"},
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting credentials for {supplier_name}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete credentials")


# Import/Export Routes


@router.post("/import", response_model=ResponseSchema[List[str]])
async def import_configurations(
    file: UploadFile = File(...), current_user: UserModel = Depends(require_permission("supplier_config:import"))
):
    """Import supplier configurations from JSON file"""
    try:
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a JSON file")

        content = await file.read()
        import_data = json.loads(content)

        service = SupplierConfigService()
        imported_suppliers = service.import_supplier_configs(import_data, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message=f"Imported {len(imported_suppliers)} supplier configurations",
            data=imported_suppliers,
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error importing supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to import supplier configurations"
        )


@router.get("/export", response_model=ResponseSchema[Dict[str, Any]])
async def export_configurations(
    include_credentials: bool = False, current_user: UserModel = Depends(require_permission("supplier_config:export"))
):
    """Export all supplier configurations to JSON"""
    try:
        service = SupplierConfigService()
        export_data = service.export_supplier_configs(include_credentials=include_credentials)

        return ResponseSchema(
            status="success",
            message=f"Exported {len(export_data['suppliers'])} supplier configurations",
            data=export_data,
        )

    except Exception as e:
        logger.error(f"Error exporting supplier configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to export supplier configurations"
        )


@router.post("/initialize-defaults", response_model=ResponseSchema[List[str]])
async def initialize_default_suppliers(current_user: UserModel = Depends(require_permission("supplier_config:create"))):
    """Initialize default supplier configurations"""
    try:
        service = SupplierConfigService()
        configs = service.initialize_default_suppliers()

        # configs is a list of dicts, extract supplier_name from each
        supplier_names = [config["supplier_name"] for config in configs]

        return ResponseSchema(
            status="success", message=f"Initialized {len(configs)} default supplier configurations", data=supplier_names
        )

    except Exception as e:
        logger.error(f"Error initializing default suppliers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize default suppliers"
        )
