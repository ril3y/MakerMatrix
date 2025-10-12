"""
Datasheet Download Task Handler

Handles asynchronous downloading of datasheets as a background task
with proper progress tracking and WebSocket notifications.
"""

import logging
from typing import Dict, Any
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.tasks.base_task import BaseTask
from MakerMatrix.services.system.file_download_service import file_download_service
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.database.db import get_session

logger = logging.getLogger(__name__)


class DatasheetDownloadTask(BaseTask):
    """
    Task handler for downloading datasheets asynchronously.

    This allows enrichment to complete immediately while the datasheet
    downloads in the background, providing better user experience with
    progress notifications.
    """

    @property
    def task_type(self) -> str:
        return "datasheet_download"

    @property
    def name(self) -> str:
        return "Datasheet Download"

    @property
    def description(self) -> str:
        return "Downloads datasheet files for parts in the background"

    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """
        Execute datasheet download task.

        Input data should contain:
        - part_id: ID of the part
        - datasheet_url: URL to download from
        - supplier: Supplier name
        - part_number: Part number for filename

        Returns:
            Dict with download result information
        """
        try:
            # Get input data
            input_data = self.get_input_data(task)

            # Validate required fields
            if not self.validate_input_data(task, ['part_id', 'datasheet_url', 'supplier']):
                raise ValueError("Missing required fields for datasheet download")

            part_id = input_data['part_id']
            datasheet_url = input_data['datasheet_url']
            supplier = input_data['supplier']
            part_number = input_data.get('part_number', part_id)

            # Get part details for logging
            part_name = None
            session = next(get_session())
            try:
                part = PartRepository.get_part_by_id(session, part_id)
                if part:
                    part_name = part.part_name
                    if not part_number:
                        part_number = part.supplier_part_number or part.part_number or part_id
            finally:
                session.close()

            # Update progress - Starting download
            await self.update_progress(task, 10, f"Starting datasheet download for {part_name or part_id}")
            self.log_info(f"Downloading datasheet from {datasheet_url}", task)

            # Download the datasheet
            await self.update_progress(task, 30, "Downloading datasheet file...")

            download_result = file_download_service.download_datasheet(
                url=datasheet_url,
                part_number=part_number,
                supplier=supplier
            )

            if not download_result:
                # Download failed
                await self.update_progress(task, 100, "Datasheet download failed")
                self.log_error(f"Failed to download datasheet from {datasheet_url}", task)

                # Update part to indicate download failure
                await self._update_part_download_status(part_id, success=False, error="Download failed")

                return {
                    'success': False,
                    'part_id': part_id,
                    'error': 'Failed to download datasheet'
                }

            # Download successful
            await self.update_progress(task, 70, "Processing downloaded datasheet...")

            # Update part with download information
            await self._update_part_download_status(
                part_id,
                success=True,
                download_info=download_result
            )

            # Final progress update
            await self.update_progress(task, 100, f"Datasheet downloaded successfully: {download_result['filename']}")
            self.log_info(f"Successfully downloaded datasheet: {download_result['filename']} ({download_result['size']} bytes)", task)

            return {
                'success': True,
                'part_id': part_id,
                'part_name': part_name,
                'filename': download_result['filename'],
                'file_path': download_result['file_path'],
                'size': download_result['size'],
                'url': datasheet_url,
                'supplier': supplier
            }

        except Exception as e:
            error_msg = f"Error downloading datasheet: {str(e)}"
            self.log_error(error_msg, task, exc_info=True)
            await self.update_progress(task, 100, "Datasheet download failed")

            # Try to update part status if we have part_id
            if 'part_id' in locals():
                await self._update_part_download_status(part_id, success=False, error=str(e))

            return {
                'success': False,
                'error': error_msg
            }

    async def _update_part_download_status(self, part_id: str, success: bool, download_info: Dict[str, Any] = None, error: str = None):
        """
        Update part's additional_properties with download status.

        Args:
            part_id: ID of the part to update
            success: Whether download was successful
            download_info: Download result information (if successful)
            error: Error message (if failed)
        """
        session = next(get_session())
        try:
            part = PartRepository.get_part_by_id(session, part_id)

            if part:
                if not part.additional_properties:
                    part.additional_properties = {}

                if success and download_info:
                    # Update with successful download information
                    # Store just the filename - frontend will construct the full path
                    part.additional_properties['datasheet_filename'] = download_info['filename']
                    part.additional_properties['datasheet_downloaded'] = True
                    part.additional_properties['datasheet_size'] = download_info['size']

                    # Remove any previous error
                    if 'datasheet_download_error' in part.additional_properties:
                        del part.additional_properties['datasheet_download_error']

                    logger.info(f"Updated part {part_id} with successful datasheet download")
                else:
                    # Update with failure information
                    part.additional_properties['datasheet_downloaded'] = False
                    if error:
                        part.additional_properties['datasheet_download_error'] = error

                    logger.warning(f"Updated part {part_id} with failed datasheet download: {error}")

                # Force SQLAlchemy to recognize the changes
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(part, 'additional_properties')

                # Save changes
                PartRepository.update_part(session, part)

        except Exception as e:
            logger.error(f"Failed to update part {part_id} with datasheet download status: {e}")
            # Don't raise - this is a non-critical update
        finally:
            session.close()