"""
Task handlers for enrichment operations.
These handlers integrate the enhanced parsers with the task system.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from MakerMatrix.models.task_models import TaskModel, TaskStatus, TaskType
from MakerMatrix.parsers.enhanced_parser import EnhancedParser, parser_registry
from MakerMatrix.parsers.supplier_capabilities import CapabilityType, find_suppliers_with_capability
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService


logger = logging.getLogger(__name__)


class EnrichmentTaskHandlers:
    """Handlers for enrichment task operations"""
    
    def __init__(self, part_repository: PartRepository, part_service: PartService):
        self.part_repository = part_repository
        self.part_service = part_service
    
    async def handle_part_enrichment(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """
        Handle comprehensive part enrichment using multiple capabilities.
        
        Input data should contain:
        - part_id: ID of the part to enrich
        - supplier: Preferred supplier (optional)
        - capabilities: List of capabilities to use (optional, defaults to recommended)
        - force_refresh: Whether to re-enrich already enriched data (default: False)
        """
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            preferred_supplier = input_data.get('supplier')
            requested_capabilities = input_data.get('capabilities', [])
            force_refresh = input_data.get('force_refresh', False)
            
            if not part_id:
                raise ValueError("part_id is required for part enrichment")
            
            # Get the part
            part = await self.part_repository.get_by_id(part_id)
            if not part:
                raise ValueError(f"Part not found: {part_id}")
            
            # Determine which supplier to use
            supplier = preferred_supplier or part.supplier or part.part_vendor
            if not supplier:
                raise ValueError("No supplier specified for part enrichment")
            
            # Get the parser for this supplier
            parser = parser_registry.get_parser(supplier)
            if not parser:
                raise ValueError(f"No parser available for supplier: {supplier}")
            
            # Determine capabilities to use
            if requested_capabilities:
                capabilities = [CapabilityType(cap) for cap in requested_capabilities]
            else:
                capabilities = parser.get_recommended_enrichment_capabilities()
            
            if not capabilities:
                return {"message": "No enrichment capabilities available for this supplier"}
            
            # Filter out capabilities already completed (unless force_refresh)
            if not force_refresh:
                existing_enrichments = part.additional_properties.get('enrichment_results', {})
                capabilities = [cap for cap in capabilities if cap.value not in existing_enrichments]
            
            if not capabilities:
                return {"message": "Part already enriched with requested capabilities"}
            
            # Perform enrichment
            results = await parser.perform_enrichment_task(
                capabilities, 
                part.part_number, 
                progress_callback
            )
            
            # Update part with enrichment results
            enrichment_data = {}
            successful_enrichments = []
            failed_enrichments = []
            
            for capability_name, result in results.items():
                if result.success and result.data:
                    enrichment_data[capability_name] = result.data
                    successful_enrichments.append(capability_name)
                    
                    # Update specific part fields based on capability type
                    await self._update_part_from_enrichment(part, capability_name, result.data)
                else:
                    failed_enrichments.append({
                        "capability": capability_name,
                        "error": result.error
                    })
            
            # Save enrichment results to part
            if not part.additional_properties:
                part.additional_properties = {}
            
            if 'enrichment_results' not in part.additional_properties:
                part.additional_properties['enrichment_results'] = {}
            
            part.additional_properties['enrichment_results'].update(enrichment_data)
            part.additional_properties['last_enrichment'] = datetime.utcnow().isoformat()
            
            # Update the part
            await self.part_repository.update(part)
            
            return {
                "part_id": part_id,
                "supplier": supplier,
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments,
                "enrichment_summary": parser.get_enrichment_summary()
            }
            
        except Exception as e:
            logger.error(f"Error in part enrichment task: {e}", exc_info=True)
            raise
    
    async def handle_datasheet_fetch(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """Handle datasheet fetching for a specific part"""
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            part_number = input_data.get('part_number')
            supplier = input_data.get('supplier')
            
            if not (part_id or part_number):
                raise ValueError("Either part_id or part_number is required")
            
            # Get part if part_id provided
            part = None
            if part_id:
                part = await self.part_repository.get_by_id(part_id)
                if not part:
                    raise ValueError(f"Part not found: {part_id}")
                part_number = part.part_number
                supplier = supplier or part.supplier or part.part_vendor
            
            if not supplier:
                raise ValueError("Supplier is required for datasheet fetch")
            
            # Find suppliers that support datasheet fetching
            if supplier not in find_suppliers_with_capability(CapabilityType.FETCH_DATASHEET):
                raise ValueError(f"Supplier {supplier} does not support datasheet fetching")
            
            # Get parser and fetch datasheet
            parser = parser_registry.get_parser(supplier)
            if not parser:
                raise ValueError(f"No parser available for supplier: {supplier}")
            
            if progress_callback:
                await progress_callback(25, "Fetching datasheet information")
            
            result = await parser.fetch_datasheet(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing datasheet result")
            
            # Update part if part_id was provided
            if part and result.success and result.data:
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['datasheet_url'] = result.data.get('url')
                await self.part_repository.update(part)
            
            if progress_callback:
                await progress_callback(100, "Datasheet fetch completed")
            
            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "datasheet_data": result.data if result.success else None,
                "error": result.error if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in datasheet fetch task: {e}", exc_info=True)
            raise
    
    async def handle_image_fetch(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """Handle image fetching for a specific part"""
        try:
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            part_number = input_data.get('part_number')
            supplier = input_data.get('supplier')
            
            if not (part_id or part_number):
                raise ValueError("Either part_id or part_number is required")
            
            # Get part if part_id provided
            part = None
            if part_id:
                part = await self.part_repository.get_by_id(part_id)
                if not part:
                    raise ValueError(f"Part not found: {part_id}")
                part_number = part.part_number
                supplier = supplier or part.supplier or part.part_vendor
            
            if not supplier:
                raise ValueError("Supplier is required for image fetch")
            
            # Check if supplier supports image fetching
            if supplier not in find_suppliers_with_capability(CapabilityType.FETCH_IMAGE):
                raise ValueError(f"Supplier {supplier} does not support image fetching")
            
            # Get parser and fetch image
            parser = parser_registry.get_parser(supplier)
            if not parser:
                raise ValueError(f"No parser available for supplier: {supplier}")
            
            if progress_callback:
                await progress_callback(25, "Fetching image information")
            
            result = await parser.fetch_image(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing image result")
            
            # Update part if part_id was provided
            if part and result.success and result.data:
                part.image_url = result.data.get('url')
                await self.part_repository.update(part)
            
            if progress_callback:
                await progress_callback(100, "Image fetch completed")
            
            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "image_data": result.data if result.success else None,
                "error": result.error if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in image fetch task: {e}", exc_info=True)
            raise
    
    async def handle_bulk_enrichment(self, task: TaskModel, progress_callback=None) -> Dict[str, Any]:
        """
        Handle bulk enrichment for multiple parts.
        
        Input data should contain:
        - part_ids: List of part IDs to enrich
        - supplier_filter: Optional supplier filter
        - capabilities: List of capabilities to use
        - batch_size: Number of parts to process in parallel (default: 5)
        """
        try:
            input_data = task.get_input_data()
            part_ids = input_data.get('part_ids', [])
            supplier_filter = input_data.get('supplier_filter')
            requested_capabilities = input_data.get('capabilities', [])
            batch_size = input_data.get('batch_size', 5)
            
            if not part_ids:
                raise ValueError("part_ids list is required for bulk enrichment")
            
            total_parts = len(part_ids)
            processed_parts = 0
            successful_enrichments = []
            failed_enrichments = []
            
            # Process parts in batches
            for i in range(0, total_parts, batch_size):
                batch = part_ids[i:i + batch_size]
                batch_tasks = []
                
                for part_id in batch:
                    # Create enrichment task for each part
                    enrichment_data = {
                        'part_id': part_id,
                        'capabilities': requested_capabilities
                    }
                    if supplier_filter:
                        enrichment_data['supplier'] = supplier_filter
                    
                    # Create a mock task for the part enrichment
                    part_task = TaskModel(
                        task_type=TaskType.PART_ENRICHMENT,
                        name=f"Part Enrichment - {part_id}",
                        status=TaskStatus.RUNNING
                    )
                    part_task.set_input_data(enrichment_data)
                    
                    batch_tasks.append(self.handle_part_enrichment(part_task))
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for j, result in enumerate(batch_results):
                    part_id = batch[j]
                    if isinstance(result, Exception):
                        failed_enrichments.append({
                            "part_id": part_id,
                            "error": str(result)
                        })
                    else:
                        successful_enrichments.append({
                            "part_id": part_id,
                            "result": result
                        })
                    
                    processed_parts += 1
                    
                    # Update progress
                    if progress_callback:
                        progress = int((processed_parts / total_parts) * 100)
                        await progress_callback(
                            progress, 
                            f"Processed {processed_parts}/{total_parts} parts"
                        )
            
            return {
                "total_parts": total_parts,
                "successful_count": len(successful_enrichments),
                "failed_count": len(failed_enrichments),
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments
            }
            
        except Exception as e:
            logger.error(f"Error in bulk enrichment task: {e}", exc_info=True)
            raise
    
    async def _update_part_from_enrichment(self, part, capability_name: str, enrichment_data: Dict[str, Any]):
        """Update part fields based on enrichment results"""
        try:
            if capability_name == CapabilityType.FETCH_DATASHEET.value:
                if 'url' in enrichment_data:
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['datasheet_url'] = enrichment_data['url']
            
            elif capability_name == CapabilityType.FETCH_IMAGE.value:
                if 'url' in enrichment_data:
                    part.image_url = enrichment_data['url']
            
            elif capability_name == CapabilityType.FETCH_PRICING.value:
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['pricing_data'] = enrichment_data
                
                # Update price if available
                if 'unit_price' in enrichment_data:
                    part.price = float(enrichment_data['unit_price'])
            
            elif capability_name == CapabilityType.FETCH_SPECIFICATIONS.value:
                if not part.additional_properties:
                    part.additional_properties = {}
                part.additional_properties['specifications'] = enrichment_data
                
                # Update specific fields if available
                if 'manufacturer' in enrichment_data:
                    part.manufacturer = enrichment_data['manufacturer']
                if 'package' in enrichment_data:
                    if not part.additional_properties:
                        part.additional_properties = {}
                    part.additional_properties['package'] = enrichment_data['package']
            
            elif capability_name == CapabilityType.ENRICH_BASIC_INFO.value:
                # Update basic fields from enrichment
                if 'description' in enrichment_data:
                    part.description = enrichment_data['description']
                if 'manufacturer' in enrichment_data:
                    part.manufacturer = enrichment_data['manufacturer']
                if 'manufacturer_part_number' in enrichment_data:
                    part.manufacturer_part_number = enrichment_data['manufacturer_part_number']
                
                # Update additional properties
                if not part.additional_properties:
                    part.additional_properties = {}
                for key, value in enrichment_data.items():
                    if key not in ['description', 'manufacturer', 'manufacturer_part_number']:
                        part.additional_properties[key] = value
            
        except Exception as e:
            logger.error(f"Error updating part from enrichment {capability_name}: {e}", exc_info=True)


# Task handler registry
ENRICHMENT_TASK_HANDLERS = {
    TaskType.PART_ENRICHMENT: 'handle_part_enrichment',
    TaskType.DATASHEET_FETCH: 'handle_datasheet_fetch',
    TaskType.IMAGE_FETCH: 'handle_image_fetch',
    TaskType.PRICING_FETCH: 'handle_pricing_fetch',
    TaskType.STOCK_FETCH: 'handle_stock_fetch',
    TaskType.SPECIFICATIONS_FETCH: 'handle_specifications_fetch',
    TaskType.BULK_ENRICHMENT: 'handle_bulk_enrichment',
}


def get_enrichment_task_handler(task_type: TaskType) -> Optional[str]:
    """Get the handler method name for a task type"""
    return ENRICHMENT_TASK_HANDLERS.get(task_type)


# Standalone handler functions for compatibility with tests
async def handle_part_enrichment(task: TaskModel, progress_callback=None) -> Dict[str, Any]:
    """Standalone function for part enrichment - compatibility wrapper"""
    try:
        from MakerMatrix.database.db import get_session
        from MakerMatrix.parsers.enhanced_parser import get_enhanced_parser
        
        if not task.input_data:
            return {
                "success": False,
                "error": "Missing required input data"
            }
        
        part_id = task.input_data.get('part_id')
        supplier = task.input_data.get('supplier')
        capabilities = task.input_data.get('capabilities', [])
        
        if not part_id:
            return {
                "success": False,
                "error": "Missing part_id in input data"
            }
        
        if not capabilities:
            return {
                "success": False,
                "error": "No capabilities specified for enrichment"
            }
        
        if progress_callback:
            await progress_callback(progress=0, step="Starting part enrichment")
        
        # Get part from database
        session = next(get_session())
        try:
            from MakerMatrix.models.models import PartModel
            part = session.get(PartModel, part_id)
            if not part:
                return {
                    "success": False,
                    "error": f"Part not found: {part_id}"
                }
            
            if progress_callback:
                await progress_callback(progress=20, step=f"Found part: {part.name}")
            
            # Get enhanced parser for supplier
            parser = get_enhanced_parser(supplier)
            if not parser:
                return {
                    "success": False,
                    "error": f"No parser available for supplier: {supplier}"
                }
            
            if progress_callback:
                await progress_callback(progress=30, step="Initializing parser")
            
            # Perform enrichment
            enrichment_results = await parser.perform_enrichment_task(
                capabilities, part, progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback(progress=90, step="Processing enrichment results")
            
            # Process results
            successful_count = 0
            failed_count = 0
            
            for capability, result in enrichment_results.items():
                if result.get('success', False):
                    successful_count += 1
                else:
                    failed_count += 1
            
            if progress_callback:
                await progress_callback(progress=100, step="Enrichment completed")
            
            return {
                "success": True,
                "enrichment_summary": {
                    "part_id": part_id,
                    "supplier": supplier,
                    "capabilities_requested": capabilities,
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "results": enrichment_results
                }
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in part enrichment: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def handle_datasheet_fetch(task: TaskModel, progress_callback=None) -> Dict[str, Any]:
    """Standalone function for datasheet fetch - compatibility wrapper"""
    try:
        from MakerMatrix.database.db import get_session
        from MakerMatrix.parsers.enhanced_parser import get_enhanced_parser
        
        if not task.input_data:
            return {
                "success": False,
                "error": "Missing required input data"
            }
        
        part_id = task.input_data.get('part_id')
        supplier = task.input_data.get('supplier')
        
        if not part_id:
            return {
                "success": False,
                "error": "Missing part_id in input data"
            }
        
        if progress_callback:
            await progress_callback(progress=0, step="Starting datasheet fetch")
        
        # Get part from database
        session = next(get_session())
        try:
            from MakerMatrix.models.models import PartModel
            part = session.get(PartModel, part_id)
            if not part:
                return {
                    "success": False,
                    "error": f"Part not found: {part_id}"
                }
            
            if progress_callback:
                await progress_callback(progress=20, step=f"Found part: {part.name}")
            
            # Get enhanced parser for supplier
            parser = get_enhanced_parser(supplier)
            if not parser:
                return {
                    "success": False,
                    "error": f"No parser available for supplier: {supplier}"
                }
            
            if progress_callback:
                await progress_callback(progress=40, step="Fetching datasheet")
            
            # Fetch datasheet
            result = await parser.fetch_datasheet(part, progress_callback=progress_callback)
            
            if progress_callback:
                await progress_callback(progress=100, step="Datasheet fetch completed")
            
            return result
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in datasheet fetch: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def handle_image_fetch(task: TaskModel, progress_callback=None) -> Dict[str, Any]:
    """Standalone function for image fetch - compatibility wrapper"""
    try:
        from MakerMatrix.database.db import get_session
        from MakerMatrix.parsers.enhanced_parser import get_enhanced_parser
        
        if not task.input_data:
            return {
                "success": False,
                "error": "Missing required input data"
            }
        
        part_id = task.input_data.get('part_id')
        supplier = task.input_data.get('supplier')
        
        if not part_id:
            return {
                "success": False,
                "error": "Missing part_id in input data"
            }
        
        if progress_callback:
            await progress_callback(progress=0, step="Starting image fetch")
        
        # Get part from database
        session = next(get_session())
        try:
            from MakerMatrix.models.models import PartModel
            part = session.get(PartModel, part_id)
            if not part:
                return {
                    "success": False,
                    "error": f"Part not found: {part_id}"
                }
            
            if progress_callback:
                await progress_callback(progress=20, step=f"Found part: {part.name}")
            
            # Get enhanced parser for supplier
            parser = get_enhanced_parser(supplier)
            if not parser:
                return {
                    "success": False,
                    "error": f"No parser available for supplier: {supplier}"
                }
            
            if progress_callback:
                await progress_callback(progress=40, step="Fetching image")
            
            # Fetch image
            result = await parser.fetch_image(part, progress_callback=progress_callback)
            
            if progress_callback:
                await progress_callback(progress=100, step="Image fetch completed")
            
            return result
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in image fetch: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def handle_bulk_enrichment(task: TaskModel, progress_callback=None) -> Dict[str, Any]:
    """Standalone function for bulk enrichment - compatibility wrapper"""
    try:
        from MakerMatrix.database.db import get_session
        from MakerMatrix.parsers.enhanced_parser import get_enhanced_parser
        
        if not task.input_data:
            return {
                "success": False,
                "error": "Missing required input data"
            }
        
        part_ids = task.input_data.get('part_ids', [])
        supplier = task.input_data.get('supplier')
        capabilities = task.input_data.get('capabilities', [])
        
        if not part_ids:
            return {
                "success": False,
                "error": "No parts specified for bulk enrichment"
            }
        
        if not capabilities:
            return {
                "success": False,
                "error": "No capabilities specified for enrichment"
            }
        
        if progress_callback:
            await progress_callback(progress=0, step=f"Starting bulk enrichment for {len(part_ids)} parts")
        
        # Get enhanced parser for supplier
        parser = get_enhanced_parser(supplier)
        if not parser:
            return {
                "success": False,
                "error": f"No parser available for supplier: {supplier}"
            }
        
        session = next(get_session())
        try:
            from MakerMatrix.models.models import PartModel
            part_results = {}
            successful_parts = 0
            failed_parts = 0
            
            for i, part_id in enumerate(part_ids):
                try:
                    if progress_callback:
                        progress = int(10 + (i / len(part_ids)) * 80)
                        await progress_callback(
                            progress=progress, 
                            step=f"Processing part {i+1}/{len(part_ids)}: {part_id}"
                        )
                    
                    # Get part from database
                    part = session.get(PartModel, part_id)
                    if not part:
                        part_results[part_id] = {
                            "success": False,
                            "error": f"Part not found: {part_id}"
                        }
                        failed_parts += 1
                        continue
                    
                    # Perform enrichment for this part
                    enrichment_results = await parser.perform_enrichment_task(
                        capabilities, part, progress_callback=None  # Don't pass progress for individual parts
                    )
                    
                    # Check if enrichment was successful
                    part_successful = any(
                        result.get('success', False) 
                        for result in enrichment_results.values()
                    )
                    
                    part_results[part_id] = {
                        "success": part_successful,
                        "part_name": part.name,
                        "enrichment_results": enrichment_results
                    }
                    
                    if part_successful:
                        successful_parts += 1
                    else:
                        failed_parts += 1
                        
                except Exception as e:
                    logger.error(f"Error enriching part {part_id}: {e}", exc_info=True)
                    part_results[part_id] = {
                        "success": False,
                        "error": str(e)
                    }
                    failed_parts += 1
            
            if progress_callback:
                await progress_callback(progress=100, step="Bulk enrichment completed")
            
            return {
                "success": True,
                "total_parts": len(part_ids),
                "successful_parts": successful_parts,
                "failed_parts": failed_parts,
                "part_results": part_results,
                "supplier": supplier,
                "capabilities": capabilities
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in bulk enrichment: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }