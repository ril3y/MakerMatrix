"""
Database Restore Task - Restores from password-protected backup files

Supports:
- Password-protected ZIP backup extraction
- Database, .env, datasheets, and images restoration
- Safety backup before restore
- Service restart coordination
- Rollback on failure
"""

import os
import shutil
import tempfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import zipfile

from .base_task import BaseTask
from .database_backup_task import DatabaseBackupTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.database.db import DATABASE_URL


class DatabaseRestoreTask(BaseTask):
    """Task for restoring from comprehensive backups"""

    @property
    def task_type(self) -> str:
        return "backup_restore"

    @property
    def name(self) -> str:
        return "Database Restore"

    @property
    def description(self) -> str:
        return "Restore database, files, and configuration from backup"

    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute database restore from backup"""
        input_data = self.get_input_data(task)
        backup_filepath = input_data.get('backup_filepath')
        password = input_data.get('password')  # Required if backup is encrypted
        create_safety_backup = input_data.get('create_safety_backup', True)

        if not backup_filepath:
            raise ValueError("backup_filepath is required")

        backup_path = Path(backup_filepath)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_filepath}")

        # Check if password-protected (by filename convention)
        is_password_protected = "_encrypted" in backup_path.name

        if is_password_protected and not password:
            raise ValueError("Password is required for password-protected backups")

        self.log_info(f"Starting restore from backup: {backup_path.name} (password protected: {is_password_protected})", task)
        await self.update_progress(task, 5, "Initializing restore process")

        # Define paths
        base_path = Path(__file__).parent.parent
        static_path = base_path / "services" / "static"
        datasheets_path = static_path / "datasheets"
        images_path = static_path / "images"

        restore_stats = {
            'backup_file': backup_path.name,
            'restore_started_at': datetime.now().isoformat(),
            'safety_backup_created': False,
            'database_restored': False,
            'env_restored': False,
            'datasheets_restored': 0,
            'images_restored': 0,
            'rollback_performed': False
        }

        safety_backup_path = None

        try:
            # Step 1: Create safety backup of current state
            if create_safety_backup:
                await self.update_progress(task, 10, "Creating safety backup of current state")
                safety_backup_task = DatabaseBackupTask(self.task_service)
                safety_backup_name = f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                safety_task_model = TaskModel(
                    task_type="backup_creation",
                    name=f"Safety Backup: {safety_backup_name}",
                    description="Automatic safety backup before restore"
                )
                safety_task_model.set_input_data({
                    'backup_name': safety_backup_name,
                    'include_datasheets': True,
                    'include_images': True,
                    'include_env': True
                })

                safety_result = await safety_backup_task.execute(safety_task_model)
                safety_backup_path = Path(safety_result['backup_file_path'])
                restore_stats['safety_backup_created'] = True
                restore_stats['safety_backup_path'] = str(safety_backup_path)

                self.log_info(f"Safety backup created: {safety_backup_path}", task)

            # Step 2: Extract backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                extract_dir = temp_path / "backup_contents"
                extract_dir.mkdir()

                # Extract with password if needed
                await self.update_progress(task, 20, "Extracting backup contents")
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    if is_password_protected and password:
                        # Set password for ZipCrypto encrypted files
                        zipf.setpassword(password.encode())
                    zipf.extractall(extract_dir)

                if is_password_protected:
                    self.log_info("Password-protected backup extracted successfully", task)
                else:
                    self.log_info("Backup extracted successfully", task)

                # Step 3: Validate backup contents
                await self.update_progress(task, 40, "Validating backup contents")
                metadata_path = extract_dir / "backup_info.json"

                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    self.log_info(f"Backup metadata: {metadata.get('backup_name', 'unknown')}", task)
                else:
                    self.log_info("Warning: backup_info.json not found, proceeding anyway", task)
                    metadata = {}

                # Step 4: Restore database file
                db_backup_file = extract_dir / "makers_matrix.db"
                if db_backup_file.exists():
                    await self.update_progress(task, 50, "Restoring database file")
                    db_path = self._get_database_path()

                    # Stop database connections (in production, you'd want to coordinate with app shutdown)
                    self.log_info("Restoring database file (ensure app is ready for restart)", task)

                    shutil.copy2(db_backup_file, db_path)
                    restore_stats['database_restored'] = True
                    self.log_info(f"Database restored to {db_path}", task)
                else:
                    self.log_info("Warning: Database file not found in backup", task)

                # Step 5: Restore .env file
                env_backup_file = extract_dir / ".env"
                if env_backup_file.exists():
                    await self.update_progress(task, 60, "Restoring .env file")
                    env_path = base_path.parent / ".env"
                    shutil.copy2(env_backup_file, env_path)
                    restore_stats['env_restored'] = True
                    self.log_info(".env file restored", task)
                else:
                    self.log_info(".env file not found in backup, skipping", task)

                # Step 6: Restore datasheets
                datasheets_backup_dir = extract_dir / "datasheets"
                if datasheets_backup_dir.exists():
                    await self.update_progress(task, 70, "Restoring datasheet files")
                    datasheets_path.mkdir(parents=True, exist_ok=True)

                    # Clear existing datasheets (optional - could make configurable)
                    for existing_file in datasheets_path.glob("*"):
                        if existing_file.is_file():
                            existing_file.unlink()

                    # Copy datasheets from backup
                    datasheet_files = list(datasheets_backup_dir.glob("*"))
                    for i, datasheet_file in enumerate(datasheet_files):
                        if datasheet_file.is_file():
                            shutil.copy2(datasheet_file, datasheets_path / datasheet_file.name)
                            restore_stats['datasheets_restored'] += 1

                            if i % 10 == 0:  # Update progress periodically
                                progress = 70 + int((i + 1) / len(datasheet_files) * 10)
                                await self.update_progress(task, progress, f"Restored datasheet {i + 1}/{len(datasheet_files)}")

                    self.log_info(f"Restored {restore_stats['datasheets_restored']} datasheets", task)

                # Step 7: Restore images
                images_backup_dir = extract_dir / "images"
                if images_backup_dir.exists():
                    await self.update_progress(task, 80, "Restoring image files")
                    images_path.mkdir(parents=True, exist_ok=True)

                    # Clear existing images (optional - could make configurable)
                    for existing_file in images_path.glob("*"):
                        if existing_file.is_file():
                            existing_file.unlink()

                    # Copy images from backup
                    image_files = list(images_backup_dir.glob("*"))
                    for i, image_file in enumerate(image_files):
                        if image_file.is_file():
                            shutil.copy2(image_file, images_path / image_file.name)
                            restore_stats['images_restored'] += 1

                            if i % 20 == 0:  # Update progress periodically
                                progress = 80 + int((i + 1) / len(image_files) * 15)
                                await self.update_progress(task, progress, f"Restored image {i + 1}/{len(image_files)}")

                    self.log_info(f"Restored {restore_stats['images_restored']} images", task)

            # Step 8: Finalize
            await self.update_progress(task, 95, "Restore completed, preparing summary")
            restore_stats['restore_completed_at'] = datetime.now().isoformat()
            restore_stats['status'] = 'success'

            await self.update_progress(task, 100, "Restore completed successfully")

            self.log_info(
                f"Restore complete. Database: {restore_stats['database_restored']}, "
                f"Datasheets: {restore_stats['datasheets_restored']}, "
                f"Images: {restore_stats['images_restored']}",
                task
            )

            return restore_stats

        except Exception as e:
            # Attempt rollback if safety backup was created
            if safety_backup_path and safety_backup_path.exists():
                self.log_error(f"Restore failed: {e}. Attempting rollback from safety backup", task, exc_info=True)
                try:
                    await self.update_progress(task, 50, "Performing rollback from safety backup")
                    # Recursive call to restore from safety backup
                    rollback_task = TaskModel(
                        task_type="backup_restore",
                        name="Rollback Restore",
                        description="Rollback from safety backup"
                    )
                    rollback_task.set_input_data({
                        'backup_filepath': str(safety_backup_path),
                        'create_safety_backup': False  # Don't create another safety backup
                    })
                    await self.execute(rollback_task)
                    restore_stats['rollback_performed'] = True
                    self.log_info("Rollback completed successfully", task)
                except Exception as rollback_error:
                    self.log_error(f"Rollback failed: {rollback_error}", task, exc_info=True)

            restore_stats['status'] = 'failed'
            restore_stats['error'] = str(e)
            raise

    def _get_database_path(self) -> Path:
        """Get the database file path from DATABASE_URL"""
        db_path_raw = DATABASE_URL.replace("sqlite:///", "")

        possible_db_paths = [
            db_path_raw,
            os.path.join(os.getcwd(), db_path_raw),
            f"/home/ril3y/MakerMatrix/{db_path_raw}",
            str(Path(__file__).parent.parent.parent / db_path_raw),
            "makers_matrix.db",
            "/home/ril3y/MakerMatrix/makers_matrix.db",
            str(Path(__file__).parent.parent.parent / "makers_matrix.db"),
        ]

        for path in possible_db_paths:
            if os.path.exists(path):
                return Path(path)

        return Path(__file__).parent.parent.parent / "makers_matrix.db"
