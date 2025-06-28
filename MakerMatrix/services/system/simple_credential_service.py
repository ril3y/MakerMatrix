"""
Simple Supplier Credential Service

Basic credential management without encryption complexity.
Stores credentials in database, falls back to environment variables.
"""

import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session, select

from MakerMatrix.models.supplier_credentials import SimpleSupplierCredentials
from MakerMatrix.models.models import engine
from MakerMatrix.suppliers import SupplierRegistry
from MakerMatrix.suppliers.exceptions import SupplierNotFoundError
import logging

logger = logging.getLogger(__name__)


class SimpleCredentialService:
    """Simple credential management with database storage and environment fallback"""
    
    async def save_credentials(
        self, 
        supplier_name: str, 
        credentials: Dict[str, Any]
    ) -> bool:
        """Save credentials for a supplier"""
        try:
            # Validate supplier exists
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name.lower())
                credential_schema = supplier.get_credential_schema()
            except SupplierNotFoundError:
                raise ValueError(f"Unknown supplier: {supplier_name}")
            
            # Filter to only include schema-defined fields with values
            schema_field_names = [field.name for field in credential_schema]
            filtered_credentials = {
                k: v for k, v in credentials.items() 
                if k in schema_field_names and v and str(v).strip()
            }
            
            if not filtered_credentials:
                raise ValueError("No valid credentials provided")
            
            with Session(engine) as session:
                # Check if credentials already exist
                existing = session.exec(
                    select(SimpleSupplierCredentials).where(
                        SimpleSupplierCredentials.supplier_name == supplier_name.lower()
                    )
                ).first()
                
                if existing:
                    # Update existing
                    existing.credentials = filtered_credentials
                    existing.updated_at = datetime.utcnow()
                    existing.test_status = None  # Reset test status
                    existing.test_error_message = None
                    existing.last_tested_at = None
                else:
                    # Create new
                    credential_record = SimpleSupplierCredentials(
                        id=str(uuid.uuid4()),
                        supplier_name=supplier_name.lower(),
                        credentials=filtered_credentials
                    )
                    session.add(credential_record)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to save credentials for {supplier_name}: {e}")
            raise
    
    async def get_credentials(self, supplier_name: str) -> Optional[Dict[str, Any]]:
        """Get credentials for a supplier (database + environment fallback)"""
        try:
            credentials = {}
            
            # Get database credentials first
            with Session(engine) as session:
                credential_record = session.exec(
                    select(SimpleSupplierCredentials).where(
                        SimpleSupplierCredentials.supplier_name == supplier_name.lower()
                    )
                ).first()
                
                if credential_record and credential_record.credentials:
                    credentials.update(credential_record.credentials)
            
            # Add environment fallback (environment takes precedence for testing)
            env_credentials = self._get_env_credentials(supplier_name)
            credentials.update(env_credentials)
            
            return credentials if credentials else None
            
        except Exception as e:
            logger.error(f"Failed to get credentials for {supplier_name}: {e}")
            return None
    
    async def get_credential_status(self, supplier_name: str) -> Dict[str, Any]:
        """Get credential status for UI display"""
        try:
            # Get supplier schema
            try:
                supplier = SupplierRegistry.get_supplier(supplier_name.lower())
                credential_schema = supplier.get_credential_schema()
                required_fields = [field.name for field in credential_schema if field.required]
                all_fields = [field.name for field in credential_schema]
            except SupplierNotFoundError:
                return {"error": f"Unknown supplier: {supplier_name}", "configured": False}
            
            # Get database credentials
            db_credentials = {}
            test_info = {}
            
            with Session(engine) as session:
                credential_record = session.exec(
                    select(SimpleSupplierCredentials).where(
                        SimpleSupplierCredentials.supplier_name == supplier_name.lower()
                    )
                ).first()
                
                if credential_record:
                    db_credentials = credential_record.credentials or {}
                    test_info = {
                        "last_tested": credential_record.last_tested_at,
                        "test_status": credential_record.test_status,
                        "test_error": getattr(credential_record, 'test_error_message', None)
                    }
            
            # Get environment credentials
            env_credentials = self._get_env_credentials(supplier_name)
            
            # Determine what's configured
            db_fields = [k for k, v in db_credentials.items() if v]
            env_fields = [k for k, v in env_credentials.items() if v]
            all_configured = list(set(db_fields + env_fields))
            
            missing_required = [field for field in required_fields if field not in all_configured]
            
            return {
                "supplier_name": supplier_name,
                "has_database_credentials": bool(db_fields),
                "has_environment_credentials": bool(env_fields),
                "database_fields": db_fields,
                "environment_fields": env_fields,
                "configured_fields": all_configured,
                "required_fields": required_fields,
                "missing_required": missing_required,
                "fully_configured": len(missing_required) == 0,
                **test_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get credential status for {supplier_name}: {e}")
            return {"error": str(e), "configured": False}
    
    async def test_credentials(self, supplier_name: str, test_credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test credentials and update status"""
        try:
            supplier = SupplierRegistry.get_supplier(supplier_name.lower())
            
            # Use provided credentials or get from storage
            credentials = test_credentials or await self.get_credentials(supplier_name)
            
            if not credentials:
                return {
                    "success": False,
                    "message": "No credentials available to test",
                    "supplier_name": supplier_name
                }
            
            # Test the supplier
            supplier.configure(credentials=credentials, config={})
            test_start = datetime.utcnow()
            result = await supplier.test_connection()
            test_duration = (datetime.utcnow() - test_start).total_seconds()
            
            # Update test status in database
            await self._update_test_status(
                supplier_name,
                result.get("success", False),
                result.get("message", ""),
                test_duration
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Test failed for {supplier_name}: {error_msg}")
            
            await self._update_test_status(supplier_name, False, error_msg, 0)
            
            return {
                "success": False,
                "message": error_msg,
                "supplier_name": supplier_name
            }
    
    async def delete_credentials(self, supplier_name: str) -> bool:
        """Delete stored credentials"""
        try:
            with Session(engine) as session:
                credential_record = session.exec(
                    select(SimpleSupplierCredentials).where(
                        SimpleSupplierCredentials.supplier_name == supplier_name.lower()
                    )
                ).first()
                
                if credential_record:
                    session.delete(credential_record)
                    session.commit()
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete credentials for {supplier_name}: {e}")
            raise
    
    def _get_env_credentials(self, supplier_name: str) -> Dict[str, str]:
        """Get credentials from environment variables"""
        try:
            supplier = SupplierRegistry.get_supplier(supplier_name.lower())
            credential_schema = supplier.get_credential_schema()
        except SupplierNotFoundError:
            return {}
        
        env_credentials = {}
        supplier_upper = supplier_name.upper()
        
        for field in credential_schema:
            field_name = field.name
            
            # Try direct pattern: DIGIKEY_CLIENT_ID
            direct_env = f"{supplier_upper}_{field_name.upper()}"
            env_value = os.getenv(direct_env)
            if env_value:
                env_credentials[field_name] = env_value
                continue
            
            # Try common patterns based on field name
            common_patterns = {
                'client_id': [f'{supplier_upper}_CLIENT_ID', f'{supplier_upper}_ID'],
                'client_secret': [f'{supplier_upper}_CLIENT_SECRET', f'{supplier_upper}_SECRET'],
                'api_key': [f'{supplier_upper}_API_KEY', f'{supplier_upper}_KEY'],
                'storage_path': [f'{supplier_upper}_STORAGE_PATH'],
            }
            
            if field_name in common_patterns:
                for env_var in common_patterns[field_name]:
                    env_value = os.getenv(env_var)
                    if env_value:
                        env_credentials[field_name] = env_value
                        break
        
        return env_credentials
    
    async def _update_test_status(self, supplier_name: str, success: bool, message: str, duration: float):
        """Update test status in database"""
        try:
            with Session(engine) as session:
                credential_record = session.exec(
                    select(SimpleSupplierCredentials).where(
                        SimpleSupplierCredentials.supplier_name == supplier_name.lower()
                    )
                ).first()
                
                if not credential_record:
                    # Create minimal record for test status
                    credential_record = SimpleSupplierCredentials(
                        id=str(uuid.uuid4()),
                        supplier_name=supplier_name.lower(),
                        credentials={}
                    )
                    session.add(credential_record)
                
                credential_record.last_tested_at = datetime.utcnow()
                credential_record.test_status = "success" if success else "failed"
                if hasattr(credential_record, 'test_error_message'):
                    credential_record.test_error_message = message if not success else None
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update test status for {supplier_name}: {e}")


# Global instance
_credential_service = None

def get_credential_service() -> SimpleCredentialService:
    """Get global credential service instance"""
    global _credential_service
    if _credential_service is None:
        _credential_service = SimpleCredentialService()
    return _credential_service