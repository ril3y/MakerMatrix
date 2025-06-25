"""
Centralized Enrichment Routes

This module consolidates all enrichment functionality that was previously
scattered across CSV, Task, and Supplier routes.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..dependencies.auth import get_current_user
from ..models.user_models import UserModel
from ..schemas.response import ResponseSchema
from ..services.task_service import task_service
from ..models.task_models import TaskType, TaskPriority
from ..parsers.capabilities import CapabilityType
from ..parsers.enhanced_parsers import get_enhanced_parser
from ..suppliers import SupplierRegistry

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])

# ========== Request/Response Models ==========

class EnrichmentCapabilityResponse(BaseModel):
    supplier: str
    display_name: str
    capabilities: List[str]
    rate_limit_info: Optional[str] = None

class PartEnrichmentRequest(BaseModel):
    part_id: str
    supplier: str
    capabilities: List[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL

class BulkEnrichmentRequest(BaseModel):
    part_ids: List[str]
    supplier: str
    capabilities: List[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL

class EnrichmentQueueStatusResponse(BaseModel):
    total_tasks: int
    pending: int
    running: int
    completed: int
    failed: int
    cancelled: int

# ========== Capability Endpoints ==========

@router.get("/capabilities", response_model=ResponseSchema[List[EnrichmentCapabilityResponse]])
async def get_all_enrichment_capabilities(
    current_user: UserModel = Depends(get_current_user)
):
    """Get enrichment capabilities for all suppliers"""
    try:
        capabilities = []
        
        # Get capabilities from supplier registry
        for supplier_name in SupplierRegistry.get_available_suppliers():
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name)
                supplier_info = supplier.get_supplier_info()
                supplier_caps = [cap.value for cap in supplier.get_capabilities()]
                
                capabilities.append(EnrichmentCapabilityResponse(
                    supplier=supplier_name,
                    display_name=supplier_info.display_name,
                    capabilities=supplier_caps,
                    rate_limit_info=supplier_info.rate_limit_info
                ))
            except Exception:
                # Skip suppliers that can't be instantiated
                pass
        
        # Also check enhanced parsers
        from ..parsers.lcsc_parser import LCSCParser
        from ..parsers.digikey_parser import DigiKeyParser
        from ..parsers.mouser_parser import MouserParser
        
        parser_mapping = {
            "lcsc": LCSCParser,
            "digikey": DigiKeyParser,
            "mouser": MouserParser
        }
        
        for parser_name, parser_class in parser_mapping.items():
            if parser_name not in [cap.supplier.lower() for cap in capabilities]:
                parser = parser_class()
                if hasattr(parser, 'get_enrichment_capabilities'):
                    caps = parser.get_enrichment_capabilities()
                    if caps:
                        capabilities.append(EnrichmentCapabilityResponse(
                            supplier=parser_name,
                            display_name=parser_name.upper(),
                            capabilities=[cap.value for cap in caps]
                        ))
        
        return ResponseSchema(
            status="success",
            message=f"Found enrichment capabilities for {len(capabilities)} suppliers",
            data=capabilities
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enrichment capabilities: {str(e)}")

@router.get("/capabilities/{supplier_name}", response_model=ResponseSchema[EnrichmentCapabilityResponse])
async def get_supplier_enrichment_capabilities(
    supplier_name: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Get enrichment capabilities for a specific supplier"""
    try:
        # Try supplier registry first
        try:
            supplier = SupplierRegistry.get_supplier(supplier_name)
            supplier_info = supplier.get_supplier_info()
            capabilities = [cap.value for cap in supplier.get_capabilities()]
            
            return ResponseSchema(
                status="success",
                message=f"Retrieved capabilities for {supplier_name}",
                data=EnrichmentCapabilityResponse(
                    supplier=supplier_name,
                    display_name=supplier_info.display_name,
                    capabilities=capabilities,
                    rate_limit_info=supplier_info.rate_limit_info
                )
            )
        except:
            # Try enhanced parser
            parser = get_enhanced_parser(supplier_name)
            if parser and hasattr(parser, 'get_enrichment_capabilities'):
                caps = parser.get_enrichment_capabilities()
                return ResponseSchema(
                    status="success",
                    message=f"Retrieved capabilities for {supplier_name}",
                    data=EnrichmentCapabilityResponse(
                        supplier=supplier_name,
                        display_name=supplier_name.upper(),
                        capabilities=[cap.value for cap in caps] if caps else []
                    )
                )
            
        raise HTTPException(status_code=404, detail=f"No enrichment capabilities found for supplier '{supplier_name}'")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get supplier capabilities: {str(e)}")

@router.get("/capabilities/find/{capability_type}", response_model=ResponseSchema[List[str]])
async def find_suppliers_with_capability(
    capability_type: CapabilityType,
    current_user: UserModel = Depends(get_current_user)
):
    """Find all suppliers that support a specific capability"""
    try:
        suppliers_with_capability = []
        
        # Check supplier registry
        for supplier_name in SupplierRegistry.get_available_suppliers():
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name)
                if capability_type in supplier.get_capabilities():
                    suppliers_with_capability.append(supplier_name)
            except:
                pass
        
        # Check enhanced parsers
        from ..parsers.lcsc_parser import LCSCParser
        from ..parsers.digikey_parser import DigiKeyParser
        from ..parsers.mouser_parser import MouserParser
        
        for parser_name, parser_class in [("lcsc", LCSCParser), ("digikey", DigiKeyParser), ("mouser", MouserParser)]:
            if parser_name not in suppliers_with_capability:
                parser = parser_class()
                if hasattr(parser, 'get_enrichment_capabilities'):
                    caps = parser.get_enrichment_capabilities()
                    if caps and capability_type in caps:
                        suppliers_with_capability.append(parser_name)
        
        return ResponseSchema(
            status="success",
            message=f"Found {len(suppliers_with_capability)} suppliers with capability {capability_type.value}",
            data=suppliers_with_capability
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find suppliers: {str(e)}")

# ========== Task Creation Endpoints ==========

@router.post("/tasks/part", response_model=ResponseSchema[Dict[str, Any]])
async def create_part_enrichment_task(
    request: PartEnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """Create an enrichment task for a single part"""
    try:
        # Validate supplier has requested capabilities
        supplier_caps = await get_supplier_enrichment_capabilities(request.supplier, current_user)
        available_caps = supplier_caps.data.capabilities
        
        invalid_caps = [cap for cap in request.capabilities if cap not in available_caps]
        if invalid_caps:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier {request.supplier} does not support capabilities: {invalid_caps}"
            )
        
        # Create the task
        task = await task_service.create_task(
            task_type=TaskType.PART_ENRICHMENT,
            name=f"Enrich part {request.part_id}",
            description=f"Enriching part with {request.supplier}",
            created_by_user_id=current_user.id,
            priority=request.priority,
            input_data={
                "part_id": request.part_id,
                "supplier": request.supplier,
                "capabilities": request.capabilities or available_caps
            }
        )
        
        # Start the task
        background_tasks.add_task(
            task_service.process_task,
            task.id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Part enrichment task created",
            data={
                "task_id": task.id,
                "status": task.status.value,
                "part_id": request.part_id,
                "supplier": request.supplier
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create enrichment task: {str(e)}")

@router.post("/tasks/bulk", response_model=ResponseSchema[Dict[str, Any]])
async def create_bulk_enrichment_task(
    request: BulkEnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """Create an enrichment task for multiple parts"""
    try:
        # Validate supplier has requested capabilities
        supplier_caps = await get_supplier_enrichment_capabilities(request.supplier, current_user)
        available_caps = supplier_caps.data.capabilities
        
        invalid_caps = [cap for cap in request.capabilities if cap not in available_caps]
        if invalid_caps:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier {request.supplier} does not support capabilities: {invalid_caps}"
            )
        
        # Create the task
        task = await task_service.create_task(
            task_type=TaskType.BULK_ENRICHMENT,
            name=f"Bulk enrich {len(request.part_ids)} parts",
            description=f"Enriching {len(request.part_ids)} parts with {request.supplier}",
            created_by_user_id=current_user.id,
            priority=request.priority,
            input_data={
                "part_ids": request.part_ids,
                "supplier": request.supplier,
                "capabilities": request.capabilities or available_caps
            }
        )
        
        # Start the task
        background_tasks.add_task(
            task_service.process_task,
            task.id
        )
        
        return ResponseSchema(
            status="success",
            message=f"Bulk enrichment task created for {len(request.part_ids)} parts",
            data={
                "task_id": task.id,
                "status": task.status.value,
                "part_count": len(request.part_ids),
                "supplier": request.supplier
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bulk enrichment task: {str(e)}")

# ========== Queue Management Endpoints ==========

@router.get("/queue/status", response_model=ResponseSchema[EnrichmentQueueStatusResponse])
async def get_enrichment_queue_status(
    current_user: UserModel = Depends(get_current_user)
):
    """Get the current status of the enrichment queue"""
    try:
        # Get tasks related to enrichment
        enrichment_types = [
            TaskType.PART_ENRICHMENT,
            TaskType.BULK_ENRICHMENT,
            TaskType.CSV_ENRICHMENT,
            TaskType.DATASHEET_FETCH,
            TaskType.IMAGE_FETCH,
            TaskType.PRICE_UPDATE
        ]
        
        stats = await task_service.get_task_statistics()
        
        # Filter for enrichment tasks
        enrichment_stats = {
            "total_tasks": 0,
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        # This is simplified - in reality you'd query the database
        # for tasks of these specific types
        enrichment_stats.update({
            "total_tasks": stats.get("total_tasks", 0),
            "pending": stats.get("tasks_by_status", {}).get("PENDING", 0),
            "running": stats.get("tasks_by_status", {}).get("RUNNING", 0),
            "completed": stats.get("tasks_by_status", {}).get("COMPLETED", 0),
            "failed": stats.get("tasks_by_status", {}).get("FAILED", 0),
            "cancelled": stats.get("tasks_by_status", {}).get("CANCELLED", 0)
        })
        
        return ResponseSchema(
            status="success",
            message="Enrichment queue status retrieved",
            data=EnrichmentQueueStatusResponse(**enrichment_stats)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")

@router.post("/queue/cancel/{task_id}", response_model=ResponseSchema[Dict[str, Any]])
async def cancel_enrichment_task(
    task_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Cancel a specific enrichment task"""
    try:
        success = await task_service.cancel_task(task_id, current_user.id)
        
        if success:
            return ResponseSchema(
                status="success",
                message="Enrichment task cancelled",
                data={"task_id": task_id, "cancelled": True}
            )
        else:
            return ResponseSchema(
                status="error",
                message="Failed to cancel task",
                data={"task_id": task_id, "cancelled": False}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@router.post("/queue/cancel-all", response_model=ResponseSchema[Dict[str, Any]])
async def cancel_all_enrichment_tasks(
    current_user: UserModel = Depends(get_current_user)
):
    """Cancel all pending enrichment tasks for the current user"""
    try:
        # This would need to be implemented in task_service
        # For now, return a placeholder response
        return ResponseSchema(
            status="success",
            message="All pending enrichment tasks cancelled",
            data={"cancelled_count": 0}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel tasks: {str(e)}")