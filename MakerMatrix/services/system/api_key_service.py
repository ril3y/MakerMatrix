"""
API Key Service

Service for managing API keys including creation, validation, and permission checking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import Engine
from sqlmodel import Session, select

from MakerMatrix.models.api_key_models import APIKeyModel, APIKeyCreate, APIKeyUpdate, generate_api_key, hash_api_key
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.services.base_service import BaseService, ServiceResponse


logger = logging.getLogger(__name__)


class APIKeyService(BaseService):
    """Service for managing API keys"""

    def __init__(self, engine: Optional[Engine] = None):
        super().__init__(engine_override=engine)
        self.entity_name = "API Key"

    def create_api_key(self, user_id: str, key_data: APIKeyCreate) -> ServiceResponse[dict]:
        """
        Create a new API key for a user.

        Args:
            user_id: ID of the user who owns the key
            key_data: API key creation data

        Returns:
            ServiceResponse with the created key (including plaintext key - only shown once!)
        """
        try:
            self.log_operation("create", self.entity_name)

            with self.get_session() as session:
                # Verify user exists
                user = session.get(UserModel, user_id)
                if not user:
                    return self.error_response(f"User with ID '{user_id}' not found")

                # Generate the actual API key
                api_key = generate_api_key()
                key_hash = hash_api_key(api_key)
                key_prefix = api_key[:8]  # Store prefix for identification

                # Get permissions from roles if specified
                permissions = list(key_data.permissions) if key_data.permissions else []
                if key_data.role_names:
                    for role_name in key_data.role_names:
                        role = session.exec(select(RoleModel).where(RoleModel.name == role_name)).first()
                        if role:
                            permissions.extend(role.permissions)

                # Remove duplicates
                permissions = list(set(permissions))

                # Calculate expiration
                expires_at = None
                if key_data.expires_in_days:
                    expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

                # Create the API key model
                api_key_model = APIKeyModel(
                    name=key_data.name,
                    description=key_data.description,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    user_id=user_id,
                    permissions=permissions,
                    role_names=key_data.role_names or [],
                    expires_at=expires_at,
                    allowed_ips=key_data.allowed_ips,
                )

                session.add(api_key_model)
                session.commit()
                session.refresh(api_key_model)

                # Return the key data including the plaintext key (only time it's shown!)
                result = api_key_model.to_dict()
                result["api_key"] = api_key  # Include plaintext key in response

                return self.success_response(
                    f"API key '{key_data.name}' created successfully. Save the key - it won't be shown again!", result
                )

        except Exception as e:
            return self.handle_exception(e, f"create {self.entity_name}")

    def validate_api_key(self, api_key: str, ip_address: Optional[str] = None) -> ServiceResponse[APIKeyModel]:
        """
        Validate an API key and return the associated model if valid.

        Args:
            api_key: The plaintext API key to validate
            ip_address: Optional IP address to check against whitelist

        Returns:
            ServiceResponse with the APIKeyModel if valid
        """
        try:
            key_hash = hash_api_key(api_key)

            with self.get_session() as session:
                api_key_model = session.exec(select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)).first()

                if not api_key_model:
                    return self.error_response("Invalid API key")

                if not api_key_model.is_valid():
                    if api_key_model.is_expired():
                        return self.error_response("API key has expired")
                    else:
                        return self.error_response("API key is inactive")

                if ip_address and not api_key_model.can_be_used_from_ip(ip_address):
                    return self.error_response(f"API key not authorized for IP: {ip_address}")

                # Record usage
                api_key_model.record_usage(ip_address)
                session.add(api_key_model)
                session.commit()
                session.refresh(api_key_model)

                # Force load all attributes before session closes
                _ = api_key_model.is_active
                _ = api_key_model.expires_at

                # Make object safe to use outside session
                session.expunge(api_key_model)

                return self.success_response("API key valid", api_key_model)

        except Exception as e:
            return self.handle_exception(e, "validate API key")

    def get_user_api_keys(self, user_id: str) -> ServiceResponse[List[dict]]:
        """Get all API keys for a user"""
        try:
            self.log_operation("get_all", f"{self.entity_name}s for user")

            with self.get_session() as session:
                api_keys = session.exec(select(APIKeyModel).where(APIKeyModel.user_id == user_id)).all()

                keys_data = [key.to_dict() for key in api_keys]

                return self.success_response(f"Found {len(keys_data)} API keys", keys_data)

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}s")

    def get_api_key(self, key_id: str) -> ServiceResponse[dict]:
        """Get a specific API key by ID"""
        try:
            self.log_operation("get", self.entity_name, key_id)

            with self.get_session() as session:
                api_key = session.get(APIKeyModel, key_id)

                if not api_key:
                    return self.error_response(f"API key with ID '{key_id}' not found")

                return self.success_response(f"API key found", api_key.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"get {self.entity_name}")

    def update_api_key(self, key_id: str, update_data: APIKeyUpdate) -> ServiceResponse[dict]:
        """Update an API key"""
        try:
            self.log_operation("update", self.entity_name, key_id)

            with self.get_session() as session:
                api_key = session.get(APIKeyModel, key_id)

                if not api_key:
                    return self.error_response(f"API key with ID '{key_id}' not found")

                # Update fields
                update_dict = update_data.model_dump(exclude_unset=True)

                for field, value in update_dict.items():
                    setattr(api_key, field, value)

                # If roles changed, update permissions
                if "role_names" in update_dict and update_dict["role_names"]:
                    permissions = list(api_key.permissions) if api_key.permissions else []
                    for role_name in update_dict["role_names"]:
                        role = session.exec(select(RoleModel).where(RoleModel.name == role_name)).first()
                        if role:
                            permissions.extend(role.permissions)
                    api_key.permissions = list(set(permissions))

                session.add(api_key)
                session.commit()
                session.refresh(api_key)

                return self.success_response(f"API key updated successfully", api_key.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"update {self.entity_name}")

    def delete_api_key(self, key_id: str) -> ServiceResponse[dict]:
        """Delete an API key"""
        try:
            self.log_operation("delete", self.entity_name, key_id)

            with self.get_session() as session:
                api_key = session.get(APIKeyModel, key_id)

                if not api_key:
                    return self.error_response(f"API key with ID '{key_id}' not found")

                session.delete(api_key)
                session.commit()

                return self.success_response(
                    f"API key '{api_key.name}' deleted successfully", {"id": key_id, "name": api_key.name}
                )

        except Exception as e:
            return self.handle_exception(e, f"delete {self.entity_name}")

    def revoke_api_key(self, key_id: str) -> ServiceResponse[dict]:
        """Revoke (deactivate) an API key"""
        try:
            self.log_operation("revoke", self.entity_name, key_id)

            with self.get_session() as session:
                api_key = session.get(APIKeyModel, key_id)

                if not api_key:
                    return self.error_response(f"API key with ID '{key_id}' not found")

                api_key.is_active = False
                session.add(api_key)
                session.commit()
                session.refresh(api_key)

                return self.success_response(f"API key '{api_key.name}' revoked successfully", api_key.to_dict())

        except Exception as e:
            return self.handle_exception(e, f"revoke {self.entity_name}")

    def check_permission(self, api_key_model: APIKeyModel, permission: str) -> bool:
        """Check if an API key has a specific permission"""
        if not api_key_model.permissions:
            return False
        return permission in api_key_model.permissions
