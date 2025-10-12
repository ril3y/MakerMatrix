"""
Test script for part service datasheet cleanup functionality.

These tests verify that the enriched datasheet cleanup logic is present
in the PartService._cleanup_part_files method.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from MakerMatrix.services.data.part_service import PartService


@pytest.fixture
def part_service():
    """Create a PartService instance."""
    return PartService()


def test_cleanup_part_files_handles_enriched_datasheet(part_service):
    """Test that _cleanup_part_files attempts to delete enriched datasheets."""
    # Create a mock part with enriched datasheet
    part = Mock()
    part.id = "part-456"
    part.part_name = "Enriched Part"
    part.additional_properties = {
        'datasheet_filename': 'enriched-uuid-123.pdf',
        'datasheet_downloaded': True,
        'datasheet_size': 1024000
    }
    part.datasheets = []  # No uploaded datasheets

    # Mock os.remove to track if it's called
    with patch('os.remove') as mock_remove:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                # Execute cleanup
                deleted_count = part_service._cleanup_part_files(part)

                # Verify that os.remove was called (indicating enriched datasheet cleanup was attempted)
                assert mock_remove.call_count >= 1


def test_cleanup_part_files_with_no_enriched_datasheet(part_service):
    """Test that cleanup works when part has no enriched datasheet."""
    # Create a mock part without enriched datasheet
    part = Mock()
    part.id = "part-no-enriched"
    part.part_name = "No Enriched Part"
    part.additional_properties = {}
    part.datasheets = []

    # Execute cleanup - should not raise an exception
    deleted_count = part_service._cleanup_part_files(part)

    # Should return 0 or non-negative number
    assert deleted_count >= 0


def test_cleanup_part_files_handles_none_additional_properties(part_service):
    """Test that cleanup handles None additional_properties gracefully."""
    part = Mock()
    part.id = "part-none"
    part.part_name = "None Props"
    part.additional_properties = None
    part.datasheets = []

    # Execute cleanup - should not raise an exception
    deleted_count = part_service._cleanup_part_files(part)

    # Should return 0 or non-negative number
    assert deleted_count >= 0


def test_cleanup_part_files_handles_missing_file(part_service):
    """Test that cleanup handles missing enriched datasheet file gracefully."""
    part = Mock()
    part.id = "part-missing"
    part.part_name = "Missing Datasheet"
    part.additional_properties = {
        'datasheet_filename': 'nonexistent-file.pdf',
        'datasheet_downloaded': True
    }
    part.datasheets = []

    # Mock Path.exists to return False (file doesn't exist)
    with patch('pathlib.Path.exists', return_value=False):
        # Execute cleanup - should handle missing file gracefully
        deleted_count = part_service._cleanup_part_files(part)

        # Should not raise an exception
        assert deleted_count >= 0


def test_cleanup_part_files_checks_datasheet_filename_key(part_service):
    """Test that cleanup checks for datasheet_filename key in additional_properties."""
    part_with_key = Mock()
    part_with_key.id = "part-with-key"
    part_with_key.part_name = "With Key"
    part_with_key.additional_properties = {'datasheet_filename': 'test.pdf'}
    part_with_key.datasheets = []

    part_without_key = Mock()
    part_without_key.id = "part-without-key"
    part_without_key.part_name = "Without Key"
    part_without_key.additional_properties = {'some_other_key': 'value'}
    part_without_key.datasheets = []

    # Mock os.remove to track calls
    with patch('os.remove') as mock_remove:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                # Part with key should attempt deletion
                part_service._cleanup_part_files(part_with_key)
                first_call_count = mock_remove.call_count

                # Part without key should not attempt deletion
                part_service._cleanup_part_files(part_without_key)
                second_call_count = mock_remove.call_count

                # First call should have attempted deletion, second should not
                assert first_call_count >= 1
                # Call count should not increase for part without key
                assert second_call_count == first_call_count


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
