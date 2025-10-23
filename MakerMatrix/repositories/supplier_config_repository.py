"""
Supplier Configuration Repository

Repository for supplier configuration database operations.
Follows the established repository pattern where ONLY repositories
handle database sessions and SQL operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlmodel import select, and_

from MakerMatrix.models.supplier_config_models import (
    SupplierConfigModel,
    SupplierCredentialsModel,
    EnrichmentProfileModel,
)
from MakerMatrix.repositories.base_repository import BaseRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    SupplierConfigAlreadyExistsError,
    InvalidReferenceError,
)

logger = logging.getLogger(__name__)


class SupplierConfigRepository(BaseRepository[SupplierConfigModel]):
    """
    Repository for supplier configuration database operations.

    Handles all database operations for supplier configurations,
    credentials, and enrichment profiles.
    """

    def __init__(self):
        super().__init__(SupplierConfigModel)

    def create_supplier_config(self, session: Session, config: SupplierConfigModel) -> SupplierConfigModel:
        """
        Create a new supplier configuration.

        Args:
            session: Database session
            config: Supplier configuration to create

        Returns:
            Created supplier configuration

        Raises:
            SupplierConfigAlreadyExistsError: If supplier already exists
        """
        try:
            # Check if supplier already exists (case-insensitive)
            existing = session.exec(
                select(SupplierConfigModel).where(SupplierConfigModel.supplier_name.ilike(config.supplier_name))
            ).first()

            if existing:
                raise SupplierConfigAlreadyExistsError(
                    f"Supplier configuration for '{config.supplier_name}' already exists. "
                    f"Only one configuration per supplier type is allowed."
                )

            session.add(config)
            session.commit()
            session.refresh(config)

            logger.info(f"Created supplier configuration: {config.supplier_name} (ID: {config.id})")
            return config

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error creating supplier config: {e}")
            raise SupplierConfigAlreadyExistsError(f"Supplier configuration '{config.supplier_name}' already exists")
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating supplier configuration: {e}")
            raise

    def get_by_supplier_name(self, session: Session, supplier_name: str) -> Optional[SupplierConfigModel]:
        """
        Get supplier configuration by name.

        Args:
            session: Database session
            supplier_name: Name of the supplier

        Returns:
            Supplier configuration or None if not found
        """
        normalized_name = (supplier_name or "").upper()

        config = session.exec(
            select(SupplierConfigModel).where(func.upper(SupplierConfigModel.supplier_name) == normalized_name)
        ).first()

        return config

    def get_by_supplier_name_required(self, session: Session, supplier_name: str) -> SupplierConfigModel:
        """
        Get supplier configuration by name, raising exception if not found.

        Args:
            session: Database session
            supplier_name: Name of the supplier

        Returns:
            Supplier configuration

        Raises:
            ResourceNotFoundError: If supplier not found
        """
        config = self.get_by_supplier_name(session, supplier_name)
        if not config:
            raise ResourceNotFoundError("error", f"Supplier configuration '{supplier_name}' not found")
        return config

    def get_all_configs(self, session: Session, enabled_only: bool = False) -> List[SupplierConfigModel]:
        """
        Get all supplier configurations.

        Args:
            session: Database session
            enabled_only: Whether to return only enabled configurations

        Returns:
            List of supplier configurations
        """
        query = select(SupplierConfigModel)

        if enabled_only:
            query = query.where(SupplierConfigModel.enabled == True)

        configs = session.exec(query).all()
        return list(configs)

    def update_supplier_config(self, session: Session, config: SupplierConfigModel) -> SupplierConfigModel:
        """
        Update supplier configuration.

        Args:
            session: Database session
            config: Updated supplier configuration

        Returns:
            Updated supplier configuration
        """
        config.updated_at = datetime.utcnow()
        session.add(config)
        session.commit()
        session.refresh(config)

        logger.info(f"Updated supplier configuration: {config.supplier_name}")
        return config

    def delete_supplier_config(self, session: Session, supplier_name: str) -> bool:
        """
        Delete supplier configuration and associated credentials.

        Args:
            session: Database session
            supplier_name: Name of the supplier to delete

        Returns:
            True if deleted, False if not found
        """
        config = self.get_by_supplier_name(session, supplier_name)
        if not config:
            return False

        session.delete(config)
        session.commit()

        logger.info(f"Deleted supplier configuration: {supplier_name}")
        return True

    def update_test_status(self, session: Session, supplier_name: str, test_status: str, test_time: datetime) -> bool:
        """
        Update supplier connection test status.

        Args:
            session: Database session
            supplier_name: Name of the supplier
            test_status: Test status ("success", "failed", "pending")
            test_time: When the test was performed

        Returns:
            True if updated, False if supplier not found
        """
        config = self.get_by_supplier_name(session, supplier_name)
        if not config:
            return False

        config.last_tested_at = test_time
        config.test_status = test_status
        session.add(config)
        session.commit()

        logger.debug(f"Updated test status for {supplier_name}: {test_status}")
        return True

    def get_enabled_suppliers(self, session: Session) -> List[str]:
        """
        Get list of enabled supplier names.

        Args:
            session: Database session

        Returns:
            List of enabled supplier names
        """
        configs = session.exec(select(SupplierConfigModel).where(SupplierConfigModel.enabled == True)).all()

        return [config.supplier_name for config in configs]

    def get_suppliers_with_capability(self, session: Session, capability: str) -> List[SupplierConfigModel]:
        """
        Get suppliers that support a specific capability.

        Args:
            session: Database session
            capability: Capability to search for

        Returns:
            List of supplier configurations that support the capability
        """
        configs = session.exec(select(SupplierConfigModel).where(SupplierConfigModel.enabled == True)).all()

        # Filter by capability
        matching_configs = []
        for config in configs:
            if capability in config.get_capabilities():
                matching_configs.append(config)

        return matching_configs

    def bulk_update_enabled_status(self, session: Session, supplier_names: List[str], enabled: bool) -> int:
        """
        Bulk update enabled status for multiple suppliers.

        Args:
            session: Database session
            supplier_names: List of supplier names to update
            enabled: New enabled status

        Returns:
            Number of suppliers updated
        """
        configs = session.exec(
            select(SupplierConfigModel).where(SupplierConfigModel.supplier_name.in_(supplier_names))
        ).all()

        updated_count = 0
        for config in configs:
            config.enabled = enabled
            config.updated_at = datetime.utcnow()
            session.add(config)
            updated_count += 1

        session.commit()
        logger.info(f"Bulk updated {updated_count} suppliers enabled status to {enabled}")
        return updated_count


class EnrichmentProfileRepository(BaseRepository[EnrichmentProfileModel]):
    """
    Repository for enrichment profile database operations.
    """

    def __init__(self):
        super().__init__(EnrichmentProfileModel)

    def get_by_name(self, session: Session, name: str, user_id: str = None) -> Optional[EnrichmentProfileModel]:
        """
        Get enrichment profile by name.

        Args:
            session: Database session
            name: Name of the profile
            user_id: User ID (for user-specific profiles)

        Returns:
            Enrichment profile or None if not found
        """
        query = select(EnrichmentProfileModel).where(EnrichmentProfileModel.name == name)

        if user_id:
            query = query.where(
                and_(EnrichmentProfileModel.created_by_user_id == user_id, EnrichmentProfileModel.is_public == True)
            )

        return session.exec(query).first()

    def get_user_profiles(self, session: Session, user_id: str) -> List[EnrichmentProfileModel]:
        """
        Get all profiles for a specific user.

        Args:
            session: Database session
            user_id: User ID

        Returns:
            List of enrichment profiles
        """
        profiles = session.exec(
            select(EnrichmentProfileModel)
            .where(EnrichmentProfileModel.created_by_user_id == user_id)
            .order_by(EnrichmentProfileModel.name)
        ).all()

        return list(profiles)

    def get_default_profile(self, session: Session, user_id: str = None) -> Optional[EnrichmentProfileModel]:
        """
        Get default enrichment profile.

        Args:
            session: Database session
            user_id: User ID (for user-specific default)

        Returns:
            Default enrichment profile or None if not found
        """
        query = select(EnrichmentProfileModel).where(EnrichmentProfileModel.is_default == True)

        if user_id:
            query = query.where(EnrichmentProfileModel.created_by_user_id == user_id)

        return session.exec(query).first()

    def increment_usage(self, session: Session, profile_id: str) -> bool:
        """
        Increment usage count for a profile.

        Args:
            session: Database session
            profile_id: Profile ID

        Returns:
            True if updated, False if profile not found
        """
        profile = self.get_by_id(session, profile_id)
        if not profile:
            return False

        profile.increment_usage()
        session.add(profile)
        session.commit()

        return True
