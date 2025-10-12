"""
Test script for datasheet download task functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus
from MakerMatrix.tasks.datasheet_download_task import DatasheetDownloadTask


@pytest.fixture
def mock_task():
    """Create a mock task for testing."""
    task = Mock(spec=TaskModel)
    task.id = "test-task-123"
    task.task_type = TaskType.DATASHEET_DOWNLOAD
    task.status = TaskStatus.PENDING
    task.get_input_data.return_value = {
        'part_id': 'part-456',
        'datasheet_url': 'https://example.com/datasheet.pdf',
        'supplier': 'LCSC',
        'part_number': 'C12345'
    }
    return task


@pytest.fixture
def datasheet_task():
    """Create a DatasheetDownloadTask instance."""
    return DatasheetDownloadTask()


@pytest.mark.asyncio
async def test_datasheet_download_task_properties(datasheet_task):
    """Test basic properties of the datasheet download task."""
    assert datasheet_task.task_type == "datasheet_download"
    assert datasheet_task.name == "Datasheet Download"
    assert "background" in datasheet_task.description.lower()


@pytest.mark.asyncio
async def test_execute_successful_download(datasheet_task, mock_task):
    """Test successful datasheet download."""
    # Mock the file download service
    with patch('MakerMatrix.tasks.datasheet_download_task.file_download_service') as mock_download:
        # Mock the part repository
        with patch('MakerMatrix.tasks.datasheet_download_task.get_session') as mock_get_session:
            with patch('MakerMatrix.tasks.datasheet_download_task.PartRepository') as MockPartRepo:
                # Setup mocks
                mock_download.download_datasheet.return_value = {
                    'filename': 'uuid-123.pdf',
                    'file_path': '/path/to/datasheet.pdf',
                    'size': 1024000,
                    'url': 'https://example.com/datasheet.pdf'
                }

                mock_part = Mock()
                mock_part.id = 'part-456'
                mock_part.part_name = 'Test Part'
                mock_part.part_number = 'C12345'
                mock_part.supplier_part_number = 'C12345'
                mock_part.additional_properties = {}

                mock_repo = Mock()
                mock_repo.get_part_by_id.return_value = mock_part
                mock_repo.update_part.return_value = mock_part
                MockPartRepo.return_value = mock_repo

                mock_session = MagicMock()
                mock_get_session.return_value.__enter__.return_value = mock_session

                # Execute task
                result = await datasheet_task.execute(mock_task)

                # Verify results
                assert result['success'] is True
                assert result['part_id'] == 'part-456'
                assert result['filename'] == 'uuid-123.pdf'
                assert result['size'] == 1024000
                assert result['supplier'] == 'LCSC'

                # Verify download was called
                mock_download.download_datasheet.assert_called_once_with(
                    url='https://example.com/datasheet.pdf',
                    part_number='C12345',
                    supplier='LCSC'
                )


@pytest.mark.asyncio
async def test_execute_failed_download(datasheet_task, mock_task):
    """Test failed datasheet download."""
    with patch('MakerMatrix.tasks.datasheet_download_task.file_download_service') as mock_download:
        with patch('MakerMatrix.tasks.datasheet_download_task.get_session') as mock_get_session:
            with patch('MakerMatrix.tasks.datasheet_download_task.PartRepository') as MockPartRepo:
                # Setup mocks for failure
                mock_download.download_datasheet.return_value = None  # Simulate download failure

                mock_part = Mock()
                mock_part.id = 'part-456'
                mock_part.part_name = 'Test Part'
                mock_part.additional_properties = {}

                mock_repo = Mock()
                mock_repo.get_part_by_id.return_value = mock_part
                MockPartRepo.return_value = mock_repo

                mock_session = MagicMock()
                mock_get_session.return_value.__enter__.return_value = mock_session

                # Execute task
                result = await datasheet_task.execute(mock_task)

                # Verify failure result
                assert result['success'] is False
                assert result['part_id'] == 'part-456'
                assert 'error' in result


@pytest.mark.asyncio
async def test_execute_missing_required_fields(datasheet_task):
    """Test execution with missing required fields."""
    task = Mock(spec=TaskModel)
    task.id = "test-task-123"
    task.get_input_data.return_value = {
        'part_id': 'part-456'
        # Missing datasheet_url and supplier
    }

    # Execute task
    result = await datasheet_task.execute(task)

    # Should fail due to missing fields
    assert result['success'] is False
    assert 'Missing required fields' in result['error']


@pytest.mark.asyncio
async def test_update_part_download_status_success(datasheet_task):
    """Test updating part status after successful download."""
    with patch('MakerMatrix.tasks.datasheet_download_task.get_session') as mock_get_session:
        with patch('MakerMatrix.tasks.datasheet_download_task.PartRepository') as MockPartRepo:
            mock_part = Mock()
            mock_part.additional_properties = {}

            mock_repo = Mock()
            mock_repo.get_part_by_id.return_value = mock_part
            MockPartRepo.return_value = mock_repo

            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Update with success
            download_info = {
                'filename': 'test.pdf',
                'size': 1024
            }
            await datasheet_task._update_part_download_status(
                'part-123',
                success=True,
                download_info=download_info
            )

            # Verify part properties were updated
            assert mock_part.additional_properties['datasheet_downloaded'] is True
            assert mock_part.additional_properties['datasheet_filename'] == 'test.pdf'
            assert mock_part.additional_properties['datasheet_size'] == 1024
            assert 'datasheet_download_error' not in mock_part.additional_properties


@pytest.mark.asyncio
async def test_update_part_download_status_failure(datasheet_task):
    """Test updating part status after failed download."""
    with patch('MakerMatrix.tasks.datasheet_download_task.get_session') as mock_get_session:
        with patch('MakerMatrix.tasks.datasheet_download_task.PartRepository') as MockPartRepo:
            mock_part = Mock()
            mock_part.additional_properties = {'datasheet_filename': 'old.pdf'}

            mock_repo = Mock()
            mock_repo.get_part_by_id.return_value = mock_part
            MockPartRepo.return_value = mock_repo

            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Update with failure
            await datasheet_task._update_part_download_status(
                'part-123',
                success=False,
                error='Download failed: 404'
            )

            # Verify part properties were updated
            assert mock_part.additional_properties['datasheet_downloaded'] is False
            assert mock_part.additional_properties['datasheet_download_error'] == 'Download failed: 404'


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])