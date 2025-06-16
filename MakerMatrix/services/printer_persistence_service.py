"""
Service for managing printer persistence and restoration.
Integrates with the PrinterManagerService to provide database persistence.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.engine import Engine
from datetime import datetime

from MakerMatrix.models.models import PrinterModel, engine
from MakerMatrix.repositories.printer_db_repository import PrinterDatabaseRepository
from MakerMatrix.services.printer_manager_service import get_printer_manager
# Import will be done dynamically when needed


class PrinterPersistenceService:
    """Service for managing printer database persistence and restoration."""
    
    def __init__(self, db_engine: Engine = engine):
        self.db_repo = PrinterDatabaseRepository(db_engine)
        self.printer_manager = get_printer_manager()  # Use the global singleton
    
    def save_printer_to_database(self, printer_data: Dict[str, Any]) -> PrinterModel:
        """Save a printer configuration to the database."""
        # Ensure required fields are present
        required_fields = ['printer_id', 'name', 'driver_type', 'model', 'backend', 'identifier']
        for field in required_fields:
            if field not in printer_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Set defaults for optional fields
        printer_data.setdefault('dpi', 300)
        printer_data.setdefault('scaling_factor', 1.0)
        printer_data.setdefault('config', {})
        
        # Check if printer already exists
        existing_printer = self.db_repo.get_printer_by_id(printer_data['printer_id'])
        if existing_printer:
            print(f"[DEBUG] Printer {printer_data['printer_id']} already exists in database, updating instead")
            # Update existing printer
            updated_printer = self.db_repo.update_printer(printer_data['printer_id'], printer_data)
            if updated_printer:
                return updated_printer
            else:
                print(f"[ERROR] Failed to update existing printer {printer_data['printer_id']}")
                raise Exception(f"Failed to update existing printer {printer_data['printer_id']}")
        else:
            # Create new printer
            print(f"[DEBUG] Creating new printer {printer_data['printer_id']} in database")
            return self.db_repo.create_printer(printer_data)
    
    async def restore_printers_from_database(self) -> List[str]:
        """Restore all active printers from database to memory."""
        restored_printer_ids = []
        
        try:
            # Get all active printers from database
            saved_printers = self.db_repo.get_all_printers(active_only=True)
            
            for printer_model in saved_printers:
                try:
                    # Convert database model to printer registration data
                    printer_data = {
                        'printer_id': printer_model.printer_id,
                        'name': printer_model.name,
                        'driver_type': printer_model.driver_type,
                        'model': printer_model.model,
                        'backend': printer_model.backend,
                        'identifier': printer_model.identifier,
                        'dpi': printer_model.dpi,
                        'scaling_factor': printer_model.scaling_factor
                    }
                    
                    # Additional config if available
                    if printer_model.config:
                        printer_data.update(printer_model.config)
                    
                    # Create printer instance and register with the printer manager
                    printer = self._create_printer_instance(printer_data)
                    success = await self.printer_manager.register_printer(printer)
                    
                    if success:
                        restored_printer_ids.append(printer_model.printer_id)
                        # Update last_seen timestamp
                        self.db_repo.update_last_seen(printer_model.printer_id)
                    else:
                        print(f"Failed to restore printer {printer_model.printer_id}")
                        
                except Exception as e:
                    print(f"Error restoring printer {printer_model.printer_id}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error during printer restoration: {str(e)}")
        
        return restored_printer_ids
    
    async def register_printer_with_persistence(self, printer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a printer both in memory and database."""
        try:
            print(f"[DEBUG] Attempting to register printer with data: {printer_data}")
            
            # Create the actual printer object based on driver type
            printer = self._create_printer_instance(printer_data)
            print(f"[DEBUG] Created printer instance: {printer}")
            
            # Register with the printer manager
            success = await self.printer_manager.register_printer(printer)
            print(f"[DEBUG] Printer manager registration result: {success}")
            
            if not success:
                print(f"[ERROR] Printer manager registration failed")
                return {
                    'success': False,
                    'error': 'Failed to register printer with manager',
                    'persisted': False
                }
            
            # Check if printer is actually in the manager
            printers = await self.printer_manager.list_printers()
            print(f"[DEBUG] Printers in manager after registration: {len(printers)}")
            for p in printers:
                info = p.get_printer_info()
                print(f"[DEBUG] - {info.id}: {info.name}")
            
            # If successful, save to database
            try:
                db_printer = self.save_printer_to_database(printer_data)
                print(f"[DEBUG] Saved to database with ID: {db_printer.id}")
                result = {
                    'success': True,
                    'database_id': db_printer.id,
                    'persisted': True
                }
            except Exception as db_error:
                # Registration succeeded but database save failed
                result = {
                    'success': True,
                    'persisted': False,
                    'persistence_error': str(db_error)
                }
                print(f"Warning: Printer registered but not persisted to database: {db_error}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Exception during printer registration: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f"Failed to register printer: {str(e)}",
                'persisted': False
            }
    
    def _create_printer_instance(self, printer_data: Dict[str, Any]):
        """Create a printer instance based on the driver type."""
        driver_type = printer_data.get('driver_type')
        
        if driver_type == 'brother_ql':
            from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern
            
            return BrotherQLModern(
                printer_id=printer_data['printer_id'],
                name=printer_data['name'],
                model=printer_data['model'],
                backend=printer_data['backend'],
                identifier=printer_data['identifier'],
                dpi=printer_data.get('dpi', 300),
                scaling_factor=printer_data.get('scaling_factor', 1.0)
            )
        else:
            raise ValueError(f"Unsupported driver type: {driver_type}")
    
    async def remove_printer_with_persistence(self, printer_id: str) -> Dict[str, Any]:
        """Remove a printer from both memory and database."""
        result = {'success': False, 'memory_removed': False, 'database_removed': False}
        
        try:
            # Remove from memory first
            memory_removed = await self.printer_manager.unregister_printer(printer_id)
            result['memory_removed'] = memory_removed
            
            # Remove from database
            database_removed = self.db_repo.delete_printer(printer_id)
            result['database_removed'] = database_removed
            
            # Consider it successful if either removal worked
            result['success'] = result['memory_removed'] or result['database_removed']
            
            if not result['success']:
                result['error'] = f"Failed to remove printer {printer_id} from both memory and database"
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_persistent_printers(self) -> List[Dict[str, Any]]:
        """Get all printers stored in the database."""
        try:
            saved_printers = self.db_repo.get_all_printers(active_only=True)
            return [printer.to_dict() for printer in saved_printers]
        except Exception as e:
            print(f"Error retrieving persistent printers: {str(e)}")
            return []
    
    def get_printer_from_database(self, printer_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific printer from the database."""
        try:
            printer = self.db_repo.get_printer_by_id(printer_id)
            return printer.to_dict() if printer else None
        except Exception as e:
            print(f"Error retrieving printer {printer_id} from database: {str(e)}")
            return None
    
    def sync_printer_status(self, printer_id: str) -> bool:
        """Update the last_seen timestamp for a printer."""
        try:
            return self.db_repo.update_last_seen(printer_id)
        except Exception as e:
            print(f"Error updating printer status for {printer_id}: {str(e)}")
            return False


# Global service instance
_printer_persistence_service: Optional[PrinterPersistenceService] = None


def get_printer_persistence_service() -> PrinterPersistenceService:
    """Get the global printer persistence service instance."""
    global _printer_persistence_service
    if _printer_persistence_service is None:
        _printer_persistence_service = PrinterPersistenceService()
    return _printer_persistence_service