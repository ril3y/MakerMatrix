"""
Comprehensive API Key System Testing Suite

Tests API key creation, validation, authentication, and permission management.
Focused on service layer and model logic testing.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict
from sqlmodel import Session

from MakerMatrix.models.api_key_models import (
    APIKeyModel, APIKeyCreate, APIKeyUpdate,
    generate_api_key, hash_api_key
)
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.services.system.api_key_service import APIKeyService


class TestAPIKeyModels:
    """Test API Key model functionality"""

    def test_generate_api_key_format(self):
        """Test that generated API keys have correct format"""
        api_key = generate_api_key()

        assert api_key.startswith("mm_")
        assert len(api_key) > 10  # mm_ + token

    def test_hash_api_key_consistency(self):
        """Test that hashing is consistent"""
        api_key = "mm_test_key_12345"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 char hex string

    def test_hash_api_key_unique(self):
        """Test that different keys produce different hashes"""
        key1 = "mm_test_key_1"
        key2 = "mm_test_key_2"

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2

    def test_api_key_expiration_check(self):
        """Test API key expiration checking"""
        # Create expired key (doesn't need DB)
        expired_key = APIKeyModel(
            name="Expired Key",
            key_hash="test_hash",
            key_prefix="mm_test",
            user_id="test_user_id",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )

        # Create valid key
        valid_key = APIKeyModel(
            name="Valid Key",
            key_hash="test_hash_2",
            key_prefix="mm_vali",
            user_id="test_user_id",
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        # Create never-expiring key
        never_expires_key = APIKeyModel(
            name="Never Expires",
            key_hash="test_hash_3",
            key_prefix="mm_neve",
            user_id="test_user_id",
            expires_at=None
        )

        assert expired_key.is_expired() is True
        assert valid_key.is_expired() is False
        assert never_expires_key.is_expired() is False

    def test_api_key_validity_check(self):
        """Test API key validity (active + not expired)"""
        # Valid key
        valid_key = APIKeyModel(
            name="Valid Key",
            key_hash="hash1",
            key_prefix="mm_vali",
            user_id="test_user_id",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )

        # Expired key
        expired_key = APIKeyModel(
            name="Expired Key",
            key_hash="hash2",
            key_prefix="mm_expi",
            user_id="test_user_id",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1)
        )

        # Inactive key
        inactive_key = APIKeyModel(
            name="Inactive Key",
            key_hash="hash3",
            key_prefix="mm_inac",
            user_id="test_user_id",
            is_active=False
        )

        assert valid_key.is_valid() is True
        assert expired_key.is_valid() is False
        assert inactive_key.is_valid() is False

    def test_api_key_ip_restriction(self):
        """Test IP address restriction checking"""
        # Key with IP restrictions
        restricted_key = APIKeyModel(
            name="Restricted Key",
            key_hash="hash1",
            key_prefix="mm_rest",
            user_id="test_user_id",
            allowed_ips=["192.168.1.100", "10.0.0.50"]
        )

        # Key without restrictions
        unrestricted_key = APIKeyModel(
            name="Unrestricted Key",
            key_hash="hash2",
            key_prefix="mm_unre",
            user_id="test_user_id",
            allowed_ips=None
        )

        assert restricted_key.can_be_used_from_ip("192.168.1.100") is True
        assert restricted_key.can_be_used_from_ip("192.168.1.101") is False
        assert unrestricted_key.can_be_used_from_ip("192.168.1.100") is True
        assert unrestricted_key.can_be_used_from_ip("any.ip.address") is True

    def test_api_key_usage_tracking(self):
        """Test usage count and last used tracking"""
        api_key = APIKeyModel(
            name="Test Key",
            key_hash="hash1",
            key_prefix="mm_test",
            user_id="test_user_id",
            usage_count=0
        )

        initial_count = api_key.usage_count
        initial_last_used = api_key.last_used_at

        # Record usage
        api_key.record_usage("192.168.1.100")

        assert api_key.usage_count == initial_count + 1
        assert api_key.last_used_at is not None
        assert api_key.last_used_at != initial_last_used


class TestAPIKeyService:
    """Test API Key service functionality"""

    def test_create_api_key(self, memory_test_engine):
        """Test creating an API key through the service"""
        # Create a test user
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        # Create API key
        service = APIKeyService(engine=memory_test_engine)
        key_data = APIKeyCreate(
            name="Test API Key",
            description="Test key for unit tests",
            expires_in_days=30
        )

        response = service.create_api_key(user_id, key_data)

        assert response.success is True
        assert "api_key" in response.data
        assert response.data["api_key"].startswith("mm_")
        assert response.data["name"] == "Test API Key"

    def test_create_api_key_with_roles(self, memory_test_engine):
        """Test creating an API key with role-based permissions"""
        with Session(memory_test_engine) as session:
            # Create user and role
            role = RoleModel(
                name="test_role",
                description="Test role",
                permissions=["parts:read", "parts:write"]
            )
            session.add(role)
            session.commit()

            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        # Create API key with role
        service = APIKeyService(engine=memory_test_engine)
        key_data = APIKeyCreate(
            name="Role-based Key",
            role_names=["test_role"]
        )

        response = service.create_api_key(user_id, key_data)

        assert response.success is True
        assert "parts:read" in response.data["permissions"]
        assert "parts:write" in response.data["permissions"]

    def test_validate_api_key_success(self, memory_test_engine):
        """Test successful API key validation"""
        # Create user and API key
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create key
        key_data = APIKeyCreate(name="Test Key")
        create_response = service.create_api_key(user_id, key_data)
        api_key = create_response.data["api_key"]

        # Validate key
        validate_response = service.validate_api_key(api_key)

        assert validate_response.success is True
        assert validate_response.data.is_valid() is True

    def test_validate_api_key_expired(self, memory_test_engine):
        """Test validation fails for expired keys"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create expired key manually
            api_key = generate_api_key()
            expired_key = APIKeyModel(
                name="Expired Key",
                key_hash=hash_api_key(api_key),
                key_prefix=api_key[:8],
                user_id=user.id,
                is_active=True,
                expires_at=datetime.utcnow() - timedelta(days=1)
            )
            session.add(expired_key)
            session.commit()

        service = APIKeyService(engine=memory_test_engine)
        response = service.validate_api_key(api_key)

        assert response.success is False
        assert "expired" in response.message.lower()

    def test_validate_api_key_ip_restriction(self, memory_test_engine):
        """Test IP restriction validation"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create key with IP restriction
            api_key = generate_api_key()
            restricted_key = APIKeyModel(
                name="IP Restricted Key",
                key_hash=hash_api_key(api_key),
                key_prefix=api_key[:8],
                user_id=user.id,
                is_active=True,
                allowed_ips=["192.168.1.100"]
            )
            session.add(restricted_key)
            session.commit()

        service = APIKeyService(engine=memory_test_engine)

        # Test with allowed IP
        response_allowed = service.validate_api_key(api_key, ip_address="192.168.1.100")
        assert response_allowed.success is True

        # Test with disallowed IP
        response_blocked = service.validate_api_key(api_key, ip_address="192.168.1.101")
        assert response_blocked.success is False
        assert "not authorized" in response_blocked.message.lower()

    def test_get_user_api_keys(self, memory_test_engine):
        """Test retrieving all API keys for a user"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create multiple keys
        for i in range(3):
            key_data = APIKeyCreate(name=f"Test Key {i}")
            service.create_api_key(user_id, key_data)

        # Get all keys
        response = service.get_user_api_keys(user_id)

        assert response.success is True
        assert len(response.data) == 3

    def test_revoke_api_key(self, memory_test_engine):
        """Test revoking an API key"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create key
        key_data = APIKeyCreate(name="Test Key")
        create_response = service.create_api_key(user_id, key_data)
        key_id = create_response.data["id"]

        # Revoke key
        revoke_response = service.revoke_api_key(key_id)

        assert revoke_response.success is True
        assert revoke_response.data["is_active"] is False

    def test_delete_api_key(self, memory_test_engine):
        """Test deleting an API key"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create key
        key_data = APIKeyCreate(name="Test Key")
        create_response = service.create_api_key(user_id, key_data)
        key_id = create_response.data["id"]

        # Delete key
        delete_response = service.delete_api_key(key_id)

        assert delete_response.success is True

        # Verify key is deleted
        get_response = service.get_api_key(key_id)
        assert get_response.success is False

    def test_update_api_key(self, memory_test_engine):
        """Test updating an API key"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create key
        key_data = APIKeyCreate(name="Original Name")
        create_response = service.create_api_key(user_id, key_data)
        key_id = create_response.data["id"]

        # Update key
        update_data = APIKeyUpdate(
            name="Updated Name",
            description="Updated description"
        )
        update_response = service.update_api_key(key_id, update_data)

        assert update_response.success is True
        assert update_response.data["name"] == "Updated Name"
        assert update_response.data["description"] == "Updated description"


class TestAPIKeyEdgeCases:
    """Test edge cases and error handling"""

    def test_create_key_for_nonexistent_user(self, memory_test_engine):
        """Test creating a key for a non-existent user"""
        service = APIKeyService(engine=memory_test_engine)
        key_data = APIKeyCreate(name="Test Key")

        response = service.create_api_key("nonexistent-user-id", key_data)

        assert response.success is False
        assert "not found" in response.message.lower()

    def test_validate_invalid_api_key(self, memory_test_engine):
        """Test validating an invalid API key"""
        service = APIKeyService(engine=memory_test_engine)

        response = service.validate_api_key("mm_invalid_key_that_doesnt_exist")

        assert response.success is False
        assert "invalid" in response.message.lower()

    def test_create_key_with_custom_permissions(self, memory_test_engine):
        """Test creating a key with custom permissions"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)
        key_data = APIKeyCreate(
            name="Custom Permissions Key",
            permissions=["parts:read", "locations:read"]
        )

        response = service.create_api_key(user_id, key_data)

        assert response.success is True
        assert "parts:read" in response.data["permissions"]
        assert "locations:read" in response.data["permissions"]

    def test_usage_tracking_on_validation(self, memory_test_engine):
        """Test that validating a key updates usage statistics"""
        with Session(memory_test_engine) as session:
            user = UserModel(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

        service = APIKeyService(engine=memory_test_engine)

        # Create key
        key_data = APIKeyCreate(name="Test Key")
        create_response = service.create_api_key(user_id, key_data)
        api_key = create_response.data["api_key"]
        initial_count = create_response.data["usage_count"]

        # Validate key (should increment usage)
        service.validate_api_key(api_key, ip_address="192.168.1.100")

        # Get key and check usage increased
        key_id = create_response.data["id"]
        get_response = service.get_api_key(key_id)

        assert get_response.data["usage_count"] == initial_count + 1
        assert get_response.data["last_used_at"] is not None
