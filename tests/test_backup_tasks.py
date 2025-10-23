"""
Test Backup Tasks

Tests for backup task execution including:
- Backup creation with/without encryption
- Backup metadata generation
- Progress tracking
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from datetime import datetime
from pathlib import Path
import zipfile
import json

from MakerMatrix.tasks.database_backup_task import DatabaseBackupTask
from MakerMatrix.models.task_models import TaskModel, TaskStatus


class TestDatabaseBackupTask:
    """Test database backup task execution"""

    @pytest.mark.asyncio
    async def test_backup_creates_encrypted_zip_with_password(self):
        """Test that backup with password creates encrypted ZIP using pyminizip"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-123"
        mock_task_model.input_data = {
            "backup_name": "test_backup",
            "password": "TestPassword123",
            "include_datasheets": True,
            "include_images": True,
            "include_env": True,
        }

        with (
            patch("MakerMatrix.tasks.database_backup_task.pyminizip") as mock_pyminizip,
            patch("MakerMatrix.tasks.database_backup_task.Path") as mock_path_class,
            patch("MakerMatrix.tasks.database_backup_task.shutil") as mock_shutil,
            patch("MakerMatrix.tasks.database_backup_task.asyncio.sleep", new_callable=AsyncMock),
            patch.object(task, "update_progress", new_callable=AsyncMock),
            patch.object(task, "log_info"),
        ):

            # Mock database file
            mock_db_path = Mock()
            mock_db_path.exists.return_value = True
            mock_db_path.stat.return_value.st_size = 1024 * 1024  # 1MB

            # Mock backup directory
            mock_backup_dir = Mock()
            mock_backup_dir.rglob.return_value = [Mock(is_file=lambda: True)]

            # Mock final ZIP path
            mock_final_zip = Mock()
            mock_final_zip.stat.return_value.st_size = 2 * 1024 * 1024  # 2MB compressed
            mock_final_zip.name = "test_backup_encrypted.zip"

            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                result = await task.execute(mock_task_model)

            # Verify pyminizip was called for encryption
            assert mock_pyminizip.compress_multiple.called
            call_args = mock_pyminizip.compress_multiple.call_args
            assert call_args[0][3] == "TestPassword123"  # Password argument

            # Verify result contains encryption info
            assert result["password_protected"] is True
            assert "ZipCrypto" in result["encryption_algorithm"]

    @pytest.mark.asyncio
    async def test_backup_creates_unencrypted_zip_without_password(self):
        """Test that backup without password creates standard ZIP"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-456"
        mock_task_model.input_data = {
            "backup_name": "test_backup_unencrypted",
            "include_datasheets": False,
            "include_images": False,
            "include_env": False,
        }

        with (
            patch("MakerMatrix.tasks.database_backup_task.zipfile.ZipFile") as mock_zipfile,
            patch("MakerMatrix.tasks.database_backup_task.Path") as mock_path_class,
            patch("MakerMatrix.tasks.database_backup_task.shutil") as mock_shutil,
            patch("MakerMatrix.tasks.database_backup_task.asyncio.sleep", new_callable=AsyncMock),
            patch.object(task, "update_progress", new_callable=AsyncMock),
            patch.object(task, "log_info"),
        ):

            mock_db_path = Mock()
            mock_db_path.exists.return_value = True
            mock_db_path.stat.return_value.st_size = 512 * 1024  # 512KB

            mock_final_zip = Mock()
            mock_final_zip.stat.return_value.st_size = 400 * 1024  # 400KB compressed
            mock_final_zip.name = "test_backup_unencrypted.zip"

            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                result = await task.execute(mock_task_model)

            # Verify standard zipfile was used (not pyminizip)
            assert mock_zipfile.called

            # Verify result shows no encryption
            assert result["password_protected"] is False

    @pytest.mark.asyncio
    async def test_backup_includes_metadata_with_version_info(self):
        """Test that backup metadata includes MakerMatrix version"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-789"
        mock_task_model.input_data = {
            "backup_name": "test_backup_metadata",
            "include_datasheets": True,
            "include_images": True,
            "include_env": True,
        }

        with (
            patch("MakerMatrix.tasks.database_backup_task.__version__", "1.0.0"),
            patch("MakerMatrix.tasks.database_backup_task.__schema_version__", "1.0.0"),
            patch("MakerMatrix.tasks.database_backup_task.zipfile.ZipFile"),
            patch("MakerMatrix.tasks.database_backup_task.Path"),
            patch("MakerMatrix.tasks.database_backup_task.shutil"),
            patch("MakerMatrix.tasks.database_backup_task.asyncio.sleep", new_callable=AsyncMock),
            patch("builtins.open", mock_open()) as mock_file,
            patch.object(task, "update_progress", new_callable=AsyncMock),
            patch.object(task, "log_info"),
        ):

            mock_db_path = Mock()
            mock_db_path.exists.return_value = True
            mock_db_path.stat.return_value.st_size = 1024 * 1024

            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                result = await task.execute(mock_task_model)

            # Verify metadata contains version info
            assert result["makermatrix_version"] == "1.0.0"
            assert result["schema_version"] == "1.0.0"
            assert result["backup_format_version"] == "2.0"
            assert "python_version" in result

    @pytest.mark.asyncio
    async def test_backup_progress_tracking(self):
        """Test that backup updates progress at each major step"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-progress"
        mock_task_model.input_data = {
            "backup_name": "test_progress",
            "include_datasheets": True,
            "include_images": True,
            "include_env": True,
        }

        progress_updates = []

        async def capture_progress(task_model, percentage, message):
            progress_updates.append((percentage, message))

        with (
            patch("MakerMatrix.tasks.database_backup_task.zipfile.ZipFile"),
            patch("MakerMatrix.tasks.database_backup_task.Path"),
            patch("MakerMatrix.tasks.database_backup_task.shutil"),
            patch("MakerMatrix.tasks.database_backup_task.asyncio.sleep", new_callable=AsyncMock),
            patch.object(task, "update_progress", side_effect=capture_progress),
            patch.object(task, "log_info"),
        ):

            mock_db_path = Mock()
            mock_db_path.exists.return_value = True
            mock_db_path.stat.return_value.st_size = 1024 * 1024

            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                await task.execute(mock_task_model)

            # Verify progress was updated multiple times
            assert len(progress_updates) >= 5

            # Verify progress increases
            percentages = [p[0] for p in progress_updates]
            assert percentages == sorted(percentages)  # Should be monotonically increasing

            # Verify final progress is 100%
            assert progress_updates[-1][0] == 100

            # Verify meaningful status messages
            messages = [p[1] for p in progress_updates]
            assert any("database" in msg.lower() for msg in messages)
            assert any("completed" in msg.lower() or "success" in msg.lower() for msg in messages)

    @pytest.mark.asyncio
    async def test_backup_with_missing_database_raises_error(self):
        """Test that backup fails gracefully when database file is not found"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-error"
        mock_task_model.input_data = {"backup_name": "test_error"}

        mock_db_path = Mock()
        mock_db_path.exists.return_value = False  # Database doesn't exist

        with pytest.raises(FileNotFoundError) as exc_info:
            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                await task.execute(mock_task_model)

        assert "Database file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_backup_filename_includes_encrypted_suffix(self):
        """Test that encrypted backups have '_encrypted' in filename"""
        task = DatabaseBackupTask()

        mock_task_model = Mock(spec=TaskModel)
        mock_task_model.id = "task-naming"
        mock_task_model.input_data = {"backup_name": "test_naming", "password": "SecretPassword"}

        with (
            patch("MakerMatrix.tasks.database_backup_task.pyminizip"),
            patch("MakerMatrix.tasks.database_backup_task.Path"),
            patch("MakerMatrix.tasks.database_backup_task.shutil"),
            patch("MakerMatrix.tasks.database_backup_task.asyncio.sleep", new_callable=AsyncMock),
            patch.object(task, "update_progress", new_callable=AsyncMock),
            patch.object(task, "log_info"),
        ):

            mock_db_path = Mock()
            mock_db_path.exists.return_value = True
            mock_db_path.stat.return_value.st_size = 1024

            mock_final_zip = Mock()
            mock_final_zip.stat.return_value.st_size = 512
            mock_final_zip.name = "test_naming_encrypted.zip"

            with patch.object(task, "_get_database_path", return_value=mock_db_path):
                result = await task.execute(mock_task_model)

            # Verify filename contains '_encrypted'
            assert "_encrypted" in result["backup_filename"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
