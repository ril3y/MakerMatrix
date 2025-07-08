"""
DatasheetHandlerService - Handles datasheet fetching and management operations.
Extracted from monolithic enrichment_task_handlers.py as part of Step 12.7.
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.models import PartModel, DatasheetModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.datasheet_repository import DatasheetRepository
from MakerMatrix.services.system.supplier_config_service import SupplierConfigService
from MakerMatrix.services.system.file_system_service import FileSystemService
from MakerMatrix.services.base_service import BaseService
from MakerMatrix.services.system.file_download_service import file_download_service

logger = logging.getLogger(__name__)


class DatasheetHandlerService(BaseService):
    """
    Service for handling datasheet fetching and management operations.
    Integrates with supplier systems and file management.
    """

    def __init__(self):
        super().__init__()
        self.supplier_config_service = SupplierConfigService()
        # Initialize file system service with default configuration
        file_config = {
            'datasheet_path': 'datasheets',
            'image_path': 'images',
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'allowed_image_extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'allowed_datasheet_extensions': ['.pdf', '.doc', '.docx', '.txt']
        }
        self.file_system_service = FileSystemService(file_config)
        self.datasheet_repository = DatasheetRepository()

    async def handle_datasheet_fetch(self, task: TaskModel, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Handle datasheet fetching for a specific part using standardized client.
        
        Args:
            task: The task model containing part information
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing success status and datasheet information
        """
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
                with self.get_session() as session:
                    part = PartRepository.get_part_by_id(session, part_id)
                    if not part:
                        raise ValueError(f"Part not found: {part_id}")
                    # Use the appropriate part number for the supplier
                    part_number = self._get_supplier_part_number(part, supplier)
                    supplier = supplier or part.supplier or part.part_vendor
            
            if not supplier:
                raise ValueError("Supplier is required for datasheet fetch")
            
            # Validate supplier configuration
            supplier_config = self._get_supplier_config(supplier)
            if not supplier_config.enabled:
                raise ValueError(f"Supplier {supplier} is not enabled")
            
            # Get supplier client
            client = self._get_supplier_client(supplier, supplier_config)
            
            if progress_callback:
                await progress_callback(25, "Fetching datasheet information")
            
            # Use standardized enrichment method
            result = await client.enrich_part_datasheet(part_number)
            
            if progress_callback:
                await progress_callback(75, "Processing datasheet result")
            
            # Update part if part_id was provided and download the datasheet
            if part and result.success and result.datasheet_url:
                await self._process_datasheet_result(
                    part, result, supplier, part_number, progress_callback
                )
            
            if progress_callback:
                await progress_callback(100, "Datasheet fetch completed")
            
            return {
                "part_number": part_number,
                "supplier": supplier,
                "success": result.success,
                "datasheet_data": result.model_dump() if result.success else None,
                "error": result.error_message if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in datasheet fetch task: {e}", exc_info=True)
            raise

    async def _process_datasheet_result(
        self, 
        part: PartModel, 
        result: Any, 
        supplier: str, 
        part_number: str, 
        progress_callback: Optional[Callable] = None
    ) -> None:
        """
        Process successful datasheet result by updating part and storing file.
        
        Args:
            part: The part model to update
            result: The datasheet enrichment result
            supplier: The supplier name
            part_number: The part number
            progress_callback: Optional callback for progress updates
        """
        # Store datasheet URL in standardized supplier data structure
        std_props = part.get_standardized_additional_properties()
        supplier_data = std_props.get('supplier_data', {})
        
        # Update supplier data with datasheet URL
        supplier_key = supplier.lower() if supplier else 'unknown'
        if supplier_key not in supplier_data:
            supplier_data[supplier_key] = {}
        supplier_data[supplier_key]['datasheet_url'] = result.datasheet_url
        
        # Update additional_properties with standardized structure
        if not part.additional_properties:
            part.additional_properties = {}
        part.additional_properties['supplier_data'] = supplier_data
        
        if progress_callback:
            await progress_callback(80, "Downloading datasheet file...")
        
        # Download the datasheet file
        download_result = file_download_service.download_datasheet(
            url=result.datasheet_url,
            part_number=part_number,
            supplier=supplier
        )
        
        # Update part with download information
        self._update_part_with_download_info(part, download_result)
        
        # Create or update datasheet record
        await self._create_or_update_datasheet_record(
            part, result, supplier, part_number, download_result
        )
        
        if progress_callback:
            if download_result:
                await progress_callback(95, f"Downloaded {download_result['filename']}")
            else:
                await progress_callback(95, "Datasheet download failed")

    def _update_part_with_download_info(self, part: PartModel, download_result: Optional[Dict[str, Any]]) -> None:
        """
        Update part model with download information for backward compatibility.
        
        Args:
            part: The part model to update
            download_result: The download result or None if failed
        """
        if download_result:
            # Store local file information in additional_properties for backward compatibility
            part.additional_properties['datasheet_filename'] = download_result['filename']
            part.additional_properties['datasheet_local_path'] = f"/static/datasheets/{download_result['filename']}"
            part.additional_properties['datasheet_downloaded'] = True
            part.additional_properties['datasheet_size'] = download_result['size']
            
            logger.info(f"Downloaded datasheet for {part.part_name}: {download_result['filename']}")
        else:
            part.additional_properties['datasheet_downloaded'] = False
            logger.warning(f"Failed to download datasheet for {part.part_name}")

    async def _create_or_update_datasheet_record(
        self, 
        part: PartModel, 
        result: Any, 
        supplier: str, 
        part_number: str, 
        download_result: Optional[Dict[str, Any]]
    ) -> None:
        """
        Create or update the datasheet record in the database.
        
        Args:
            part: The part model
            result: The datasheet enrichment result
            supplier: The supplier name
            part_number: The part number
            download_result: The download result or None if failed
        """
        with self.get_session() as session:
            # Check if datasheet already exists for this part and URL
            existing_datasheet = self.datasheet_repository.get_datasheet_by_part_and_url(
                session, part.id, result.datasheet_url
            )
            
            if not existing_datasheet:
                # Create new datasheet record
                datasheet_data = {
                    'part_id': part.id,
                    'source_url': result.datasheet_url,
                    'supplier': supplier,
                    'title': f"{supplier} Datasheet - {part_number}",
                    'description': f"Datasheet for {part.part_name or part_number}",
                    'is_downloaded': download_result is not None,
                    'download_error': None if download_result else "Failed to download datasheet file"
                }
                
                # Add download details if successful
                if download_result:
                    datasheet_data.update({
                        'file_uuid': download_result['file_uuid'],
                        'original_filename': download_result['original_filename'],
                        'file_extension': download_result['extension'],
                        'file_size': download_result['size']
                    })
                
                self.datasheet_repository.create_datasheet(session, datasheet_data)
            else:
                # Update existing datasheet record
                if download_result:
                    self.datasheet_repository.mark_download_successful(
                        session,
                        existing_datasheet.id,
                        download_result['file_uuid'],
                        download_result['size'],
                        download_result['original_filename'],
                        download_result['extension']
                    )
                else:
                    self.datasheet_repository.mark_download_failed(
                        session,
                        existing_datasheet.id,
                        "Failed to download datasheet file"
                    )
            
            # Update the part record
            PartRepository.update_part(session, part)

    def _get_supplier_part_number(self, part: PartModel, supplier: Optional[str]) -> str:
        """
        Get the appropriate part number for the given supplier.
        
        Args:
            part: The part model
            supplier: The supplier name
            
        Returns:
            The appropriate part number for the supplier
        """
        # Implementation would depend on how part numbers are mapped to suppliers
        # For now, use the general part number logic
        return part.part_number or part.lcsc_part_number

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
        config = supplier_config.custom_parameters or {}
        client.configure(credentials or {}, config)
        
        return client