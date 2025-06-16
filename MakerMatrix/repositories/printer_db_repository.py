"""
Database-based repository for printer persistence operations.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.engine import Engine
from sqlmodel import Session, select
from datetime import datetime

from MakerMatrix.models.models import PrinterModel


class PrinterDatabaseRepository:
    """Repository for managing printer persistence in database."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def create_printer(self, printer_data: Dict[str, Any]) -> PrinterModel:
        """Create a new printer in the database."""
        with Session(self.engine) as session:
            printer = PrinterModel(**printer_data)
            session.add(printer)
            session.commit()
            session.refresh(printer)
            return printer
    
    def get_printer_by_id(self, printer_id: str) -> Optional[PrinterModel]:
        """Get a printer by its printer_id."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            return session.exec(statement).first()
    
    def get_printer_by_db_id(self, db_id: str) -> Optional[PrinterModel]:
        """Get a printer by its database ID."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.id == db_id)
            return session.exec(statement).first()
    
    def get_all_printers(self, active_only: bool = True) -> List[PrinterModel]:
        """Get all printers, optionally filtering by active status."""
        with Session(self.engine) as session:
            statement = select(PrinterModel)
            if active_only:
                statement = statement.where(PrinterModel.is_active == True)
            return list(session.exec(statement).all())
    
    def update_printer(self, printer_id: str, update_data: Dict[str, Any]) -> Optional[PrinterModel]:
        """Update a printer's data."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            printer = session.exec(statement).first()
            
            if not printer:
                return None
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(printer, key):
                    setattr(printer, key, value)
            
            # Update timestamp
            printer.updated_at = datetime.utcnow()
            
            session.add(printer)
            session.commit()
            session.refresh(printer)
            return printer
    
    def update_last_seen(self, printer_id: str) -> bool:
        """Update the last_seen timestamp for a printer."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            printer = session.exec(statement).first()
            
            if not printer:
                return False
            
            printer.last_seen = datetime.utcnow()
            session.add(printer)
            session.commit()
            return True
    
    def delete_printer(self, printer_id: str) -> bool:
        """Delete a printer from the database."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            printer = session.exec(statement).first()
            
            if not printer:
                return False
            
            session.delete(printer)
            session.commit()
            return True
    
    def deactivate_printer(self, printer_id: str) -> bool:
        """Mark a printer as inactive instead of deleting it."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            printer = session.exec(statement).first()
            
            if not printer:
                return False
            
            printer.is_active = False
            printer.updated_at = datetime.utcnow()
            session.add(printer)
            session.commit()
            return True
    
    def printer_exists(self, printer_id: str) -> bool:
        """Check if a printer exists in the database."""
        with Session(self.engine) as session:
            statement = select(PrinterModel).where(PrinterModel.printer_id == printer_id)
            return session.exec(statement).first() is not None