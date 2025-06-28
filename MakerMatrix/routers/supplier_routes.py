"""
Generic Supplier API Routes

Provides a unified API interface for discovering, configuring, and using suppliers.
Works with any supplier that implements the BaseSupplier interface.
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.suppliers import SupplierRegistry
from MakerMatrix.suppliers.exceptions import (
    SupplierNotFoundError, SupplierConfigurationError,
    SupplierAuthenticationError, SupplierConnectionError
)
from MakerMatrix.schemas.response import ResponseSchema

router = APIRouter()

# ========== Request/Response Models ==========

class FieldDefinitionResponse(BaseModel):
    name: str
    label: str
    field_type: str
    required: bool = True
    description: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[List[Dict[str, str]]] = None
    validation: Optional[Dict[str, Any]] = None

class SupplierInfoResponse(BaseModel):
    name: str
    display_name: str
    description: str
    website_url: Optional[str] = None
    api_documentation_url: Optional[str] = None
    supports_oauth: bool = False
    rate_limit_info: Optional[str] = None
    capabilities: List[str]

class SupplierConfigurationRequest(BaseModel):
    credentials: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None

class PartSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=50, ge=1, le=100)

class BulkSearchRequest(BaseModel):
    queries: List[str] = Field(..., max_items=20)
    limit_per_query: int = Field(default=10, ge=1, le=50)

class PartSearchResultResponse(BaseModel):
    supplier_part_number: str
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    stock_quantity: Optional[int] = None
    pricing: Optional[List[Dict[str, Any]]] = None
    specifications: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None

# ========== Discovery Endpoints ==========

@router.get("/", response_model=ResponseSchema[List[str]])
async def get_available_suppliers(
    current_user: UserModel = Depends(get_current_user)
):
    """Get list of available supplier names"""
    try:
        suppliers = SupplierRegistry.get_available_suppliers()
        return ResponseSchema(
            status="success",
            message=f"Found {len(suppliers)} available suppliers",
            data=suppliers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suppliers: {str(e)}")

@router.get("/dropdown", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_suppliers_for_dropdown(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get suppliers formatted for dropdown selection (configured and enabled only)
    
    Returns suppliers that are:
    - Available in the supplier registry
    - Properly configured with credentials (if applicable)
    - Currently enabled
    """
    try:
        from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
        
        supplier_service = SupplierConfigService()
        
        # Get all available suppliers from registry
        available_suppliers = SupplierRegistry.get_available_suppliers()
        
        # Get configured suppliers
        configured_suppliers = supplier_service.get_all_supplier_configs(enabled_only=True)
        configured_names = {config["supplier_name"].lower() for config in configured_suppliers}
        
        dropdown_suppliers = []
        
        for supplier_name in available_suppliers:
            try:
                # Get supplier instance
                supplier = SupplierRegistry.get_supplier(supplier_name)
                supplier_info = supplier.get_supplier_info()
                
                # Check if supplier is configured and enabled
                is_configured = supplier_name.lower() in configured_names
                
                # For dropdown, show all suppliers but mark configuration status
                dropdown_suppliers.append({
                    "id": supplier_name.lower(),
                    "name": supplier_info.display_name,
                    "description": supplier_info.description,
                    "configured": is_configured,
                    "enabled": is_configured,  # Only enabled if configured
                    "requires_config": len(supplier.get_credential_schema()) > 0,
                    "rate_limit_info": supplier_info.rate_limit_info if supplier_info.rate_limit_info else "No rate limits",
                    "capabilities_count": len(supplier.get_capabilities())
                })
                
            except Exception as e:
                # Add basic info for suppliers that can't be instantiated
                dropdown_suppliers.append({
                    "id": supplier_name.lower(),
                    "name": supplier_name.title(),
                    "description": f"{supplier_name} electronics supplier",
                    "configured": False,
                    "enabled": False,
                    "requires_config": True,
                    "rate_limit_info": "Configuration required",
                    "capabilities_count": 0
                })
        
        # Sort by name for consistent ordering
        dropdown_suppliers.sort(key=lambda x: x["name"])
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(dropdown_suppliers)} suppliers for dropdown",
            data=dropdown_suppliers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dropdown suppliers: {str(e)}")

@router.get("/configured", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_configured_suppliers_only(
    current_user: UserModel = Depends(get_current_user)
):
    """Get list of configured and enabled suppliers only"""
    try:
        from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
        
        supplier_service = SupplierConfigService()
        
        # Get only enabled and configured suppliers
        configured_suppliers = supplier_service.get_all_supplier_configs(enabled_only=True)
        
        # Enhance with supplier registry information
        enhanced_suppliers = []
        for config in configured_suppliers:
            try:
                supplier_name = config["supplier_name"]
                supplier = SupplierRegistry.get_supplier(supplier_name.lower())
                supplier_info = supplier.get_supplier_info()
                
                enhanced_suppliers.append({
                    "id": supplier_name.lower(),
                    "name": supplier_info.display_name,
                    "description": supplier_info.description,
                    "configured": True,
                    "enabled": config.get("enabled", True),
                    "rate_limit_info": supplier_info.rate_limit_info,
                    "capabilities": [cap.value for cap in supplier.get_capabilities()],
                    "last_tested": config.get("last_tested_at"),
                    "test_status": config.get("test_status")
                })
                
            except Exception as e:
                # Fallback to basic config info
                enhanced_suppliers.append({
                    "id": config["supplier_name"].lower(),
                    "name": config.get("display_name", config["supplier_name"]),
                    "description": config.get("description", ""),
                    "configured": True,
                    "enabled": config.get("enabled", True),
                    "rate_limit_info": "Unknown",
                    "capabilities": [],
                    "last_tested": config.get("last_tested_at"),
                    "test_status": config.get("test_status", "unknown")
                })
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(enhanced_suppliers)} configured suppliers",
            data=enhanced_suppliers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configured suppliers: {str(e)}")

@router.get("/info", response_model=ResponseSchema[Dict[str, SupplierInfoResponse]])
async def get_all_suppliers_info(
    current_user: UserModel = Depends(get_current_user)
):
    """Get information about all available suppliers"""
    try:
        suppliers_info = {}
        for name in SupplierRegistry.get_available_suppliers():
            supplier = SupplierRegistry.get_supplier(name)
            info = supplier.get_supplier_info()
            capabilities = [cap.value for cap in supplier.get_capabilities()]
            
            suppliers_info[name] = SupplierInfoResponse(
                name=info.name,
                display_name=info.display_name,
                description=info.description,
                website_url=info.website_url,
                api_documentation_url=info.api_documentation_url,
                supports_oauth=info.supports_oauth,
                rate_limit_info=info.rate_limit_info,
                capabilities=capabilities
            )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved info for {len(suppliers_info)} suppliers",
            data=suppliers_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supplier info: {str(e)}")

@router.get("/{supplier_name}/info", response_model=ResponseSchema[SupplierInfoResponse])
async def get_supplier_info(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get information about a specific supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        info = supplier.get_supplier_info()
        capabilities = [cap.value for cap in supplier.get_capabilities()]
        
        response_data = SupplierInfoResponse(
            name=info.name,
            display_name=info.display_name,
            description=info.description,
            website_url=info.website_url,
            api_documentation_url=info.api_documentation_url,
            supports_oauth=info.supports_oauth,
            rate_limit_info=info.rate_limit_info,
            capabilities=capabilities
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved info for {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supplier info: {str(e)}")

# ========== Schema Endpoints ==========

@router.get("/{supplier_name}/credentials-schema", response_model=ResponseSchema[List[FieldDefinitionResponse]])
async def get_supplier_credential_schema(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get the credential fields required by a supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        schema = supplier.get_credential_schema()
        
        response_data = [
            FieldDefinitionResponse(
                name=field.name,
                label=field.label,
                field_type=field.field_type.value,
                required=field.required,
                description=field.description,
                placeholder=field.placeholder,
                help_text=field.help_text,
                default_value=field.default_value,
                options=field.options,
                validation=field.validation
            )
            for field in schema
        ]
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved credential schema for {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get credential schema: {str(e)}")

@router.get("/{supplier_name}/config-schema", response_model=ResponseSchema[List[FieldDefinitionResponse]])
async def get_supplier_config_schema(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get the configuration fields supported by a supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        schema = supplier.get_configuration_schema()
        
        response_data = [
            FieldDefinitionResponse(
                name=field.name,
                label=field.label,
                field_type=field.field_type.value,
                required=field.required,
                description=field.description,
                placeholder=field.placeholder,
                help_text=field.help_text,
                default_value=field.default_value,
                options=field.options,
                validation=field.validation
            )
            for field in schema
        ]
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration schema for {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration schema: {str(e)}")

@router.get("/{supplier_name}/capabilities", response_model=ResponseSchema[List[str]])
async def get_supplier_capabilities(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get the capabilities supported by a supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        capabilities = [cap.value for cap in supplier.get_capabilities()]
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved capabilities for {supplier_name}",
            data=capabilities
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")

@router.post("/{supplier_name}/credentials-schema-with-config", response_model=ResponseSchema[List[FieldDefinitionResponse]])
async def get_supplier_credential_schema_with_config(
    supplier_name: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get the credential fields required by a supplier with current configuration context"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        
        # Configure the supplier with current values to get context-aware schema
        supplier.configure(
            credentials=config_request.credentials or {},
            config=config_request.config or {}
        )
        
        schema = supplier.get_credential_schema()
        
        response_data = [
            FieldDefinitionResponse(
                name=field.name,
                label=field.label,
                field_type=field.field_type.value,
                required=field.required,
                description=field.description,
                placeholder=field.placeholder,
                help_text=field.help_text,
                default_value=field.default_value,
                options=field.options,
                validation=field.validation
            )
            for field in schema
        ]
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved credential schema for {supplier_name} with config context",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get credential schema: {str(e)}")

@router.post("/{supplier_name}/config-schema-with-config", response_model=ResponseSchema[List[FieldDefinitionResponse]])
async def get_supplier_config_schema_with_config(
    supplier_name: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get the configuration fields supported by a supplier with current configuration context"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        
        # Configure the supplier with current values to get context-aware schema
        supplier.configure(
            credentials=config_request.credentials or {},
            config=config_request.config or {}
        )
        
        schema = supplier.get_configuration_schema()
        
        response_data = [
            FieldDefinitionResponse(
                name=field.name,
                label=field.label,
                field_type=field.field_type.value,
                required=field.required,
                description=field.description,
                placeholder=field.placeholder,
                help_text=field.help_text,
                default_value=field.default_value,
                options=field.options,
                validation=field.validation
            )
            for field in schema
        ]
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved configuration schema for {supplier_name} with config context",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration schema: {str(e)}")

@router.get("/{supplier_name}/env-defaults", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_env_defaults(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get environment variable defaults for supplier credentials"""
    import os
    try:
        defaults = {}
        
        # Get supplier instance to understand what credentials it needs
        supplier = SupplierRegistry.get_supplier(supplier_name)
        credential_schema = supplier.get_credential_schema()
        
        # Map credential fields to common environment variable patterns
        env_var_patterns = {
            'client_id': [f'{supplier_name.upper()}_CLIENT_ID', f'{supplier_name.upper()}_ID'],
            'client_secret': [f'{supplier_name.upper()}_CLIENT_SECRET', f'{supplier_name.upper()}_SECRET'],
            'api_key': [f'{supplier_name.upper()}_API_KEY', f'{supplier_name.upper()}_KEY'],
            'username': [f'{supplier_name.upper()}_USERNAME', f'{supplier_name.upper()}_USER'],
            'password': [f'{supplier_name.upper()}_PASSWORD', f'{supplier_name.upper()}_PASS'],
            'oauth_token': [f'{supplier_name.upper()}_OAUTH_TOKEN', f'{supplier_name.upper()}_TOKEN'],
            'refresh_token': [f'{supplier_name.upper()}_REFRESH_TOKEN']
        }
        
        # Check for environment variables based on what credentials this supplier needs
        for field in credential_schema:
            field_name = field.name
            if field_name in env_var_patterns:
                # Try each possible environment variable pattern
                for env_var_name in env_var_patterns[field_name]:
                    env_value = os.getenv(env_var_name)
                    if env_value:
                        defaults[field_name] = env_value
                        break  # Use first found environment variable
            
        return ResponseSchema(
            status="success",
            message=f"Retrieved environment defaults for {supplier_name}",
            data=defaults
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get environment defaults: {str(e)}")

# ========== Configuration and Testing ==========

@router.post("/{supplier_name}/test", response_model=ResponseSchema[Dict[str, Any]])
async def test_supplier_connection(
    supplier_name: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Test connection to a supplier with provided credentials/config (rate limited)"""
    from MakerMatrix.services.rate_limit_service import RateLimitService
    from MakerMatrix.models.models import engine
    import time
    
    # Initialize rate limiting service
    rate_limit_service = RateLimitService(engine)
    
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        # Use rate limiting for the connection test
        async with rate_limit_service.rate_limited_request(supplier_name.upper(), "connection_test") as rate_ctx:
            if not rate_ctx.allowed:
                rate_status = rate_ctx.rate_status
                return ResponseSchema(
                    status="warning",
                    message=f"Rate limit exceeded for {supplier_name}. Please wait {rate_status['retry_after_seconds']} seconds.",
                    data={
                        "success": False,
                        "rate_limited": True,
                        "rate_limit_info": rate_status,
                        "retry_after": rate_status['retry_after_seconds']
                    }
                )
            
            # Record the start time for response time tracking
            start_time = time.time()
            
            try:
                result = await supplier.test_connection()
                print(f"🔍 supplier.test_connection() returned: {result}")
                
                # Calculate response time
                response_time = int((time.time() - start_time) * 1000)
                await rate_ctx.record_success(response_time)
                
                # Add rate limit info to the response
                rate_status = await rate_limit_service.check_rate_limit(supplier_name.upper())
                result["rate_limit_info"] = {
                    "current_usage": rate_status.get("current_usage", {}),
                    "limits": rate_status.get("limits", {}),
                    "usage_percentage": rate_status.get("usage_percentage", {})
                }
                
                wrapped_response = ResponseSchema(
                    status="success" if result.get("success") else "error",
                    message=result.get("message", "Connection test completed"),
                    data=result
                )
                print(f"🔍 Final wrapped response: {wrapped_response}")
                return wrapped_response
                
            except Exception as test_error:
                # Record the failure with response time
                response_time = int((time.time() - start_time) * 1000)
                await rate_ctx.record_failure(str(test_error))
                raise test_error
                
        await supplier.close()  # Clean up
        
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierConfigurationError as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# ========== OAuth Support for DigiKey ==========

@router.post("/{supplier_name}/oauth/authorization-url", response_model=ResponseSchema[str])
async def get_oauth_authorization_url(
    supplier_name: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get OAuth authorization URL for suppliers that support OAuth"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        # Check if this supplier supports OAuth
        if not hasattr(supplier, 'get_oauth_authorization_url'):
            raise HTTPException(
                status_code=400, 
                detail=f"Supplier '{supplier_name}' does not support OAuth"
            )
        
        auth_url = supplier.get_oauth_authorization_url()
        
        return ResponseSchema(
            status="success",
            message=f"OAuth authorization URL generated for {supplier_name}",
            data=auth_url
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierConfigurationError as e:
        raise HTTPException(status_code=400, detail=f"Configuration error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OAuth URL: {str(e)}")

@router.post("/{supplier_name}/oauth/exchange", response_model=ResponseSchema[Dict[str, Any]])
async def exchange_oauth_code(
    supplier_name: str,
    authorization_code: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Exchange OAuth authorization code for tokens"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        if not hasattr(supplier, 'exchange_code_for_tokens'):
            raise HTTPException(
                status_code=400,
                detail=f"Supplier '{supplier_name}' does not support OAuth"
            )
        
        success = await supplier.exchange_code_for_tokens(authorization_code)
        
        if success:
            return ResponseSchema(
                status="success",
                message=f"OAuth tokens obtained for {supplier_name}",
                data={"authenticated": True}
            )
        else:
            return ResponseSchema(
                status="error",
                message="Failed to exchange authorization code",
                data={"authenticated": False}
            )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")

# ========== Part Search and Data Retrieval ==========

@router.post("/{supplier_name}/search", response_model=ResponseSchema[List[PartSearchResultResponse]])
async def search_parts(
    supplier_name: str,
    search_request: PartSearchRequest,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Search for parts using a specific supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        results = await supplier.search_parts(search_request.query, search_request.limit)
        await supplier.close()
        
        # Convert to response format
        response_data = [
            PartSearchResultResponse(
                supplier_part_number=result.supplier_part_number,
                manufacturer=result.manufacturer,
                manufacturer_part_number=result.manufacturer_part_number,
                description=result.description,
                category=result.category,
                datasheet_url=result.datasheet_url,
                image_url=result.image_url,
                stock_quantity=result.stock_quantity,
                pricing=result.pricing,
                specifications=result.specifications,
                additional_data=result.additional_data
            )
            for result in results
        ]
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(response_data)} parts from {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SupplierConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/{supplier_name}/bulk-search", response_model=ResponseSchema[Dict[str, List[PartSearchResultResponse]]])
async def bulk_search_parts(
    supplier_name: str,
    search_request: BulkSearchRequest,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Search for multiple parts at once using a specific supplier"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        results = await supplier.bulk_search_parts(search_request.queries, search_request.limit_per_query)
        await supplier.close()
        
        # Convert to response format
        response_data = {}
        for query, query_results in results.items():
            response_data[query] = [
                PartSearchResultResponse(
                    supplier_part_number=result.supplier_part_number,
                    manufacturer=result.manufacturer,
                    manufacturer_part_number=result.manufacturer_part_number,
                    description=result.description,
                    category=result.category,
                    datasheet_url=result.datasheet_url,
                    image_url=result.image_url,
                    stock_quantity=result.stock_quantity,
                    pricing=result.pricing,
                    specifications=result.specifications,
                    additional_data=result.additional_data
                )
                for result in query_results
            ]
        
        total_results = sum(len(results) for results in response_data.values())
        
        return ResponseSchema(
            status="success",
            message=f"Bulk search completed: {total_results} total results from {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SupplierConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk search failed: {str(e)}")

@router.post("/{supplier_name}/part/{part_number}", response_model=ResponseSchema[PartSearchResultResponse])
async def get_part_details(
    supplier_name: str,
    part_number: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get detailed information about a specific part"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        result = await supplier.get_part_details(part_number)
        await supplier.close()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Part '{part_number}' not found")
        
        response_data = PartSearchResultResponse(
            supplier_part_number=result.supplier_part_number,
            manufacturer=result.manufacturer,
            manufacturer_part_number=result.manufacturer_part_number,
            description=result.description,
            category=result.category,
            datasheet_url=result.datasheet_url,
            image_url=result.image_url,
            stock_quantity=result.stock_quantity,
            pricing=result.pricing,
            specifications=result.specifications,
            additional_data=result.additional_data
        )
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved details for {part_number} from {supplier_name}",
            data=response_data
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except SupplierConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get part details: {str(e)}")

# ========== Specific Data Fetching ==========

@router.post("/{supplier_name}/part/{part_number}/datasheet", response_model=ResponseSchema[str])
async def get_part_datasheet(
    supplier_name: str,
    part_number: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get datasheet URL for a specific part"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        datasheet_url = await supplier.fetch_datasheet(part_number)
        await supplier.close()
        
        if not datasheet_url:
            raise HTTPException(status_code=404, detail="Datasheet not available")
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved datasheet URL for {part_number}",
            data=datasheet_url
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get datasheet: {str(e)}")

@router.post("/{supplier_name}/part/{part_number}/pricing", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_part_pricing(
    supplier_name: str,
    part_number: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get current pricing for a specific part"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        pricing = await supplier.fetch_pricing(part_number)
        await supplier.close()
        
        if not pricing:
            raise HTTPException(status_code=404, detail="Pricing not available")
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved pricing for {part_number}",
            data=pricing
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pricing: {str(e)}")

@router.post("/{supplier_name}/part/{part_number}/stock", response_model=ResponseSchema[int])
async def get_part_stock(
    supplier_name: str,
    part_number: str,
    config_request: SupplierConfigurationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Get current stock level for a specific part"""
    try:
        supplier = SupplierRegistry.get_supplier(supplier_name)
        supplier.configure(config_request.credentials, config_request.config)
        
        stock = await supplier.fetch_stock(part_number)
        await supplier.close()
        
        if stock is None:
            raise HTTPException(status_code=404, detail="Stock information not available")
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved stock level for {part_number}",
            data=stock
        )
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_name}' not found")
    except SupplierAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stock: {str(e)}")

# ========== OAuth Callback Handling ==========

@router.get("/{supplier_name}/oauth/callback", response_class=HTMLResponse)
async def handle_oauth_callback(
    supplier_name: str,
    code: str = Query(None, description="OAuth authorization code"),
    error: str = Query(None, description="OAuth error"),
    state: str = Query(None, description="OAuth state parameter")
):
    """Handle OAuth callback for supplier authentication"""
    
    # Simple HTML response to inform user about the OAuth result
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MakerMatrix - {supplier_name} OAuth</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
            .success {{ color: #22c55e; }}
            .error {{ color: #ef4444; }}
            .info {{ color: #3b82f6; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .code-box {{ 
                background: #f3f4f6; 
                border: 1px solid #d1d5db; 
                border-radius: 8px; 
                padding: 16px; 
                margin: 20px 0; 
                font-family: monospace; 
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>MakerMatrix - {supplier_name} OAuth</h1>
            {content}
        </div>
    </body>
    </html>
    """
    
    if error:
        content = f"""
        <h2 class="error">OAuth Authorization Failed</h2>
        <p>Error: {error}</p>
        <p>Please return to MakerMatrix and try the OAuth setup again.</p>
        <p>If this problem persists, check your {supplier_name} app configuration.</p>
        """
        return HTMLResponse(
            content=html_template.format(
                supplier_name=supplier_name.title(),
                content=content
            ),
            status_code=400
        )
    
    if not code:
        content = f"""
        <h2 class="error">Missing Authorization Code</h2>
        <p>No authorization code received from {supplier_name}.</p>
        <p>Please return to MakerMatrix and restart the OAuth setup process.</p>
        """
        return HTMLResponse(
            content=html_template.format(
                supplier_name=supplier_name.title(),
                content=content
            ),
            status_code=400
        )
    
    # Success - show the authorization code for manual entry
    content = f"""
    <h2 class="success">OAuth Authorization Successful!</h2>
    <p>Authorization code received from {supplier_name}.</p>
    
    <div class="info">
        <h3>Next Steps:</h3>
        <p>Copy the authorization code below and paste it into MakerMatrix:</p>
        <div class="code-box">{code}</div>
        <p><strong>Instructions:</strong></p>
        <ol style="text-align: left;">
            <li>Copy the authorization code above</li>
            <li>Return to MakerMatrix supplier configuration</li>
            <li>Paste the code when prompted</li>
            <li>Complete the authentication setup</li>
        </ol>
    </div>
    
    <p><small>You can close this window after copying the code.</small></p>
    """
    
    return HTMLResponse(
        content=html_template.format(
            supplier_name=supplier_name.title(),
            content=content
        )
    )