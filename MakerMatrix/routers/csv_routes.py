from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, UploadFile, File
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import os
from MakerMatrix.services.csv_import_service import csv_import_service, CSVImportService
from MakerMatrix.services.enhanced_import_service import EnhancedImportService
from MakerMatrix.services.enrichment_queue_manager import EnrichmentPriority
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.order_service import order_service
from MakerMatrix.services.parser_client_registry import get_all_enrichment_mappings, get_enrichment_capabilities, validate_mapping, supports_enrichment
from MakerMatrix.dependencies.auth import require_permission
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
from MakerMatrix.schemas.response import ResponseSchema
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["csv"])

# Global reference to the active import service for progress tracking
_active_import_service = None

# Request models
class CSVPreviewRequest(BaseModel):
    csv_content: str

class FilenameExtractionRequest(BaseModel):
    filename: str

class CSVImportRequest(BaseModel):
    csv_content: str

class EnhancedImportRequest(BaseModel):
    csv_content: Optional[str] = None
    file_path: Optional[str] = None
    parser_type: Optional[str] = None
    order_info: Optional[Dict[str, Any]] = None
    enrichment_enabled: bool = True
    enrichment_priority: str = "normal"  # normal, high, urgent, low

class BulkEnrichmentRequest(BaseModel):
    part_ids: List[str]
    supplier_name: Optional[str] = None
    capabilities: Optional[List[str]] = None
    priority: str = "normal"

# Response models
class CSVPreviewResponse(BaseModel):
    detected_type: str | None
    type_info: str
    headers: List[str]
    preview_rows: List[Dict[str, Any]]
    parsed_preview: List[Dict[str, Any]]
    total_rows: int
    is_supported: bool
    validation_errors: List[str]
    error: str | None = None

class CSVImportResponse(BaseModel):
    success_parts: List[str]
    failed_parts: List[str]
    order_id: str | None = None


@router.get("/supported-types", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_supported_types():
    """Get list of supported CSV file types using dynamic parser registry"""
    try:
        types = csv_import_service.get_supported_types()
        return ResponseSchema(
            status="success",
            message="Supported CSV types retrieved successfully",
            data=types
        )
    except Exception as e:
        logger.error(f"Error getting supported types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported types")


@router.get("/available-suppliers", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_available_suppliers():
    """Get list of available suppliers from new supplier registry"""
    try:
        from MakerMatrix.suppliers.registry import get_available_suppliers, get_supplier
        
        suppliers = []
        for supplier_name in get_available_suppliers():
            try:
                supplier = get_supplier(supplier_name)
                capabilities = supplier.get_capabilities()
                capability_names = [cap.name.lower() for cap in capabilities]
                
                suppliers.append({
                    "id": supplier_name.lower(),
                    "name": supplier_name,
                    "description": f"{supplier_name} electronics supplier",
                    "color": _get_supplier_color(supplier_name),
                    "supported": True,
                    "capabilities": capability_names
                })
            except Exception as e:
                # If we can't get supplier info, skip it
                logger.warning(f"Failed to get info for supplier {supplier_name}: {e}")
                continue
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(suppliers)} available suppliers",
            data=suppliers
        )
    except Exception as e:
        logger.error(f"Error getting available suppliers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available suppliers")


def _get_supplier_color(supplier_name: str) -> str:
    """Get a color for the supplier based on name"""
    color_map = {
        "LCSC": "bg-blue-500",
        "DIGIKEY": "bg-red-500", 
        "MOUSER": "bg-green-500",
        "ARROW": "bg-purple-500",
        "FARNELL": "bg-orange-500"
    }
    return color_map.get(supplier_name.upper(), "bg-gray-500")


@router.post("/preview", response_model=ResponseSchema[Dict[str, Any]])
async def preview_csv(
    request: CSVPreviewRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Preview CSV content and detect file type"""
    try:
        preview_data = csv_import_service.preview_csv(request.csv_content)
        
        # Transform to match expected test format
        response_data = {
            "detected_parser": preview_data.get("detected_type"),
            "preview_rows": preview_data.get("preview_rows", []),
            "headers": preview_data.get("headers", []),
            "total_rows": preview_data.get("total_rows", 0),
            "is_supported": preview_data.get("is_supported", False),
            "validation_errors": preview_data.get("validation_errors", [])
        }
        
        return ResponseSchema(
            status="success",
            message="CSV preview generated successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error previewing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview CSV: {str(e)}")


@router.post("/import", response_model=ResponseSchema[Dict[str, Any]])
async def import_csv(
    csv_request: CSVImportRequest,
    http_request: Request,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Import parts from CSV file with order tracking"""
    try:
        # Get user's enrichment settings
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        
        session = next(get_session())
        try:
            config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            
            if not config:
                config = CSVImportConfigModel(id="default")
                session.add(config)
                session.commit()
                session.refresh(config)
        finally:
            session.close()
        
        # Parse CSV to parts data with user's enrichment settings
        enable_enrichment = config.enable_enrichment and supports_enrichment(csv_request.parser_type)
        parts_data, parsing_errors = csv_import_service.parse_csv_to_parts(
            csv_request.csv_content, 
            csv_request.parser_type,
            enable_enrichment=enable_enrichment
        )
        
        if parsing_errors:
            logger.warning(f"CSV parsing errors: {parsing_errors}")
        
        if not parts_data:
            return ResponseSchema(
                status="success",
                message="CSV import completed with no valid parts found",
                data={
                    "total_rows": 0,
                    "successful_imports": 0,
                    "failed_imports": 1,
                    "failures": ["No valid parts data found in CSV"]
                }
            )
        
        # Import parts with order tracking
        part_service = PartService()
        success_parts, failed_parts, imported_part_ids = await csv_import_service.import_parts_with_order(
            parts_data,
            part_service,
            csv_request.order_info
        )
        
        # Add parsing errors to failed parts if any
        if parsing_errors:
            failed_parts.extend([f"Parsing error: {error}" for error in parsing_errors])
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_activity(
                action="imported",
                entity_type="csv",
                entity_name=f"CSV import: {len(success_parts)} parts",
                details={
                    "parser_type": csv_request.parser_type,
                    "total_parts": len(parts_data),
                    "success_count": len(success_parts),
                    "failed_count": len(failed_parts),
                    "success_parts": success_parts[:10],  # First 10 for brevity
                    "has_parsing_errors": len(parsing_errors) > 0
                },
                user=current_user,
                request=http_request
            )
        except Exception as e:
            logger.warning(f"Failed to log CSV import activity: {e}")
        
        logger.info(f"CSV import completed: {len(success_parts)} success, {len(failed_parts)} failed")
        
        # Create enrichment task if enrichment is enabled and we have successful imports
        response_data = {
            "total_rows": len(parts_data),
            "successful_imports": len(success_parts),
            "failed_imports": len(failed_parts),
            "imported_parts": success_parts,
            "failures": failed_parts
        }
        
        if enable_enrichment and imported_part_ids:
            try:
                from MakerMatrix.services.task_service import create_csv_enrichment_task
                enrichment_task = await create_csv_enrichment_task(
                    imported_part_ids,
                    csv_request.parser_type,
                    current_user.id
                )
                response_data["enrichment_task_id"] = enrichment_task.id
                logger.info(f"Created enrichment task {enrichment_task.id} for {len(success_parts)} imported parts")
            except Exception as e:
                logger.error(f"Failed to create enrichment task: {e}")
                # Don't fail the entire import if enrichment task creation fails
        
        return ResponseSchema(
            status="success",
            message=f"CSV import completed: {len(success_parts)} parts imported successfully",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error importing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import CSV: {str(e)}")


@router.post("/parse")
async def parse_csv_only(
    request: CSVImportRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Parse CSV content into parts data without importing"""
    try:
        # Get user's enrichment settings
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        
        session = next(get_session())
        try:
            config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            
            if not config:
                config = CSVImportConfigModel(id="default")
                session.add(config)
                session.commit()
                session.refresh(config)
        finally:
            session.close()
        
        # Parse CSV with user's enrichment settings
        enable_enrichment = config.enable_enrichment and supports_enrichment(request.parser_type)
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type,
            enable_enrichment=enable_enrichment
        )
        
        return {
            "parts_data": parts_data,
            "errors": errors,
            "total_parts": len(parts_data)
        }
        
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV: {str(e)}")


@router.post("/extract-filename-info")
async def extract_filename_info(
    request: FilenameExtractionRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Extract order information from filename"""
    try:
        order_info = csv_import_service.extract_order_info_from_filename(request.filename)
        
        if order_info:
            return {
                "success": True,
                "order_info": order_info
            }
        else:
            return {
                "success": False,
                "message": "No order information could be extracted from filename"
            }
        
    except Exception as e:
        logger.error(f"Error extracting filename info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract filename info: {str(e)}")


@router.get("/parsers/{parser_type}/info", response_model=ResponseSchema[Dict[str, Any]])
async def get_parser_info(parser_type: str):
    """Get information about a specific parser"""
    try:
        parser = csv_import_service.get_parser(parser_type)
        if not parser:
            raise HTTPException(status_code=404, detail=f"Parser '{parser_type}' not found")
        
        parser_info = parser.get_info()
        return ResponseSchema(
            status="success",
            message=f"Parser information for {parser_type} retrieved successfully",
            data=parser_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parser info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get parser information")


# CSV Import Configuration Routes
class CSVConfigRequest(BaseModel):
    download_datasheets: bool = True
    download_images: bool = True
    overwrite_existing_files: bool = False
    download_timeout_seconds: int = 30
    show_progress: bool = True
    enable_enrichment: bool = True
    auto_create_enrichment_tasks: bool = True


@router.get("/config", response_model=ResponseSchema[Dict[str, Any]])
async def get_csv_import_config(
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Get CSV import configuration"""
    try:
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        
        session = next(get_session())
        try:
            config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            
            if not config:
                # Create default config
                config = CSVImportConfigModel(id="default")
                session.add(config)
                session.commit()
                session.refresh(config)
            
            return ResponseSchema(
                status="success",
                message="CSV import configuration retrieved successfully",
                data=config.to_dict()
            )
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting CSV config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get CSV configuration")


@router.put("/config", response_model=ResponseSchema[Dict[str, Any]])
async def update_csv_import_config(
    config_request: CSVConfigRequest,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Update CSV import configuration"""
    try:
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        
        session = next(get_session())
        try:
            config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            
            if not config:
                config = CSVImportConfigModel(id="default")
            
            # Update configuration
            config.download_datasheets = config_request.download_datasheets
            config.download_images = config_request.download_images
            config.overwrite_existing_files = config_request.overwrite_existing_files
            config.download_timeout_seconds = config_request.download_timeout_seconds
            config.show_progress = config_request.show_progress
            config.enable_enrichment = config_request.enable_enrichment
            config.auto_create_enrichment_tasks = config_request.auto_create_enrichment_tasks
            
            session.add(config)
            session.commit()
            session.refresh(config)
            
            return ResponseSchema(
                status="success",
                message="CSV configuration updated successfully",
                data=config.to_dict()
            )
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error updating CSV config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update CSV configuration")


@router.get("/import/progress")
async def get_import_progress(
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Get current import progress"""
    try:
        # Check the active import service first, then fall back to the singleton
        global _active_import_service
        logger.info(f"📊 Progress poll - Active service: {_active_import_service is not None}")
        
        if _active_import_service:
            progress = _active_import_service.get_current_progress()
            logger.info(f"📊 Active service progress: {progress is not None}")
        else:
            progress = csv_import_service.get_current_progress()
            logger.info(f"📊 Singleton service progress: {progress is not None}")
            
        if progress:
            logger.info(f"📊 Returning progress: {progress}")
            return progress
        else:
            logger.info(f"📊 No progress available")
            return {"message": "No import in progress"}
            
    except Exception as e:
        logger.error(f"Error getting import progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get import progress")


@router.post("/import/with-progress", response_model=ResponseSchema[Dict[str, Any]])
async def import_csv_with_progress(
    request: CSVImportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Import CSV with progress tracking and download options"""
    try:
        # Get current configuration
        from MakerMatrix.database.db import get_session
        from sqlmodel import select
        
        session = next(get_session())
        try:
            config = session.exec(
                select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
            ).first()
            
            if not config:
                config = CSVImportConfigModel(id="default")
                session.add(config)
                session.commit()
                session.refresh(config)
        finally:
            session.close()
        
        # Create new service instance with downloads disabled during parsing
        config_dict = config.to_dict()
        parsing_config = config_dict.copy()
        parsing_config['download_datasheets'] = False  # Disable during parsing
        parsing_config['download_images'] = False      # Disable during parsing
        
        import_service = CSVImportService(download_config=parsing_config)
        
        # Parse CSV with user's enrichment settings (no downloads during this phase)
        enable_enrichment = config.enable_enrichment and supports_enrichment(request.parser_type)
        parts_data, parsing_errors = import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type,
            enable_enrichment=enable_enrichment
        )
        
        # Now create the import service with the real config for actual import
        import_service_for_import = CSVImportService(download_config=config_dict)
        
        # Store reference for progress tracking
        global _active_import_service
        _active_import_service = import_service_for_import
        
        if not parts_data:
            return ResponseSchema(
                status="success",
                message="CSV import with progress completed with no valid parts found",
                data={
                    "message": "Import initiated with no valid parts found",
                    "total_rows": 0,
                    "successful_imports": 0,
                    "failed_imports": 1
                }
            )
        
        # Progress callback function that updates the shared service state
        def progress_callback(progress):
            logger.info(f"Progress callback received: {type(progress)}")
            # Handle both dict and ImportProgressModel
            if hasattr(progress, 'processed_parts'):
                # ImportProgressModel object
                processed = progress.processed_parts
                total = progress.total_parts
                operation = progress.current_operation
                logger.info(f"✅ PROGRESS UPDATE: {processed}/{total} - {operation}")
                import_service_for_import.current_progress = progress
            else:
                # Dictionary format
                processed = progress.get('processed_parts', 0)
                total = progress.get('total_parts', 0)
                operation = progress.get('current_operation', 'Processing...')
                logger.info(f"✅ PROGRESS UPDATE (dict): {processed}/{total} - {operation}")
                # Convert dict to ImportProgressModel for consistency
                from MakerMatrix.models.csv_import_config_model import ImportProgressModel
                progress_model = ImportProgressModel(
                    total_parts=total,
                    processed_parts=processed,
                    successful_parts=progress.get('successful_parts', 0),
                    failed_parts=progress.get('failed_parts', 0),
                    current_operation=operation,
                    is_downloading=progress.get('is_downloading', False),
                    download_progress=progress.get('download_progress'),
                    start_time=progress.get('start_time', '')
                )
                import_service_for_import.current_progress = progress_model
        
        # Import parts with progress tracking using the service with real config
        part_service = PartService()
        success_parts, failed_parts = await import_service_for_import.import_parts_with_progress(
            parts_data,
            part_service,
            request.order_info,
            progress_callback
        )
        
        # Add parsing errors to failed parts if any
        if parsing_errors:
            failed_parts.extend([f"Parsing error: {error}" for error in parsing_errors])
        
        logger.info(f"CSV import with progress completed: {len(success_parts)} success, {len(failed_parts)} failed")
        
        # Clear progress when import is complete
        import_service_for_import.current_progress = None
        _active_import_service = None
        
        return ResponseSchema(
            status="success",
            message=f"CSV import with progress completed: {len(success_parts)} parts imported successfully",
            data={
                "message": f"Import completed with progress tracking: {len(success_parts)} successful, {len(failed_parts)} failed",
                "total_rows": len(parts_data),
                "successful_imports": len(success_parts),
                "failed_imports": len(failed_parts)
            }
        )
        
    except Exception as e:
        logger.error(f"Error importing CSV with progress: {e}", exc_info=True)
        # Clear progress on error
        if 'import_service_for_import' in locals():
            import_service_for_import.current_progress = None
        _active_import_service = None
        # Return more detailed error for debugging
        error_details = f"CSV import failed: {str(e)}"
        if hasattr(e, '__cause__') and e.__cause__:
            error_details += f" (Caused by: {str(e.__cause__)})"
        raise HTTPException(status_code=500, detail=error_details)


# File upload endpoints for CSV and XLS files
@router.post("/preview-file", response_model=ResponseSchema[Dict[str, Any]])
async def preview_file(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Preview uploaded CSV or XLS file and detect file type"""
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type {file_extension}. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        
        # For CSV files, convert to string and use existing preview
        if file_extension == '.csv':
            csv_content = content.decode('utf-8')
            preview_data = csv_import_service.preview_csv(csv_content)
        else:
            # For XLS files, use the new XLS parser
            try:
                from MakerMatrix.parsers.mouser_xls_parser import MouserXLSParser
                xls_parser = MouserXLSParser()
                
                if xls_parser.can_parse(file_content=content, filename=file.filename):
                    preview_data = xls_parser.get_preview_data(file_content=content)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported XLS file format")
            except ImportError:
                raise HTTPException(status_code=400, detail="XLS parser not available - CSV only mode")
        
        # Transform to match expected format
        response_data = {
            "detected_parser": preview_data.get("detected_parser") or preview_data.get("detected_type"),
            "preview_rows": preview_data.get("preview_rows", []),
            "headers": preview_data.get("headers", []),
            "total_rows": preview_data.get("total_rows", 0),
            "is_supported": preview_data.get("is_supported", False),
            "validation_errors": preview_data.get("validation_errors", []),
            "file_format": preview_data.get("file_format", "csv")
        }
        
        return ResponseSchema(
            status="success",
            message="File preview generated successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")


@router.post("/import-file", response_model=ResponseSchema[Dict[str, Any]])
async def import_file(
    http_request: Request,
    file: UploadFile = File(...),
    parser_type: str = None,
    order_number: str = "",
    order_date: str = "",
    notes: str = "",
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Import uploaded CSV or XLS file"""
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type {file_extension}. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Prepare order info - will add supplier based on parser type below
        order_info = {
            "order_number": order_number,
            "order_date": order_date if order_date else None,
            "notes": notes
        }
        
        if file_extension == '.csv':
            # For CSV files, convert to string and use existing import
            csv_content = content.decode('utf-8')
            
            # Parse CSV to parts data
            # Use auto-detection if no parser_type specified
            effective_parser_type = parser_type
            if not effective_parser_type:
                effective_parser_type = csv_import_service.detect_csv_type(csv_content)
                if not effective_parser_type:
                    raise HTTPException(status_code=400, detail="Could not auto-detect CSV format")
            
            # Set supplier based on parser type
            parser_to_supplier = {
                'lcsc': 'LCSC',
                'digikey': 'DigiKey', 
                'mouser': 'Mouser'
            }
            order_info['supplier'] = parser_to_supplier.get(effective_parser_type, 'Unknown')
            
            # Get user's enrichment settings
            from MakerMatrix.database.db import get_session
            from sqlmodel import select
            
            session = next(get_session())
            try:
                config = session.exec(
                    select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
                ).first()
                
                if not config:
                    config = CSVImportConfigModel(id="default")
                    session.add(config)
                    session.commit()
                    session.refresh(config)
            finally:
                session.close()
            
            # Parse with user's enrichment settings
            enable_enrichment = config.enable_enrichment and supports_enrichment(effective_parser_type)
            parts_data, parsing_errors = csv_import_service.parse_csv_to_parts(
                csv_content, 
                effective_parser_type,
                enable_enrichment=enable_enrichment
            )
            
            if parsing_errors:
                logger.warning(f"CSV parsing errors: {parsing_errors}")
            
            if not parts_data:
                result = {
                    "total_rows": 0,
                    "successful_imports": 0,
                    "failed_imports": 1,
                    "imported_parts": [],
                    "failures": ["No valid parts data found in CSV"]
                }
            else:
                # Import parts with order tracking
                part_service = PartService()
                success_parts, failed_parts, imported_part_ids = await csv_import_service.import_parts_with_order(
                    parts_data,
                    part_service,
                    order_info
                )
                
                # Add parsing errors to failed parts if any
                if parsing_errors:
                    failed_parts.extend([f"Parsing error: {error}" for error in parsing_errors])
                
                result = {
                    "total_rows": len(parts_data),
                    "successful_imports": len(success_parts),
                    "failed_imports": len(failed_parts),
                    "imported_parts": success_parts,
                    "failures": failed_parts
                }
                
                # Create enrichment task if enrichment is enabled and we have successful imports
                logger.info(f"Enrichment check: enable_enrichment={enable_enrichment}, imported_part_ids_count={len(imported_part_ids) if imported_part_ids else 0}")
                if enable_enrichment and imported_part_ids:
                    try:
                        logger.info(f"Creating enrichment task for {len(imported_part_ids)} parts with supplier {effective_parser_type}")
                        from MakerMatrix.services.task_service import create_csv_enrichment_task
                        enrichment_task = await create_csv_enrichment_task(
                            imported_part_ids,
                            effective_parser_type,
                            current_user.id
                        )
                        result["enrichment_task_id"] = enrichment_task.id
                        logger.info(f"✅ Created enrichment task {enrichment_task.id} for {len(success_parts)} imported parts")
                    except Exception as e:
                        logger.error(f"❌ Failed to create enrichment task: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Don't fail the entire import if enrichment task creation fails
                else:
                    logger.info(f"❌ No enrichment task created: enable_enrichment={enable_enrichment}, imported_part_ids={bool(imported_part_ids)}")
        else:
            # For XLS files, use the new XLS parser
            try:
                from MakerMatrix.parsers.mouser_xls_parser import MouserXLSParser
                xls_parser = MouserXLSParser()
                
                if not xls_parser.can_parse(file_content=content, filename=file.filename):
                    raise HTTPException(status_code=400, detail="Unsupported XLS file format")
                
                # Parse the XLS file
                parsing_result = xls_parser.parse_content(content)
                
                if not parsing_result.success:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Failed to parse XLS file: {parsing_result.error_message}"
                    )
                
                # Convert XLS parsing result to parts_data format
                parts_data = parsing_result.parts
            except ImportError:
                raise HTTPException(status_code=400, detail="XLS parser not available - CSV only mode")
            
            # Merge parser's order_info with user-provided order_info
            # User input takes precedence, parser provides defaults for missing values
            if hasattr(locals(), 'parsing_result') and parsing_result.order_info:
                # Start with parser-extracted order_info as defaults
                merged_order_info = parsing_result.order_info.copy()
                
                # Override with user-provided values (user input has priority)
                if order_number:  # User provided order_number
                    merged_order_info['order_number'] = order_number
                if order_date:   # User provided order_date
                    merged_order_info['order_date'] = order_date
                if notes:        # User provided notes
                    merged_order_info['notes'] = notes
                
                order_info = merged_order_info
            
            # Ensure supplier is set for XLS files (default to Mouser for .xls files)
            if 'supplier' not in order_info or not order_info['supplier']:
                order_info['supplier'] = 'Mouser'
            
            if not parts_data:
                result = {
                    "total_rows": parsing_result.total_rows,
                    "successful_imports": 0,
                    "failed_imports": 1,
                    "imported_parts": [],
                    "failures": ["No valid parts data found in XLS file"]
                }
            else:
                # Import parts with order tracking using the same method as CSV
                part_service = PartService()
                success_parts, failed_parts, imported_part_ids = await csv_import_service.import_parts_with_order(
                    parts_data,
                    part_service,
                    order_info
                )
                
                # Add any XLS parsing errors to failed parts
                if parsing_result.errors:
                    failed_parts.extend([f"XLS parsing error: {error}" for error in parsing_result.errors])
                
                result = {
                    "total_rows": parsing_result.total_rows,
                    "successful_imports": len(success_parts),
                    "failed_imports": len(failed_parts),
                    "imported_parts": success_parts,
                    "failures": failed_parts
                }
        
        # Log activity
        try:
            from MakerMatrix.services.activity_service import get_activity_service
            activity_service = get_activity_service()
            await activity_service.log_activity(
                action="imported",
                entity_type="file_upload",
                entity_name=f"File import ({file_extension.upper()}): {result.get('successful_imports', 0)} parts",
                details={
                    "filename": file.filename,
                    "file_type": file_extension,
                    "parser_type": parser_type,
                    "total_parts": result.get('total_rows', 0),
                    "success_count": result.get('successful_imports', 0),
                    "failed_count": result.get('failed_imports', 0),
                    "order_info": order_info
                },
                user=current_user,
                request=http_request
            )
        except Exception as e:
            logger.warning(f"Failed to log file import activity: {e}")
        
        logger.info(f"File import completed: {result.get('successful_imports', 0)} success, {result.get('failed_imports', 0)} failed")
        
        return ResponseSchema(
            status="success",
            message=f"File import completed: {result.get('successful_imports', 0)} parts imported successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import file: {str(e)}")


# ============================================================================
# ENRICHMENT INTEGRATION ENDPOINTS
# ============================================================================

@router.get("/parsers/enrichment-capabilities", response_model=ResponseSchema[Dict[str, Dict[str, Any]]])
async def get_all_parser_enrichment_capabilities():
    """
    Get enrichment capabilities for all CSV parsers
    
    Returns comprehensive information about which parsers support enrichment
    and what capabilities are available for each.
    """
    try:
        mappings = get_all_enrichment_mappings()
        return ResponseSchema(
            status="success",
            message=f"Retrieved enrichment capabilities for {len(mappings)} parsers",
            data=mappings
        )
    except Exception as e:
        logger.error(f"Error getting parser enrichment capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsers/{parser_type}/enrichment-capabilities", response_model=ResponseSchema[Dict[str, Any]])
async def get_parser_enrichment_capabilities(parser_type: str):
    """
    Get enrichment capabilities for a specific parser type
    
    Args:
        parser_type: CSV parser type (e.g., 'lcsc', 'digikey', 'mouser')
        
    Returns:
        Parser enrichment information including capabilities and client availability
    """
    try:
        if not supports_enrichment(parser_type):
            return ResponseSchema(
                status="success",
                message=f"Parser '{parser_type}' does not support enrichment",
                data={
                    "parser_type": parser_type,
                    "supports_enrichment": False,
                    "capabilities": [],
                    "client_available": False
                }
            )
        
        capabilities = get_enrichment_capabilities(parser_type)
        validation = validate_mapping(parser_type)
        
        return ResponseSchema(
            status="success",
            message=f"Retrieved enrichment capabilities for {parser_type}",
            data={
                "parser_type": parser_type,
                "supports_enrichment": True,
                "capabilities": capabilities,
                "client_available": validation['client_exists'],
                "validation": validation
            }
        )
    except Exception as e:
        logger.error(f"Error getting enrichment capabilities for {parser_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parsers/{parser_type}/validate-enrichment", response_model=ResponseSchema[Dict[str, Any]])
async def validate_parser_enrichment_mapping(parser_type: str):
    """
    Validate that a parser's enrichment mapping is working correctly
    
    Args:
        parser_type: CSV parser type to validate
        
    Returns:
        Detailed validation results including parser existence, client availability, etc.
    """
    try:
        validation_result = validate_mapping(parser_type)
        
        status = "success" if not validation_result['errors'] else "warning"
        message = f"Validation completed for {parser_type}"
        if validation_result['errors']:
            message += f" with {len(validation_result['errors'])} issues"
        
        return ResponseSchema(
            status=status,
            message=message,
            data=validation_result
        )
    except Exception as e:
        logger.error(f"Error validating enrichment mapping for {parser_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enrichment/supported-parsers", response_model=ResponseSchema[List[str]])
async def get_enrichment_supported_parsers():
    """
    Get list of parser types that support enrichment
    
    Returns:
        List of parser type names that have working enrichment clients
    """
    try:
        from MakerMatrix.services.parser_client_registry import parser_client_registry
        supported_parsers = parser_client_registry.get_parsers_with_enrichment()
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(supported_parsers)} parsers with enrichment support",
            data=supported_parsers
        )
    except Exception as e:
        logger.error(f"Error getting enrichment-supported parsers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENHANCED IMPORT SERVICE ENDPOINTS
# ============================================================================

@router.post("/enhanced-import", response_model=ResponseSchema[Dict[str, Any]])
async def enhanced_import_with_enrichment(
    request: EnhancedImportRequest,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """
    Enhanced CSV/XLS import with intelligent enrichment and rate limiting
    
    This endpoint provides:
    - Rate-limited supplier API calls
    - Intelligent enrichment queue management
    - Real-time WebSocket progress updates
    - Priority-based task processing
    """
    try:
        logger.info(f"Starting enhanced import for user {current_user.username}")
        
        # Convert priority string to enum
        priority_map = {
            "low": EnrichmentPriority.LOW,
            "normal": EnrichmentPriority.NORMAL,
            "high": EnrichmentPriority.HIGH,
            "urgent": EnrichmentPriority.URGENT
        }
        enrichment_priority = priority_map.get(request.enrichment_priority.lower(), EnrichmentPriority.NORMAL)
        
        # Initialize enhanced import service
        enhanced_service = EnhancedImportService()
        
        # TODO: Set WebSocket broadcast function when WebSocket manager is available
        # enhanced_service.set_websocket_broadcast(websocket_manager.broadcast)
        
        # Perform enhanced import
        result = await enhanced_service.import_csv_with_enrichment(
            csv_content=request.csv_content,
            file_path=request.file_path,
            parser_type=request.parser_type,
            order_info=request.order_info,
            enrichment_enabled=request.enrichment_enabled,
            enrichment_priority=enrichment_priority,
            user_id=current_user.id
        )
        
        return ResponseSchema(
            status="success" if result["success"] else "error",
            message=result["message"],
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Enhanced import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced import failed: {str(e)}")


@router.post("/enhanced-import-file", response_model=ResponseSchema[Dict[str, Any]])
async def enhanced_import_file_with_enrichment(
    file: UploadFile = File(...),
    parser_type: Optional[str] = None,
    order_number: Optional[str] = None,
    order_date: Optional[str] = None,
    notes: Optional[str] = None,
    enrichment_enabled: bool = True,
    enrichment_priority: str = "normal",
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """
    Enhanced file upload import with enrichment
    
    Supports CSV and XLS files with automatic format detection and enrichment.
    """
    try:
        logger.info(f"Starting enhanced file import: {file.filename}")
        
        # Validate file type
        allowed_extensions = ['.csv', '.xls', '.xlsx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type {file_extension}. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await file.read()
        csv_content = None
        
        # Convert to CSV format if needed
        if file_extension == '.csv':
            csv_content = content.decode('utf-8')
        else:
            # Convert XLS to CSV
            try:
                import pandas as pd
                df = pd.read_excel(content)
                csv_content = df.to_csv(index=False)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process XLS file: {str(e)}")
        
        # Prepare order info
        order_info = {}
        if order_number:
            order_info["order_number"] = order_number
        if order_date:
            order_info["order_date"] = order_date
        if notes:
            order_info["notes"] = notes
        
        # Convert priority
        priority_map = {
            "low": EnrichmentPriority.LOW,
            "normal": EnrichmentPriority.NORMAL,
            "high": EnrichmentPriority.HIGH,
            "urgent": EnrichmentPriority.URGENT
        }
        enrichment_priority_enum = priority_map.get(enrichment_priority.lower(), EnrichmentPriority.NORMAL)
        
        # Initialize enhanced import service
        enhanced_service = EnhancedImportService()
        
        # Perform enhanced import
        result = await enhanced_service.import_csv_with_enrichment(
            csv_content=csv_content,
            parser_type=parser_type,
            order_info=order_info,
            enrichment_enabled=enrichment_enabled,
            enrichment_priority=enrichment_priority_enum,
            user_id=current_user.id
        )
        
        return ResponseSchema(
            status="success" if result["success"] else "error",
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced file import failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced file import failed: {str(e)}")


@router.post("/bulk-enrich", response_model=ResponseSchema[Dict[str, Any]])
async def bulk_enrich_existing_parts(
    request: BulkEnrichmentRequest,
    current_user: UserModel = Depends(require_permission("parts:update"))
):
    """
    Bulk enrich existing parts with supplier data
    
    Uses the intelligent enrichment queue with rate limiting to enrich
    multiple parts without overwhelming supplier APIs.
    """
    try:
        logger.info(f"Starting bulk enrichment for {len(request.part_ids)} parts")
        
        if len(request.part_ids) > 100:
            raise HTTPException(status_code=400, detail="Bulk enrichment limited to 100 parts at once")
        
        # Convert priority
        priority_map = {
            "low": EnrichmentPriority.LOW,
            "normal": EnrichmentPriority.NORMAL,
            "high": EnrichmentPriority.HIGH,
            "urgent": EnrichmentPriority.URGENT
        }
        enrichment_priority = priority_map.get(request.priority.lower(), EnrichmentPriority.NORMAL)
        
        # Initialize enhanced import service
        enhanced_service = EnhancedImportService()
        
        # Perform bulk enrichment
        result = await enhanced_service.enrich_existing_parts(
            part_ids=request.part_ids,
            supplier_name=request.supplier_name,
            capabilities=request.capabilities,
            priority=enrichment_priority
        )
        
        return ResponseSchema(
            status="success" if result["success"] else "error",
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk enrichment failed: {str(e)}")


@router.get("/enrichment-queue/status", response_model=ResponseSchema[Dict[str, Any]])
async def get_enrichment_queue_status(
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """
    Get current enrichment queue status across all suppliers
    """
    try:
        enhanced_service = EnhancedImportService()
        result = await enhanced_service.get_enrichment_queue_status()
        
        return ResponseSchema(
            status="success" if result["success"] else "error",
            message="Retrieved enrichment queue status",
            data=result["data"] if result["success"] else {"error": result["message"]}
        )
        
    except Exception as e:
        logger.error(f"Failed to get enrichment queue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@router.post("/enrichment-queue/cancel", response_model=ResponseSchema[Dict[str, Any]])
async def cancel_enrichment_tasks(
    task_ids: List[str],
    current_user: UserModel = Depends(require_permission("parts:update"))
):
    """
    Cancel specific enrichment tasks
    """
    try:
        enhanced_service = EnhancedImportService()
        result = await enhanced_service.cancel_enrichment_tasks(task_ids)
        
        return ResponseSchema(
            status="success" if result["success"] else "error",
            message=result["message"],
            data=result["data"]
        )
        
    except Exception as e:
        logger.error(f"Failed to cancel enrichment tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel tasks: {str(e)}")