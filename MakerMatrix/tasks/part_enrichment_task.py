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
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.system.enrichment_coordinator_service import EnrichmentCoordinatorService
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
                
                # Capture part details while session is active to avoid DetachedInstanceError
                part_name = part.part_name
                await self._update_task_progress(task, 40, f"Found part: {part_name}")
                
                # Use the real enrichment task handlers
                await self._update_task_progress(task, 60, f"Enriching data from {supplier}...")
                
                # Create enrichment handlers with download configuration
                part_repository = PartRepository(engine)
                part_service = PartService()
                enrichment_handlers = EnrichmentCoordinatorService(part_repository, part_service)  # Gets CSV config automatically
                
                # Progress callback for enrichment
                async def progress_callback(percentage, step):
                    await self._update_task_progress(task, 60 + int(percentage * 0.2), step)
                
                # Run actual enrichment - pass session to avoid DetachedInstanceError
                enrichment_result = await enrichment_handlers.handle_part_enrichment(task, progress_callback, session=session)
                
                await self._update_task_progress(task, 90, "Enrichment completed")
                
                # The enrichment handlers already update the part, so we don't need to do it again
                # Just update the task result
                return {
                    "status": "success",
                    "message": f"Successfully enriched part {part_name} using {supplier}",
                    "enrichment_result": enrichment_result
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
                enrichment_handlers = EnrichmentCoordinatorService(part_repository, part_service)  # Gets CSV config automatically
                
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
                enrichment_handlers = EnrichmentCoordinatorService(part_repository, part_service)  # Gets CSV config automatically
                
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
                enrichment_handlers = EnrichmentCoordinatorService(part_repository, part_service)  # Gets CSV config automatically
                
                async def progress_callback(percentage: int, step: str):
                    await self._update_task_progress(task, percentage, step)
                
                result = await enrichment_handlers.handle_bulk_enrichment(task, progress_callback)
                session.commit()
            
            # Check if the task should be considered failed
            total_parts = result.get('total_parts', 0)
            successful_count = result.get('successful_count', 0)
            failed_count = result.get('failed_count', 0)
            
            if total_parts == 0:
                await self._update_task_progress(task, 100, "No parts to enrich")
            elif failed_count == total_parts:
                # All parts failed - mark task as failed
                error_msg = f"All {total_parts} parts failed enrichment"
                await self._update_task_progress(task, 100, error_msg)
                raise ValueError(error_msg)
            elif failed_count > 0:
                # Some parts failed - complete with warning
                await self._update_task_progress(task, 100, f"Completed: {successful_count} successful, {failed_count} failed")
            else:
                # All parts succeeded
                await self._update_task_progress(task, 100, f"Bulk enrichment completed successfully - {successful_count} parts enriched")
            
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