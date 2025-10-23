"""
ImageHandlerService - Handles image fetching operations for parts.
Extracted from monolithic enrichment_task_handlers.py as part of Step 12.7.
"""

import logging
from typing import Dict, Any, Optional, Callable

from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.services.system.file_system_service import FileSystemService
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class ImageHandlerService(BaseService):
    """
    Service for handling image fetching operations for parts.
    Integrates with supplier systems for image retrieval.
    """

    def __init__(self):
        super().__init__()
        self.supplier_config_service = SupplierConfigService()
        # Initialize file system service with default configuration
        file_config = {
            "datasheet_path": "datasheets",
            "image_path": "images",
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_image_extensions": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
            "allowed_datasheet_extensions": [".pdf", ".doc", ".docx", ".txt"],
        }
        self.file_system_service = FileSystemService(file_config)

    async def handle_image_fetch(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle image fetching for a specific part using standardized client.

        Args:
            task: The task model containing part information
            progress_callback: Optional callback for progress updates

        Returns:
            Dict containing success status and image information
        """
        try:
            input_data = task.get_input_data()
            part_id = input_data.get("part_id")
            part_number = input_data.get("part_number")
            supplier = input_data.get("supplier")

            if not (part_id or part_number):
                raise ValueError("Either part_id or part_number is required")

            # Get part if part_id provided
            part = None
            if part_id:
                with self.get_session() as session:
                    part = PartRepository.get_part_by_id(session, part_id)
                    if not part:
                        raise ValueError(f"Part not found: {part_id}")
                    part_number = part.part_number or part.lcsc_part_number
                    supplier = supplier or part.supplier or part.part_vendor

            if not supplier:
                raise ValueError("Supplier is required for image fetch")

            # Validate supplier configuration
            supplier_config = self._get_supplier_config(supplier)
            if not supplier_config.get("enabled", False):
                raise ValueError(f"Supplier {supplier} is not enabled")

            # Get supplier client
            client = self._get_supplier_client(supplier, supplier_config)

            if progress_callback:
                await progress_callback(25, "Fetching image information")

            # Use standardized enrichment method
            result = await client.enrich_part_image(part_number)

            if progress_callback:
                await progress_callback(75, "Processing image result")

            # Update part if part_id was provided and image was found
            if part and result.success and result.primary_image_url:
                await self._update_part_image(part, result.primary_image_url)

            if progress_callback:
                await progress_callback(100, "Image fetch completed")

            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "image_data": result.model_dump() if result.success else None,
                "error": result.error_message if not result.success else None,
            }

        except Exception as e:
            logger.error(f"Error in image fetch task: {e}", exc_info=True)
            raise

    async def _update_part_image(self, part: PartModel, image_url: str) -> None:
        """
        Update part model with new image URL.

        Args:
            part: The part model to update
            image_url: The new image URL
        """
        part.image_url = image_url

        with self.get_session() as session:
            PartRepository.update_part(session, part)

        logger.info(f"Updated image URL for part {part.part_name}: {image_url}")

    def _get_supplier_config(self, supplier: str) -> Any:
        """
        Get supplier configuration with error handling.

        Args:
            supplier: The supplier name

        Returns:
            The supplier configuration

        Raises:
            ValueError: If supplier configuration is not found
        """
        try:
            return self.supplier_config_service.get_supplier_config(supplier.upper())
        except Exception as e:
            raise ValueError(f"Supplier configuration not found for: {supplier}") from e

    def _get_supplier_client(self, supplier: str, supplier_config: Any) -> Any:
        """
        Get and configure supplier client.

        Args:
            supplier: The supplier name
            supplier_config: The supplier configuration

        Returns:
            The configured supplier client

        Raises:
            ValueError: If supplier client is not found
        """
        from MakerMatrix.suppliers.registry import get_supplier

        client = get_supplier(supplier.lower())
        if not client:
            raise ValueError(f"Supplier implementation not found for: {supplier}")

        # Configure the supplier with credentials and config
        credentials = self.supplier_config_service.get_supplier_credentials(supplier.upper())
        config = supplier_config.get("custom_parameters", {})
        client.configure(credentials or {}, config)

        return client
