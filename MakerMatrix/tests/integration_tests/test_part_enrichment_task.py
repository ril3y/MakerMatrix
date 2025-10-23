"""
Integration tests for part enrichment task functionality
"""

import pytest
import asyncio
import json
from datetime import datetime
from sqlmodel import Session

from MakerMatrix.models.task_models import TaskModel, TaskType, TaskPriority, TaskStatus
from MakerMatrix.tasks.part_enrichment_task import PartEnrichmentTask
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.database.db import get_session


@pytest.mark.asyncio
async def test_part_enrichment_task_creation():
    """Test that part enrichment task can be created and has correct properties"""
    task_handler = PartEnrichmentTask()

    assert task_handler.task_type == "part_enrichment"
    assert task_handler.name == "Part Enrichment"
    assert "enrich part data" in task_handler.description.lower()


@pytest.mark.asyncio
async def test_part_enrichment_task_missing_part_id():
    """Test that task fails gracefully when part_id is missing"""
    task_handler = PartEnrichmentTask()

    # Create task with missing part_id
    task = TaskModel(
        task_type=TaskType.PART_ENRICHMENT,
        name="Test Task",
        priority=TaskPriority.NORMAL,
        input_data=json.dumps({"supplier": "LCSC"}),  # Missing part_id
    )

    with pytest.raises(ValueError, match="part_id is required"):
        await task_handler.execute(task)


@pytest.mark.asyncio
async def test_part_enrichment_task_part_not_found():
    """Test that task fails gracefully when part doesn't exist"""
    task_handler = PartEnrichmentTask()

    # Create task with non-existent part_id
    task = TaskModel(
        task_type=TaskType.PART_ENRICHMENT,
        name="Test Task",
        priority=TaskPriority.NORMAL,
        input_data=json.dumps({"part_id": "non_existent_part_12345", "supplier": "LCSC"}),
    )

    with pytest.raises(ValueError, match="Part not found"):
        await task_handler.execute(task)


@pytest.mark.asyncio
async def test_part_enrichment_task_with_real_part():
    """Test enrichment task with a real part in the database"""
    task_handler = PartEnrichmentTask()

    # Create a test part first
    with Session(engine) as session:
        test_part = PartModel(
            part_name="Test Resistor", part_number="RES-001-TEST", part_vendor="LCSC", additional_properties={}
        )
        session.add(test_part)
        session.commit()
        session.refresh(test_part)
        test_part_id = test_part.id

    try:
        # Create enrichment task
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test Enrichment",
            priority=TaskPriority.NORMAL,
            input_data=json.dumps({"part_id": test_part_id, "supplier": "LCSC"}),
        )

        # Execute task
        result = await task_handler.execute(task)

        # Verify result
        assert result["status"] == "success"
        assert result["part_id"] == test_part_id
        assert result["supplier"] == "LCSC"
        assert "enriched_fields" in result
        assert "last_enrichment" in result["enriched_fields"]

        # Verify part was updated in database
        with Session(engine) as session:
            updated_part = PartRepository.get_part_by_id(session, test_part_id)
            assert updated_part is not None
            assert "last_enrichment" in updated_part.additional_properties

            enrichment_data = updated_part.additional_properties["last_enrichment"]
            assert enrichment_data["supplier"] == "LCSC"
            assert "timestamp" in enrichment_data
            assert enrichment_data["task_id"] == task.id

    finally:
        # Clean up test part
        with Session(engine) as session:
            test_part = PartRepository.get_part_by_id(session, test_part_id)
            if test_part:
                session.delete(test_part)
                session.commit()


@pytest.mark.asyncio
async def test_part_enrichment_task_progress_updates():
    """Test that task properly updates progress during execution"""
    task_handler = PartEnrichmentTask()
    progress_updates = []

    # Mock the progress update method to capture calls
    original_update = task_handler._update_task_progress

    async def mock_update_progress(task, percentage, step):
        progress_updates.append((percentage, step))
        # Don't call original to avoid needing task service

    task_handler._update_task_progress = mock_update_progress

    # Create a test part first
    with Session(engine) as session:
        test_part = PartModel(part_name="Test Capacitor", part_number="CAP-001-TEST", part_vendor="DigiKey")
        session.add(test_part)
        session.commit()
        session.refresh(test_part)
        test_part_id = test_part.id

    try:
        # Create and execute task
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="Progress Test",
            priority=TaskPriority.NORMAL,
            input_data=json.dumps({"part_id": test_part_id, "supplier": "DigiKey"}),
        )

        await task_handler.execute(task)

        # Verify progress updates were made
        assert len(progress_updates) >= 4  # Should have multiple progress updates

        # Check that progress goes from 0 to 100
        assert progress_updates[0][0] == 0  # First update should be 0%
        assert progress_updates[-1][0] == 100  # Last update should be 100%

        # Check that steps are descriptive
        assert any("initializing" in step.lower() for _, step in progress_updates)
        assert any("completed" in step.lower() for _, step in progress_updates)

    finally:
        # Clean up
        task_handler._update_task_progress = original_update
        with Session(engine) as session:
            test_part = PartRepository.get_part_by_id(session, test_part_id)
            if test_part:
                session.delete(test_part)
                session.commit()


@pytest.mark.asyncio
async def test_part_enrichment_task_preserves_existing_properties():
    """Test that enrichment preserves existing additional_properties"""
    task_handler = PartEnrichmentTask()

    # Create a test part with existing properties
    with Session(engine) as session:
        test_part = PartModel(
            part_name="Test IC",
            part_number="IC-001-TEST",
            part_vendor="Mouser",
            additional_properties={"existing_field": "existing_value", "specifications": {"voltage": "5V"}},
        )
        session.add(test_part)
        session.commit()
        session.refresh(test_part)
        test_part_id = test_part.id

    try:
        # Create and execute enrichment task
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="Preserve Properties Test",
            priority=TaskPriority.NORMAL,
            input_data=json.dumps({"part_id": test_part_id, "supplier": "Mouser"}),
        )

        # Mock progress updates to avoid task service dependency
        original_progress = task_handler._update_task_progress

        async def mock_progress(*args):
            pass

        task_handler._update_task_progress = mock_progress

        try:
            await task_handler.execute(task)
        finally:
            # Restore original progress function
            task_handler._update_task_progress = original_progress

        # Verify existing properties are preserved
        with Session(engine) as session:
            updated_part = PartRepository.get_part_by_id(session, test_part_id)
            assert updated_part is not None

            props = updated_part.additional_properties
            assert "existing_field" in props
            assert props["existing_field"] == "existing_value"
            assert "specifications" in props
            assert props["specifications"]["voltage"] == "5V"
            assert "last_enrichment" in props  # New field added

    finally:
        # Clean up
        with Session(engine) as session:
            test_part = PartRepository.get_part_by_id(session, test_part_id)
            if test_part:
                session.delete(test_part)
                session.commit()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
