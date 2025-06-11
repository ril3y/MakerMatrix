"""
Part Enrichment Task Handler
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from MakerMatrix.tasks.base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel, TaskStatus, UpdateTaskRequest
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.database.db import get_session

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
            
            # Initialize repositories and services
            part_repository = PartRepository()
            part_service = PartService()
            enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
            
            # Create progress callback
            async def progress_callback(percentage: int, step: str):
                await self._update_task_progress(task, percentage, step)
            
            # Execute enrichment
            result = await enrichment_handlers.handle_part_enrichment(task, progress_callback)
            
            # Final progress update
            await self._update_task_progress(task, 100, "Enrichment completed successfully")
            
            return result
                
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
            
            part_repository = PartRepository()
            part_service = PartService()
            enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
            
            async def progress_callback(percentage: int, step: str):
                await self._update_task_progress(task, percentage, step)
            
            result = await enrichment_handlers.handle_datasheet_fetch(task, progress_callback)
            
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
            
            part_repository = PartRepository()
            part_service = PartService()
            enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
            
            async def progress_callback(percentage: int, step: str):
                await self._update_task_progress(task, percentage, step)
            
            result = await enrichment_handlers.handle_image_fetch(task, progress_callback)
            
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
            
            part_repository = PartRepository()
            part_service = PartService()
            enrichment_handlers = EnrichmentTaskHandlers(part_repository, part_service)
            
            async def progress_callback(percentage: int, step: str):
                await self._update_task_progress(task, percentage, step)
            
            result = await enrichment_handlers.handle_bulk_enrichment(task, progress_callback)
            
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