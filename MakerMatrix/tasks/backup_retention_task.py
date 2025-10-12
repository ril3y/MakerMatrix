"""
Backup Retention Task - Manages backup file lifecycle and cleanup

Supports:
- Automatic cleanup of old backups based on retention policy
- Preserves most recent backups
- Logs deletion actions
- Calculates storage space freed
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlmodel import Session

from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.models.backup_models import BackupConfigModel
from MakerMatrix.database.db import engine


class BackupRetentionTask(BaseTask):
    """Task for managing backup retention and cleanup"""

    @property
    def task_type(self) -> str:
        return "backup_retention"

    @property
    def name(self) -> str:
        return "Backup Retention"

    @property
    def description(self) -> str:
        return "Clean up old backups based on retention policy"

    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute backup retention cleanup"""
        self.log_info("Starting backup retention cleanup", task)
        await self.update_progress(task, 10, "Loading retention configuration")

        # Get retention configuration
        retention_count = await self._get_retention_count()

        if retention_count <= 0:
            self.log_info("Retention policy disabled (retention_count <= 0), skipping cleanup", task)
            return {
                'retention_count': retention_count,
                'backups_deleted': 0,
                'space_freed_mb': 0,
                'status': 'skipped'
            }

        self.log_info(f"Retention policy: keep {retention_count} most recent backups", task)
        await self.update_progress(task, 20, "Scanning backup directory")

        # Define backup directory
        base_path = Path(__file__).parent.parent
        backup_dir = base_path / "backups"

        if not backup_dir.exists():
            self.log_info("Backup directory does not exist, nothing to clean up", task)
            return {
                'retention_count': retention_count,
                'backups_deleted': 0,
                'space_freed_mb': 0,
                'status': 'no_backups'
            }

        # Get all backup files
        backup_files = self._get_backup_files(backup_dir)

        if not backup_files:
            self.log_info("No backup files found, nothing to clean up", task)
            return {
                'retention_count': retention_count,
                'backups_deleted': 0,
                'space_freed_mb': 0,
                'status': 'no_backups'
            }

        total_backups = len(backup_files)
        self.log_info(f"Found {total_backups} backup files", task)
        await self.update_progress(task, 40, f"Found {total_backups} backups")

        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Determine which backups to delete
        backups_to_keep = backup_files[:retention_count]
        backups_to_delete = backup_files[retention_count:]

        if not backups_to_delete:
            self.log_info(f"All {total_backups} backups are within retention policy, nothing to delete", task)
            return {
                'retention_count': retention_count,
                'total_backups': total_backups,
                'backups_deleted': 0,
                'space_freed_mb': 0,
                'status': 'within_policy'
            }

        # Delete old backups
        await self.update_progress(task, 60, f"Deleting {len(backups_to_delete)} old backups")

        deleted_count = 0
        space_freed = 0
        deleted_files = []

        for i, backup_file in enumerate(backups_to_delete):
            try:
                file_size = backup_file.stat().st_size
                file_name = backup_file.name

                # Delete file
                backup_file.unlink()

                deleted_count += 1
                space_freed += file_size
                deleted_files.append(file_name)

                self.log_info(f"Deleted old backup: {file_name} ({round(file_size / (1024 * 1024), 2)} MB)", task)

                # Update progress
                if len(backups_to_delete) > 0:
                    progress = 60 + int((i + 1) / len(backups_to_delete) * 30)
                    await self.update_progress(task, progress, f"Deleted {i + 1}/{len(backups_to_delete)} old backups")

            except Exception as e:
                self.log_error(f"Failed to delete backup {backup_file.name}: {e}", task, exc_info=True)

        space_freed_mb = round(space_freed / (1024 * 1024), 2)

        await self.update_progress(task, 100, "Retention cleanup completed")

        self.log_info(
            f"Retention cleanup complete. Deleted {deleted_count} backups, freed {space_freed_mb} MB. "
            f"Retained {len(backups_to_keep)} most recent backups.",
            task
        )

        return {
            'retention_count': retention_count,
            'total_backups_found': total_backups,
            'backups_kept': len(backups_to_keep),
            'backups_deleted': deleted_count,
            'space_freed_mb': space_freed_mb,
            'deleted_files': deleted_files,
            'status': 'success'
        }

    async def _get_retention_count(self) -> int:
        """Get retention count from backup configuration"""
        with Session(engine) as session:
            # Get the first (and should be only) backup config
            config = session.query(BackupConfigModel).first()

            if config:
                return config.retention_count

            # Return default if no config exists
            return 7

    def _get_backup_files(self, backup_dir: Path) -> List[Path]:
        """Get all backup files (both .zip and .zip.enc)"""
        backup_files = []

        # Get .zip files
        backup_files.extend(backup_dir.glob("*.zip"))

        # Get .zip.enc files
        backup_files.extend(backup_dir.glob("*.zip.enc"))

        # Filter to only include actual backup files (not directories)
        backup_files = [f for f in backup_files if f.is_file()]

        return backup_files
