#!/usr/bin/env python3
"""
Pytest to reproduce and fix the file download issue.
This test demonstrates why some parts get files downloaded and others don't.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from sqlmodel import Session

from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService


class TestDownloadIssueReproduction:
    """Test to reproduce and fix the file download issue"""

    @pytest.fixture
    def mock_part_with_lcsc_data(self):
        """Create a mock part similar to the failing case"""
        part = Mock()
        part.id = "test-part-id"
        part.part_name = "CL21A475KAQNNNE"
        part.part_number = "CL21A475KAQNNNE"
        part.supplier = "LCSC"
        part.part_vendor = "LCSC"
        part.image_url = None
        part.description = None
        part.additional_properties = {
            "lcsc_part_number": "C1779",
            "manufacturer": "Samsung Electro-Mechanics"
        }
        return part

    @pytest.fixture
    def download_config_enabled(self):
        """Download configuration with downloads enabled"""
        return {
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }

    @pytest.fixture
    def enrichment_handler_enabled(self, download_config_enabled):
        """Create enrichment handler with downloads enabled"""
        part_repo = PartRepository(engine)
        part_service = PartService()
        return EnrichmentTaskHandlers(part_repo, part_service, download_config_enabled)

    @pytest.mark.asyncio
    async def test_datasheet_download_flow_working_case(self, enrichment_handler_enabled, mock_part_with_lcsc_data):
        """Test the datasheet download flow that should work"""
        
        # Mock successful file download
        mock_download_result = {
            'filename': 'C1779_Samsung_datasheet.pdf',
            'size': 1024000,
            'file_uuid': 'test-uuid-123'
        }
        
        with patch('MakerMatrix.services.file_download_service.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.return_value = mock_download_result
            mock_service.return_value = mock_file_service
            
            # Create enrichment results that match the failing case
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_Samsung-Electro-Mechanics-CL21A475KAQNNNE_C1779.pdf'
                }
            }
            
            # This should trigger download
            await enrichment_handler_enabled._update_part_from_enrichment_results(
                mock_part_with_lcsc_data, 
                enrichment_results
            )
            
            # Verify download was attempted
            mock_service.assert_called_once_with(enrichment_handler_enabled.download_config)
            mock_file_service.download_datasheet.assert_called_once()
            
            # Verify part was updated with download info
            assert mock_part_with_lcsc_data.additional_properties['datasheet_downloaded'] == True
            assert mock_part_with_lcsc_data.additional_properties['datasheet_filename'] == 'C1779_Samsung_datasheet.pdf'
            assert mock_part_with_lcsc_data.additional_properties['datasheet_url'] == enrichment_results['fetch_datasheet']['datasheet_url']

    @pytest.mark.asyncio
    async def test_image_download_flow_working_case(self, enrichment_handler_enabled, mock_part_with_lcsc_data):
        """Test the image download flow that should work"""
        
        # Mock successful image download
        mock_download_result = {
            'filename': 'C1779_Samsung_image.jpg',
            'size': 256000
        }
        
        with patch('MakerMatrix.services.file_download_service.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_image.return_value = mock_download_result
            mock_service.return_value = mock_file_service
            
            # Create enrichment results that match the failing case
            enrichment_results = {
                'fetch_image': {
                    'success': True,
                    'primary_image_url': 'https://assets.lcsc.com/images/lcsc/900x900/20240318_Samsung-Electro-Mechanics-CL21A475KAQNNNE_C1779_front.jpg'
                }
            }
            
            # This should trigger download
            await enrichment_handler_enabled._update_part_from_enrichment_results(
                mock_part_with_lcsc_data, 
                enrichment_results
            )
            
            # Verify image URL was set
            assert mock_part_with_lcsc_data.image_url == enrichment_results['fetch_image']['primary_image_url']
            
            # Verify download was attempted
            mock_service.assert_called_once_with(enrichment_handler_enabled.download_config)
            mock_file_service.download_image.assert_called_once()
            
            # Verify part was updated with download info
            assert mock_part_with_lcsc_data.additional_properties['image_downloaded'] == True
            assert mock_part_with_lcsc_data.additional_properties['image_filename'] == 'C1779_Samsung_image.jpg'

    @pytest.mark.asyncio
    async def test_download_disabled_case(self, mock_part_with_lcsc_data):
        """Test when downloads are disabled in configuration"""
        
        # Create handler with downloads disabled
        download_config_disabled = {
            'download_datasheets': False,
            'download_images': False,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30
        }
        
        part_repo = PartRepository(engine)
        part_service = PartService()
        handler = EnrichmentTaskHandlers(part_repo, part_service, download_config_disabled)
        
        with patch('MakerMatrix.services.file_download_service.get_file_download_service') as mock_service:
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://example.com/datasheet.pdf'
                }
            }
            
            await handler._update_part_from_enrichment_results(
                mock_part_with_lcsc_data, 
                enrichment_results
            )
            
            # Download service should not be called
            mock_service.assert_not_called()
            
            # URL should still be saved
            assert mock_part_with_lcsc_data.additional_properties['datasheet_url'] == 'https://example.com/datasheet.pdf'
            
            # But no download flags should be set
            assert 'datasheet_downloaded' not in mock_part_with_lcsc_data.additional_properties

    @pytest.mark.asyncio
    async def test_download_failure_case(self, enrichment_handler_enabled, mock_part_with_lcsc_data):
        """Test when download fails"""
        
        with patch('MakerMatrix.services.file_download_service.get_file_download_service') as mock_service:
            mock_file_service = Mock()
            mock_file_service.download_datasheet.return_value = None  # Simulate failure
            mock_service.return_value = mock_file_service
            
            enrichment_results = {
                'fetch_datasheet': {
                    'success': True,
                    'datasheet_url': 'https://invalid-url.com/datasheet.pdf'
                }
            }
            
            await enrichment_handler_enabled._update_part_from_enrichment_results(
                mock_part_with_lcsc_data, 
                enrichment_results
            )
            
            # Download should have been attempted
            mock_file_service.download_datasheet.assert_called_once()
            
            # Failure should be recorded
            assert mock_part_with_lcsc_data.additional_properties['datasheet_downloaded'] == False
            
            # URL should still be saved
            assert mock_part_with_lcsc_data.additional_properties['datasheet_url'] == 'https://invalid-url.com/datasheet.pdf'

    @pytest.mark.asyncio
    async def test_part_number_detection_for_download(self, enrichment_handler_enabled):
        """Test that the correct part number is used for download filename"""
        
        # Test with different part number scenarios
        test_cases = [
            {
                'name': 'part_number_primary',
                'part_number': 'C1779',
                'manufacturer_part_number': None,
                'part_name': 'Some Name',
                'expected': 'C1779'
            },
            {
                'name': 'manufacturer_part_fallback', 
                'part_number': None,
                'manufacturer_part_number': 'CL21A475KAQNNNE',
                'part_name': 'Some Name',
                'expected': 'CL21A475KAQNNNE'
            },
            {
                'name': 'part_name_fallback',
                'part_number': None,
                'manufacturer_part_number': None,
                'part_name': 'TEST-PART-123',
                'expected': 'TEST-PART-123'
            }
        ]
        
        for case in test_cases:
            with patch('MakerMatrix.services.file_download_service.get_file_download_service') as mock_service:
                mock_file_service = Mock()
                mock_file_service.download_datasheet.return_value = {
                    'filename': f'{case["expected"]}_datasheet.pdf',
                    'size': 1024000,
                    'file_uuid': 'test-uuid'
                }
                mock_service.return_value = mock_file_service
                
                # Create part with specific attributes
                part = Mock()
                part.part_number = case['part_number']
                part.manufacturer_part_number = case['manufacturer_part_number']
                part.part_name = case['part_name']
                part.supplier = 'LCSC'
                part.part_vendor = 'LCSC'
                part.additional_properties = {}
                
                enrichment_results = {
                    'fetch_datasheet': {
                        'success': True,
                        'datasheet_url': 'https://example.com/datasheet.pdf'
                    }
                }
                
                await enrichment_handler_enabled._update_part_from_enrichment_results(part, enrichment_results)
                
                # Verify correct part number was used
                call_args = mock_file_service.download_datasheet.call_args
                assert call_args[1]['part_number'] == case['expected'], f"Failed case: {case['name']}"

    @pytest.mark.asyncio 
    async def test_config_loading_from_database(self):
        """Test that config is properly loaded from database"""
        
        # Test that when no explicit config is provided, it loads from database
        part_repo = PartRepository(engine)
        part_service = PartService()
        
        # This should load config from database
        handler = EnrichmentTaskHandlers(part_repo, part_service)
        
        # Should have loaded config with downloads enabled
        assert handler.download_config['download_datasheets'] == True
        assert handler.download_config['download_images'] == True
        assert 'download_timeout_seconds' in handler.download_config


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])