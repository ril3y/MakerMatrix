from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, UploadFile, File
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import os
from MakerMatrix.services.csv_import_service import csv_import_service, CSVImportService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.order_service import order_service
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

# Enrichment request models moved to enrichment_routes.py

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


# Available suppliers endpoint removed - use /api/suppliers/ from supplier_routes.py instead


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
        
        # Task creation removed - use enrichment_routes.py to create enrichment tasks after import
        # The frontend should:
        # 1. Call this endpoint to import CSV
        # 2. Use returned part_ids to create enrichment task via /api/enrichment/tasks/bulk
        
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
            
            # Parse CSV data
            parts_data, parsing_errors = csv_import_service.parse_csv_to_parts(
                csv_content, 
                effective_parser_type,
                enable_enrichment=False  # Enrichment handled separately via enrichment routes
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
                
                # Task creation removed - use enrichment_routes.py to create enrichment tasks after import
                # Return part_ids so frontend can create enrichment task if desired
                result["imported_part_ids"] = imported_part_ids
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


# Enrichment endpoints moved to enrichment_routes.py