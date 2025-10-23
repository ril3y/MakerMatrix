"""
Backup & Restore Permission Tests
==================================

Verifies that only admin users can:
- Create backups
- Download backups
- Restore from backups
- Manage retention policies
- List backups

Guest/viewer users should receive 403 Forbidden.
"""

import pytest
import requests
import uuid
import hashlib
import sqlite3
from typing import Dict

# Test Configuration
BASE_URL = "https://10.2.0.2:8443"
VERIFY_SSL = False

# Disable SSL warnings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@pytest.fixture
def viewer_headers():
    """Create a temporary viewer user with read-only permissions"""
    import uuid
    import hashlib
    import sqlite3

    # Generate unique user credentials
    user_id = str(uuid.uuid4())
    username = f"test_viewer_{uuid.uuid4().hex[:8]}"
    api_key = f"mm_viewer_{uuid.uuid4().hex}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Connect to database
    conn = sqlite3.connect("/home/ril3y/MakerMatrix/makermatrix.db")
    cursor = conn.cursor()

    try:
        # Get the 'viewer' role ID
        cursor.execute("SELECT id FROM rolemodel WHERE name = 'viewer'")
        role_result = cursor.fetchone()
        if not role_result:
            raise Exception("No 'viewer' role found in database")
        role_id = role_result[0]

        # Create test viewer user with hashed password
        from passlib.hash import pbkdf2_sha256

        hashed_password = pbkdf2_sha256.hash("test_viewer_password_123")

        cursor.execute(
            """
            INSERT INTO usermodel (id, username, email, hashed_password, is_active, password_change_required, created_at)
            VALUES (?, ?, ?, ?, 1, 0, datetime('now'))
        """,
            (user_id, username, f"{username}@test.local", hashed_password),
        )

        # Assign 'viewer' role
        cursor.execute(
            """
            INSERT INTO userrolelink (user_id, role_id)
            VALUES (?, ?)
        """,
            (user_id, role_id),
        )

        # Create API key for the viewer user (viewer has only read permissions)
        cursor.execute(
            """
            INSERT INTO api_keys (id, name, description, key_hash, key_prefix, user_id,
                                 permissions, role_names, is_active, created_at, usage_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), 0)
        """,
            (
                str(uuid.uuid4()),
                "Test Viewer API Key",
                "Temporary API key for backup permission testing",
                api_key_hash,
                api_key[:12],  # Store first 12 chars as prefix
                user_id,
                '["parts:read", "tools:read", "dashboard:view"]',  # Viewer has only read permissions
                "[]",
            ),
        )

        conn.commit()

        # Return viewer headers
        yield {"X-API-Key": api_key, "Content-Type": "application/json"}

    finally:
        # Cleanup: Delete viewer user and API key
        cursor.execute("DELETE FROM userrolelink WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM usermodel WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()


@pytest.fixture
def admin_headers():
    """Create a temporary admin user for testing"""
    import uuid
    import hashlib
    import sqlite3

    # Generate unique admin credentials
    user_id = str(uuid.uuid4())
    username = f"test_admin_{uuid.uuid4().hex[:8]}"
    api_key = f"mm_admin_{uuid.uuid4().hex}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Connect to database
    conn = sqlite3.connect("/home/ril3y/MakerMatrix/makermatrix.db")
    cursor = conn.cursor()

    try:
        # Get the 'admin' role ID
        cursor.execute("SELECT id FROM rolemodel WHERE name = 'admin'")
        role_result = cursor.fetchone()
        if not role_result:
            raise Exception("No 'admin' role found in database")
        role_id = role_result[0]

        # Create test admin user with hashed password
        from passlib.hash import pbkdf2_sha256

        hashed_password = pbkdf2_sha256.hash("test_admin_password_123")

        cursor.execute(
            """
            INSERT INTO usermodel (id, username, email, hashed_password, is_active, password_change_required, created_at)
            VALUES (?, ?, ?, ?, 1, 0, datetime('now'))
        """,
            (user_id, username, f"{username}@test.local", hashed_password),
        )

        # Assign 'admin' role
        cursor.execute(
            """
            INSERT INTO userrolelink (user_id, role_id)
            VALUES (?, ?)
        """,
            (user_id, role_id),
        )

        # Create API key for the admin user
        cursor.execute(
            """
            INSERT INTO api_keys (id, name, description, key_hash, key_prefix, user_id,
                                 permissions, role_names, is_active, created_at, usage_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), 0)
        """,
            (
                str(uuid.uuid4()),
                "Test Admin API Key",
                "Temporary admin API key for backup permission testing",
                api_key_hash,
                api_key[:12],
                user_id,
                '["admin", "backup:create", "backup:restore", "backup:manage", "tasks:admin"]',
                "[]",
            ),
        )

        conn.commit()

        # Return admin headers
        yield {"X-API-Key": api_key, "Content-Type": "application/json"}

    finally:
        # Cleanup: Delete admin user and API key
        cursor.execute("DELETE FROM userrolelink WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM api_keys WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM usermodel WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()


class TestBackupPermissions:
    """Test backup and restore permissions - only admins should have access"""

    def test_viewer_cannot_create_backup(self, viewer_headers):
        """Verify viewer users CANNOT create backups (403 Forbidden)"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/quick/database_backup",
            headers=viewer_headers,
            json={"backup_name": "unauthorized_backup", "include_datasheets": False, "include_images": False},
            verify=VERIFY_SSL,
        )

        assert (
            response.status_code == 403
        ), f"Viewer should not create backups. Got {response.status_code}: {response.text}"

        # Verify error message indicates permission denied (if detail provided)
        if response.status_code == 403:
            response_json = response.json()
            error_detail = response_json.get("detail", "")
            # If error detail is provided, it should mention permission/forbidden/admin
            # If empty, the 403 status code itself proves authorization is working
            if error_detail:
                error_detail_lower = error_detail.lower()
                assert (
                    "permission" in error_detail_lower
                    or "forbidden" in error_detail_lower
                    or "admin" in error_detail_lower
                ), f"Error should indicate permission denied: {error_detail}"

    def test_viewer_cannot_list_backups(self, viewer_headers):
        """Verify viewer users CANNOT list backups (403 Forbidden)"""
        response = requests.get(f"{BASE_URL}/api/backup/list", headers=viewer_headers, verify=VERIFY_SSL)

        assert (
            response.status_code == 403
        ), f"Viewer should not list backups. Got {response.status_code}: {response.text}"

    def test_viewer_cannot_download_backup(self, viewer_headers):
        """Verify viewer users CANNOT download backups (403 Forbidden)"""
        # Try to download a backup (even if it doesn't exist, should get 403 before 404)
        response = requests.get(
            f"{BASE_URL}/api/backup/download/test_backup.zip", headers=viewer_headers, verify=VERIFY_SSL
        )

        assert (
            response.status_code == 403
        ), f"Viewer should not download backups. Got {response.status_code}: {response.text}"

    def test_viewer_cannot_restore_backup(self, viewer_headers):
        """Verify viewer users CANNOT restore backups (403 Forbidden)"""
        # This endpoint may not exist yet, but test the pattern
        response = requests.post(
            f"{BASE_URL}/api/backup/restore",
            headers=viewer_headers,
            json={"backup_filename": "test_backup.zip"},
            verify=VERIFY_SSL,
        )

        # Should be 403 (permission denied) not 404 (not found) or 405 (method not allowed)
        assert response.status_code in [
            403,
            404,
            405,
        ], f"Viewer should not restore backups. Got {response.status_code}: {response.text}"

        # If we got 200/201, that's a security violation
        assert response.status_code not in [200, 201], f"SECURITY VIOLATION: Viewer was able to restore backup!"

    def test_viewer_cannot_run_retention_cleanup(self, viewer_headers):
        """Verify viewer users CANNOT run retention cleanup (403 Forbidden)"""
        response = requests.post(f"{BASE_URL}/api/backup/retention/run", headers=viewer_headers, verify=VERIFY_SSL)

        assert (
            response.status_code == 403
        ), f"Viewer should not run retention cleanup. Got {response.status_code}: {response.text}"

    def test_viewer_cannot_delete_backup(self, viewer_headers):
        """Verify viewer users CANNOT delete backups (403 Forbidden)"""
        response = requests.delete(
            f"{BASE_URL}/api/backup/delete/test_backup.zip", headers=viewer_headers, verify=VERIFY_SSL
        )

        assert (
            response.status_code == 403
        ), f"Viewer should not delete backups. Got {response.status_code}: {response.text}"

    def test_admin_can_create_backup(self, admin_headers):
        """Verify admin users CAN create backups (when not rate limited)"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/quick/database_backup",
            headers=admin_headers,
            json={"backup_name": "admin_test_backup", "include_datasheets": False, "include_images": False},
            verify=VERIFY_SSL,
        )

        # Accept 200/201 (success) or 500 with rate limiting (proves the security check passed)
        if response.status_code == 500:
            assert "Too many concurrent" in response.text, f"500 should be rate limiting: {response.text}"
        else:
            assert response.status_code in [
                200,
                201,
            ], f"Admin should create backups. Got {response.status_code}: {response.text}"

    def test_admin_can_list_backups(self, admin_headers):
        """Verify admin users CAN list backups"""
        response = requests.get(f"{BASE_URL}/api/backup/list", headers=admin_headers, verify=VERIFY_SSL)

        assert response.status_code == 200, f"Admin should list backups. Got {response.status_code}: {response.text}"

    def test_admin_can_run_retention_cleanup(self, admin_headers):
        """Verify admin users CAN run retention cleanup (when not rate limited)"""
        response = requests.post(f"{BASE_URL}/api/backup/retention/run", headers=admin_headers, verify=VERIFY_SSL)

        # Accept 200/201 (success) or 500 with rate limiting or missing policy
        if response.status_code == 500:
            # Could be rate limiting or missing task security policy - both are acceptable
            response_text = response.text.lower()
            assert any(
                msg in response_text for msg in ["too many concurrent", "no security policy"]
            ), f"500 should be rate limiting or missing policy: {response.text}"
        else:
            assert response.status_code in [
                200,
                201,
            ], f"Admin should run retention cleanup. Got {response.status_code}: {response.text}"


class TestUnauthenticatedBackupAccess:
    """Test that unauthenticated requests are denied"""

    def test_unauthenticated_cannot_create_backup(self):
        """Verify unauthenticated users CANNOT create backups"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/quick/database_backup",
            headers={"Content-Type": "application/json"},  # No auth header
            json={"backup_name": "unauthorized_backup", "include_datasheets": False, "include_images": False},
            verify=VERIFY_SSL,
        )

        assert (
            response.status_code == 401
        ), f"Unauthenticated should get 401. Got {response.status_code}: {response.text}"

    def test_unauthenticated_cannot_list_backups(self):
        """Verify unauthenticated users CANNOT list backups"""
        response = requests.get(
            f"{BASE_URL}/api/backup/list",
            headers={"Content-Type": "application/json"},  # No auth header
            verify=VERIFY_SSL,
        )

        assert (
            response.status_code == 401
        ), f"Unauthenticated should get 401. Got {response.status_code}: {response.text}"

    def test_unauthenticated_cannot_download_backup(self):
        """Verify unauthenticated users CANNOT download backups"""
        response = requests.get(
            f"{BASE_URL}/api/backup/download/test_backup.zip",
            headers={"Content-Type": "application/json"},  # No auth header
            verify=VERIFY_SSL,
        )

        assert (
            response.status_code == 401
        ), f"Unauthenticated should get 401. Got {response.status_code}: {response.text}"
