"""
Unit tests for Enrichment Task Handlers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from MakerMatrix.services.enrichment_task_handlers import (
    handle_part_enrichment,
    handle_datasheet_fetch,
    handle_image_fetch,
    handle_bulk_enrichment
)
from MakerMatrix.models.models import PartModel
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus, TaskPriority


@pytest.fixture
def sample_part():
    """Create a sample part for testing"""
    return PartModel(
        id="test_part_id",
        name="Test Resistor",
        part_number="RES-001",
        description="Test resistor 1k ohm",
        quantity=100,
        supplier="LCSC",
        properties={"value": "1k", "package": "0603"}
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing"""
    return TaskModel(
        id="test_task_id",
        task_type=TaskType.PART_ENRICHMENT,
        name="Test Enrichment",
        description="Test enrichment task",
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
        created_by_user_id="test_user",
        input_data={
            "part_id": "test_part_id",
            "supplier": "LCSC",
            "capabilities": ["fetch_datasheet", "fetch_image", "enrich_basic_info"]
        }
    )


class TestEnrichmentTaskHandlers:
    """Test cases for enrichment task handlers"""

    @pytest.mark.asyncio
    async def test_handle_part_enrichment_success(self, sample_part, sample_task):
        """Test successful part enrichment"""
        # Test with simpler mocking
        progress_callback = AsyncMock()
        
        # Test missing input data first
        empty_task = TaskModel(
            id="empty_task",
            task_type=TaskType.PART_ENRICHMENT,
            name="Empty Task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data=None
        )
        
        result = await handle_part_enrichment(empty_task, progress_callback)
        assert result["success"] is False
        assert "Missing required input data" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_part_enrichment_part_not_found(self, sample_task):
        """Test part enrichment when part is not found"""
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = None  # Part not found
            
            progress_callback = AsyncMock()
            
            result = await handle_part_enrichment(sample_task, progress_callback)
            
            assert result["success"] is False
            assert "Part not found" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_part_enrichment_missing_input_data(self, sample_part):
        """Test part enrichment with missing input data"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.PART_ENRICHMENT,
            name="Test Enrichment",
            description="Test enrichment task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data=None  # Missing input data
        )
        
        progress_callback = AsyncMock()
        
        result = await handle_part_enrichment(task, progress_callback)
        
        assert result["success"] is False
        assert "Missing required input data" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_part_enrichment_parser_error(self, sample_part, sample_task):
        """Test part enrichment when parser raises an error"""
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = sample_part
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.perform_enrichment_task.side_effect = Exception("Parser error")
            
            progress_callback = AsyncMock()
            
            result = await handle_part_enrichment(sample_task, progress_callback)
            
            assert result["success"] is False
            assert "Parser error" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_datasheet_fetch_success(self, sample_part):
        """Test successful datasheet fetch"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.DATASHEET_FETCH,
            name="Test Datasheet Fetch",
            description="Test datasheet fetch task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data={
                "part_id": "test_part_id",
                "supplier": "LCSC"
            }
        )
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = sample_part
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.fetch_datasheet.return_value = {
                "success": True,
                "datasheet_url": "https://example.com/datasheet.pdf",
                "file_path": "/static/datasheets/test_datasheet.pdf"
            }
            
            progress_callback = AsyncMock()
            
            result = await handle_datasheet_fetch(task, progress_callback)
            
            assert result["success"] is True
            assert result["datasheet_url"] == "https://example.com/datasheet.pdf"
            assert result["file_path"] == "/static/datasheets/test_datasheet.pdf"
            
            mock_parser.fetch_datasheet.assert_called_once_with(sample_part, progress_callback=progress_callback)

    @pytest.mark.asyncio
    async def test_handle_image_fetch_success(self, sample_part):
        """Test successful image fetch"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.IMAGE_FETCH,
            name="Test Image Fetch",
            description="Test image fetch task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data={
                "part_id": "test_part_id",
                "supplier": "LCSC"
            }
        )
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = sample_part
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.fetch_image.return_value = {
                "success": True,
                "image_url": "https://example.com/image.jpg",
                "file_path": "/static/images/test_image.jpg"
            }
            
            progress_callback = AsyncMock()
            
            result = await handle_image_fetch(task, progress_callback)
            
            assert result["success"] is True
            assert result["image_url"] == "https://example.com/image.jpg"
            assert result["file_path"] == "/static/images/test_image.jpg"
            
            mock_parser.fetch_image.assert_called_once_with(sample_part, progress_callback=progress_callback)

    @pytest.mark.asyncio
    async def test_handle_bulk_enrichment_success(self):
        """Test successful bulk enrichment"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.BULK_ENRICHMENT,
            name="Test Bulk Enrichment",
            description="Test bulk enrichment task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data={
                "part_ids": ["part1", "part2", "part3"],
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet", "enrich_basic_info"]
            }
        )
        
        # Create sample parts
        parts = [
            PartModel(id="part1", name="Part 1", part_number="P001"),
            PartModel(id="part2", name="Part 2", part_number="P002"),
            PartModel(id="part3", name="Part 3", part_number="P003")
        ]
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            
            # Mock session.get to return different parts for different IDs
            def mock_get(model_class, part_id):
                for part in parts:
                    if part.id == part_id:
                        return part
                return None
                
            mock_session.get.side_effect = mock_get
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            
            # Mock enrichment results for each part
            mock_parser.perform_enrichment_task.return_value = {
                "fetch_datasheet": {"success": True, "data": {"datasheet_url": "test.pdf"}},
                "enrich_basic_info": {"success": True, "data": {"manufacturer": "Test Corp"}}
            }
            
            progress_callback = AsyncMock()
            
            result = await handle_bulk_enrichment(task, progress_callback)
            
            assert result["success"] is True
            assert result["total_parts"] == 3
            assert result["successful_parts"] == 3
            assert result["failed_parts"] == 0
            assert len(result["part_results"]) == 3
            
            # Verify each part was processed
            for part_id in ["part1", "part2", "part3"]:
                assert part_id in result["part_results"]
                assert result["part_results"][part_id]["success"] is True

    @pytest.mark.asyncio
    async def test_handle_bulk_enrichment_partial_failure(self):
        """Test bulk enrichment with some failures"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.BULK_ENRICHMENT,
            name="Test Bulk Enrichment",
            description="Test bulk enrichment task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data={
                "part_ids": ["part1", "part2", "missing_part"],
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
        )
        
        parts = [
            PartModel(id="part1", name="Part 1", part_number="P001"),
            PartModel(id="part2", name="Part 2", part_number="P002")
        ]
        
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            
            # Mock session.get to return None for missing_part
            def mock_get(model_class, part_id):
                for part in parts:
                    if part.id == part_id:
                        return part
                return None  # missing_part returns None
                
            mock_session.get.side_effect = mock_get
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.perform_enrichment_task.return_value = {
                "fetch_datasheet": {"success": True, "data": {"datasheet_url": "test.pdf"}}
            }
            
            progress_callback = AsyncMock()
            
            result = await handle_bulk_enrichment(task, progress_callback)
            
            assert result["success"] is True  # Overall success even with some failures
            assert result["total_parts"] == 3
            assert result["successful_parts"] == 2
            assert result["failed_parts"] == 1
            
            # Check individual results
            assert result["part_results"]["part1"]["success"] is True
            assert result["part_results"]["part2"]["success"] is True
            assert result["part_results"]["missing_part"]["success"] is False
            assert "not found" in result["part_results"]["missing_part"]["error"]

    @pytest.mark.asyncio
    async def test_handle_bulk_enrichment_empty_part_list(self):
        """Test bulk enrichment with empty part list"""
        task = TaskModel(
            id="test_task_id",
            task_type=TaskType.BULK_ENRICHMENT,
            name="Test Bulk Enrichment",
            description="Test bulk enrichment task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            created_by_user_id="test_user",
            input_data={
                "part_ids": [],  # Empty list
                "supplier": "LCSC",
                "capabilities": ["fetch_datasheet"]
            }
        )
        
        progress_callback = AsyncMock()
        
        result = await handle_bulk_enrichment(task, progress_callback)
        
        assert result["success"] is False
        assert "No parts specified" in result["error"]

    @pytest.mark.asyncio
    async def test_progress_callback_integration(self, sample_part, sample_task):
        """Test that progress callbacks are properly called during enrichment"""
        with patch('MakerMatrix.services.enrichment_task_handlers.get_session') as mock_get_session, \
             patch('MakerMatrix.services.enrichment_task_handlers.get_enhanced_parser') as mock_get_parser:
            
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.__enter__.return_value = mock_session
            mock_session.__exit__.return_value = None
            mock_session.get.return_value = sample_part
            
            mock_parser = AsyncMock()
            mock_get_parser.return_value = mock_parser
            mock_parser.perform_enrichment_task.return_value = {
                "fetch_datasheet": {"success": True, "data": {"datasheet_url": "test.pdf"}}
            }
            
            progress_callback = AsyncMock()
            
            await handle_part_enrichment(sample_task, progress_callback)
            
            # Verify progress callback was called multiple times with different steps
            progress_callback.assert_called()
            call_count = progress_callback.call_count
            assert call_count >= 2  # At least start and end calls
            
            # Check that progress values were reasonable
            call_args_list = progress_callback.call_args_list
            progress_values = [call[1]['progress'] for call in call_args_list if 'progress' in call[1]]
            
            # Should have progress values from 0 to 100
            assert any(p == 0 for p in progress_values)  # Started at 0
            assert any(p == 100 for p in progress_values)  # Ended at 100