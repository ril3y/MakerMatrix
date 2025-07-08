import logging
from typing import Optional
from sqlmodel import Session, select
from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
from MakerMatrix.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class CSVImportConfigRepository(BaseRepository[CSVImportConfigModel]):
    """
    Repository for CSV import configuration database operations.
    
    Follows the established repository pattern where ONLY repositories
    handle database sessions and SQL operations. Services delegate all
    database operations to repositories.
    """
    
    def __init__(self):
        super().__init__(CSVImportConfigModel)
    
    def get_default_config(self, session: Session) -> Optional[CSVImportConfigModel]:
        """Get the default CSV import configuration."""
        query = select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")
        config = session.exec(query).first()
        return config
    
    def save_config(self, session: Session, config_data: dict) -> CSVImportConfigModel:
        """Save CSV import configuration (create or update default config)."""
        # Check if default config exists
        existing_config = self.get_default_config(session)
        
        if existing_config:
            # Update existing config
            for key, value in config_data.items():
                if hasattr(existing_config, key):
                    setattr(existing_config, key, value)
            
            session.add(existing_config)
            session.commit()
            session.refresh(existing_config)
            
            logger.info("Updated default CSV import configuration")
            return existing_config
        else:
            # Create new default config
            config_data['id'] = 'default'
            config = CSVImportConfigModel(**config_data)
            session.add(config)
            session.commit()
            session.refresh(config)
            
            logger.info("Created new default CSV import configuration")
            return config
    
    def get_config_by_id(self, session: Session, config_id: str) -> Optional[CSVImportConfigModel]:
        """Get configuration by ID (convenience method, uses base repository)."""
        return self.get_by_id(session, config_id)
    
    def delete_config(self, session: Session, config_id: str) -> bool:
        """Delete a configuration by ID. Returns True if deleted, False if not found."""
        config = self.get_by_id(session, config_id)
        if not config:
            return False
        
        session.delete(config)
        session.commit()
        logger.info(f"Deleted CSV import configuration {config_id}")
        return True
    
    def get_all_configs(self, session: Session) -> list[CSVImportConfigModel]:
        """Get all CSV import configurations."""
        query = select(CSVImportConfigModel)
        configs = session.exec(query).all()
        return list(configs)
    
    def reset_to_defaults(self, session: Session) -> CSVImportConfigModel:
        """Reset configuration to default values."""
        default_config = {
            'id': 'default',
            'download_datasheets': True,
            'download_images': True,
            'overwrite_existing_files': False,
            'download_timeout_seconds': 30,
            'show_progress': True
        }
        
        # Delete existing default config if it exists
        existing_config = self.get_default_config(session)
        if existing_config:
            session.delete(existing_config)
            session.commit()
        
        # Create new default config
        config = CSVImportConfigModel(**default_config)
        session.add(config)
        session.commit()
        session.refresh(config)
        
        logger.info("Reset CSV import configuration to defaults")
        return config