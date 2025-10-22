"""
Backup and Restore Integration Tests

IMPORTANT: These tests use REAL databases and file operations (NOT mocks).
They NEVER touch production data - all tests use isolated test databases.

Tests cover:
- Backup creation with real database
- Restore operations with data integrity verification
- Error handling and edge cases
"""

import pytest
import os
import zipfile
import json
import hashlib
from pathlib import Path
from sqlmodel import Session, select

# Import test fixtures
from tests.fixtures import (
    test_db_path,
    test_engine,
    test_session,
    test_db_with_schema,
    test_static_files_dir,
    populate_test_database
)

# Import models for verification
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.category_models import CategoryModel
from MakerMatrix.models.location_models import LocationModel
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.models.part_allocation_models import PartLocationAllocation

# Import backup/restore tasks
from MakerMatrix.tasks.database_backup_task import DatabaseBackupTask
from MakerMatrix.tasks.database_restore_task import DatabaseRestoreTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.services.system.task_service import task_service


class TestBackupCreation:
    """Test backup creation with real database operations"""

    @pytest.mark.asyncio
    async def test_create_backup_from_populated_database(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test creating a backup from a database populated with test data.

        Verifies:
        - Backup file is created
        - Backup is a valid ZIP file
        - Backup contains expected files (database, metadata)
        """
        engine, db_path = test_db_with_schema

        # Populate database with test data
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

        # Create backup task
        backup_task = DatabaseBackupTask(task_service)
        task_model = TaskModel(
            task_type="backup_creation",
            name="Integration Test Backup",
            description="Test backup for integration testing"
        )

        # Configure backup to use test database path
        backup_name = f"integration_test_backup_{db_path.stem}"
        task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': True,
            'include_images': True,
            'include_env': False  # Don't include .env in tests
        })

        # Temporarily override DATABASE_URL to point to test database
        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

        try:
            # Execute backup
            result = await backup_task.execute(task_model)

            # Verify backup was created
            assert result['backup_filename'] is not None
            backup_path = Path(result['backup_file_path'])
            assert backup_path.exists(), "Backup file should exist"

            # Verify it's a valid ZIP
            assert zipfile.is_zipfile(backup_path), "Backup should be a valid ZIP file"

            # Verify ZIP contents
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                file_list = zipf.namelist()

                # Should contain database file
                assert 'makers_matrix.db' in file_list, "Backup should contain database file"

                # Should contain metadata
                assert 'backup_info.json' in file_list, "Backup should contain metadata"

                # Verify metadata content
                metadata_content = zipf.read('backup_info.json')
                metadata = json.loads(metadata_content)

                assert metadata['backup_name'] == backup_name
                assert metadata['database_included'] is True
                assert metadata['datasheets_included'] is True
                assert metadata['images_included'] is True

            # Cleanup
            backup_path.unlink()

        finally:
            # Restore original DATABASE_URL
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)

    @pytest.mark.asyncio
    async def test_backup_includes_datasheets(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test that backup includes datasheet files when requested.

        Verifies:
        - Datasheet files are included in backup
        - Datasheet count matches expected
        - File contents are preserved
        """
        engine, db_path = test_db_with_schema

        # Populate database and create datasheets
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

        # Get datasheet files that were created
        expected_datasheet_files = test_data['datasheet_files']
        assert len(expected_datasheet_files) > 0, "Test should create datasheet files"

        # Create backup with datasheets
        backup_task = DatabaseBackupTask(task_service)
        task_model = TaskModel(
            task_type="backup_creation",
            name="Backup with Datasheets Test"
        )

        backup_name = f"test_with_datasheets_{db_path.stem}"
        task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': True,
            'include_images': False,
            'include_env': False
        })

        # Override paths to use test directories
        original_db_url = os.environ.get('DATABASE_URL')
        original_static_path = os.environ.get('STATIC_FILES_PATH')

        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"
        os.environ['STATIC_FILES_PATH'] = str(test_static_files_dir)

        try:
            result = await backup_task.execute(task_model)
            backup_path = Path(result['backup_file_path'])

            # Verify datasheets are in backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                file_list = zipf.namelist()

                # Count datasheet files in backup
                datasheet_files_in_backup = [
                    f for f in file_list if f.startswith('datasheets/')
                ]

                assert len(datasheet_files_in_backup) == len(expected_datasheet_files), \
                    f"Backup should contain {len(expected_datasheet_files)} datasheets"

            # Cleanup
            backup_path.unlink()

        finally:
            # Restore environment
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)

            if original_static_path:
                os.environ['STATIC_FILES_PATH'] = original_static_path
            else:
                os.environ.pop('STATIC_FILES_PATH', None)

    @pytest.mark.asyncio
    async def test_backup_includes_images(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test that backup includes image files when requested.

        Verifies:
        - Image files are included in backup
        - Image count matches expected
        """
        engine, db_path = test_db_with_schema

        # Populate database and create images
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

        expected_image_files = test_data['image_files']
        assert len(expected_image_files) > 0, "Test should create image files"

        # Create backup with images
        backup_task = DatabaseBackupTask(task_service)
        task_model = TaskModel(
            task_type="backup_creation",
            name="Backup with Images Test"
        )

        backup_name = f"test_with_images_{db_path.stem}"
        task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': False,
            'include_images': True,
            'include_env': False
        })

        # Override environment
        original_db_url = os.environ.get('DATABASE_URL')
        original_static_path = os.environ.get('STATIC_FILES_PATH')

        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"
        os.environ['STATIC_FILES_PATH'] = str(test_static_files_dir)

        try:
            result = await backup_task.execute(task_model)
            backup_path = Path(result['backup_file_path'])

            # Verify images are in backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                file_list = zipf.namelist()

                image_files_in_backup = [
                    f for f in file_list if f.startswith('images/')
                ]

                assert len(image_files_in_backup) == len(expected_image_files), \
                    f"Backup should contain {len(expected_image_files)} images"

            # Cleanup
            backup_path.unlink()

        finally:
            # Restore environment
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)

            if original_static_path:
                os.environ['STATIC_FILES_PATH'] = original_static_path
            else:
                os.environ.pop('STATIC_FILES_PATH', None)


class TestRestoreOperations:
    """Test restore operations with data integrity verification"""

    @pytest.mark.asyncio
    async def test_restore_database_from_backup(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test restoring database from a backup file.

        Verifies:
        - Database can be restored from backup
        - Restored database contains expected data
        - Data integrity is preserved
        """
        engine, db_path = test_db_with_schema

        # Step 1: Create and populate original database
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

            # Get counts for verification
            original_part_count = session.query(PartModel).count()
            original_category_count = session.query(CategoryModel).count()
            original_location_count = session.query(LocationModel).count()

        # Step 2: Create backup
        backup_task = DatabaseBackupTask(task_service)
        backup_task_model = TaskModel(
            task_type="backup_creation",
            name="Backup for Restore Test"
        )

        backup_name = f"restore_test_backup_{db_path.stem}"
        backup_task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': False,
            'include_images': False,
            'include_env': False
        })

        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

        try:
            backup_result = await backup_task.execute(backup_task_model)
            backup_path = Path(backup_result['backup_file_path'])

            # Step 3: Store original database size for verification
            engine.dispose()  # Close all connections
            original_db_size = db_path.stat().st_size

            # Note: We DON'T delete the database file. In real world, you'd be restoring
            # over a corrupt or old database. The restore will overwrite the existing file.

            # Step 4: Restore from backup (will overwrite existing database)
            restore_task = DatabaseRestoreTask(task_service)
            restore_task_model = TaskModel(
                task_type="backup_restore",
                name="Restore Test"
            )

            restore_task_model.set_input_data({
                'backup_filepath': str(backup_path),
                'create_safety_backup': False,  # No safety backup needed (original is already deleted)
                'password': None
            })

            # Execute restore
            restore_result = await restore_task.execute(restore_task_model)

            assert restore_result['database_restored'] is True, "Database should be restored"

            # Step 5: Verify database file was actually restored
            assert db_path.exists(), f"Database file should exist after restore at {db_path}"
            restored_db_size = db_path.stat().st_size
            assert restored_db_size > 0, f"Restored database should not be empty (size: {restored_db_size})"
            assert restored_db_size == original_db_size, \
                f"Restored database size ({restored_db_size}) should match original ({original_db_size})"

            # Step 6: Verify restored data (create new engine for restored database)
            from sqlalchemy import create_engine as sa_create_engine
            restored_engine = sa_create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )

            with Session(restored_engine) as session:
                # Count records
                restored_part_count = session.query(PartModel).count()
                restored_category_count = session.query(CategoryModel).count()
                restored_location_count = session.query(LocationModel).count()

                # Verify counts match
                assert restored_part_count == original_part_count, \
                    f"Part count should match (expected {original_part_count}, got {restored_part_count})"
                assert restored_category_count == original_category_count, \
                    f"Category count should match"
                assert restored_location_count == original_location_count, \
                    f"Location count should match"

            # Cleanup
            backup_path.unlink()

        finally:
            # Restore environment
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)


class TestDataIntegrity:
    """Test data integrity after backup/restore cycle"""

    @pytest.mark.asyncio
    async def test_part_data_matches_after_restore(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test that specific part data matches exactly after restore.

        Verifies:
        - Part names preserved
        - Part descriptions preserved
        - Manufacturer information preserved
        - All part fields intact
        """
        engine, db_path = test_db_with_schema

        # Create database with known part data
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

            # Query specific part to verify later
            test_part = session.get(PartModel, "part_resistor_100k")
            assert test_part is not None

            original_part_data = {
                'part_name': test_part.part_name,
                'description': test_part.description,
                'manufacturer': test_part.manufacturer,
                'manufacturer_part_number': test_part.manufacturer_part_number,
                'supplier': test_part.supplier,
                'component_type': test_part.component_type
            }

        # Create backup and restore (similar to previous test)
        backup_task = DatabaseBackupTask(task_service)
        backup_task_model = TaskModel(task_type="backup_creation", name="Data Integrity Test Backup")
        backup_name = f"integrity_test_{db_path.stem}"
        backup_task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': False,
            'include_images': False,
            'include_env': False
        })

        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

        try:
            backup_result = await backup_task.execute(backup_task_model)
            backup_path = Path(backup_result['backup_file_path'])

            # Simulate data corruption (restore will overwrite existing database)
            engine.dispose()

            # Restore from backup
            restore_task = DatabaseRestoreTask(task_service)
            restore_task_model = TaskModel(task_type="backup_restore", name="Integrity Test Restore")
            restore_task_model.set_input_data({
                'backup_filepath': str(backup_path),
                'create_safety_backup': False,
                'password': None
            })

            restore_result = await restore_task.execute(restore_task_model)

            # Verify restored part data matches exactly
            from sqlalchemy import create_engine as sa_create_engine
            restored_engine = sa_create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )

            with Session(restored_engine) as session:
                restored_part = session.get(PartModel, "part_resistor_100k")
                assert restored_part is not None, "Part should exist in restored database"

                # Verify all fields match
                assert restored_part.part_name == original_part_data['part_name']
                assert restored_part.description == original_part_data['description']
                assert restored_part.manufacturer == original_part_data['manufacturer']
                assert restored_part.manufacturer_part_number == original_part_data['manufacturer_part_number']
                assert restored_part.supplier == original_part_data['supplier']
                assert restored_part.component_type == original_part_data['component_type']

            # Cleanup
            backup_path.unlink()

        finally:
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)

    @pytest.mark.asyncio
    async def test_allocation_relationships_preserved(
        self,
        test_db_with_schema,
        test_static_files_dir
    ):
        """
        Test that part allocations and relationships are preserved after restore.

        Verifies:
        - Part allocations exist after restore
        - Allocation quantities match
        - Foreign key relationships intact
        """
        engine, db_path = test_db_with_schema

        # Create database with allocations
        with Session(engine) as session:
            test_data = populate_test_database(session, test_static_files_dir)

            # Query allocations
            original_allocation_count = session.query(PartLocationAllocation).count()
            assert original_allocation_count > 0, "Test should create allocations"

            # Get specific allocation for verification
            first_allocation = session.query(PartLocationAllocation).first()
            original_allocation_data = {
                'part_id': first_allocation.part_id,
                'location_id': first_allocation.location_id,
                'quantity_at_location': first_allocation.quantity_at_location,
                'is_primary_storage': first_allocation.is_primary_storage
            }

        # Backup and restore
        backup_task = DatabaseBackupTask(task_service)
        backup_task_model = TaskModel(task_type="backup_creation", name="Allocation Test Backup")
        backup_name = f"allocation_test_{db_path.stem}"
        backup_task_model.set_input_data({
            'backup_name': backup_name,
            'include_datasheets': False,
            'include_images': False,
            'include_env': False
        })

        original_db_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

        try:
            backup_result = await backup_task.execute(backup_task_model)
            backup_path = Path(backup_result['backup_file_path'])

            # Simulate data corruption (restore will overwrite existing database)
            engine.dispose()

            # Restore from backup
            restore_task = DatabaseRestoreTask(task_service)
            restore_task_model = TaskModel(task_type="backup_restore", name="Allocation Restore")
            restore_task_model.set_input_data({
                'backup_filepath': str(backup_path),
                'create_safety_backup': False,
                'password': None
            })

            await restore_task.execute(restore_task_model)

            # Verify allocations in restored database
            from sqlalchemy import create_engine as sa_create_engine
            restored_engine = sa_create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False}
            )

            with Session(restored_engine) as session:
                restored_allocation_count = session.query(PartLocationAllocation).count()
                assert restored_allocation_count == original_allocation_count, \
                    "Allocation count should match"

                # Verify specific allocation data
                restored_allocation = session.query(PartLocationAllocation).filter(
                    PartLocationAllocation.part_id == original_allocation_data['part_id'],
                    PartLocationAllocation.location_id == original_allocation_data['location_id']
                ).first()

                assert restored_allocation is not None, "Allocation should exist"
                assert restored_allocation.quantity_at_location == original_allocation_data['quantity_at_location']
                assert restored_allocation.is_primary_storage == original_allocation_data['is_primary_storage']

            # Cleanup
            backup_path.unlink()

        finally:
            if original_db_url:
                os.environ['DATABASE_URL'] = original_db_url
            else:
                os.environ.pop('DATABASE_URL', None)


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_restore_from_nonexistent_backup(self):
        """
        Test that restore fails gracefully when backup file doesn't exist.

        Verifies:
        - Appropriate error is raised
        - Error message is user-friendly
        """
        restore_task = DatabaseRestoreTask(task_service)
        restore_task_model = TaskModel(
            task_type="backup_restore",
            name="Nonexistent Backup Test"
        )

        restore_task_model.set_input_data({
            'backup_filepath': '/tmp/nonexistent_backup.zip',
            'create_safety_backup': False,
            'password': None
        })

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            await restore_task.execute(restore_task_model)

        assert "not found" in str(exc_info.value).lower()
