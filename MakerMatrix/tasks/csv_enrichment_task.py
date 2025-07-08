"""
CSV Enrichment Task - DEPRECATED: Use FileImportEnrichmentTask instead

This task is kept for backward compatibility but new code should use FileImportEnrichmentTask
which supports multiple file formats (CSV, XLS, etc.)
"""

import asyncio
import logging
from typing import Dict, Any
from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel, TaskType
from MakerMatrix.services.system.enrichment_coordinator_service import EnrichmentCoordinatorService
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.database.db import get_session

logger = logging.getLogger(__name__)


class CSVEnrichmentTask(BaseTask):
    """DEPRECATED: Task for enriching parts imported from CSV files using real supplier APIs
    
    Use FileImportEnrichmentTask instead which supports multiple file formats.
    """
    
    def __init__(self, task_service=None):
        super().__init__(task_service)
        # Initialize enrichment handlers
        self.part_service = PartService()
        self.enrichment_handlers = None  # Will be initialized when needed
    
    @property
    def task_type(self) -> str:
        return "csv_enrichment"
    
    @property
    def name(self) -> str:
        return "CSV Enrichment"
    
    @property
    def description(self) -> str:
        return "Enrich parts imported from CSV with real supplier data including datasheets, images, and specifications"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute CSV enrichment task using real supplier APIs"""
        input_data = self.get_input_data(task)
        enrichment_queue = input_data.get('enrichment_queue', [])
        
        if not enrichment_queue:
            await self.update_step(task, "No parts to enrich")
            return {"parts_processed": 0, "message": "No parts in enrichment queue"}
        
        # Initialize enrichment handlers
        if not self.enrichment_handlers:
            with next(get_session()) as session:
                part_repository = PartRepository(session.bind)
                self.enrichment_handlers = EnrichmentCoordinatorService(
                    part_repository=part_repository,
                    part_service=self.part_service
                )
        
        await self.update_progress(task, 10, f"Processing {len(enrichment_queue)} parts for real enrichment")
        
        enriched_parts = []
        failed_parts = []
        
        for i, item in enumerate(enrichment_queue):
            part_id = item.get('part_id')
            part_data = item.get('part_data', {})
            part_name = part_data.get('part_name', f'Part {i+1}')
            
            try:
                await self.update_progress(
                    task, 
                    int(10 + (i / len(enrichment_queue)) * 80),
                    f"Enriching part {i+1}/{len(enrichment_queue)}: {part_name}"
                )
                
                # Perform real enrichment using the enrichment handlers
                enrichment_result = await self._enrich_part_real(part_id, part_data, task)
                
                if enrichment_result.get('success', False):
                    enriched_parts.append({
                        'part_id': part_id,
                        'part_name': part_name,
                        'enrichment_result': enrichment_result
                    })
                    self.log_info(f"Successfully enriched part: {part_name}", task)
                else:
                    failed_parts.append({
                        'part_id': part_id,
                        'part_name': part_name,
                        'error': enrichment_result.get('error', 'Unknown enrichment error')
                    })
                    self.log_error(f"Failed to enrich part {part_name}: {enrichment_result.get('error', 'Unknown error')}", task)
                
            except Exception as e:
                self.log_error(f"Failed to enrich part {part_name}: {str(e)}", task, exc_info=True)
                failed_parts.append({
                    'part_id': part_id,
                    'part_name': part_name,
                    'error': str(e)
                })
        
        await self.update_progress(task, 100, "Enrichment completed")
        
        result = {
            "parts_processed": len(enriched_parts),
            "parts_failed": len(failed_parts),
            "enriched_parts": enriched_parts,
            "failed_parts": failed_parts
        }
        
        self.log_info(
            f"CSV enrichment complete: {len(enriched_parts)} successful, {len(failed_parts)} failed", 
            task
        )
        
        return result
    
    async def _enrich_part_real(self, part_id: str, part_data: Dict[str, Any], task: TaskModel) -> Dict[str, Any]:
        """Perform real enrichment for a single part using supplier APIs"""
        try:
            # Get enrichment source from part data
            enrichment_source = part_data.get('additional_properties', {}).get('enrichment_source')
            if not enrichment_source:
                return {'success': False, 'error': 'No enrichment source specified'}
            
            # Get available capabilities for this enrichment source
            available_capabilities = part_data.get('additional_properties', {}).get('available_capabilities', [])
            if not available_capabilities:
                return {'success': False, 'error': 'No enrichment capabilities available'}
            
            self.log_info(f"Starting enrichment for part {part_id} using {enrichment_source} with capabilities: {available_capabilities}", task)
            
            # Create a mock task for the part enrichment handler
            enrichment_task = TaskModel(
                task_type=TaskType.PART_ENRICHMENT,
                name=f"CSV Part Enrichment - {part_data.get('part_name', part_id)}",
                status=task.status
            )
            
            # Set input data for the enrichment task
            enrichment_input = {
                'part_id': part_id,
                'supplier': enrichment_source.upper(),
                'capabilities': available_capabilities,
                'force_refresh': True  # Force refresh since this is from CSV import
            }
            enrichment_task.set_input_data(enrichment_input)
            
            # Progress callback to track enrichment progress
            async def progress_callback(progress, message):
                self.log_info(f"Enrichment progress for {part_data.get('part_name', part_id)}: {progress}% - {message}", task)
            
            # Execute the real part enrichment
            enrichment_result = await self.enrichment_handlers.handle_part_enrichment(
                enrichment_task, 
                progress_callback=progress_callback
            )
            
            self.log_info(f"Enrichment completed for part {part_id}: {enrichment_result}", task)
            
            return {
                'success': True,
                'enrichment_result': enrichment_result,
                'capabilities_processed': available_capabilities
            }
            
        except Exception as e:
            error_msg = f"Error during real enrichment for part {part_id}: {str(e)}"
            self.log_error(error_msg, task, exc_info=True)
            return {'success': False, 'error': error_msg}