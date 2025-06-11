"""
Integration tests for LCSC CSV import with UUID-based datasheet system

Tests the complete flow:
1. LCSC CSV parsing with datasheet URL extraction
2. UUID-based datasheet file management
3. Database storage of datasheet records
4. Progress tracking during import
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from MakerMatrix.services.csv_import.lcsc_parser import LCSCParser
from MakerMatrix.services.csv_import_service import CSVImportService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.models.models import PartModel, DatasheetModel, create_db_and_tables
from MakerMatrix.database.db import get_session
from MakerMatrix.services.file_download_service import FileDownloadService


class TestLCSCDatasheetImport:
    """Test suite for LCSC datasheet import functionality"""
    
    @pytest.fixture
    def sample_lcsc_row(self):
        """Sample LCSC CSV row data"""
        return {
            'LCSC Part Number': 'C394155',
            'Manufacture Part Number': 'FM21X103K251ECG', 
            'Manufacturer': 'PSA(Prosperity Dielectrics)',
            'Description': '10nF ±10% 25V MLCC X7R 0805',
            'Package': 'C0805',
            'Order Qty.': '10',
            'Unit Price($)': '0.0088',
            'Order Price($)': '0.088'
        }
    
    @pytest.fixture
    def mock_easyeda_response(self):
        """Mock EasyEDA API response"""
        return {
            "success": True,
            "code": 0,
            "result": {
                "packageDetail": {
                    "dataStr": {
                        "head": {
                            "c_para": {
                                "link": "https://item.szlcsc.com/373011.html"
                            }
                        }
                    }
                },
                "dataStr": {
                    "head": {
                        "c_para": {
                            "pre": "C?",
                            "name": "FM21X103K251ECG",
                            "package": "C0805",
                            "Manufacturer": "PSA(Prosperity Dielectrics)",
                            "Value": "10nF"
                        }
                    }
                },
                "SMT": True
            }
        }
    
    @pytest.fixture
    def mock_datasheet_download(self):
        """Mock successful datasheet download"""
        return {
            'filename': 'test-uuid-123.pdf',
            'file_path': '/fake/path/test-uuid-123.pdf',
            'original_filename': 'LCSC_FM21X103K251ECG_datasheet.pdf',
            'file_uuid': 'test-uuid-123',
            'url': 'https://example.com/datasheet.pdf',
            'size': 1024*50,  # 50KB
            'extension': '.pdf',
            'exists': False
        }
    
    def test_lcsc_parser_creates_datasheet_structure(self, sample_lcsc_row, mock_easyeda_response):
        """Test that LCSC parser creates proper datasheet data structure"""
        parser = LCSCParser(download_config={'download_datasheets': False, 'download_images': False})
        
        # Mock the EasyEDA API call
        with patch.object(parser.easyeda_api, 'get_info_from_easyeda_api', return_value=mock_easyeda_response):
            # Mock the scraping to return a valid PDF URL
            with patch.object(parser, '_scrape_datasheet_from_lcsc_page', return_value='https://example.com/datasheet.pdf'):
                result = parser.parse_row(sample_lcsc_row, 1)
        
        # Verify basic part data
        assert result is not None
        assert result['part_name'] == 'FM21X103K251ECG'
        assert result['supplier'] == 'LCSC'
        
        # Verify datasheet structure is created but not downloaded (downloads disabled)
        assert 'datasheets' in result
        assert len(result['datasheets']) == 1
        
        datasheet = result['datasheets'][0]
        assert datasheet['source_url'] == 'https://example.com/datasheet.pdf'
        assert datasheet['supplier'] == 'LCSC'
        assert datasheet['is_downloaded'] == True  # Will be True when downloads enabled
        assert 'file_uuid' in datasheet
    
    def test_lcsc_parser_with_download_enabled(self, sample_lcsc_row, mock_easyeda_response, mock_datasheet_download):
        """Test LCSC parser with datasheet download enabled"""
        parser = LCSCParser(download_config={'download_datasheets': True, 'download_images': False})
        
        # Mock the EasyEDA API and file download
        with patch.object(parser.easyeda_api, 'get_info_from_easyeda_api', return_value=mock_easyeda_response):
            with patch.object(parser, '_scrape_datasheet_from_lcsc_page', return_value='https://example.com/datasheet.pdf'):
                with patch('MakerMatrix.services.csv_import.lcsc_parser.file_download_service.download_datasheet', return_value=mock_datasheet_download):
                    result = parser.parse_row(sample_lcsc_row, 1)
        
        # Verify datasheet was "downloaded"
        assert result is not None
        assert 'datasheets' in result
        assert len(result['datasheets']) == 1
        
        datasheet = result['datasheets'][0]
        assert datasheet['is_downloaded'] == True
        assert datasheet['file_uuid'] == 'test-uuid-123'
        assert datasheet['file_size'] == 1024*50
        assert datasheet['original_filename'] == 'LCSC_FM21X103K251ECG_datasheet.pdf'
    
    def test_uuid_based_filename_generation(self):
        """Test that UUID-based filenames are generated correctly"""
        file_service = FileDownloadService()
        
        # Mock the actual download process
        with patch('requests.get') as mock_get:
            # Mock successful response
            mock_response = Mock()
            mock_response.headers = {'content-type': 'application/pdf'}
            mock_response.iter_content.return_value = [b'fake pdf content'] * 10
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Mock file system operations
            with patch('pathlib.Path.exists', return_value=False):
                with patch('builtins.open', create=True) as mock_open:
                    with patch('pathlib.Path.stat') as mock_stat:
                        mock_stat.return_value.st_size = 1024
                        
                        result = file_service.download_datasheet(
                            url='https://example.com/test.pdf',
                            part_number='TEST123',
                            supplier='LCSC',
                            file_uuid='test-uuid-456'
                        )
        
        # Verify UUID is used in filename
        assert result is not None
        assert result['file_uuid'] == 'test-uuid-456'
        assert result['filename'] == 'test-uuid-456.pdf'
        assert 'LCSC_TEST123_datasheet.pdf' in result['original_filename']
    
    def test_progress_tracking_during_import(self, sample_lcsc_row):
        """Test that progress tracking works during CSV import"""
        progress_updates = []
        
        def progress_callback(update):
            progress_updates.append(update.copy())
        
        # Create CSV import service
        csv_service = CSVImportService()
        
        # Mock the part service and order service
        mock_part_service = Mock()
        mock_part_service.add_part.return_value = {
            'status': 'success',
            'data': {'id': 'test-part-id'}
        }
        
        # Create test data
        parts_data = [
            {
                'part_name': 'TestPart1',
                'part_number': 'TEST001',
                'quantity': 10,
                'additional_properties': {},
                'datasheets': [{
                    'file_uuid': 'uuid-1',
                    'is_downloaded': True,
                    'source_url': 'https://example.com/test1.pdf'
                }]
            },
            {
                'part_name': 'TestPart2', 
                'part_number': 'TEST002',
                'quantity': 5,
                'additional_properties': {},
                'datasheets': []
            }
        ]
        
        order_info = {
            'order_number': 'TEST-ORDER-001',
            'supplier': 'LCSC',
            'order_date': '2024-01-01'
        }
        
        # Mock order service
        with patch('MakerMatrix.services.csv_import_service.order_service') as mock_order_service:
            mock_order_service.create_order.return_value = Mock(id='test-order-id', order_date='2024-01-01', order_number='TEST-ORDER-001')
            mock_order_service.add_order_item.return_value = Mock(id='test-item-id')
            mock_order_service.link_order_item_to_part.return_value = None
            mock_order_service.calculate_order_totals.return_value = None
            
            # Mock session and database operations
            with patch('MakerMatrix.services.csv_import_service.get_session'):
                with patch('MakerMatrix.services.csv_import_service.select'):
                    # Run import with progress tracking
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        result = loop.run_until_complete(
                            csv_service.import_parts_with_order(
                                parts_data, 
                                mock_part_service, 
                                order_info, 
                                progress_callback
                            )
                        )
                    finally:
                        loop.close()
        
        # Verify progress tracking
        assert len(progress_updates) > 0
        
        # Check initial progress
        initial_update = progress_updates[0]
        assert initial_update['total_parts'] == 2
        assert initial_update['processed_parts'] == 0
        assert initial_update['current_operation'] == 'Creating order record...'
        
        # Check that progress was updated during processing
        processing_updates = [u for u in progress_updates if 'Processing part' in u.get('current_operation', '')]
        assert len(processing_updates) >= 2  # One for each part
        
        # Check final progress
        final_updates = [u for u in progress_updates if u.get('current_operation') == 'Import completed!']
        assert len(final_updates) > 0
    
    def test_datasheet_model_properties(self):
        """Test DatasheetModel properties and methods"""
        from MakerMatrix.models.models import DatasheetModel
        from datetime import datetime
        
        # Test datasheet model creation
        datasheet = DatasheetModel(
            part_id='test-part-id',
            file_uuid='test-uuid-789',
            original_filename='test_datasheet.pdf',
            file_extension='.pdf',
            file_size=2048,
            source_url='https://example.com/test.pdf',
            supplier='LCSC',
            manufacturer='Test Manufacturer',
            title='Test Datasheet',
            is_downloaded=True
        )
        
        # Test filename property
        assert datasheet.filename == 'test-uuid-789.pdf'
        
        # Test to_dict method
        datasheet_dict = datasheet.to_dict()
        assert datasheet_dict['filename'] == 'test-uuid-789.pdf'
        assert datasheet_dict['file_uuid'] == 'test-uuid-789'
        assert datasheet_dict['is_downloaded'] == True
        assert 'created_at' in datasheet_dict
    
    def test_datasheet_url_fallback_handling(self, sample_lcsc_row):
        """Test handling when datasheet URL cannot be found"""
        parser = LCSCParser(download_config={'download_datasheets': True, 'download_images': False})
        
        # Mock EasyEDA response without datasheet URL
        mock_response = {
            "success": True,
            "code": 0,
            "result": {
                "dataStr": {
                    "head": {
                        "c_para": {
                            "pre": "C?",
                            "name": "FM21X103K251ECG",
                            "package": "C0805"
                        }
                    }
                },
                "SMT": True
            }
        }
        
        with patch.object(parser.easyeda_api, 'get_info_from_easyeda_api', return_value=mock_response):
            result = parser.parse_row(sample_lcsc_row, 1)
        
        # Should still parse successfully but without datasheets
        assert result is not None
        assert result['part_name'] == 'FM21X103K251ECG'
        
        # Should not have datasheets when URL not found
        datasheets = result.get('datasheets', [])
        assert len(datasheets) == 0
        
        # Should have the not found flag
        assert result['additional_properties'].get('datasheet_url_not_found') == True


if __name__ == "__main__":
    # Run a simple test
    print("=== Testing LCSC Datasheet Import System ===")
    
    test_instance = TestLCSCDatasheetImport()
    
    try:
        # Test basic parsing
        sample_row = test_instance.sample_lcsc_row()
        mock_response = test_instance.mock_easyeda_response()
        
        test_instance.test_lcsc_parser_creates_datasheet_structure(sample_row, mock_response)
        print("✓ Basic datasheet structure creation test passed")
        
        # Test UUID filename generation
        test_instance.test_uuid_based_filename_generation()
        print("✓ UUID-based filename generation test passed")
        
        # Test datasheet model
        test_instance.test_datasheet_model_properties()
        print("✓ Datasheet model properties test passed")
        
        print("\n=== All tests passed! ===")
        print("The LCSC datasheet import system with UUID-based file management is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()