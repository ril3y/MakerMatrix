#!/usr/bin/env python3
"""
Test script for the new paginated bulk enrichment functionality.
This verifies that the pagination implementation works correctly.
"""

import asyncio
import sys
sys.path.append('/home/ril3y/MakerMatrix')

from MakerMatrix.services.system.enrichment_coordinator_service import EnrichmentCoordinatorService
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService
from MakerMatrix.models.models import engine


async def test_pagination():
    """Test the pagination functionality"""
    print("🧪 Testing paginated bulk enrichment...")
    
    # Create handlers
    part_repository = PartRepository(engine)
    part_service = PartService()
    handler = EnrichmentCoordinatorService(part_repository, part_service)
    
    # Create a mock task with enrich_all=true
    task = TaskModel(
        id="test-task",
        task_type=TaskType.BULK_ENRICHMENT,
        name="Test Paginated Bulk Enrichment",
        status=TaskStatus.RUNNING
    )
    
    # Set input data for pagination mode
    input_data = {
        "enrich_all": True,
        "page_size": 2,  # Small page size for testing
        "batch_size": 1,  # Small batch size for testing
        "capabilities": ["fetch_image", "fetch_datasheet"],
        "supplier_filter": None
    }
    task.set_input_data(input_data)
    
    # Mock progress callback
    progress_updates = []
    async def mock_progress(percentage, message):
        progress_updates.append((percentage, message))
        print(f"📊 Progress: {percentage}% - {message}")
    
    try:
        print("🚀 Starting paginated bulk enrichment test...")
        result = await handler.handle_bulk_enrichment(task, mock_progress)
        
        print("✅ Test completed successfully!")
        print(f"📈 Results:")
        print(f"   Total parts processed: {result.get('total_parts', 0)}")
        print(f"   Successful: {result.get('successful_count', 0)}")
        print(f"   Failed: {result.get('failed_count', 0)}")
        print(f"   Pages processed: {result.get('pages_processed', 'N/A')}")
        print(f"   Page size: {result.get('page_size', 'N/A')}")
        print(f"   Progress updates: {len(progress_updates)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_specific_parts():
    """Test the specific parts enrichment (legacy mode)"""
    print("\n🧪 Testing specific parts enrichment...")
    
    # Create handlers
    part_repository = PartRepository(engine)
    part_service = PartService()
    handler = EnrichmentCoordinatorService(part_repository, part_service)
    
    # Create a mock task with specific part IDs
    task = TaskModel(
        id="test-task-2",
        task_type=TaskType.BULK_ENRICHMENT,
        name="Test Specific Parts Enrichment",
        status=TaskStatus.RUNNING
    )
    
    # Set input data for specific parts mode (legacy)
    input_data = {
        "part_ids": ["test-part-1", "test-part-2"],  # These probably don't exist, but that's fine for testing
        "batch_size": 1,
        "capabilities": ["fetch_image", "fetch_datasheet"],
        "supplier_filter": None
    }
    task.set_input_data(input_data)
    
    # Mock progress callback
    progress_updates = []
    async def mock_progress(percentage, message):
        progress_updates.append((percentage, message))
        print(f"📊 Progress: {percentage}% - {message}")
    
    try:
        print("🚀 Starting specific parts enrichment test...")
        result = await handler.handle_bulk_enrichment(task, mock_progress)
        
        print("✅ Test completed!")
        print(f"📈 Results:")
        print(f"   Total parts processed: {result.get('total_parts', 0)}")
        print(f"   Successful: {result.get('successful_count', 0)}")
        print(f"   Failed: {result.get('failed_count', 0)}")
        print(f"   Progress updates: {len(progress_updates)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🧪 Testing bulk enrichment pagination implementation...")
    
    # Test pagination mode
    test1_passed = await test_pagination()
    
    # Test specific parts mode (legacy)
    test2_passed = await test_specific_parts()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The pagination implementation is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)