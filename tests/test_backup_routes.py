"""
Test Backup Routes

Tests for backup management API endpoints including:
- Configuration management
- Password security
- Backup creation/restore
- Backup list/download/delete operations
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from pathlib import Path

from MakerMatrix.models.backup_models import BackupConfigModel
from MakerMatrix.models.user_models import UserModel


class TestBackupConfigRoutes:
    """Test backup configuration API endpoints"""

    @pytest.mark.asyncio
    async def test_get_backup_config_never_returns_password(self):
        """Test that GET /api/backup/config never returns the actual password"""
        # Create a mock config with a password set
        mock_config = BackupConfigModel(
            id="test-config-1",
            schedule_enabled=True,
            schedule_type="nightly",
            retention_count=7,
            encryption_required=True,
            encryption_password="SecretPassword123",  # This should never be returned
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mock the database session
        with patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            # Import and call the route
            from MakerMatrix.routers.backup_routes import get_backup_config

            mock_user = Mock(spec=UserModel)
            response = await get_backup_config(current_user=mock_user)

            # Verify password is NOT in response
            assert response.data["encryption_password"] is None
            assert "SecretPassword123" not in str(response)

            # Verify other fields are present
            assert response.data["schedule_enabled"] is True
            assert response.data["schedule_type"] == "nightly"
            assert response.data["encryption_required"] is True

    @pytest.mark.asyncio
    async def test_password_set_endpoint_returns_boolean(self):
        """Test that /api/backup/config/password-set returns only a boolean"""
        # Test when password is set
        mock_config_with_password = BackupConfigModel(id="test-config-2", encryption_password="SomePassword")

        with patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config_with_password

            from MakerMatrix.routers.backup_routes import check_password_set

            mock_user = Mock(spec=UserModel)
            response = await check_password_set(current_user=mock_user)

            # Verify only boolean is returned
            assert response.data["password_set"] is True
            assert "SomePassword" not in str(response)
            assert len(response.data) == 1  # Only password_set field

    @pytest.mark.asyncio
    async def test_password_set_endpoint_false_when_no_password(self):
        """Test that password_set returns False when no password configured"""
        mock_config_no_password = BackupConfigModel(id="test-config-3", encryption_password=None)

        with patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config_no_password

            from MakerMatrix.routers.backup_routes import check_password_set

            mock_user = Mock(spec=UserModel)
            response = await check_password_set(current_user=mock_user)

            assert response.data["password_set"] is False

    @pytest.mark.asyncio
    async def test_password_set_endpoint_false_when_empty_password(self):
        """Test that password_set returns False for empty string password"""
        mock_config_empty_password = BackupConfigModel(id="test-config-4", encryption_password="")

        with patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config_empty_password

            from MakerMatrix.routers.backup_routes import check_password_set

            mock_user = Mock(spec=UserModel)
            response = await check_password_set(current_user=mock_user)

            assert response.data["password_set"] is False

    @pytest.mark.asyncio
    async def test_update_config_accepts_password(self):
        """Test that update config endpoint accepts and saves password"""
        from MakerMatrix.models.backup_models import BackupConfigUpdate

        mock_config = BackupConfigModel(id="test-config-5", encryption_password=None)

        with patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            # Mock the scheduler reload
            with patch("MakerMatrix.services.system.backup_scheduler.backup_scheduler") as mock_scheduler:
                mock_scheduler.reload_schedule = AsyncMock()

                from MakerMatrix.routers.backup_routes import update_backup_config

                mock_user = Mock(spec=UserModel)
                config_update = BackupConfigUpdate(encryption_password="NewPassword123")

                response = await update_backup_config(config_update=config_update, current_user=mock_user)

                # Verify the password was set in the config
                assert mock_config.encryption_password == "NewPassword123"
                mock_session.add.assert_called()
                mock_session.commit.assert_called()


class TestBackupCreation:
    """Test backup creation endpoints"""

    @pytest.mark.asyncio
    async def test_create_backup_with_password(self):
        """Test creating an encrypted backup with password"""
        with (
            patch("MakerMatrix.routers.backup_routes.task_service") as mock_task_service,
            patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class,
        ):

            mock_task_response = Mock()
            mock_task_response.success = True
            mock_task_response.data = {
                "id": "task-123",
                "task_type": "backup_creation",
                "name": "Encrypted Backup: test_backup",
                "status": "pending",
                "priority": "high",
            }
            mock_task_service.create_task = AsyncMock(return_value=mock_task_response)

            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_config = BackupConfigModel()
            mock_session.exec.return_value.first.return_value = mock_config

            from MakerMatrix.routers.backup_routes import create_backup

            mock_user = Mock(spec=UserModel)
            mock_user.id = "user-123"

            response = await create_backup(
                password="TestPassword123",
                include_datasheets=True,
                include_images=True,
                include_env=True,
                current_user=mock_user,
            )

            # Verify task was created with password
            assert response.data["encrypted"] is True
            assert mock_task_service.create_task.called
            call_args = mock_task_service.create_task.call_args[0][0]
            assert "password" in call_args.input_data
            assert call_args.input_data["password"] == "TestPassword123"

    @pytest.mark.asyncio
    async def test_create_backup_without_password(self):
        """Test creating an unencrypted backup"""
        with (
            patch("MakerMatrix.routers.backup_routes.task_service") as mock_task_service,
            patch("MakerMatrix.routers.backup_routes.Session") as mock_session_class,
        ):

            mock_task_response = Mock()
            mock_task_response.success = True
            mock_task_response.data = {
                "id": "task-456",
                "task_type": "backup_creation",
                "name": "Backup: test_backup",
                "status": "pending",
                "priority": "high",
            }
            mock_task_service.create_task = AsyncMock(return_value=mock_task_response)

            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_config = BackupConfigModel()
            mock_session.exec.return_value.first.return_value = mock_config

            from MakerMatrix.routers.backup_routes import create_backup

            mock_user = Mock(spec=UserModel)
            mock_user.id = "user-456"

            response = await create_backup(
                password=None, include_datasheets=True, include_images=False, include_env=True, current_user=mock_user
            )

            # Verify task was created without password
            assert response.data["encrypted"] is False
            call_args = mock_task_service.create_task.call_args[0][0]
            assert "password" not in call_args.input_data


class TestBackupList:
    """Test backup listing and file operations"""

    @pytest.mark.asyncio
    async def test_list_backups_identifies_encrypted(self):
        """Test that list endpoint correctly identifies encrypted backups"""
        # Mock backup files
        encrypted_file = Mock()
        encrypted_file.name = "makermatrix_backup_20250101_120000_encrypted.zip"
        encrypted_file.is_file.return_value = True
        encrypted_file.stat.return_value.st_size = 1024 * 1024  # 1MB
        encrypted_file.stat.return_value.st_mtime = datetime(2025, 1, 1, 12, 0, 0).timestamp()

        unencrypted_file = Mock()
        unencrypted_file.name = "makermatrix_backup_20250101_100000.zip"
        unencrypted_file.is_file.return_value = True
        unencrypted_file.stat.return_value.st_size = 2 * 1024 * 1024  # 2MB
        unencrypted_file.stat.return_value.st_mtime = datetime(2025, 1, 1, 10, 0, 0).timestamp()

        mock_backups_dir = Mock()
        mock_backups_dir.exists.return_value = True
        mock_backups_dir.glob.return_value = [encrypted_file, unencrypted_file]

        # Mock the Path class to return proper mocks
        with patch("MakerMatrix.routers.backup_routes.Path") as mock_path_class:
            mock_file = Mock()
            mock_base_path = Mock()

            # Path(__file__) returns mock_file
            mock_path_class.return_value = mock_file

            # mock_file.parent returns mock for first parent
            mock_file.parent = Mock()

            # mock_file.parent.parent returns the base_path
            mock_file.parent.parent = mock_base_path

            # base_path / "backups" returns mock_backups_dir
            mock_base_path.__truediv__ = Mock(return_value=mock_backups_dir)

            from MakerMatrix.routers.backup_routes import list_backups

            mock_user = Mock(spec=UserModel)
            response = await list_backups(current_user=mock_user)

            backups = response.data["backups"]
            assert len(backups) == 2

            # Find encrypted backup
            encrypted = next(b for b in backups if "_encrypted" in b["filename"])
            assert encrypted["encrypted"] is True

            # Find unencrypted backup
            unencrypted = next(b for b in backups if "_encrypted" not in b["filename"])
            assert unencrypted["encrypted"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
