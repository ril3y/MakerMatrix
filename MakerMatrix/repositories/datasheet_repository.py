import logging
from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select, and_
from MakerMatrix.models.models import DatasheetModel
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class DatasheetRepository(BaseRepository[DatasheetModel]):
    """
    Repository for datasheet database operations.

    Follows the established repository pattern where ONLY repositories
    handle database sessions and SQL operations. Services delegate all
    database operations to repositories.
    """

    def __init__(self):
        super().__init__(DatasheetModel)

    def get_datasheet_by_part_and_url(
        self, session: Session, part_id: str, source_url: str
    ) -> Optional[DatasheetModel]:
        """Get datasheet by part ID and source URL."""
        query = select(DatasheetModel).where(
            and_(DatasheetModel.part_id == part_id, DatasheetModel.source_url == source_url)
        )
        datasheet = session.exec(query).first()
        return datasheet

    def create_datasheet(self, session: Session, datasheet_data: dict) -> DatasheetModel:
        """Create a new datasheet with proper session management."""
        datasheet = DatasheetModel(**datasheet_data)
        session.add(datasheet)
        session.commit()
        session.refresh(datasheet)
        return datasheet

    def update_datasheet(self, session: Session, datasheet: DatasheetModel) -> DatasheetModel:
        """Update an existing datasheet with proper session management."""
        datasheet.updated_at = datetime.utcnow()
        session.add(datasheet)
        session.commit()
        session.refresh(datasheet)
        return datasheet

    def get_datasheets_by_part(self, session: Session, part_id: str) -> List[DatasheetModel]:
        """Get all datasheets for a specific part."""
        query = select(DatasheetModel).where(DatasheetModel.part_id == part_id)
        datasheets = session.exec(query).all()
        return list(datasheets)

    def delete_datasheet(self, session: Session, datasheet_id: str) -> bool:
        """Delete a datasheet by ID. Returns True if deleted, False if not found."""
        datasheet = self.get_by_id(session, datasheet_id)
        if not datasheet:
            return False

        session.delete(datasheet)
        session.commit()
        logger.info(f"Deleted datasheet {datasheet_id} for part {datasheet.part_id}")
        return True

    def get_datasheet_by_id(self, session: Session, datasheet_id: str) -> Optional[DatasheetModel]:
        """Get datasheet by ID (convenience method, uses base repository)."""
        return self.get_by_id(session, datasheet_id)

    def get_downloaded_datasheets(self, session: Session, part_id: str = None) -> List[DatasheetModel]:
        """Get all successfully downloaded datasheets, optionally filtered by part."""
        query = select(DatasheetModel).where(DatasheetModel.is_downloaded == True)

        if part_id:
            query = query.where(DatasheetModel.part_id == part_id)

        datasheets = session.exec(query).all()
        return list(datasheets)

    def get_failed_datasheets(self, session: Session, part_id: str = None) -> List[DatasheetModel]:
        """Get all datasheets that failed to download, optionally filtered by part."""
        query = select(DatasheetModel).where(
            and_(DatasheetModel.is_downloaded == False, DatasheetModel.download_error.is_not(None))
        )

        if part_id:
            query = query.where(DatasheetModel.part_id == part_id)

        datasheets = session.exec(query).all()
        return list(datasheets)

    def mark_download_failed(self, session: Session, datasheet_id: str, error_message: str) -> Optional[DatasheetModel]:
        """Mark a datasheet as failed to download with error message."""
        datasheet = self.get_by_id(session, datasheet_id)
        if not datasheet:
            return None

        datasheet.is_downloaded = False
        datasheet.download_error = error_message
        datasheet.updated_at = datetime.utcnow()

        session.add(datasheet)
        session.commit()
        session.refresh(datasheet)

        logger.warning(f"Marked datasheet {datasheet_id} as failed: {error_message}")
        return datasheet

    def mark_download_successful(
        self,
        session: Session,
        datasheet_id: str,
        file_uuid: str,
        file_size: int,
        original_filename: str,
        file_extension: str,
    ) -> Optional[DatasheetModel]:
        """Mark a datasheet as successfully downloaded with file details."""
        datasheet = self.get_by_id(session, datasheet_id)
        if not datasheet:
            return None

        datasheet.is_downloaded = True
        datasheet.download_error = None
        datasheet.file_uuid = file_uuid
        datasheet.file_size = file_size
        datasheet.original_filename = original_filename
        datasheet.file_extension = file_extension
        datasheet.updated_at = datetime.utcnow()

        session.add(datasheet)
        session.commit()
        session.refresh(datasheet)

        logger.info(f"Marked datasheet {datasheet_id} as successfully downloaded")
        return datasheet
