"""
Backup Scheduler Service

Manages scheduled backups and retention cleanup using APScheduler.
Integrates with the task-based backup system.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select
import logging

from MakerMatrix.models.backup_models import BackupConfigModel
from MakerMatrix.models.task_models import CreateTaskRequest, TaskType, TaskPriority
from MakerMatrix.database.db import engine
from MakerMatrix.services.system.task_service import task_service

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled backup operations"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.backup_job_id = "scheduled_backup"
        self.retention_job_id = "backup_retention"

    async def start(self):
        """Start the backup scheduler"""
        try:
            # Load configuration and schedule backups
            await self.reload_schedule()

            # Start the scheduler
            self.scheduler.start()
            logger.info("Backup scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start backup scheduler: {e}", exc_info=True)

    async def stop(self):
        """Stop the backup scheduler"""
        try:
            self.scheduler.shutdown(wait=False)
            logger.info("Backup scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop backup scheduler: {e}", exc_info=True)

    async def reload_schedule(self):
        """Reload backup schedule from configuration"""
        try:
            with Session(engine) as session:
                config = session.exec(select(BackupConfigModel)).first()

                if not config:
                    logger.warning("No backup configuration found, skipping schedule setup")
                    return

                # Remove existing jobs
                if self.scheduler.get_job(self.backup_job_id):
                    self.scheduler.remove_job(self.backup_job_id)

                # Schedule backup if enabled
                if config.schedule_enabled:
                    trigger = self._get_trigger_from_config(config)

                    if trigger:
                        self.scheduler.add_job(
                            self._create_scheduled_backup,
                            trigger=trigger,
                            id=self.backup_job_id,
                            name="Scheduled Backup",
                            replace_existing=True
                        )

                        # Update next backup time (try to get next_run_time if available)
                        try:
                            job = self.scheduler.get_job(self.backup_job_id)
                            # APScheduler 3.x uses next_run_time, 4.x may use different API
                            next_run = getattr(job, 'next_run_time', None)
                            if next_run:
                                config.next_backup_at = next_run
                                session.add(config)
                                session.commit()
                                logger.info(f"Scheduled backup configured: {trigger}, next run: {next_run}")
                            else:
                                logger.info(f"Scheduled backup configured: {trigger} (next run time unavailable)")
                        except AttributeError:
                            logger.info(f"Scheduled backup configured: {trigger} (next_run_time not available in this APScheduler version)")
                    else:
                        logger.warning("Invalid backup schedule configuration")

                # Schedule retention cleanup (runs daily at 3 AM)
                if not self.scheduler.get_job(self.retention_job_id):
                    self.scheduler.add_job(
                        self._run_retention_cleanup,
                        trigger=CronTrigger(hour=3, minute=0),
                        id=self.retention_job_id,
                        name="Daily Retention Cleanup",
                        replace_existing=True
                    )
                    logger.info("Retention cleanup scheduled for daily 3:00 AM")

        except Exception as e:
            logger.error(f"Failed to reload backup schedule: {e}", exc_info=True)

    def _get_trigger_from_config(self, config: BackupConfigModel) -> Optional[CronTrigger]:
        """Convert backup configuration to APScheduler trigger"""
        try:
            if config.schedule_type == "nightly":
                # Nightly at 2 AM
                return CronTrigger(hour=2, minute=0)

            elif config.schedule_type == "weekly":
                # Weekly on Sunday at 2 AM
                return CronTrigger(day_of_week="sun", hour=2, minute=0)

            elif config.schedule_type == "custom" and config.schedule_cron:
                # Custom cron expression
                # Parse cron: minute hour day month day_of_week
                parts = config.schedule_cron.split()

                if len(parts) == 5:
                    return CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    )
                else:
                    logger.error(f"Invalid cron expression: {config.schedule_cron}")
                    return None

            else:
                logger.error(f"Unknown schedule type: {config.schedule_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create trigger from config: {e}", exc_info=True)
            return None

    async def _create_scheduled_backup(self):
        """Create a scheduled backup task"""
        try:
            logger.info("Creating scheduled backup...")

            # Load backup configuration
            with Session(engine) as session:
                config = session.exec(select(BackupConfigModel)).first()

                if not config:
                    logger.error("Backup configuration not found")
                    return

                # Generate backup name
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"scheduled_backup_{timestamp}"

                # Prepare input data for backup task
                input_data = {
                    "backup_name": backup_name,
                    "include_datasheets": True,
                    "include_images": True,
                    "include_env": True,
                }

                # Add encryption password if configured
                if config.encryption_required and config.encryption_password:
                    input_data["password"] = config.encryption_password
                    logger.info("Scheduled backup will use encryption password from configuration")
                elif config.encryption_required:
                    logger.warning("Encryption required but no password configured - backup will proceed without encryption")

                # Create backup task
                task_request = CreateTaskRequest(
                    task_type=TaskType.BACKUP_SCHEDULED,
                    name=f"Scheduled Backup: {backup_name}",
                    description="Automated scheduled backup",
                    priority=TaskPriority.HIGH,
                    input_data=input_data,
                    related_entity_type="system",
                    related_entity_id="scheduled_backup"
                )

                task = await task_service.create_task(task_request)
                logger.info(f"Scheduled backup task created: {task.id}")

                # Update last backup time
                config.last_backup_at = datetime.utcnow()

                # Calculate next backup time (if available)
                try:
                    job = self.scheduler.get_job(self.backup_job_id)
                    next_run = getattr(job, 'next_run_time', None)
                    if next_run:
                        config.next_backup_at = next_run
                except (AttributeError, Exception) as e:
                    logger.debug(f"Could not get next run time: {e}")

                session.add(config)
                session.commit()

                # After backup completes, run retention cleanup
                # (We'll let the daily retention job handle this, or trigger it manually)

        except Exception as e:
            logger.error(f"Failed to create scheduled backup: {e}", exc_info=True)

    async def _run_retention_cleanup(self):
        """Run backup retention cleanup"""
        try:
            logger.info("Running retention cleanup...")

            task_request = CreateTaskRequest(
                task_type=TaskType.BACKUP_RETENTION,
                name="Automatic Retention Cleanup",
                description="Automatic cleanup of old backups based on retention policy",
                priority=TaskPriority.NORMAL,
                input_data={},
                related_entity_type="system",
                related_entity_id="retention_cleanup"
            )

            task = await task_service.create_task(task_request)
            logger.info(f"Retention cleanup task created: {task.id}")

        except Exception as e:
            logger.error(f"Failed to run retention cleanup: {e}", exc_info=True)


# Global scheduler instance
backup_scheduler = BackupScheduler()
