"""
Supplier Credentials API Routes

API endpoints for managing supplier credentials.
Works with any supplier type without hardcoding.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from MakerMatrix.auth.dependencies import get_current_user
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.services.system.simple_credential_service import get_credential_service
from MakerMatrix.schemas.response import ResponseSchema

router = APIRouter()

# Request/Response Models
class CredentialSaveRequest(BaseModel):
    credentials: Dict[str, str]

class CredentialTestRequest(BaseModel):
    credentials: Optional[Dict[str, str]] = None

class CredentialStatusResponse(BaseModel):
    supplier_name: str
    has_database_credentials: bool
    has_environment_credentials: bool
    database_fields: list[str]
    environment_fields: list[str]
    configured_fields: list[str]
    required_fields: list[str]
    missing_required: list[str]
    fully_configured: bool
    last_tested: Optional[str] = None
    test_status: Optional[str] = None
    test_error: Optional[str] = None


@router.post("/suppliers/{supplier_name}/credentials", response_model=ResponseSchema[str])
async def save_supplier_credentials(
    supplier_name: str,
    request: CredentialSaveRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Save credentials for a supplier"""
    try:
        credential_service = get_credential_service()
        success = await credential_service.save_credentials(
            supplier_name.lower(),
            request.credentials
        )
        
        if success:
            return ResponseSchema(
                status="success",
                message=f"Credentials saved for {supplier_name}",
                data="saved"
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to save credentials")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")


@router.get("/suppliers/{supplier_name}/credentials", response_model=ResponseSchema[Dict[str, Any]])
async def get_supplier_credentials(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get credentials for a supplier (for editing)"""
    try:
        credential_service = get_credential_service()
        credentials = await credential_service.get_credentials(supplier_name.lower())
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved credentials for {supplier_name}",
            data=credentials or {}
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get credentials: {str(e)}")


@router.get("/suppliers/{supplier_name}/credentials/status", response_model=ResponseSchema[Dict[str, Any]])
async def get_credential_status(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get comprehensive credential status for a supplier"""
    try:
        credential_service = get_credential_service()
        status = await credential_service.get_credential_status(supplier_name.lower())
        
        if "error" in status:
            raise HTTPException(status_code=400, detail=status["error"])
        
        # Convert datetime to string for JSON serialization
        if "last_tested" in status and status["last_tested"]:
            status["last_tested"] = status["last_tested"].isoformat()
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved credential status for {supplier_name}",
            data=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get credential status: {str(e)}")


@router.post("/suppliers/{supplier_name}/credentials/test", response_model=ResponseSchema[Dict[str, Any]])
async def test_supplier_credentials(
    supplier_name: str,
    request: CredentialTestRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Test supplier credentials"""
    try:
        credential_service = get_credential_service()
        result = await credential_service.test_credentials(
            supplier_name.lower(),
            request.credentials
        )
        
        return ResponseSchema(
            status="success" if result.get("success") else "error",
            message=result.get("message", "Test completed"),
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test credentials: {str(e)}")


@router.delete("/suppliers/{supplier_name}/credentials", response_model=ResponseSchema[str])
async def delete_supplier_credentials(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete stored credentials for a supplier"""
    try:
        credential_service = get_credential_service()
        deleted = await credential_service.delete_credentials(supplier_name.lower())
        
        if deleted:
            return ResponseSchema(
                status="success",
                message=f"Credentials deleted for {supplier_name}",
                data="deleted"
            )
        else:
            return ResponseSchema(
                status="success",
                message=f"No credentials found to delete for {supplier_name}",
                data="not_found"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete credentials: {str(e)}")


@router.get("/suppliers/{supplier_name}/credentials/test-existing", response_model=ResponseSchema[Dict[str, Any]])
async def test_existing_credentials(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Test currently stored/configured credentials"""
    try:
        credential_service = get_credential_service()
        result = await credential_service.test_credentials(supplier_name.lower())
        
        return ResponseSchema(
            status="success" if result.get("success") else "error",
            message=result.get("message", "Test completed"),
            data=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test existing credentials: {str(e)}")