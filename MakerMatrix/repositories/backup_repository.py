"""
Backup Configuration Repository

Encapsulates SQL access for BackupConfigModel so routes can use a repository
through Depends() / mocking instead of constructing raw Session(engine) blocks.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from MakerMatrix.models.backup_models import BackupConfigModel


class BackupRepository:
    """Repository for backup configuration storage."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def get_config(self) -> Optional[BackupConfigModel]:
        """Return the singleton backup config row, or None if not set."""
        with Session(self.engine) as session:
            return session.exec(select(BackupConfigModel)).first()

    def get_or_create_config(self) -> BackupConfigModel:
        """Return existing backup config, creating a default one if missing."""
        with Session(self.engine) as session:
            config = session.exec(select(BackupConfigModel)).first()
            if not config:
                config = BackupConfigModel()
                session.add(config)
                session.commit()
                session.refresh(config)
            return config

    def update_last_backup_at(self, when: datetime) -> None:
        """Mark the last-backup timestamp on the singleton config."""
        with Session(self.engine) as session:
            config = session.exec(select(BackupConfigModel)).first()
            if config:
                config.last_backup_at = when
                session.add(config)
                session.commit()

    def update_config(self, update_data: dict) -> BackupConfigModel:
        """Update fields on the singleton backup config, creating it if missing."""
        with Session(self.engine) as session:
            config = session.exec(select(BackupConfigModel)).first()
            if not config:
                config = BackupConfigModel()
                session.add(config)

            for key, value in update_data.items():
                setattr(config, key, value)
            config.updated_at = datetime.utcnow()

            session.add(config)
            session.commit()
            session.refresh(config)
            return config

    def is_password_set(self) -> bool:
        """Return True if a scheduled-backup encryption password is stored."""
        with Session(self.engine) as session:
            config = session.exec(select(BackupConfigModel)).first()
            return bool(config and config.encryption_password)
