from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Dict, Any, List
from pydantic import BaseModel
from MakerMatrix.services.csv_import_service import csv_import_service, CSVImportService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.order_service import order_service
from MakerMatrix.dependencies.auth import require_permission
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
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
    parser_type: str
    order_info: Dict[str, Any]

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


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported CSV file types"""
    try:
        types = csv_import_service.get_supported_types()
        return {"supported_types": types}
    except Exception as e:
        logger.error(f"Error getting supported types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get supported types")


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv(
    request: CSVPreviewRequest,
    current_user: UserModel = Depends(require_permission("parts:read"))
):
    """Preview CSV content and detect file type"""
    try:
        preview_data = csv_import_service.preview_csv(request.csv_content)
        
        return CSVPreviewResponse(
            detected_type=preview_data.get("detected_type"),
            type_info=preview_data.get("type_info", "Unknown"),
            headers=preview_data.get("headers", []),
            preview_rows=preview_data.get("preview_rows", []),
            parsed_preview=preview_data.get("parsed_preview", []),
            total_rows=preview_data.get("total_rows", 0),
            is_supported=preview_data.get("is_supported", False),
            validation_errors=preview_data.get("validation_errors", []),
            error=preview_data.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error previewing CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview CSV: {str(e)}")


@router.post("/import", response_model=CSVImportResponse)
async def import_csv(
    csv_request: CSVImportRequest,
    http_request: Request,
    current_user: UserModel = Depends(require_permission("parts:create"))
):
    """Import parts from CSV file with order tracking"""
    try:
        # Parse CSV to parts data
        parts_data, parsing_errors = csv_import_service.parse_csv_to_parts(
            csv_request.csv_content, 
            csv_request.parser_type
        )
        
        if parsing_errors:
            logger.warning(f"CSV parsing errors: {parsing_errors}")
        
        if not parts_data:
            return CSVImportResponse(
                success_parts=[],
                failed_parts=["No valid parts data found in CSV"],
                order_id=None
            )
        
        # Import parts with order tracking
        part_service = PartService()
        success_parts, failed_parts = await csv_import_service.import_parts_with_order(
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
        
        return CSVImportResponse(
            success_parts=success_parts,
            failed_parts=failed_parts,
            order_id=None  # Could include order ID in future if needed
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
        parts_data, errors = csv_import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type
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


@router.get("/parsers/{parser_type}/info")
async def get_parser_info(parser_type: str):
    """Get information about a specific parser"""
    try:
        parser = csv_import_service.get_parser(parser_type)
        if not parser:
            raise HTTPException(status_code=404, detail=f"Parser '{parser_type}' not found")
        
        return parser.get_info()
        
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


@router.get("/config")
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
            
            return config.to_dict()
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error getting CSV config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get CSV configuration")


@router.put("/config")
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
            
            session.add(config)
            session.commit()
            session.refresh(config)
            
            return {"message": "Configuration updated successfully", "config": config.to_dict()}
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


@router.post("/import/with-progress", response_model=CSVImportResponse)
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
        
        # Parse CSV (no downloads during this phase)
        parts_data, parsing_errors = import_service.parse_csv_to_parts(
            request.csv_content, 
            request.parser_type
        )
        
        # Now create the import service with the real config for actual import
        import_service_for_import = CSVImportService(download_config=config_dict)
        
        # Store reference for progress tracking
        global _active_import_service
        _active_import_service = import_service_for_import
        
        if not parts_data:
            return CSVImportResponse(
                success_parts=[],
                failed_parts=["No valid parts data found in CSV"],
                order_id=None
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
        
        return CSVImportResponse(
            success_parts=success_parts,
            failed_parts=failed_parts,
            order_id=None
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