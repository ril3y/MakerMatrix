"""
Part Enrichment Task Handler
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from MakerMatrix.tasks.base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel, TaskStatus, UpdateTaskRequest
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import engine
from sqlmodel import Session

logger = logging.getLogger(__name__)


class PartEnrichmentTask(BaseTask):
    """Handler for part enrichment operations"""
    
    @property
    def task_type(self) -> str:
        return "part_enrichment"
    
    @property
    def name(self) -> str:
        return "Part Enrichment"
    
    @property
    def description(self) -> str:
        return "Enrich part data from supplier APIs with comprehensive information"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute part enrichment task"""
        try:
            # Update task status to running
            await self._update_task_progress(task, 0, "Initializing enrichment...")
            
            # Get task input data
            input_data = task.get_input_data()
            part_id = input_data.get('part_id')
            supplier = input_data.get('supplier', 'Unknown')
            
            if not part_id:
                raise ValueError("part_id is required for part enrichment")
            
            await self._update_task_progress(task, 20, f"Looking up part {part_id}...")
            
            # Create database session for this task execution
            with Session(engine) as session:
                # Get the part using repository
                try:
                    part = PartRepository.get_part_by_id(session, part_id)
                except Exception as e:
                    if "not found" in str(e).lower():
                        raise ValueError(f"Part not found: {part_id}")
                    else:
                        raise
                
                await self._update_task_progress(task, 40, f"Found part: {part.part_name}")
                
                # For now, let's do a simple enrichment simulation
                # In the future, this would integrate with the enhanced parsers
                await self._update_task_progress(task, 60, f"Enriching data from {supplier}...")
                
                # Simulate enrichment work
                await asyncio.sleep(2)
                
                await self._update_task_progress(task, 80, "Updating part data...")
                
                # Update part with enrichment timestamp
                # Create a new dict to ensure SQLModel detects the change
                current_props = part.additional_properties or {}
                updated_props = current_props.copy()
                updated_props['last_enrichment'] = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'supplier': supplier,
                    'task_id': task.id
                }
                
                # Assign the new dict to force SQLModel to detect the change
                part.additional_properties = updated_props
                
                # Save changes
                session.add(part)
                session.commit()
            
            # Final progress update
            await self._update_task_progress(task, 100, "Enrichment completed successfully")
            
            return {
                'status': 'success',
                'part_id': part_id,
                'supplier': supplier,
                'enriched_fields': ['last_enrichment'],
                'message': f"Successfully enriched part {part_id} from {supplier}"
            }
                
        except Exception as e:
            error_msg = f"Part enrichment failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._update_task_progress(task, task.progress_percentage, f"Error: {str(e)}")
            raise
    
    async def _update_task_progress(self, task: TaskModel, percentage: int, step: str):
        """Update task progress"""
        if self.task_service:
            try:
                update_request = UpdateTaskRequest(
                    progress_percentage=percentage,
                    current_step=step
                )
                await self.task_service.update_task(task.id, update_request)
            except Exception as e:
                logger.warning(f"Failed to update task progress: {e}")


class DatasheetFetchTask(BaseTask):
    """Handler for datasheet fetching operations"""
    
    @property
    def task_type(self) -> str:
        return "datasheet_fetch"
    
    @property
    def name(self) -> str:
        return "Datasheet Fetch"
    
    @property
    def description(self) -> str:
        return "Fetch datasheet documents for parts from supplier APIs"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute datasheet fetch task"""
        try:
            await self._update_task_progress(task, 0, "Starting datasheet fetch...")
            
            with Session(engine) as session:
                part_repository = PartRepository(engine)
                part_service = PartService()
                enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
                
                async def progress_callback(percentage: int, step: str):
                    await self._update_task_progress(task, percentage, step)
                
                result = await enrichment_handlers.handle_datasheet_fetch(task, progress_callback)
                session.commit()
            
            await self._update_task_progress(task, 100, "Datasheet fetch completed")
            return result
                
        except Exception as e:
            error_msg = f"Datasheet fetch failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._update_task_progress(task, task.progress_percentage, f"Error: {str(e)}")
            raise
    
    async def _update_task_progress(self, task: TaskModel, percentage: int, step: str):
        """Update task progress"""
        if self.task_service:
            try:
                update_request = UpdateTaskRequest(
                    progress_percentage=percentage,
                    current_step=step
                )
                await self.task_service.update_task(task.id, update_request)
            except Exception as e:
                logger.warning(f"Failed to update task progress: {e}")


class ImageFetchTask(BaseTask):
    """Handler for image fetching operations"""
    
    @property
    def task_type(self) -> str:
        return "image_fetch"
    
    @property
    def name(self) -> str:
        return "Image Fetch"
    
    @property
    def description(self) -> str:
        return "Fetch product images for parts from supplier APIs"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute image fetch task"""
        try:
            await self._update_task_progress(task, 0, "Starting image fetch...")
            
            with Session(engine) as session:
                part_repository = PartRepository(engine)
                part_service = PartService()
                enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
                
                async def progress_callback(percentage: int, step: str):
                    await self._update_task_progress(task, percentage, step)
                
                result = await enrichment_handlers.handle_image_fetch(task, progress_callback)
                session.commit()
            
            await self._update_task_progress(task, 100, "Image fetch completed")
            return result
                
        except Exception as e:
            error_msg = f"Image fetch failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._update_task_progress(task, task.progress_percentage, f"Error: {str(e)}")
            raise
    
    async def _update_task_progress(self, task: TaskModel, percentage: int, step: str):
        """Update task progress"""
        if self.task_service:
            try:
                update_request = UpdateTaskRequest(
                    progress_percentage=percentage,
                    current_step=step
                )
                await self.task_service.update_task(task.id, update_request)
            except Exception as e:
                logger.warning(f"Failed to update task progress: {e}")


class BulkEnrichmentTask(BaseTask):
    """Handler for bulk enrichment operations"""
    
    @property
    def task_type(self) -> str:
        return "bulk_enrichment"
    
    @property
    def name(self) -> str:
        return "Bulk Enrichment"
    
    @property
    def description(self) -> str:
        return "Enrich multiple parts in parallel from supplier APIs"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute bulk enrichment task"""
        try:
            await self._update_task_progress(task, 0, "Starting bulk enrichment...")
            
            with Session(engine) as session:
                part_repository = PartRepository(engine)
                part_service = PartService()
                enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
                
                async def progress_callback(percentage: int, step: str):
                    await self._update_task_progress(task, percentage, step)
                
                result = await enrichment_handlers.handle_bulk_enrichment(task, progress_callback)
                session.commit()
            
            await self._update_task_progress(task, 100, "Bulk enrichment completed")
            return result
                
        except Exception as e:
            error_msg = f"Bulk enrichment failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self._update_task_progress(task, task.progress_percentage, f"Error: {str(e)}")
            raise
    
    async def _update_task_progress(self, task: TaskModel, percentage: int, step: str):
        """Update task progress"""
        if self.task_service:
            try:
                update_request = UpdateTaskRequest(
                    progress_percentage=percentage,
                    current_step=step
                )
                await self.task_service.update_task(task.id, update_request)
            except Exception as e:
                logger.warning(f"Failed to update task progress: {e}")