"""
Credential Repository
Simple credential management repository following established patterns.
"""

import logging
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, delete
from MakerMatrix.models.supplier_credentials import SimpleSupplierCredentials
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class CredentialRepository:
    """Repository for managing supplier credentials."""
    
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_credentials(session: Session, supplier_name: str) -> Optional[SimpleSupplierCredentials]:
        """
        Get credentials for a specific supplier.
        
        Args:
            session: Database session
            supplier_name: Name of the supplier
            
        Returns:
            SimpleSupplierCredentials or None if not found
        """
        return session.exec(
            select(SimpleSupplierCredentials).where(
                SimpleSupplierCredentials.supplier_name == supplier_name.lower()
            )
        ).first()

    @staticmethod
    def save_credentials(session: Session, supplier_name: str, credentials: Dict[str, Any]) -> SimpleSupplierCredentials:
        """
        Save or update credentials for a supplier.
        
        Args:
            session: Database session
            supplier_name: Name of the supplier
            credentials: Credential data dictionary
            
        Returns:
            SimpleSupplierCredentials: The saved credential record
        """
        existing = CredentialRepository.get_credentials(session, supplier_name)
        
        if existing:
            # Update existing credentials
            existing.credentials = credentials
            existing.updated_at = None  # Will be set by model if field exists
            session.add(existing)
            session.commit()
            session.refresh(existing)
            logger.debug(f"[REPO] Updated credentials for supplier: {supplier_name}")
            return existing
        else:
            # Create new credentials
            new_cred = SimpleSupplierCredentials(
                supplier_name=supplier_name.lower(),
                credentials=credentials
            )
            session.add(new_cred)
            session.commit()
            session.refresh(new_cred)
            logger.debug(f"[REPO] Created new credentials for supplier: {supplier_name}")
            return new_cred

    @staticmethod
    def delete_credentials(session: Session, supplier_name: str) -> bool:
        """
        Delete credentials for a supplier.
        
        Args:
            session: Database session
            supplier_name: Name of the supplier
            
        Returns:
            bool: True if credentials were deleted, False if not found
        """
        credential_record = CredentialRepository.get_credentials(session, supplier_name)
        if credential_record:
            session.delete(credential_record)
            session.commit()
            logger.debug(f"[REPO] Deleted credentials for supplier: {supplier_name}")
            return True
        return False

    @staticmethod
    def get_all_credentials(session: Session) -> List[SimpleSupplierCredentials]:
        """
        Get all stored credentials.
        
        Args:
            session: Database session
            
        Returns:
            List[SimpleSupplierCredentials]: List of all credential records
        """
        return session.exec(select(SimpleSupplierCredentials)).all()

    @staticmethod
    def clear_all_credentials(session: Session) -> int:
        """
        Delete all credentials (admin function).
        
        Args:
            session: Database session
            
        Returns:
            int: Number of credential records deleted
        """
        # Count existing records
        existing_count = len(session.exec(select(SimpleSupplierCredentials)).all())
        
        # Delete all credentials
        session.exec(delete(SimpleSupplierCredentials))
        session.commit()
        
        logger.warning(f"[REPO] Deleted all {existing_count} credential records")
        return existing_count

    @staticmethod
    def update_test_status(session: Session, supplier_name: str, success: bool, message: str = None) -> SimpleSupplierCredentials:
        """
        Update test status for a supplier's credentials.
        
        Args:
            session: Database session
            supplier_name: Name of the supplier
            success: Whether the test was successful
            message: Error message if test failed
            
        Returns:
            SimpleSupplierCredentials: The updated credential record
        """
        from datetime import datetime
        import uuid
        
        credential_record = CredentialRepository.get_credentials(session, supplier_name)
        
        if not credential_record:
            # Create minimal record for test status
            credential_record = SimpleSupplierCredentials(
                id=str(uuid.uuid4()),
                supplier_name=supplier_name.lower(),
                credentials={}
            )
            session.add(credential_record)
            session.flush()  # Ensure the record exists before updating
        
        # Update test status fields
        credential_record.last_tested_at = datetime.utcnow()
        credential_record.test_status = "success" if success else "failed"
        credential_record.test_error_message = message if not success else None
        
        session.add(credential_record)
        session.commit()
        session.refresh(credential_record)
        
        logger.debug(f"[REPO] Updated test status for supplier: {supplier_name} - {'success' if success else 'failed'}")
        return credential_record