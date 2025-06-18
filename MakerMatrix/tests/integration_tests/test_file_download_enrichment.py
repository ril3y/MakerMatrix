"""
Integration tests for file download functionality during part enrichment.
Tests that datasheets and images are properly downloaded to local filesystem.
"""

import pytest
import asyncio
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from sqlmodel import Session

from MakerMatrix.models.task_models import TaskModel, TaskType, TaskPriority, TaskStatus
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService


class TestFileDownloadEnrichment:
    """Test file download functionality during part enrichment"""

    @pytest.fixture
    def temp_directories(self):
        """Create temporary directories for testing file downloads"""
        base_temp_dir = tempfile.mkdtemp()
        datasheets_dir = os.path.join(base_temp_dir, 'datasheets')
        images_dir = os.path.join(base_temp_dir, 'images')
        
        os.makedirs(datasheets_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        yield {
            'base': base_temp_dir,
            'datasheets': datasheets_dir,
            'images': images_dir
        }
        
        # Cleanup
        shutil.rmtree(base_temp_dir, ignore_errors=True)

    @pytest.fixture
    def download_config(self, temp_directories):
        """Create download configuration for testing"""
        return {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30,
            'datasheets_dir': temp_directories['datasheets'],
            'images_dir': temp_directories['images']
        }

    @pytest.fixture
    def mock_part(self):
        """Create a test part with LCSC data"""
        with Session(engine) as session:
            part = PartModel(
                part_name="Test Capacitor",
                part_number="CL21A475KAQNNNE",
                supplier="LCSC",
                part_vendor="LCSC",
                additional_properties={
                    "lcsc_part_number": "C1779",
                    "manufacturer": "Samsung Electro-Mechanics",
                    "enrichment_source": "lcsc"
                }
            )
            session.add(part)
            session.commit()
            session.refresh(part)
            yield part
            
            # Cleanup
            session.delete(part)
            session.commit()

    @pytest.fixture
    def enrichment_handler(self, download_config):
        """Create enrichment handler with test configuration"""
        part_repo = PartRepository(engine)
        part_service = PartService()
        return EnrichmentTaskHandlers(part_repo, part_service, download_config)

    @pytest.mark.asyncio
    async def test_datasheet_download_configuration_enabled(self, enrichment_handler, download_config):
        """Test that datasheet download configuration is properly read"""
        assert enrichment_handler.download_config['download_datasheets'] == True
        assert enrichment_handler.download_config['download_images'] == True
        assert 'datasheets_dir' in enrichment_handler.download_config
        assert 'images_dir' in enrichment_handler.download_config

    @pytest.mark.asyncio
    async def test_datasheet_download_configuration_disabled(self, temp_directories):
        """Test behavior when downloads are disabled"""
        disabled_config = {
            'download_datasheets': False,
            'download_images': False,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }
        
        part_repo = PartRepository(engine)
        part_service = PartService()
        handler = EnrichmentTaskHandlers(part_repo, part_service, disabled_config)
        
        assert handler.download_config['download_datasheets'] == False
        assert handler.download_config['download_images'] == False

    @pytest.mark.asyncio
    async def test_file_download_service_integration(self, enrichment_handler, temp_directories):
        """Test that file download service is properly integrated"""
        
        # Mock the file download service
        mock_download_result = {
            'filename': 'C1779_Samsung_datasheet.pdf',
            'size': 1024000,
            'file_uuid': 'test-uuid-123',
            'local_path': os.path.join(temp_directories['datasheets'], 'C1779_Samsung_datasheet.pdf')
        }
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.return_value = mock_download_result
            mock_service.return_value = mock_file_service
            
            # Test that the service is called correctly
            part = Mock()
            part.part_name = "Test Part"
            part.part_number = "C1779"
            part.supplier = "LCSC"
            part.additional_properties = {}
            
            # Create enrichment results that would trigger download
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://example.com/datasheet.pdf'
                }
            }
            
            # Call the method that should trigger download
            await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify download service was called
            mock_service.assert_called_once_with(enrichment_handler.download_config)
            mock_file_service.download_datasheet.assert_called_once_with(
                url='https://example.com/datasheet.pdf',
                part_number='C1779',
                supplier='LCSC'
            )
            
            # Verify part was updated with download information
            assert part.additional_properties['datasheet_filename'] == 'C1779_Samsung_datasheet.pdf'
            assert part.additional_properties['datasheet_downloaded'] == True
            assert part.additional_properties['datasheet_size'] == 1024000

    @pytest.mark.asyncio
    async def test_image_download_integration(self, enrichment_handler, temp_directories):
        """Test that image download works correctly"""
        
        mock_download_result = {
            'filename': 'C1779_Samsung_image.jpg',
            'size': 256000,
            'local_path': os.path.join(temp_directories['images'], 'C1779_Samsung_image.jpg')
        }
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_image.return_value = mock_download_result
            mock_service.return_value = mock_file_service
            
            part = Mock()
            part.part_name = "Test Part"
            part.part_number = "C1779"
            part.supplier = "LCSC"
            part.additional_properties = {}
            part.image_url = None
            
            enrichment_results = {
                'fetch_image': {
                    'success': True,
                    'primary_image_url': 'https://example.com/image.jpg'
                }
            }
            
            await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify image URL was set
            assert part.image_url == 'https://example.com/image.jpg'
            
            # Verify download service was called
            mock_file_service.download_image.assert_called_once_with(
                url='https://example.com/image.jpg',
                part_number='C1779',
                supplier='LCSC'
            )
            
            # Verify part was updated with download information
            assert part.additional_properties['image_filename'] == 'C1779_Samsung_image.jpg'
            assert part.additional_properties['image_downloaded'] == True
            assert part.additional_properties['image_size'] == 256000

    @pytest.mark.asyncio
    async def test_download_failure_handling(self, enrichment_handler):
        """Test handling of download failures"""
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.return_value = None  # Simulate failure
            mock_service.return_value = mock_file_service
            
            part = Mock()
            part.part_name = "Test Part"
            part.part_number = "C1779"
            part.supplier = "LCSC"
            part.additional_properties = {}
            
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://invalid-url.com/datasheet.pdf'
                }
            }
            
            await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify failure was recorded
            assert part.additional_properties['datasheet_downloaded'] == False
            assert 'datasheet_filename' not in part.additional_properties

    @pytest.mark.asyncio
    async def test_download_exception_handling(self, enrichment_handler):
        """Test handling of download exceptions"""
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.side_effect = Exception("Network error")
            mock_service.return_value = mock_file_service
            
            part = Mock()
            part.part_name = "Test Part"
            part.part_number = "C1779"
            part.supplier = "LCSC"
            part.additional_properties = {}
            
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://example.com/datasheet.pdf'
                }
            }
            
            # Should not raise exception, should handle gracefully
            await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify exception was handled
            assert part.additional_properties['datasheet_downloaded'] == False

    @pytest.mark.asyncio
    async def test_download_disabled_in_config(self, temp_directories):
        """Test that downloads are skipped when disabled in config"""
        
        disabled_config = {
            'download_datasheets': False,
            'download_images': False,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }
        
        part_repo = PartRepository(engine)
        part_service = PartService()
        handler = EnrichmentTaskHandlers(part_repo, part_service, disabled_config)
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            part = Mock()
            part.part_name = "Test Part"
            part.additional_properties = {}
            
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://example.com/datasheet.pdf'
                }
            }
            
            await handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify download service was never called
            mock_service.assert_not_called()
            
            # Verify URL was still saved
            assert part.additional_properties['datasheet_url'] == 'https://example.com/datasheet.pdf'
            
            # Verify no download flags were set
            assert 'datasheet_downloaded' not in part.additional_properties

    @pytest.mark.asyncio
    async def test_full_enrichment_with_downloads(self, mock_part, enrichment_handler, temp_directories):
        """Test complete enrichment flow with file downloads"""
        
        # Mock the supplier config service and API client
        mock_enrichment_results = {
            'fetch_datasheet': {
                'success': True,
                'datasheet_url': 'https://example.com/C1779_datasheet.pdf',
                'status': 'success'
            },
            'fetch_image': {
                'success': True,
                'primary_image_url': 'https://example.com/C1779_image.jpg',
                'status': 'success'
            }
        }
        
        mock_download_results = {
            'datasheet': {
                'filename': 'C1779_Samsung_datasheet.pdf',
                'size': 1024000,
                'file_uuid': 'datasheet-uuid'
            },
            'image': {
                'filename': 'C1779_Samsung_image.jpg',
                'size': 256000
            }
        }
        
        with patch('MakerMatrix.services.enrichment_task_handlers.SupplierConfigService') as mock_supplier_service, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_file_service:
            
            # Setup supplier service mock
            mock_supplier = Mock()
            mock_supplier.enabled = True
            mock_supplier.get_capabilities.return_value = ['fetch_datasheet', 'fetch_image']
            mock_supplier_service.return_value.get_supplier_config.return_value = mock_supplier
            mock_supplier_service.return_value.get_supplier_credentials.return_value = {}
            
            # Setup API client mock
            mock_client = AsyncMock()
            mock_client.enrich_part_datasheet.return_value = Mock(
                success=True, 
                model_dump=lambda: mock_enrichment_results['fetch_datasheet']
            )
            mock_client.enrich_part_image.return_value = Mock(
                success=True,
                model_dump=lambda: mock_enrichment_results['fetch_image']
            )
            mock_supplier_service.return_value._create_api_client.return_value = mock_client
            
            # Setup file download service mock
            mock_file_dl = Mock()
            mock_file_dl.download_datasheet.return_value = mock_download_results['datasheet']
            mock_file_dl.download_image.return_value = mock_download_results['image']
            mock_file_service.return_value = mock_file_dl
            
            # Create task
            task = TaskModel(
                task_type=TaskType.PART_ENRICHMENT,
                name="Test File Download Enrichment",
                priority=TaskPriority.NORMAL,
                input_data=json.dumps({
                    "part_id": mock_part.id,
                    "supplier": "LCSC",
                    "capabilities": ["fetch_datasheet", "fetch_image"]
                })
            )
            
            # Execute enrichment
            result = await enrichment_handler.handle_part_enrichment(task)
            
            # Verify task completed successfully
            assert "successful_enrichments" in result
            assert "fetch_datasheet" in result["successful_enrichments"]
            assert "fetch_image" in result["successful_enrichments"]
            
            # Verify downloads were attempted
            mock_file_dl.download_datasheet.assert_called_once()
            mock_file_dl.download_image.assert_called_once()
            
            # Verify part was updated in database
            with Session(engine) as session:
                updated_part = PartRepository.get_part_by_id(session, mock_part.id)
                assert updated_part is not None
                
                # Check enrichment results were saved
                assert 'enrichment_results' in updated_part.additional_properties
                assert 'fetch_datasheet' in updated_part.additional_properties['enrichment_results']
                assert 'fetch_image' in updated_part.additional_properties['enrichment_results']
                
                # Check URLs were saved
                assert updated_part.additional_properties.get('datasheet_url') == 'https://example.com/C1779_datasheet.pdf'
                assert updated_part.image_url == 'https://example.com/C1779_image.jpg'
                
                # Check download information was saved
                assert updated_part.additional_properties.get('datasheet_downloaded') == True
                assert updated_part.additional_properties.get('datasheet_filename') == 'C1779_Samsung_datasheet.pdf'
                assert updated_part.additional_properties.get('image_downloaded') == True
                assert updated_part.additional_properties.get('image_filename') == 'C1779_Samsung_image.jpg'

    @pytest.mark.asyncio
    async def test_csv_import_config_integration(self):
        """Test that CSV import configuration is properly used for downloads"""
        
        # Mock the database config
        mock_config = CSVImportConfigModel(
            download_datasheets=True,
            download_images=True,
            download_timeout_seconds=60,
            overwrite_existing_files=True
        )
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.select') as mock_select:
            
            mock_session_instance = Mock()
            mock_session_instance.__enter__ = Mock(return_value=mock_session_instance)
            mock_session_instance.__exit__ = Mock(return_value=None)
            mock_session_instance.exec.return_value.first.return_value = mock_config
            mock_session.return_value = mock_session_instance
            
            part_repo = PartRepository(engine)
            part_service = PartService(part_repo)
            handler = EnrichmentTaskHandlers(part_repo, part_service)
            
            # Verify config was loaded correctly
            assert handler.download_config['download_datasheets'] == True
            assert handler.download_config['download_images'] == True
            assert handler.download_config['download_timeout_seconds'] == 60
            assert handler.download_config['overwrite_existing_files'] == True

    @pytest.mark.asyncio 
    async def test_file_paths_generation(self, enrichment_handler):
        """Test that proper file paths are generated for downloads"""
        
        mock_download_result = {
            'filename': 'C1779_Samsung_datasheet.pdf',
            'size': 1024000,
            'file_uuid': 'test-uuid-123'
        }
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.return_value = mock_download_result
            mock_service.return_value = mock_file_service
            
            part = Mock()
            part.part_name = "Test Part"
            part.part_number = "C1779"
            part.supplier = "LCSC"
            part.additional_properties = {}
            
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://example.com/datasheet.pdf'
                }
            }
            
            await enrichment_handler._update_part_from_enrichment_results(part, enrichment_results)
            
            # Verify static path was generated correctly
            assert part.additional_properties['datasheet_local_path'] == '/static/datasheets/C1779_Samsung_datasheet.pdf'
            assert part.additional_properties['datasheet_file_uuid'] == 'test-uuid-123'


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])