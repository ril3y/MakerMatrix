"""
Supplier Credentials Repository

Data access layer for supplier credentials (plain text storage).
Protected by password-encrypted backup ZIPs and OS file permissions.
"""

import logging
from typing import Optional, Dict
from datetime import datetime
from sqlmodel import Session, select

from MakerMatrix.models.supplier_config_models import SupplierCredentialsModel, SupplierConfigModel

logger = logging.getLogger(__name__)


class SupplierCredentialsRepository:
    """Repository for managing supplier credentials"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.SupplierCredentialsRepository")

    def create_credentials(
        self, session: Session, supplier_config_id: str, credentials: Dict[str, str], user_id: Optional[str] = None
    ) -> SupplierCredentialsModel:
        """
        Create credentials for a supplier

        Args:
            session: Database session
            supplier_config_id: ID of the supplier configuration
            credentials: Dictionary of credential key-value pairs
            user_id: ID of the user creating the credentials

        Returns:
            Created SupplierCredentialsModel
        """
        self.logger.info(f"Creating credentials for supplier config {supplier_config_id}")

        # Create credentials model
        credentials_model = SupplierCredentialsModel(supplier_config_id=supplier_config_id, created_by_user_id=user_id)

        # Map common credential fields
        if "api_key" in credentials:
            credentials_model.api_key = credentials["api_key"]

        if "secret_key" in credentials:
            credentials_model.secret_key = credentials["secret_key"]

        if "client_id" in credentials:
            # Store client_id as api_key for compatibility
            credentials_model.api_key = credentials["client_id"]

        if "client_secret" in credentials:
            # Store client_secret as secret_key for compatibility
            credentials_model.secret_key = credentials["client_secret"]

        if "username" in credentials:
            credentials_model.username = credentials["username"]

        if "password" in credentials:
            credentials_model.password = credentials["password"]

        if "oauth_token" in credentials:
            credentials_model.oauth_token = credentials["oauth_token"]

        if "refresh_token" in credentials:
            credentials_model.refresh_token = credentials["refresh_token"]

        # Handle additional custom credentials
        additional_creds = {
            k: v
            for k, v in credentials.items()
            if k
            not in [
                "api_key",
                "secret_key",
                "client_id",
                "client_secret",
                "username",
                "password",
                "oauth_token",
                "refresh_token",
            ]
        }
        if additional_creds:
            import json

            credentials_model.additional_data = json.dumps(additional_creds)

        # Save to database
        session.add(credentials_model)
        session.commit()
        session.refresh(credentials_model)

        self.logger.info(f"Created credentials for supplier config {supplier_config_id}")
        return credentials_model

    def get_credentials(self, session: Session, supplier_config_id: str) -> Optional[SupplierCredentialsModel]:
        """
        Get credentials for a supplier configuration

        Args:
            session: Database session
            supplier_config_id: ID of the supplier configuration

        Returns:
            SupplierCredentialsModel or None if not found
        """
        statement = select(SupplierCredentialsModel).where(
            SupplierCredentialsModel.supplier_config_id == supplier_config_id
        )
        return session.exec(statement).first()

    def get_credentials_by_supplier_name(
        self, session: Session, supplier_name: str
    ) -> Optional[SupplierCredentialsModel]:
        """
        Get credentials for a supplier by supplier name

        Args:
            session: Database session
            supplier_name: Name of the supplier

        Returns:
            SupplierCredentialsModel or None if not found
        """
        # Join with supplier_configs to get credentials by name
        statement = (
            select(SupplierCredentialsModel)
            .join(SupplierConfigModel)
            .where(SupplierConfigModel.supplier_name == supplier_name.upper())
        )
        return session.exec(statement).first()

    def get_credentials_as_dict(self, credentials_model: SupplierCredentialsModel) -> Dict[str, str]:
        """
        Convert credentials model to dictionary

        Args:
            credentials_model: SupplierCredentialsModel

        Returns:
            Dictionary of credentials with proper field names
        """
        if not credentials_model:
            return {}

        creds = {}

        # Map stored fields to expected field names
        # For DigiKey compatibility: api_key -> client_id, secret_key -> client_secret
        if credentials_model.api_key:
            creds["api_key"] = credentials_model.api_key
            creds["client_id"] = credentials_model.api_key  # DigiKey uses client_id

        if credentials_model.secret_key:
            creds["secret_key"] = credentials_model.secret_key
            creds["client_secret"] = credentials_model.secret_key  # DigiKey uses client_secret

        if credentials_model.username:
            creds["username"] = credentials_model.username

        if credentials_model.password:
            creds["password"] = credentials_model.password

        if credentials_model.oauth_token:
            creds["oauth_token"] = credentials_model.oauth_token

        if credentials_model.refresh_token:
            creds["refresh_token"] = credentials_model.refresh_token

        if credentials_model.additional_data:
            import json

            try:
                additional = json.loads(credentials_model.additional_data)
                creds.update(additional)
            except (json.JSONDecodeError, TypeError):
                self.logger.warning("Failed to parse additional_data JSON")

        return creds

    def update_credentials(
        self, session: Session, supplier_config_id: str, credentials: Dict[str, str], user_id: Optional[str] = None
    ) -> SupplierCredentialsModel:
        """
        Update credentials for a supplier

        Args:
            session: Database session
            supplier_config_id: ID of the supplier configuration
            credentials: Dictionary of credential key-value pairs
            user_id: ID of the user updating the credentials

        Returns:
            Updated SupplierCredentialsModel
        """
        self.logger.info(f"Updating credentials for supplier config {supplier_config_id}")

        # Get existing credentials
        existing = self.get_credentials(session, supplier_config_id)

        if existing:
            # Delete old credentials
            session.delete(existing)
            session.commit()

        # Create new credentials
        return self.create_credentials(session, supplier_config_id, credentials, user_id)

    def delete_credentials(self, session: Session, supplier_config_id: str) -> bool:
        """
        Delete credentials for a supplier

        Args:
            session: Database session
            supplier_config_id: ID of the supplier configuration

        Returns:
            True if deleted, False if not found
        """
        credentials = self.get_credentials(session, supplier_config_id)

        if not credentials:
            return False

        session.delete(credentials)
        session.commit()

        self.logger.info(f"Deleted credentials for supplier config {supplier_config_id}")
        return True

    def has_credentials(self, session: Session, supplier_config_id: str) -> bool:
        """
        Check if credentials exist for a supplier

        Args:
            session: Database session
            supplier_config_id: ID of the supplier configuration

        Returns:
            True if credentials exist, False otherwise
        """
        credentials = self.get_credentials(session, supplier_config_id)
        return credentials is not None
