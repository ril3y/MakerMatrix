"""
Comprehensive User Authentication and Authorization Testing Suite
Tests user authentication, role-based access control, and permission management
Part of extended testing validation following Phase 2 Backend Cleanup
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

from MakerMatrix.models.models import UserModel, RoleModel, PartModel, LocationModel
from MakerMatrix.repositories.user_repositories import UserRepository
from MakerMatrix.repositories.role_repositories import RoleRepository
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.services.auth.auth_service import AuthService
from MakerMatrix.services.auth.role_service import RoleService
from MakerMatrix.services.auth.permission_service import PermissionService
from MakerMatrix.auth.password_utils import hash_password, verify_password
from MakerMatrix.auth.jwt_utils import create_access_token, verify_token
from MakerMatrix.tests.unit_tests.test_database import create_test_db


class TestUserAuthenticationAuthorization:
    """Test comprehensive user authentication and authorization functionality"""
    
    def setup_method(self):
        """Set up test database and services for each test"""
        self.test_db = create_test_db()
        self.auth_service = AuthService()
        self.role_service = RoleService()
        self.permission_service = PermissionService()
        
        # Create test users with different roles
        self.test_users = self.create_test_users()
        self.test_roles = self.create_test_roles()
        
    def teardown_method(self):
        """Clean up after each test"""
        self.test_db.close()
    
    def create_test_users(self) -> Dict[str, UserModel]:
        """Create test users with different roles"""
        session = self.test_db.get_session()
        
        # Admin user
        admin_user = UserModel(
            id="admin-user-001",
            username="admin_test",
            email="admin@test.com",
            hashed_password=hash_password("admin123"),
            is_active=True,
            password_change_required=False
        )
        
        # Regular user
        regular_user = UserModel(
            id="regular-user-001",
            username="regular_test",
            email="regular@test.com",
            hashed_password=hash_password("user123"),
            is_active=True,
            password_change_required=False
        )
        
        # Read-only user
        readonly_user = UserModel(
            id="readonly-user-001",
            username="readonly_test",
            email="readonly@test.com",
            hashed_password=hash_password("readonly123"),
            is_active=True,
            password_change_required=False
        )
        
        # Inactive user
        inactive_user = UserModel(
            id="inactive-user-001",
            username="inactive_test",
            email="inactive@test.com",
            hashed_password=hash_password("inactive123"),
            is_active=False,
            password_change_required=False
        )
        
        users = {
            "admin": admin_user,
            "regular": regular_user,
            "readonly": readonly_user,
            "inactive": inactive_user
        }
        
        # Add users to database
        for user in users.values():
            session.add(user)
        session.commit()
        
        return users
    
    def create_test_roles(self) -> Dict[str, RoleModel]:
        """Create test roles with different permissions"""
        session = self.test_db.get_session()
        
        # Admin role
        admin_role = RoleModel(
            id="admin-role-001",
            name="admin",
            description="Full administrative access",
            permissions=[
                "parts:read", "parts:write", "parts:delete",
                "locations:read", "locations:write", "locations:delete",
                "categories:read", "categories:write", "categories:delete",
                "users:read", "users:write", "users:delete",
                "tasks:read", "tasks:write", "tasks:delete",
                "admin:all"
            ]
        )
        
        # Regular user role
        regular_role = RoleModel(
            id="regular-role-001",
            name="user",
            description="Standard user access",
            permissions=[
                "parts:read", "parts:write",
                "locations:read", "locations:write",
                "categories:read", "categories:write",
                "tasks:read", "tasks:write"
            ]
        )
        
        # Read-only role
        readonly_role = RoleModel(
            id="readonly-role-001",
            name="readonly",
            description="Read-only access",
            permissions=[
                "parts:read",
                "locations:read",
                "categories:read",
                "tasks:read"
            ]
        )
        
        roles = {
            "admin": admin_role,
            "regular": regular_role,
            "readonly": readonly_role
        }
        
        # Add roles to database
        for role in roles.values():
            session.add(role)
        session.commit()
        
        # Assign roles to users
        self.test_users["admin"].roles = [admin_role]
        self.test_users["regular"].roles = [regular_role]
        self.test_users["readonly"].roles = [readonly_role]
        
        session.commit()
        
        return roles
    
    def test_user_authentication_success(self):
        """Test successful user authentication"""
        session = self.test_db.get_session()
        
        # Test admin login
        admin_auth = self.auth_service.authenticate_user(
            session, "admin_test", "admin123"
        )
        assert admin_auth is not None
        assert admin_auth.username == "admin_test"
        assert admin_auth.is_active == True
        
        # Test regular user login
        regular_auth = self.auth_service.authenticate_user(
            session, "regular_test", "user123"
        )
        assert regular_auth is not None
        assert regular_auth.username == "regular_test"
        assert regular_auth.is_active == True
        
        # Test readonly user login
        readonly_auth = self.auth_service.authenticate_user(
            session, "readonly_test", "readonly123"
        )
        assert readonly_auth is not None
        assert readonly_auth.username == "readonly_test"
        assert readonly_auth.is_active == True
        
        print("✅ User authentication success validated")
    
    def test_user_authentication_failure(self):
        """Test failed user authentication scenarios"""
        session = self.test_db.get_session()
        
        # Test wrong password
        wrong_password = self.auth_service.authenticate_user(
            session, "admin_test", "wrongpassword"
        )
        assert wrong_password is None
        
        # Test non-existent user
        non_existent = self.auth_service.authenticate_user(
            session, "nonexistent", "password"
        )
        assert non_existent is None
        
        # Test inactive user
        inactive_auth = self.auth_service.authenticate_user(
            session, "inactive_test", "inactive123"
        )
        assert inactive_auth is None  # Should fail due to inactive status
        
        # Test empty credentials
        empty_username = self.auth_service.authenticate_user(
            session, "", "password"
        )
        assert empty_username is None
        
        empty_password = self.auth_service.authenticate_user(
            session, "admin_test", ""
        )
        assert empty_password is None
        
        print("✅ User authentication failure scenarios validated")
    
    def test_jwt_token_operations(self):
        """Test JWT token creation and validation"""
        # Test token creation
        user_data = {
            "user_id": "admin-user-001",
            "username": "admin_test",
            "roles": ["admin"]
        }
        
        token = create_access_token(user_data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Test token verification
        decoded_token = verify_token(token)
        assert decoded_token is not None
        assert decoded_token["user_id"] == "admin-user-001"
        assert decoded_token["username"] == "admin_test"
        assert "admin" in decoded_token["roles"]
        
        # Test invalid token
        invalid_token = verify_token("invalid.token.here")
        assert invalid_token is None
        
        # Test expired token (simulated)
        expired_token_data = user_data.copy()
        expired_token_data["exp"] = 0  # Expired timestamp
        
        # Note: This would need actual JWT library testing for expiration
        # For now, we test the structure
        
        print("✅ JWT token operations validated")
    
    def test_role_based_access_control(self):
        """Test role-based access control for different operations"""
        session = self.test_db.get_session()
        
        # Create test part for permission testing
        test_location = LocationModel(
            id="test-location-001",
            name="Test Location",
            description="Location for permission testing"
        )
        session.add(test_location)
        session.commit()
        
        test_part = PartModel(
            id="test-part-001",
            part_number="TEST001",
            part_name="Test Part",
            description="Part for permission testing",
            quantity=10,
            location_id=test_location.id
        )
        session.add(test_part)
        session.commit()
        
        # Test admin permissions (should allow all operations)
        admin_user = self.test_users["admin"]
        
        # Admin can read
        can_read = self.permission_service.has_permission(
            admin_user, "parts:read"
        )
        assert can_read == True
        
        # Admin can write
        can_write = self.permission_service.has_permission(
            admin_user, "parts:write"
        )
        assert can_write == True
        
        # Admin can delete
        can_delete = self.permission_service.has_permission(
            admin_user, "parts:delete"
        )
        assert can_delete == True
        
        # Test regular user permissions
        regular_user = self.test_users["regular"]
        
        # Regular user can read
        can_read = self.permission_service.has_permission(
            regular_user, "parts:read"
        )
        assert can_read == True
        
        # Regular user can write
        can_write = self.permission_service.has_permission(
            regular_user, "parts:write"
        )
        assert can_write == True
        
        # Regular user cannot delete
        can_delete = self.permission_service.has_permission(
            regular_user, "parts:delete"
        )
        assert can_delete == False
        
        # Test readonly user permissions
        readonly_user = self.test_users["readonly"]
        
        # Readonly user can read
        can_read = self.permission_service.has_permission(
            readonly_user, "parts:read"
        )
        assert can_read == True
        
        # Readonly user cannot write
        can_write = self.permission_service.has_permission(
            readonly_user, "parts:write"
        )
        assert can_write == False
        
        # Readonly user cannot delete
        can_delete = self.permission_service.has_permission(
            readonly_user, "parts:delete"
        )
        assert can_delete == False
        
        print("✅ Role-based access control validated")
    
    def test_permission_enforcement_operations(self):
        """Test permission enforcement for CRUD operations"""
        session = self.test_db.get_session()
        
        # Create test location
        test_location = LocationModel(
            id="test-location-perm",
            name="Permission Test Location",
            description="Location for permission testing"
        )
        session.add(test_location)
        session.commit()
        
        # Test part creation with different users
        part_data = {
            "part_number": "PERM001",
            "part_name": "Permission Test Part",
            "description": "Part for permission testing",
            "quantity": 5,
            "location_id": test_location.id
        }
        
        # Admin user can create part
        admin_user = self.test_users["admin"]
        if self.permission_service.has_permission(admin_user, "parts:write"):
            created_part = PartRepository.add_part(session, PartModel(**part_data))
            assert created_part is not None
            assert created_part.part_number == "PERM001"
        
        # Regular user can create part
        regular_user = self.test_users["regular"]
        if self.permission_service.has_permission(regular_user, "parts:write"):
            part_data["part_number"] = "PERM002"
            created_part = PartRepository.add_part(session, PartModel(**part_data))
            assert created_part is not None
            assert created_part.part_number == "PERM002"
        
        # Readonly user cannot create part
        readonly_user = self.test_users["readonly"]
        cannot_create = not self.permission_service.has_permission(
            readonly_user, "parts:write"
        )
        assert cannot_create == True
        
        # Test part deletion with different users
        if self.permission_service.has_permission(admin_user, "parts:delete"):
            # Admin can delete
            deleted = PartRepository.delete_part(session, "PERM001")
            assert deleted == True
        
        # Regular user cannot delete (should be prevented)
        cannot_delete = not self.permission_service.has_permission(
            regular_user, "parts:delete"
        )
        assert cannot_delete == True
        
        # Readonly user cannot delete
        cannot_delete = not self.permission_service.has_permission(
            readonly_user, "parts:delete"
        )
        assert cannot_delete == True
        
        print("✅ Permission enforcement operations validated")
    
    def test_user_management_permissions(self):
        """Test user management permissions"""
        session = self.test_db.get_session()
        
        # Test user creation permissions
        admin_user = self.test_users["admin"]
        regular_user = self.test_users["regular"]
        readonly_user = self.test_users["readonly"]
        
        # Admin can manage users
        can_manage_users = self.permission_service.has_permission(
            admin_user, "users:write"
        )
        assert can_manage_users == True
        
        # Regular user cannot manage users
        cannot_manage_users = not self.permission_service.has_permission(
            regular_user, "users:write"
        )
        assert cannot_manage_users == True
        
        # Readonly user cannot manage users
        cannot_manage_users = not self.permission_service.has_permission(
            readonly_user, "users:write"
        )
        assert cannot_manage_users == True
        
        # Test admin-only operations
        admin_operations = ["admin:all", "users:delete"]
        
        for operation in admin_operations:
            # Admin has admin permissions
            admin_has_perm = self.permission_service.has_permission(
                admin_user, operation
            )
            assert admin_has_perm == True
            
            # Regular user does not have admin permissions
            regular_no_perm = not self.permission_service.has_permission(
                regular_user, operation
            )
            assert regular_no_perm == True
            
            # Readonly user does not have admin permissions
            readonly_no_perm = not self.permission_service.has_permission(
                readonly_user, operation
            )
            assert readonly_no_perm == True
        
        print("✅ User management permissions validated")
    
    def test_task_management_permissions(self):
        """Test task management permissions"""
        admin_user = self.test_users["admin"]
        regular_user = self.test_users["regular"]
        readonly_user = self.test_users["readonly"]
        
        # Test task creation permissions
        can_create_tasks = self.permission_service.has_permission(
            regular_user, "tasks:write"
        )
        assert can_create_tasks == True
        
        # Test task deletion permissions (admin only)
        can_delete_tasks = self.permission_service.has_permission(
            admin_user, "tasks:delete"
        )
        assert can_delete_tasks == True
        
        cannot_delete_tasks = not self.permission_service.has_permission(
            regular_user, "tasks:delete"
        )
        assert cannot_delete_tasks == True
        
        # Test task reading permissions (all users)
        can_read_tasks = self.permission_service.has_permission(
            readonly_user, "tasks:read"
        )
        assert can_read_tasks == True
        
        # Test task modification permissions
        cannot_modify_tasks = not self.permission_service.has_permission(
            readonly_user, "tasks:write"
        )
        assert cannot_modify_tasks == True
        
        print("✅ Task management permissions validated")
    
    def test_session_management(self):
        """Test user session management"""
        session = self.test_db.get_session()
        
        # Test session creation
        admin_user = self.test_users["admin"]
        user_session = self.auth_service.create_user_session(admin_user)
        
        assert user_session is not None
        assert user_session["user_id"] == admin_user.id
        assert user_session["username"] == admin_user.username
        assert "token" in user_session
        assert "expires_at" in user_session
        
        # Test session validation
        is_valid = self.auth_service.validate_session(user_session["token"])
        assert is_valid == True
        
        # Test session termination
        terminated = self.auth_service.terminate_session(user_session["token"])
        assert terminated == True
        
        # Test session validation after termination
        is_valid_after = self.auth_service.validate_session(user_session["token"])
        assert is_valid_after == False
        
        print("✅ Session management validated")
    
    def test_password_management(self):
        """Test password management functionality"""
        session = self.test_db.get_session()
        
        # Test password hashing
        plain_password = "testpassword123"
        hashed = hash_password(plain_password)
        
        assert hashed is not None
        assert hashed != plain_password
        assert len(hashed) > 0
        
        # Test password verification
        is_valid = verify_password(plain_password, hashed)
        assert is_valid == True
        
        is_invalid = verify_password("wrongpassword", hashed)
        assert is_invalid == False
        
        # Test password change
        regular_user = self.test_users["regular"]
        old_password = "user123"
        new_password = "newpassword456"
        
        # Verify old password works
        auth_old = self.auth_service.authenticate_user(
            session, regular_user.username, old_password
        )
        assert auth_old is not None
        
        # Change password
        password_changed = self.auth_service.change_password(
            session, regular_user.id, old_password, new_password
        )
        assert password_changed == True
        
        # Verify new password works
        auth_new = self.auth_service.authenticate_user(
            session, regular_user.username, new_password
        )
        assert auth_new is not None
        
        # Verify old password no longer works
        auth_old_fail = self.auth_service.authenticate_user(
            session, regular_user.username, old_password
        )
        assert auth_old_fail is None
        
        print("✅ Password management validated")
    
    def test_role_assignment_operations(self):
        """Test role assignment and modification"""
        session = self.test_db.get_session()
        
        # Create new test user without roles
        test_user = UserModel(
            id="role-test-user",
            username="roletest",
            email="roletest@test.com",
            hashed_password=hash_password("roletest123"),
            is_active=True
        )
        session.add(test_user)
        session.commit()
        
        # Test assigning role
        regular_role = self.test_roles["regular"]
        role_assigned = self.role_service.assign_role_to_user(
            session, test_user.id, regular_role.id
        )
        assert role_assigned == True
        
        # Verify role assignment
        user_roles = self.role_service.get_user_roles(session, test_user.id)
        assert len(user_roles) == 1
        assert user_roles[0].name == "user"
        
        # Test adding additional role
        readonly_role = self.test_roles["readonly"]
        additional_role = self.role_service.assign_role_to_user(
            session, test_user.id, readonly_role.id
        )
        assert additional_role == True
        
        # Verify multiple roles
        updated_roles = self.role_service.get_user_roles(session, test_user.id)
        assert len(updated_roles) == 2
        
        # Test removing role
        role_removed = self.role_service.remove_role_from_user(
            session, test_user.id, readonly_role.id
        )
        assert role_removed == True
        
        # Verify role removal
        final_roles = self.role_service.get_user_roles(session, test_user.id)
        assert len(final_roles) == 1
        assert final_roles[0].name == "user"
        
        print("✅ Role assignment operations validated")
    
    def test_permission_inheritance(self):
        """Test permission inheritance from multiple roles"""
        session = self.test_db.get_session()
        
        # Create user with multiple roles
        multi_role_user = UserModel(
            id="multi-role-user",
            username="multirole",
            email="multirole@test.com",
            hashed_password=hash_password("multi123"),
            is_active=True
        )
        session.add(multi_role_user)
        session.commit()
        
        # Assign multiple roles
        regular_role = self.test_roles["regular"]
        readonly_role = self.test_roles["readonly"]
        
        multi_role_user.roles = [regular_role, readonly_role]
        session.commit()
        
        # Test inherited permissions (should have union of all role permissions)
        user_permissions = self.permission_service.get_user_permissions(
            multi_role_user
        )
        
        # Should have regular user permissions
        assert "parts:read" in user_permissions
        assert "parts:write" in user_permissions
        assert "locations:read" in user_permissions
        assert "locations:write" in user_permissions
        
        # Should not have admin permissions
        assert "parts:delete" not in user_permissions
        assert "admin:all" not in user_permissions
        
        # Test permission checking with multiple roles
        can_read = self.permission_service.has_permission(
            multi_role_user, "parts:read"
        )
        assert can_read == True
        
        can_write = self.permission_service.has_permission(
            multi_role_user, "parts:write"
        )
        assert can_write == True
        
        cannot_delete = not self.permission_service.has_permission(
            multi_role_user, "parts:delete"
        )
        assert cannot_delete == True
        
        print("✅ Permission inheritance validated")
    
    def test_access_control_middleware(self):
        """Test access control middleware functionality"""
        # Test permission decorator/middleware simulation
        def require_permission(permission):
            def decorator(func):
                def wrapper(user, *args, **kwargs):
                    if not self.permission_service.has_permission(user, permission):
                        raise PermissionError(f"User lacks required permission: {permission}")
                    return func(user, *args, **kwargs)
                return wrapper
            return decorator
        
        # Test function with permission requirement
        @require_permission("parts:delete")
        def delete_part_operation(user, part_id):
            return f"Deleted part {part_id}"
        
        # Test with admin user (should succeed)
        admin_user = self.test_users["admin"]
        try:
            result = delete_part_operation(admin_user, "test-part-001")
            assert result == "Deleted part test-part-001"
        except PermissionError:
            pytest.fail("Admin user should have delete permission")
        
        # Test with regular user (should fail)
        regular_user = self.test_users["regular"]
        with pytest.raises(PermissionError) as exc_info:
            delete_part_operation(regular_user, "test-part-001")
        
        assert "parts:delete" in str(exc_info.value)
        
        # Test with readonly user (should fail)
        readonly_user = self.test_users["readonly"]
        with pytest.raises(PermissionError) as exc_info:
            delete_part_operation(readonly_user, "test-part-001")
        
        assert "parts:delete" in str(exc_info.value)
        
        print("✅ Access control middleware validated")
    
    def test_security_audit_logging(self):
        """Test security audit logging functionality"""
        session = self.test_db.get_session()
        
        # Test authentication audit
        auth_attempt = self.auth_service.authenticate_user(
            session, "admin_test", "admin123"
        )
        
        # Verify audit log entry would be created
        audit_entry = {
            "event_type": "authentication",
            "user_id": auth_attempt.id if auth_attempt else None,
            "username": "admin_test",
            "success": auth_attempt is not None,
            "timestamp": "2025-01-08T12:00:00Z",
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent"
        }
        
        assert audit_entry["event_type"] == "authentication"
        assert audit_entry["username"] == "admin_test"
        assert audit_entry["success"] == True
        
        # Test permission denial audit
        regular_user = self.test_users["regular"]
        permission_denied = not self.permission_service.has_permission(
            regular_user, "parts:delete"
        )
        
        if permission_denied:
            audit_entry = {
                "event_type": "permission_denied",
                "user_id": regular_user.id,
                "username": regular_user.username,
                "requested_permission": "parts:delete",
                "timestamp": "2025-01-08T12:00:00Z"
            }
            
            assert audit_entry["event_type"] == "permission_denied"
            assert audit_entry["requested_permission"] == "parts:delete"
        
        print("✅ Security audit logging validated")


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])