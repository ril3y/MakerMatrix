"""
Backup Management Routes

Comprehensive backup, restore, and retention management endpoints.
Supports encrypted backups, scheduled backups, and retention policies.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from sqlmodel import Session, select

from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority
from MakerMatrix.models.backup_models import BackupConfigModel, BackupConfigCreate, BackupConfigUpdate
from MakerMatrix.auth.guards import require_permission
from MakerMatrix.database.db import engine
from MakerMatrix.routers.base import BaseRouter, standard_error_handling
from MakerMatrix.services.system.task_service import task_service

router = APIRouter(prefix="/api/backup", tags=["Backup Management"])
base_router = BaseRouter()


# ========================================
# Backup Creation Routes
# ========================================

@router.post("/create")
@standard_error_handling
async def create_backup(
    password: Optional[str] = Form(None),
    include_datasheets: bool = Form(True),
    include_images: bool = Form(True),
    include_env: bool = Form(True),
    current_user: UserModel = Depends(require_permission("admin"))
):
    """
    Create a comprehensive encrypted backup

    Creates a task-based backup operation that includes:
    - SQLite database file
    - Environment configuration (.env)
    - Datasheet files
    - Image files

    Optionally encrypts the backup with a password.
    """
    # Generate backup name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"makermatrix_backup_{timestamp}"

    # Prepare input data
    input_data = {
        "backup_name": backup_name,
        "include_datasheets": include_datasheets,
        "include_images": include_images,
        "include_env": include_env
    }

    # Add password if provided
    if password:
        input_data["password"] = password

    # Create backup task
    task_request = CreateTaskRequest(
        task_type=TaskType.BACKUP_CREATION,
        name=f"Encrypted Backup: {backup_name}" if password else f"Backup: {backup_name}",
        description="Create comprehensive backup with encryption" if password else "Create comprehensive backup",
        priority=TaskPriority.HIGH,
        input_data=input_data,
        related_entity_type="system",
        related_entity_id="database",
        created_by_user_id=current_user.id
    )

    task_response = await task_service.create_task(task_request, user_id=current_user.id)

    if not task_response.success:
        raise HTTPException(status_code=500, detail=task_response.message)

    task_data = task_response.data

    # Update backup config with last backup time
    with Session(engine) as session:
        config = session.exec(select(BackupConfigModel)).first()
        if config:
            config.last_backup_at = datetime.utcnow()
            session.add(config)
            session.commit()

    return base_router.build_success_response(
        message="Backup task created successfully. Monitor progress via task endpoints.",
        data={
            "task_id": task_data["id"],
            "task_type": task_data["task_type"],
            "task_name": task_data["name"],
            "status": task_data["status"],
            "priority": task_data["priority"],
            "backup_name": backup_name,
            "encrypted": bool(password),
            "monitor_url": f"/api/tasks/{task_data['id']}"
        }
    )


# ========================================
# Backup Restore Routes
# ========================================

@router.post("/restore")
@standard_error_handling
async def restore_backup(
    backup_file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    create_safety_backup: bool = Form(True),
    current_user: UserModel = Depends(require_permission("admin"))
):
    """
    Restore from an encrypted backup file

    Accepts a backup file upload and restores:
    - Database
    - .env file
    - Datasheets
    - Images

    Creates a safety backup before restore and supports rollback on failure.
    """
    # Validate file extension
    filename = backup_file.filename
    if not filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Must be .zip"
        )

    # Save uploaded file temporarily
    base_path = Path(__file__).parent.parent
    temp_dir = base_path / "temp"
    temp_dir.mkdir(exist_ok=True)

    temp_file_path = temp_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"

    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            content = await backup_file.read()
            buffer.write(content)

        # Create restore task
        input_data = {
            "backup_filepath": str(temp_file_path),
            "create_safety_backup": create_safety_backup
        }

        # Add password if provided
        if password:
            input_data["password"] = password

        task_request = CreateTaskRequest(
            task_type=TaskType.BACKUP_RESTORE,
            name=f"Restore from: {filename}",
            description="Restore database and files from encrypted backup" if password else "Restore database and files from backup",
            priority=TaskPriority.URGENT,
            input_data=input_data,
            related_entity_type="system",
            related_entity_id="database",
            created_by_user_id=current_user.id
        )

        task_response = await task_service.create_task(task_request, user_id=current_user.id)

        if not task_response.success:
            raise HTTPException(status_code=500, detail=task_response.message)

        task_data = task_response.data

        return base_router.build_success_response(
            message="Restore task created successfully. Application will restart after restore completes.",
            data={
                "task_id": task_data["id"],
                "task_type": task_data["task_type"],
                "task_name": task_data["name"],
                "status": task_data["status"],
                "priority": task_data["priority"],
                "safety_backup_enabled": create_safety_backup,
                "monitor_url": f"/api/tasks/{task_data['id']}",
                "warning": "Application services will need to restart after restore completion"
            }
        )

    except Exception as e:
        # Clean up temp file on error
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise


# ========================================
# Backup Download and List Routes
# ========================================

@router.get("/list")
@standard_error_handling
async def list_backups(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """List all available backup files"""
    base_path = Path(__file__).parent.parent
    backups_dir = base_path / "backups"

    if not backups_dir.exists():
        return base_router.build_success_response(
            message="No backups found",
            data={"backups": [], "total_count": 0, "total_size_mb": 0}
        )

    backups = []
    total_size = 0

    # Get all .zip files
    for backup_file in backups_dir.glob("*.zip"):
        if backup_file.is_file():
            stat = backup_file.stat()
            size_bytes = stat.st_size
            total_size += size_bytes

            backups.append({
                "filename": backup_file.name,
                "encrypted": "_encrypted" in backup_file.name,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "download_url": f"/api/backup/download/{backup_file.name}"
            })

    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x["created_at"], reverse=True)

    return base_router.build_success_response(
        message=f"Found {len(backups)} backup files",
        data={
            "backups": backups,
            "total_count": len(backups),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    )


@router.get("/download/{backup_filename}")
@standard_error_handling
async def download_backup(
    backup_filename: str,
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Download a backup file"""
    # Security validation
    if '..' in backup_filename or '/' in backup_filename:
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    if not backup_filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Locate backup file
    base_path = Path(__file__).parent.parent
    backups_dir = base_path / "backups"
    backup_file_path = backups_dir / backup_filename

    if not backup_file_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    # All files are zip format
    media_type = "application/zip"

    return FileResponse(
        path=str(backup_file_path),
        filename=backup_filename,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={backup_filename}"}
    )


@router.delete("/delete/{backup_filename}")
@standard_error_handling
async def delete_backup(
    backup_filename: str,
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Delete a backup file"""
    # Security validation
    if '..' in backup_filename or '/' in backup_filename:
        raise HTTPException(status_code=400, detail="Invalid backup filename")

    if not backup_filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid file format")

    # Locate and delete backup file
    base_path = Path(__file__).parent.parent
    backups_dir = base_path / "backups"
    backup_file_path = backups_dir / backup_filename

    if not backup_file_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    # Get file size before deletion
    size_mb = round(backup_file_path.stat().st_size / (1024 * 1024), 2)

    # Delete file
    backup_file_path.unlink()

    return base_router.build_success_response(
        message=f"Backup '{backup_filename}' deleted successfully",
        data={
            "deleted_filename": backup_filename,
            "space_freed_mb": size_mb
        }
    )


# ========================================
# Retention Policy Routes
# ========================================

@router.post("/retention/run")
@standard_error_handling
async def run_retention_cleanup(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Manually trigger backup retention cleanup"""
    task_request = CreateTaskRequest(
        task_type=TaskType.BACKUP_RETENTION,
        name="Manual Backup Retention Cleanup",
        description="Clean up old backups based on retention policy",
        priority=TaskPriority.NORMAL,
        input_data={},
        related_entity_type="system",
        related_entity_id="backup_retention",
        created_by_user_id=current_user.id
    )

    task_response = await task_service.create_task(task_request, user_id=current_user.id)

    if not task_response.success:
        raise HTTPException(status_code=500, detail=task_response.message)

    task_data = task_response.data

    return base_router.build_success_response(
        message="Retention cleanup task created successfully",
        data={
            "task_id": task_data["id"],
            "task_type": task_data["task_type"],
            "task_name": task_data["name"],
            "status": task_data["status"],
            "monitor_url": f"/api/tasks/{task_data['id']}"
        }
    )


# ========================================
# Backup Configuration Routes
# ========================================

@router.get("/config")
@standard_error_handling
async def get_backup_config(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Get current backup configuration (password excluded for security)"""
    with Session(engine) as session:
        config = session.exec(select(BackupConfigModel)).first()

        if not config:
            # Create default config
            config = BackupConfigModel()
            session.add(config)
            session.commit()
            session.refresh(config)

        return base_router.build_success_response(
            message="Backup configuration retrieved successfully",
            data={
                "id": config.id,
                "schedule_enabled": config.schedule_enabled,
                "schedule_type": config.schedule_type,
                "schedule_cron": config.schedule_cron,
                "retention_count": config.retention_count,
                "last_backup_at": config.last_backup_at.isoformat() if config.last_backup_at else None,
                "next_backup_at": config.next_backup_at.isoformat() if config.next_backup_at else None,
                "encryption_required": config.encryption_required,
                "encryption_password": None,  # Never send password to frontend
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat()
            }
        )


@router.get("/config/password-set")
@standard_error_handling
async def check_password_set(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Check if scheduled backup encryption password is configured"""
    with Session(engine) as session:
        config = session.exec(select(BackupConfigModel)).first()

        password_set = bool(config and config.encryption_password)

        return base_router.build_success_response(
            message="Password status retrieved successfully",
            data={
                "password_set": password_set
            }
        )


@router.put("/config")
@standard_error_handling
async def update_backup_config(
    config_update: BackupConfigUpdate,
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Update backup configuration"""
    with Session(engine) as session:
        config = session.exec(select(BackupConfigModel)).first()

        if not config:
            # Create new config
            config = BackupConfigModel()
            session.add(config)

        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)

        config.updated_at = datetime.utcnow()

        session.add(config)
        session.commit()
        session.refresh(config)

        # Reload scheduler to apply new schedule
        try:
            from MakerMatrix.services.system.backup_scheduler import backup_scheduler
            await backup_scheduler.reload_schedule()
        except Exception as e:
            # Log error but don't fail the update
            import logging
            logging.error(f"Failed to reload backup schedule: {e}")

        return base_router.build_success_response(
            message="Backup configuration updated successfully",
            data={
                "id": config.id,
                "schedule_enabled": config.schedule_enabled,
                "schedule_type": config.schedule_type,
                "schedule_cron": config.schedule_cron,
                "retention_count": config.retention_count,
                "encryption_required": config.encryption_required,
                "updated_at": config.updated_at.isoformat()
            }
        )


# ========================================
# Backup Status Routes
# ========================================

@router.get("/status")
@standard_error_handling
async def get_backup_status(
    current_user: UserModel = Depends(require_permission("admin"))
):
    """Get comprehensive backup system status"""
    from MakerMatrix.database.db import DATABASE_URL

    # Get database info
    db_path_raw = DATABASE_URL.replace("sqlite:///", "")
    db_path = Path(db_path_raw)

    if not db_path.exists():
        db_path = Path(__file__).parent.parent.parent / "makers_matrix.db"

    db_size_mb = 0
    db_last_modified = None

    if db_path.exists():
        stat = db_path.stat()
        db_size_mb = round(stat.st_size / (1024 * 1024), 2)
        db_last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

    # Get backup directory info
    base_path = Path(__file__).parent.parent
    backups_dir = base_path / "backups"

    backup_count = 0
    backup_size_mb = 0
    latest_backup = None

    if backups_dir.exists():
        backup_files = list(backups_dir.glob("*.zip"))
        backup_count = len(backup_files)

        for backup_file in backup_files:
            backup_size_mb += backup_file.stat().st_size / (1024 * 1024)

        if backup_files:
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest = backup_files[0]
            latest_backup = {
                "filename": latest.name,
                "size_mb": round(latest.stat().st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(latest.stat().st_mtime).isoformat(),
                "encrypted": "_encrypted" in latest.name
            }

    # Get backup config
    with Session(engine) as session:
        config = session.exec(select(BackupConfigModel)).first()

        config_data = None
        if config:
            config_data = {
                "schedule_enabled": config.schedule_enabled,
                "schedule_type": config.schedule_type,
                "retention_count": config.retention_count,
                "last_backup_at": config.last_backup_at.isoformat() if config.last_backup_at else None,
                "next_backup_at": config.next_backup_at.isoformat() if config.next_backup_at else None
            }

    return base_router.build_success_response(
        message="Backup status retrieved successfully",
        data={
            "database": {
                "size_mb": db_size_mb,
                "last_modified": db_last_modified,
                "path": str(db_path)
            },
            "backups": {
                "count": backup_count,
                "total_size_mb": round(backup_size_mb, 2),
                "latest_backup": latest_backup
            },
            "configuration": config_data
        }
    )
