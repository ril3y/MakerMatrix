"""
Enhanced Import Service

Comprehensive import service that integrates all modern MakerMatrix systems:
- Rate limiting for supplier API protection
- Intelligent enrichment queue management
- Real-time WebSocket progress updates
- New consolidated supplier system
- CSV/XLS file processing with automatic enrichment
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from MakerMatrix.database.db import engine
from MakerMatrix.services.rate_limit_service import RateLimitService
from MakerMatrix.services.system.enrichment_queue_manager import EnrichmentQueueManager, EnrichmentPriority
from MakerMatrix.schemas.websocket_schemas import (
    create_import_progress_message, 
    create_enrichment_progress_message,
    create_notification_message
)
from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.suppliers.base import SupplierCapability

from MakerMatrix.models.models import PartModel
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class EnhancedImportService:
    """
    Enhanced import service with intelligent enrichment and rate limiting
    """
    
    def __init__(self):
        self.rate_limit_service = RateLimitService(engine)
        self.enrichment_queue = EnrichmentQueueManager(self.rate_limit_service)
        self.part_service = PartService()
        self.part_repository = PartRepository(engine)
        
        # WebSocket broadcasting function (to be set by calling code)
        self._websocket_broadcast = None
        
        logger.info("Enhanced import service initialized with rate limiting and enrichment queue")
    
    def set_websocket_broadcast(self, broadcast_func):
        """Set WebSocket broadcast function for real-time updates"""
        self._websocket_broadcast = broadcast_func
        self.enrichment_queue.set_websocket_broadcast(broadcast_func)
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """Internal method to broadcast WebSocket messages"""
        if self._websocket_broadcast:
            try:
                await self._websocket_broadcast(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast WebSocket message: {e}")
    
    async def import_csv_with_enrichment(
        self,
        csv_content: str = None,
        file_path: str = None,
        parser_type: str = None,
        order_info: Dict[str, Any] = None,
        enrichment_enabled: bool = True,
        enrichment_priority: EnrichmentPriority = EnrichmentPriority.NORMAL,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Import CSV/XLS file with intelligent enrichment
        
        Args:
            csv_content: CSV content as string
            file_path: Path to CSV/XLS file to import
            parser_type: Override parser type detection
            order_info: Order metadata (number, date, notes)
            enrichment_enabled: Whether to perform enrichment
            enrichment_priority: Priority for enrichment tasks
            user_id: User performing the import
            
        Returns:
            Dictionary with import results and enrichment status
        """
        import_id = f"import_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Broadcast import start
            await self._broadcast_message(create_import_progress_message(
                import_id=import_id,
                progress_percentage=0,
                current_step="Starting CSV import",
                parts_processed=0,
                total_parts=0
            ))
            
            # Step 1: Import CSV file
            logger.info(f"Starting enhanced CSV import with ID: {import_id}")
            
            import_result = await self._import_csv_data(
                csv_content=csv_content,
                file_path=file_path,
                parser_type=parser_type,
                order_info=order_info,
                import_id=import_id
            )
            
            if not import_result["success"]:
                await self._broadcast_message(create_notification_message(
                    title="Import Failed",
                    message=import_result["message"],
                    level="error"
                ))
                return import_result
            
            imported_parts = import_result["data"]["imported_parts"]
            total_parts = len(imported_parts)
            
            # Step 2: Queue enrichment tasks if enabled
            enrichment_results = []
            if enrichment_enabled and total_parts > 0:
                await self._broadcast_message(create_import_progress_message(
                    import_id=import_id,
                    progress_percentage=60,
                    current_step="Queuing enrichment tasks",
                    parts_processed=total_parts,
                    total_parts=total_parts
                ))
                
                enrichment_results = await self._queue_enrichment_tasks(
                    imported_parts, 
                    import_result["data"]["parser_type"],
                    enrichment_priority,
                    import_id
                )
            
            # Step 3: Complete import
            await self._broadcast_message(create_import_progress_message(
                import_id=import_id,
                progress_percentage=100,
                current_step="Import completed",
                parts_processed=total_parts,
                total_parts=total_parts
            ))
            
            # Final success notification
            await self._broadcast_message(create_notification_message(
                title="Import Completed",
                message=f"Successfully imported {total_parts} parts" + 
                        (f" with {len(enrichment_results)} enrichment tasks queued" if enrichment_enabled else ""),
                level="success"
            ))
            
            return {
                "success": True,
                "message": f"Successfully imported {total_parts} parts",
                "data": {
                    "import_id": import_id,
                    "imported_parts": total_parts,
                    "parser_type": import_result["data"]["parser_type"],
                    "order_created": import_result["data"].get("order_created", False),
                    "enrichment_enabled": enrichment_enabled,
                    "enrichment_tasks_queued": len(enrichment_results) if enrichment_enabled else 0,
                    "enrichment_results": enrichment_results if enrichment_enabled else []
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced import failed for {import_id}: {e}")
            await self._broadcast_message(create_notification_message(
                title="Import Error",
                message=f"Import failed: {str(e)}",
                level="error"
            ))
            
            return {
                "success": False,
                "message": f"Import failed: {str(e)}",
                "data": {"import_id": import_id, "error": str(e)}
            }
    
    async def _import_csv_data(
        self,
        csv_content: str = None,
        file_path: str = None,
        parser_type: str = None,
        order_info: Dict[str, Any] = None,
        import_id: str = None
    ) -> Dict[str, Any]:
        """Import CSV/file data using the supplier-based import system"""
        
        try:
            # Read file content if file_path provided
            if file_path:
                file_path_obj = Path(file_path)
                if file_path_obj.suffix.lower() in ['.xls', '.xlsx']:
                    # Handle Excel files
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    filename = file_path_obj.name
                else:
                    # Handle CSV files
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    filename = file_path_obj.name
            elif csv_content:
                # Handle CSV content as bytes
                file_content = csv_content.encode('utf-8')
                filename = "import.csv"
            else:
                raise ValueError("No file content provided")
            
            # Get supplier
            supplier_name = parser_type or "lcsc"  # Default to LCSC
            try:
                supplier = get_supplier(supplier_name)
            except Exception as e:
                raise ValueError(f"Unknown supplier: {supplier_name}")
            
            # Check if supplier supports imports
            if SupplierCapability.IMPORT_ORDERS not in supplier.get_capabilities():
                raise ValueError(f"{supplier_name} does not support file imports")
            
            # Check if supplier can handle this file
            if not supplier.can_import_file(filename, file_content):
                raise ValueError(f"{supplier_name} cannot import this file type")
            
            # Import using supplier
            file_type = filename.split('.')[-1].lower() if '.' in filename else 'csv'
            import_result = await supplier.import_order_file(file_content, file_type, filename)
            
            if not import_result.success:
                error_msg = import_result.error_message or "Import failed"
                logger.error(f"Import failed for {supplier_name}: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg,
                    "data": {}
                }
            
            if not import_result.parts:
                logger.warning(f"No parts found in {filename} for supplier {supplier_name}")
                return {
                    "success": False,
                    "message": "No parts found in file",
                    "data": {}
                }
            
            # Create parts in database using PartService
            part_ids = []
            failed_items = []
            
            for part_data in import_result.parts:
                try:
                    # Create part using PartService
                    result = await self.part_service.create_part_async(part_data)
                    if result.get("success"):
                        part_ids.append(result["data"]["id"])
                    else:
                        failed_items.append({
                            "part_data": part_data,
                            "error": result.get("message", "Unknown error")
                        })
                except Exception as e:
                    failed_items.append({
                        "part_data": part_data,
                        "error": str(e)
                    })
            
            # Format result similar to expected structure
            imported_parts = []
            for part_id in part_ids:
                try:
                    with Session(engine) as session:
                        part = self.part_repository.get_part_by_id(session, part_id)
                        imported_parts.append({
                            "id": part.id,
                            "part_name": part.part_name,
                            "part_number": part.part_number,
                            "supplier": part.supplier
                        })
                except ResourceNotFoundError:
                    continue
            
            return {
                "success": True,
                "message": f"Successfully imported {len(imported_parts)} parts",
                "data": {
                    "imported_parts": imported_parts,
                    "parser_type": supplier_name,
                    "failed_items": failed_items,
                    "order_created": False  # Could be enhanced later
                }
            }
            
        except Exception as e:
            logger.error(f"File import failed: {e}")
            return {
                "success": False,
                "message": f"File import failed: {str(e)}",
                "data": {}
            }
    
    async def _queue_enrichment_tasks(
        self,
        imported_parts: List[Dict[str, Any]],
        parser_type: str,
        priority: EnrichmentPriority,
        import_id: str
    ) -> List[Dict[str, Any]]:
        """Queue enrichment tasks for imported parts"""
        
        enrichment_results = []
        
        # Check if parser type supports enrichment
        supplier_name = parser_type.upper()  # e.g., 'lcsc' -> 'LCSC'
        
        # Get supplier and check enrichment capabilities
        try:
            supplier = get_supplier(parser_type)
            
            # Check if supplier supports enrichment capabilities
            enrichment_capabilities = [
                SupplierCapability.FETCH_PART_DETAILS,
                SupplierCapability.FETCH_DATASHEET,
                SupplierCapability.FETCH_PRICING_STOCK
            ]
            
            supports_enrichment = any(
                cap in supplier.get_capabilities() and supplier.is_capability_available(cap)
                for cap in enrichment_capabilities
            )
            
            if not supports_enrichment:
                logger.info(f"Parser type '{parser_type}' does not support enrichment - supplier not configured or enabled")
                
                # Notify user that enrichment is disabled due to supplier configuration
                await self._broadcast_message({
                    "type": "notification",
                    "data": {
                        "title": "Enrichment Disabled",
                        "message": f"Parts imported successfully, but enrichment is disabled because the {parser_type.upper()} supplier is not configured. To enable enrichment with additional part data, images, and datasheets, please configure the {parser_type.upper()} supplier in settings.",
                        "level": "warning",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                })
                
                return enrichment_results
                
        except Exception as e:
            logger.warning(f"Could not check enrichment support for '{parser_type}': {e}")
            return enrichment_results
        
        # Queue enrichment tasks for each part
        for i, part_data in enumerate(imported_parts):
            try:
                part_id = part_data.get("id")
                part_name = part_data.get("part_name", "Unknown")
                
                if not part_id:
                    continue
                
                # Determine capabilities for this supplier
                capabilities = ["fetch_datasheet", "fetch_image", "fetch_specifications"]
                
                # Queue the enrichment task
                task_id = await self.enrichment_queue.queue_part_enrichment(
                    part_id=part_id,
                    part_name=part_name,
                    supplier_name=supplier_name,
                    capabilities=capabilities,
                    priority=priority
                )
                
                enrichment_results.append({
                    "part_id": part_id,
                    "part_name": part_name,
                    "task_id": task_id,
                    "supplier": supplier_name,
                    "capabilities": capabilities,
                    "status": "queued"
                })
                
                # Broadcast enrichment progress
                await self._broadcast_message(create_enrichment_progress_message(
                    task_id=task_id,
                    part_id=part_id,
                    part_name=part_name,
                    supplier=supplier_name,
                    current_step="Queued for enrichment",
                    progress_percentage=0
                ))
                
            except Exception as e:
                logger.error(f"Failed to queue enrichment for part {part_data.get('part_name', 'unknown')}: {e}")
                enrichment_results.append({
                    "part_id": part_data.get("id"),
                    "part_name": part_data.get("part_name", "Unknown"),
                    "task_id": None,
                    "supplier": supplier_name,
                    "status": "failed",
                    "error": str(e)
                })
        
        logger.info(f"Queued {len([r for r in enrichment_results if r['status'] == 'queued'])} enrichment tasks for import {import_id}")
        
        return enrichment_results
    
    async def enrich_existing_parts(
        self,
        part_ids: List[str],
        supplier_name: str = None,
        capabilities: List[str] = None,
        priority: EnrichmentPriority = EnrichmentPriority.NORMAL
    ) -> Dict[str, Any]:
        """
        Enrich existing parts with supplier data
        
        Args:
            part_ids: List of part IDs to enrich
            supplier_name: Specific supplier to use (auto-detect if None)
            capabilities: Specific capabilities to use
            priority: Task priority
            
        Returns:
            Enrichment results dictionary
        """
        enrichment_id = f"enrich_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        try:
            logger.info(f"Starting bulk enrichment for {len(part_ids)} parts with ID: {enrichment_id}")
            
            results = []
            
            for i, part_id in enumerate(part_ids):
                try:
                    # Get part details using repository pattern
                    with Session(engine) as session:
                        try:
                            part = self.part_repository.get_part_by_id(session, part_id)
                        except ResourceNotFoundError:
                            continue
                    
                    # Auto-detect supplier if not provided
                    if not supplier_name:
                        # Try to determine supplier from part data
                        auto_supplier = self._auto_detect_supplier(part)
                        if not auto_supplier:
                            continue
                        supplier_name = auto_supplier
                    
                    # Use default capabilities if not provided
                    if not capabilities:
                        capabilities = ["fetch_datasheet", "fetch_image", "fetch_specifications"]
                    
                    # Queue enrichment task
                    task_id = await self.enrichment_queue.queue_part_enrichment(
                        part_id=part_id,
                        part_name=part.part_name,
                        supplier_name=supplier_name,
                        capabilities=capabilities,
                        priority=priority
                    )
                    
                    results.append({
                        "part_id": part_id,
                        "part_name": part.part_name,
                        "task_id": task_id,
                        "supplier": supplier_name,
                        "capabilities": capabilities,
                        "status": "queued"
                    })
                    
                    # Broadcast progress
                    progress = int((i + 1) / len(part_ids) * 100)
                    await self._broadcast_message(create_enrichment_progress_message(
                        task_id=task_id,
                        part_id=part_id,
                        part_name=part.part_name,
                        supplier=supplier_name,
                        current_step=f"Queued for enrichment ({i+1}/{len(part_ids)})",
                        progress_percentage=progress
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to queue enrichment for part {part_id}: {e}")
                    results.append({
                        "part_id": part_id,
                        "task_id": None,
                        "status": "failed",
                        "error": str(e)
                    })
            
            success_count = len([r for r in results if r["status"] == "queued"])
            
            await self._broadcast_message(create_notification_message(
                title="Bulk Enrichment Queued",
                message=f"Successfully queued {success_count} parts for enrichment",
                level="success"
            ))
            
            return {
                "success": True,
                "message": f"Queued {success_count} parts for enrichment",
                "data": {
                    "enrichment_id": enrichment_id,
                    "total_parts": len(part_ids),
                    "queued_successfully": success_count,
                    "results": results
                }
            }
            
        except Exception as e:
            logger.error(f"Bulk enrichment failed for {enrichment_id}: {e}")
            await self._broadcast_message(create_notification_message(
                title="Enrichment Error",
                message=f"Bulk enrichment failed: {str(e)}",
                level="error"
            ))
            
            return {
                "success": False,
                "message": f"Bulk enrichment failed: {str(e)}",
                "data": {"enrichment_id": enrichment_id, "error": str(e)}
            }
    
    def _auto_detect_supplier(self, part: PartModel) -> Optional[str]:
        """Auto-detect supplier for a part based on part data"""
        
        # Check supplier field first
        if part.supplier:
            supplier_upper = part.supplier.upper()
            if supplier_upper in ["LCSC", "MOUSER", "DIGIKEY"]:
                return supplier_upper
        
        # Check additional properties for supplier hints
        if part.additional_properties:
            props = part.additional_properties
            
            # Look for supplier-specific identifiers
            if any(key.lower().startswith('lcsc') for key in props.keys()):
                return "LCSC"
            elif any(key.lower().startswith('mouser') for key in props.keys()):
                return "MOUSER"
            elif any(key.lower().startswith('digikey') for key in props.keys()):
                return "DIGIKEY"
        
        # Default fallback
        return None
    
    async def get_import_status(self, import_id: str) -> Dict[str, Any]:
        """Get status of an import operation"""
        
        # For now, return basic status - could be enhanced with persistent tracking
        return {
            "import_id": import_id,
            "status": "completed",  # Would need persistent storage for real tracking
            "message": "Import status tracking not yet implemented with persistent storage"
        }
    
    async def get_enrichment_queue_status(self) -> Dict[str, Any]:
        """Get current enrichment queue status"""
        
        try:
            stats = self.enrichment_queue.get_queue_statistics()
            
            return {
                "success": True,
                "data": {
                    "total_queues": len(stats),
                    "queue_details": stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return {
                "success": False,
                "message": f"Failed to get queue status: {str(e)}"
            }
    
    async def cancel_enrichment_tasks(self, task_ids: List[str]) -> Dict[str, Any]:
        """Cancel enrichment tasks"""
        
        try:
            results = []
            
            for task_id in task_ids:
                try:
                    success = self.enrichment_queue.cancel_task(task_id)
                    results.append({
                        "task_id": task_id,
                        "cancelled": success,
                        "status": "cancelled" if success else "not_found"
                    })
                except Exception as e:
                    results.append({
                        "task_id": task_id,
                        "cancelled": False,
                        "status": "error",
                        "error": str(e)
                    })
            
            cancelled_count = len([r for r in results if r["cancelled"]])
            
            return {
                "success": True,
                "message": f"Cancelled {cancelled_count}/{len(task_ids)} tasks",
                "data": {
                    "cancelled_count": cancelled_count,
                    "total_requested": len(task_ids),
                    "results": results
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel tasks: {e}")
            return {
                "success": False,
                "message": f"Failed to cancel tasks: {str(e)}"
            }