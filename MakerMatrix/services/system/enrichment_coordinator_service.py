"""
EnrichmentCoordinatorService - Main coordinator for all enrichment operations.
Replaces the monolithic EnrichmentTaskHandlers class as part of Step 12.7.
"""

import logging
from typing import Dict, Any, Optional, Callable

from MakerMatrix.models.task_models import TaskModel, TaskType
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.csv_import_config_repository import CSVImportConfigRepository
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.services.system.part_enrichment_service import PartEnrichmentService
from MakerMatrix.services.system.datasheet_handler_service import DatasheetHandlerService
from MakerMatrix.services.system.image_handler_service import ImageHandlerService
from MakerMatrix.services.system.bulk_enrichment_service import BulkEnrichmentService
from MakerMatrix.services.data.enrichment_data_mapper import EnrichmentDataMapper
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class EnrichmentCoordinatorService(BaseService):
    """
    Main coordinator service for all enrichment operations.
    Replaces the monolithic EnrichmentTaskHandlers class and delegates to focused services.
    """

    def __init__(self, part_repository: Optional[PartRepository] = None, part_service: Optional[PartService] = None, download_config: Optional[dict] = None):
        super().__init__()
        # Repository will be created when needed with proper engine
        self.part_repository = part_repository
        self.part_service = part_service or PartService()
        self.download_config = download_config or self._get_csv_import_config()
        
        # Initialize specialized services
        self.part_enrichment_service = PartEnrichmentService()
        self.datasheet_handler_service = DatasheetHandlerService()
        self.image_handler_service = ImageHandlerService()
        self.bulk_enrichment_service = BulkEnrichmentService()
        # Initialize data mapper with supplier data mapper
        from MakerMatrix.services.data.supplier_data_mapper import SupplierDataMapper
        self.data_mapper = EnrichmentDataMapper(SupplierDataMapper())

    def _get_csv_import_config(self) -> dict:
        """Get the current CSV import configuration for download settings."""
        try:
            with self.get_session() as session:
                config_repo = CSVImportConfigRepository()
                config = config_repo.get_default_config(session)
                if config:
                    return config.to_dict()
        except Exception as e:
            logger.warning(f"Failed to get CSV import config, using defaults: {e}")
        
        # Return default configuration
        return {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }

    async def handle_task(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Main entry point for handling enrichment tasks.
        Delegates to appropriate specialized services based on task type.
        
        Args:
            task: The task model to handle
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing task results
        """
        try:
            logger.info(f"[ENRICHMENT COORDINATOR] Handling task: {task.task_type} - {task.name}")
            
            # Delegate to appropriate service based on task type
            if task.task_type == TaskType.PART_ENRICHMENT:
                return await self.part_enrichment_service.handle_part_enrichment(task, progress_callback)
            
            elif task.task_type == TaskType.DATASHEET_FETCH:
                return await self.datasheet_handler_service.handle_datasheet_fetch(task, progress_callback)
            
            elif task.task_type == TaskType.IMAGE_FETCH:
                return await self.image_handler_service.handle_image_fetch(task, progress_callback)
            
            elif task.task_type == TaskType.BULK_ENRICHMENT:
                return await self.bulk_enrichment_service.handle_bulk_enrichment(task, progress_callback)
            
            else:
                raise ValueError(f"Unsupported task type for enrichment coordinator: {task.task_type}")
                
        except Exception as e:
            logger.error(f"[ENRICHMENT COORDINATOR] Error handling task {task.id}: {e}", exc_info=True)
            raise

    # Backward compatibility methods for legacy code
    async def handle_part_enrichment(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Backward compatibility method for part enrichment."""
        return await self.part_enrichment_service.handle_part_enrichment(task, progress_callback)

    async def handle_datasheet_fetch(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Backward compatibility method for datasheet fetch."""
        return await self.datasheet_handler_service.handle_datasheet_fetch(task, progress_callback)

    async def handle_image_fetch(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Backward compatibility method for image fetch."""
        return await self.image_handler_service.handle_image_fetch(task, progress_callback)

    async def handle_bulk_enrichment(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Backward compatibility method for bulk enrichment."""
        return await self.bulk_enrichment_service.handle_bulk_enrichment(task, progress_callback)

    # Additional utility methods that may be needed for compatibility
    def get_download_config(self) -> dict:
        """Get the current download configuration."""
        return self.download_config

    def get_data_mapper(self) -> EnrichmentDataMapper:
        """Get the data mapper instance."""
        return self.data_mapper