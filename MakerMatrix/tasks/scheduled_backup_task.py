"""
Scheduled Backup Task - Handles automated scheduled backups

Reuses DatabaseBackupTask logic but registers under the 'backup_scheduled' task type
so the backup scheduler's tasks are properly handled.
"""

from .database_backup_task import DatabaseBackupTask


class ScheduledBackupTask(DatabaseBackupTask):
    """Task handler for scheduled backups - same as manual backup but with its own task type"""

    @property
    def task_type(self) -> str:
        return "backup_scheduled"

    @property
    def name(self) -> str:
        return "Scheduled Backup"

    @property
    def description(self) -> str:
        return "Automated scheduled backup of database, datasheets, and images"
