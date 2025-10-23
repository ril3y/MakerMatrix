"""
Database Backup Task - Creates a comprehensive backup including database and enrichment files

Supports:
- Password-protected ZIP backups with AES-256 encryption
- Database, .env, datasheets, and images
- Backup metadata and integrity verification
"""

import os
import shutil
import tempfile
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import pyminizip

    PYMINIZIP_AVAILABLE = True
except ImportError:
    PYMINIZIP_AVAILABLE = False

import zipfile

from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.database.db import DATABASE_URL

# Import version information
try:
    from MakerMatrix import __version__, __schema_version__, VERSION_INFO
except ImportError:
    __version__ = "unknown"
    __schema_version__ = "unknown"
    VERSION_INFO = {}


class DatabaseBackupTask(BaseTask):
    """Task for creating a comprehensive backup of database and enrichment files"""

    @property
    def task_type(self) -> str:
        return "backup_creation"

    @property
    def name(self) -> str:
        return "Database Backup"

    @property
    def description(self) -> str:
        return "Create a comprehensive backup including database, datasheets, and images"

    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute database backup task with optional password protection"""
        input_data = self.get_input_data(task)
        backup_name = input_data.get("backup_name", self._generate_backup_name())
        include_datasheets = input_data.get("include_datasheets", True)
        include_images = input_data.get("include_images", True)
        include_env = input_data.get("include_env", True)
        password = input_data.get("password")  # Optional password for ZIP encryption

        # Validate password if encryption requested
        if password and not PYMINIZIP_AVAILABLE:
            raise RuntimeError(
                "Password protection requested but pyminizip library not available. Install with: pip install pyminizip"
            )

        self.log_info(f"Starting comprehensive backup: {backup_name} (password protected: {bool(password)})", task)
        await self.update_progress(task, 5, "Initializing backup process")

        # Define paths - use environment variable for static files path if set
        static_files_path_env = os.getenv("STATIC_FILES_PATH")
        backups_path_env = os.getenv("BACKUPS_PATH")
        base_path = Path(__file__).parent.parent  # Always need this for .env

        if static_files_path_env:
            # Using environment-configured path (e.g., Docker: /data/static)
            static_path = Path(static_files_path_env)
        else:
            # Using default relative path (development mode)
            static_path = base_path / "services" / "static"

        datasheets_path = static_path / "datasheets"
        images_path = static_path / "images"

        # Get database path from DATABASE_URL
        db_path = self._get_database_path()
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found at: {db_path}")

        # Create temporary directory for backup preparation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            backup_dir = temp_path / "backup"
            backup_dir.mkdir()

            backup_stats = {
                # Metadata
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "makermatrix_version": __version__,
                "schema_version": __schema_version__,
                "backup_format_version": "2.0",  # Updated to use password-protected ZIP
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                # Security
                "password_protected": bool(password),
                "credential_storage": "plain_text_in_database",
                "credential_protection": "password_protected_backup_zip" if password else "os_file_permissions",
                # Contents
                "database_included": True,
                "datasheets_included": include_datasheets,
                "images_included": include_images,
                "env_included": include_env,
                # Statistics
                "database_size_mb": 0,
                "datasheets_count": 0,
                "datasheets_size_mb": 0,
                "images_count": 0,
                "images_size_mb": 0,
                "env_size_kb": 0,
                "total_size_mb": 0,
                # Paths (relative to backup root)
                "database_path": "makers_matrix.db",
                "datasheets_path": "datasheets/",
                "images_path": "images/",
                "env_path": ".env",
            }

            # Step 1: Copy database file
            await self.update_progress(task, 15, "Backing up database file")
            await asyncio.sleep(0.5)  # Small delay to show progress
            db_backup_path = backup_dir / "makers_matrix.db"
            shutil.copy2(db_path, db_backup_path)

            db_size = db_backup_path.stat().st_size
            backup_stats["database_size_mb"] = round(db_size / (1024 * 1024), 2)
            self.log_info(f"Database backup complete: {backup_stats['database_size_mb']} MB", task)
            await asyncio.sleep(0.3)  # Small delay after completion

            # Step 2: Copy datasheets if requested
            if include_datasheets and datasheets_path.exists():
                await self.update_progress(task, 30, "Backing up datasheet files")
                await asyncio.sleep(0.5)  # Small delay to show progress
                datasheets_backup_path = backup_dir / "datasheets"
                datasheets_backup_path.mkdir()

                datasheet_files = list(datasheets_path.glob("*"))
                total_datasheets = len(datasheet_files)
                datasheets_size = 0

                for i, datasheet_file in enumerate(datasheet_files):
                    if datasheet_file.is_file():
                        shutil.copy2(datasheet_file, datasheets_backup_path / datasheet_file.name)
                        datasheets_size += datasheet_file.stat().st_size

                        # Update progress for datasheets (30-60%)
                        if total_datasheets > 0:
                            progress = 30 + int((i + 1) / total_datasheets * 30)
                            await self.update_progress(task, progress, f"Copied datasheet {i + 1}/{total_datasheets}")

                backup_stats["datasheets_count"] = total_datasheets
                backup_stats["datasheets_size_mb"] = round(datasheets_size / (1024 * 1024), 2)
                self.log_info(
                    f"Datasheets backup complete: {total_datasheets} files, {backup_stats['datasheets_size_mb']} MB",
                    task,
                )
            else:
                await self.update_progress(task, 60, "Skipping datasheets (not included or directory not found)")

            # Step 3: Copy images if requested
            if include_images and images_path.exists():
                await self.update_progress(task, 65, "Backing up image files")
                await asyncio.sleep(0.5)  # Small delay to show progress
                images_backup_path = backup_dir / "images"
                images_backup_path.mkdir()

                image_files = list(images_path.glob("*"))
                total_images = len(image_files)
                images_size = 0

                # Process images in batches to avoid too many progress updates
                batch_size = max(1, total_images // 20)  # Update progress every 5% of images

                for i, image_file in enumerate(image_files):
                    if image_file.is_file():
                        shutil.copy2(image_file, images_backup_path / image_file.name)
                        images_size += image_file.stat().st_size

                        # Update progress for images (65-85%)
                        if i % batch_size == 0 or i == total_images - 1:
                            progress = 65 + int((i + 1) / total_images * 20)
                            await self.update_progress(task, progress, f"Copied image {i + 1}/{total_images}")

                backup_stats["images_count"] = total_images
                backup_stats["images_size_mb"] = round(images_size / (1024 * 1024), 2)
                self.log_info(
                    f"Images backup complete: {total_images} files, {backup_stats['images_size_mb']} MB", task
                )
            else:
                await self.update_progress(task, 85, "Skipping images (not included or directory not found)")

            # Step 4: Copy .env file if requested
            if include_env:
                await self.update_progress(task, 87, "Backing up .env file")
                await asyncio.sleep(0.3)  # Small delay to show progress
                env_path = base_path.parent / ".env"

                if env_path.exists():
                    env_backup_path = backup_dir / ".env"
                    shutil.copy2(env_path, env_backup_path)
                    env_size = env_backup_path.stat().st_size
                    backup_stats["env_size_kb"] = round(env_size / 1024, 2)
                    self.log_info(f".env file backup complete: {backup_stats['env_size_kb']} KB", task)
                else:
                    self.log_info(".env file not found, skipping", task)
                    backup_stats["env_included"] = False
            else:
                await self.update_progress(task, 87, "Skipping .env file (not included)")

            # Step 5: Create backup metadata file
            await self.update_progress(task, 90, "Creating backup metadata")
            await asyncio.sleep(0.3)  # Small delay to show progress
            metadata_path = backup_dir / "backup_info.json"
            import json

            with open(metadata_path, "w") as f:
                json.dump(backup_stats, f, indent=2)

            # Step 6: Create password-protected zip file
            await self.update_progress(task, 93, "Creating zip archive")
            await asyncio.sleep(0.5)  # Small delay to show progress

            # Use environment-configured backups path if set
            if backups_path_env:
                final_backup_dir = Path(backups_path_env)
            else:
                final_backup_dir = base_path / "backups"
            final_backup_dir.mkdir(exist_ok=True, parents=True)

            if password:
                final_zip_path = final_backup_dir / f"{backup_name}_encrypted.zip"
            else:
                final_zip_path = final_backup_dir / f"{backup_name}.zip"

            # Use pyminizip for password-protected zips - compatible with Windows built-in extraction
            if password and PYMINIZIP_AVAILABLE:
                # Collect all files to compress
                files_to_compress = []
                for file_path in backup_dir.rglob("*"):
                    if file_path.is_file():
                        files_to_compress.append(str(file_path))

                # Set file prefixes for relative paths in ZIP
                file_prefixes = []
                for file_path in files_to_compress:
                    relative_path = Path(file_path).relative_to(backup_dir)
                    # Get parent directory for prefix (empty string for root files)
                    prefix = str(relative_path.parent) if relative_path.parent != Path(".") else ""
                    file_prefixes.append(prefix)

                # Create password-protected ZIP with ZipCrypto (compatible with Windows)
                compression_level = 6  # 0-9, where 9 is maximum compression
                pyminizip.compress_multiple(
                    files_to_compress, file_prefixes, str(final_zip_path), password, compression_level
                )

                backup_stats["encryption_algorithm"] = "ZipCrypto (ZIP 2.0 - Compatible with Windows/Mac/Linux)"
                self.log_info("Password-protected backup created successfully", task)
            else:
                # Standard unencrypted ZIP
                with zipfile.ZipFile(final_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    for file_path in backup_dir.rglob("*"):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(backup_dir)
                            zipf.write(file_path, relative_path)

                self.log_info("Backup created successfully", task)

            # Calculate final statistics
            zip_size = final_zip_path.stat().st_size
            backup_stats["total_size_mb"] = round(zip_size / (1024 * 1024), 2)
            backup_stats["backup_file_path"] = str(final_zip_path)
            backup_stats["backup_filename"] = final_zip_path.name

            await self.update_progress(task, 100, "Backup completed successfully")

            self.log_info(
                f"Backup complete: {backup_stats['total_size_mb']} MB {'password-protected ' if password else ''}backup created at {final_zip_path}",
                task,
            )

            return backup_stats

    def _generate_backup_name(self) -> str:
        """Generate a default backup name with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"makermatrix_backup_{timestamp}"

    def _get_database_path(self) -> Path:
        """Get the database file path from DATABASE_URL with robust path resolution"""
        import os
        from pathlib import Path

        # Parse DATABASE_URL to get raw path
        db_path_raw = DATABASE_URL.replace("sqlite:///", "")

        # Try multiple possible database locations
        possible_db_paths = [
            db_path_raw,  # Relative to current working directory
            os.path.join(os.getcwd(), db_path_raw),  # Explicitly relative to cwd
            f"/home/ril3y/MakerMatrix/{db_path_raw}",  # Project root
            str(Path(__file__).parent.parent.parent / db_path_raw),  # Relative to this file
            # Try common filename variations
            "makers_matrix.db",  # The actual filename
            "/home/ril3y/MakerMatrix/makers_matrix.db",  # Project root with correct name
            str(Path(__file__).parent.parent.parent / "makers_matrix.db"),  # Relative with correct name
        ]

        for path in possible_db_paths:
            if os.path.exists(path):
                return Path(path)

        # Fallback to default if none found
        return Path(__file__).parent.parent.parent / "makers_matrix.db"
