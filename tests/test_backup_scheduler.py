"""
Test Backup Scheduler

Tests for the automated backup scheduler including:
- Schedule configuration
- Cron trigger generation
- Scheduled backup password usage
- Retention cleanup scheduling
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

from MakerMatrix.models.backup_models import BackupConfigModel
from MakerMatrix.services.system.backup_scheduler import BackupScheduler


class TestBackupScheduler:
    """Test automated backup scheduling"""

    @pytest.mark.asyncio
    async def test_scheduled_backup_uses_configured_password(self):
        """Test that scheduled backups use the encryption_password from config"""
        scheduler = BackupScheduler()

        # Create a mock config with password
        mock_config = BackupConfigModel(
            id="test-config-1",
            schedule_enabled=True,
            schedule_type="nightly",
            encryption_required=True,
            encryption_password="ScheduledBackupPassword123",
        )

        with (
            patch("MakerMatrix.services.system.backup_scheduler.Session") as mock_session_class,
            patch("MakerMatrix.services.system.backup_scheduler.task_service") as mock_task_service,
        ):

            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            mock_task_service.create_task = AsyncMock()

            # Call the internal backup creation method
            await scheduler._create_scheduled_backup()

            # Verify task was created with the password
            assert mock_task_service.create_task.called
            call_args = mock_task_service.create_task.call_args[0][0]
            assert call_args.input_data["password"] == "ScheduledBackupPassword123"

    @pytest.mark.asyncio
    async def test_scheduled_backup_without_password_when_not_configured(self):
        """Test that scheduled backups work without password when none is configured"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(
            id="test-config-2",
            schedule_enabled=True,
            schedule_type="weekly",
            encryption_required=False,
            encryption_password=None,
        )

        with (
            patch("MakerMatrix.services.system.backup_scheduler.Session") as mock_session_class,
            patch("MakerMatrix.services.system.backup_scheduler.task_service") as mock_task_service,
        ):

            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            mock_task_service.create_task = AsyncMock()

            await scheduler._create_scheduled_backup()

            # Verify task was created without password
            call_args = mock_task_service.create_task.call_args[0][0]
            assert "password" not in call_args.input_data

    @pytest.mark.asyncio
    async def test_scheduled_backup_warning_when_encryption_required_but_no_password(self):
        """Test warning is logged when encryption is required but no password is set"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(
            id="test-config-3",
            schedule_enabled=True,
            schedule_type="nightly",
            encryption_required=True,
            encryption_password=None,  # Encryption required but no password!
        )

        with (
            patch("MakerMatrix.services.system.backup_scheduler.Session") as mock_session_class,
            patch("MakerMatrix.services.system.backup_scheduler.task_service") as mock_task_service,
            patch("MakerMatrix.services.system.backup_scheduler.logger") as mock_logger,
        ):

            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            mock_task_service.create_task = AsyncMock()

            await scheduler._create_scheduled_backup()

            # Verify warning was logged
            assert mock_logger.warning.called
            warning_message = mock_logger.warning.call_args[0][0]
            assert "no password configured" in warning_message.lower()

            # Verify backup still proceeds without password
            call_args = mock_task_service.create_task.call_args[0][0]
            assert "password" not in call_args.input_data

    def test_nightly_trigger_generation(self):
        """Test that nightly schedule generates correct cron trigger"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(schedule_type="nightly", schedule_cron=None)

        trigger = scheduler._get_trigger_from_config(mock_config)

        assert trigger is not None
        # Verify it's a CronTrigger
        from apscheduler.triggers.cron import CronTrigger

        assert isinstance(trigger, CronTrigger)

    def test_weekly_trigger_generation(self):
        """Test that weekly schedule generates correct cron trigger"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(schedule_type="weekly", schedule_cron=None)

        trigger = scheduler._get_trigger_from_config(mock_config)

        assert trigger is not None
        # Verify it's a CronTrigger
        from apscheduler.triggers.cron import CronTrigger

        assert isinstance(trigger, CronTrigger)

    def test_custom_cron_trigger_generation(self):
        """Test that custom cron expressions are parsed correctly"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(schedule_type="custom", schedule_cron="30 3 * * 1")  # 3:30 AM every Monday

        trigger = scheduler._get_trigger_from_config(mock_config)

        assert trigger is not None
        # Verify it's a CronTrigger
        from apscheduler.triggers.cron import CronTrigger

        assert isinstance(trigger, CronTrigger)

    def test_invalid_cron_expression_returns_none(self):
        """Test that invalid cron expressions return None"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(schedule_type="custom", schedule_cron="invalid cron")

        trigger = scheduler._get_trigger_from_config(mock_config)

        assert trigger is None

    @pytest.mark.asyncio
    async def test_reload_schedule_updates_next_backup_time(self):
        """Test that reload_schedule updates the next_backup_at field"""
        scheduler = BackupScheduler()

        mock_config = BackupConfigModel(
            id="test-config-4", schedule_enabled=True, schedule_type="nightly", next_backup_at=None
        )

        with patch("MakerMatrix.services.system.backup_scheduler.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            # Mock scheduler methods - need to mock remove_job to not throw error
            mock_job = Mock()
            mock_job.next_run_time = datetime(2025, 1, 2, 2, 0, 0)

            with (
                patch.object(scheduler.scheduler, "get_job") as mock_get_job,
                patch.object(scheduler.scheduler, "add_job") as mock_add_job,
                patch.object(scheduler.scheduler, "remove_job"),
            ):

                # First call to get_job returns None (no existing job)
                # Second call returns mock_job (after adding the job)
                mock_get_job.side_effect = [None, mock_job]

                await scheduler.reload_schedule()

                # Verify job was added
                assert mock_add_job.called

                # Verify next_backup_at was updated
                assert mock_config.next_backup_at == datetime(2025, 1, 2, 2, 0, 0)
                assert mock_session.add.called
                assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_retention_cleanup_scheduled(self):
        """Test that retention cleanup is scheduled at 3 AM"""
        scheduler = BackupScheduler()

        # Create a config so the function doesn't exit early
        mock_config = BackupConfigModel(
            id="test-config-5", schedule_enabled=False, schedule_type="nightly"  # Don't need backup job for this test
        )

        with patch("MakerMatrix.services.system.backup_scheduler.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = mock_config

            with (
                patch.object(scheduler.scheduler, "add_job") as mock_add_job,
                patch.object(scheduler.scheduler, "get_job", return_value=None),
            ):

                await scheduler.reload_schedule()

                # Verify retention job was added
                add_job_calls = mock_add_job.call_args_list

                # Find the retention cleanup job
                retention_call = next((call for call in add_job_calls if call[1].get("id") == "backup_retention"), None)

                assert retention_call is not None
                # Verify it has a CronTrigger
                from apscheduler.triggers.cron import CronTrigger

                trigger = retention_call[1]["trigger"]
                assert isinstance(trigger, CronTrigger)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
