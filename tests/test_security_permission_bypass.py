"""
Security Test Suite: Permission Bypass Vulnerabilities

This test suite attempts to exploit missing permission checks across 71 API endpoints.
Tests verify that guest users (viewer role with READ-ONLY permissions) cannot perform
CREATE, UPDATE, or DELETE operations.

Expected Behavior:
- All tests should FAIL initially (demonstrating vulnerabilities)
- After permission fixes are applied, all tests should PASS
- Guest users should receive 403 Forbidden for write operations

CVSS Score: 8.1 (HIGH)
- Attack Vector: Network
- Attack Complexity: Low
- Privileges Required: Low (guest account)
- User Interaction: None
- Scope: Unchanged
- Confidentiality: High
- Integrity: High
- Availability: None

Author: Security Assessment
Date: 2025-10-22
"""

import pytest
import requests
import json
from typing import Dict, Optional

# Test Configuration
BASE_URL = "https://10.2.0.2:8443"
GUEST_TOKEN_PATH = "/tmp/guest_token.json"

# Disable SSL verification warnings for self-signed cert
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SecurityTester:
    """Helper class for security testing"""

    def __init__(self):
        self.base_url = BASE_URL
        self.guest_token = self._load_guest_token()
        self.headers = {"Authorization": f"Bearer {self.guest_token}", "Content-Type": "application/json"}

    def _load_guest_token(self) -> str:
        """Load guest token from file"""
        try:
            with open(GUEST_TOKEN_PATH, "r") as f:
                data = json.load(f)
                return data["access_token"]
        except Exception as e:
            pytest.fail(f"Failed to load guest token: {e}")

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make authenticated POST request"""
        url = f"{self.base_url}{endpoint}"
        return requests.post(url, headers=self.headers, json=data or {}, verify=False)

    def put(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make authenticated PUT request"""
        url = f"{self.base_url}{endpoint}"
        return requests.put(url, headers=self.headers, json=data or {}, verify=False)

    def delete(self, endpoint: str) -> requests.Response:
        """Make authenticated DELETE request"""
        url = f"{self.base_url}{endpoint}"
        return requests.delete(url, headers=self.headers, verify=False)

    def get(self, endpoint: str) -> requests.Response:
        """Make authenticated GET request"""
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, verify=False)


@pytest.fixture(scope="session")
def security_tester():
    """Fixture to provide security tester instance"""
    return SecurityTester()


# ========================================
# CRITICAL: User Management Vulnerabilities (9 endpoints)
# ========================================


class TestUserManagementBypass:
    """Test user management endpoints that lack permission checks"""

    def test_guest_cannot_register_user(self, security_tester):
        """
        CRITICAL: Test if guest can create new users
        Endpoint: POST /api/users/register
        Expected: 403 Forbidden (missing require_permission check)
        Current: NO AUTHENTICATION - completely unprotected!
        """
        response = security_tester.post(
            "/api/users/register",
            {
                "username": "malicious_admin",
                "email": "hacker@evil.com",
                "password": "EvilPassword123!",
                "roles": ["admin"],  # Attempting to create admin user!
            },
        )

        # This should be 403, but will likely be 200 (success) - CRITICAL VULNERABILITY
        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest created user! Status: {response.status_code}, Response: {response.text}"

    def test_guest_cannot_get_user_by_id(self, security_tester):
        """
        HIGH: Test if guest can view other users
        Endpoint: GET /api/users/{user_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.get("/api/users/admin")

        # Should be 403 for guests viewing user details
        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest accessed user details! Status: {response.status_code}"

    def test_guest_cannot_get_user_by_username(self, security_tester):
        """
        HIGH: Test if guest can view users by username
        Endpoint: GET /api/users/by-username/{username}
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION
        """
        response = security_tester.get("/api/users/by-username/admin")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest accessed user by username! Status: {response.status_code}"

    def test_guest_cannot_update_user(self, security_tester):
        """
        CRITICAL: Test if guest can modify user details
        Endpoint: PUT /api/users/{user_id}
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION - can escalate privileges!
        """
        response = security_tester.put("/api/users/admin", {"email": "pwned@hacker.com", "roles": ["admin"]})

        assert response.status_code == 403, f"VULNERABILITY: Guest modified user! Status: {response.status_code}"

    def test_guest_cannot_update_user_password(self, security_tester):
        """
        CRITICAL: Test if guest can change passwords
        Endpoint: PUT /api/users/{user_id}/password
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.put(
            "/api/users/admin/password", {"current_password": "Admin123!", "new_password": "Hacked123!"}
        )

        # Even if current password is wrong, should be 403 not 400
        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest attempted password change! Status: {response.status_code}"

    def test_guest_cannot_delete_user(self, security_tester):
        """
        CRITICAL: Test if guest can delete users
        Endpoint: DELETE /api/users/{user_id}
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION
        """
        response = security_tester.delete("/api/users/some-user-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted user! Status: {response.status_code}"

    def test_guest_cannot_update_user_roles(self, security_tester):
        """
        CRITICAL: Test if guest can modify user roles
        Endpoint: PUT /api/users/{user_id}/roles
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION - privilege escalation!
        """
        response = security_tester.put(
            "/api/users/guest_9fe60030/roles", {"role_ids": ["admin-role-id"]}  # Attempting privilege escalation!
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest modified roles! Status: {response.status_code}"

    def test_guest_cannot_update_user_status(self, security_tester):
        """
        CRITICAL: Test if guest can activate/deactivate users
        Endpoint: PUT /api/users/{user_id}/status
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION
        """
        response = security_tester.put("/api/users/admin/status", {"is_active": False})  # Attempting to disable admin!

        assert response.status_code == 403, f"VULNERABILITY: Guest changed user status! Status: {response.status_code}"

    def test_guest_cannot_create_role(self, security_tester):
        """
        CRITICAL: Test if guest can create new roles
        Endpoint: POST /api/users/roles/add_role
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION - can create superuser role!
        """
        response = security_tester.post(
            "/api/users/roles/add_role",
            {"name": "superadmin", "description": "Evil role", "permissions": ["*:*"]},  # All permissions!
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest created role! Status: {response.status_code}"

    def test_guest_cannot_update_role(self, security_tester):
        """
        CRITICAL: Test if guest can modify role permissions
        Endpoint: PUT /api/users/roles/{role_id}
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION
        """
        response = security_tester.put(
            "/api/users/roles/viewer-role-id", {"permissions": ["*:*"]}  # Escalate viewer to full access!
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest modified role! Status: {response.status_code}"

    def test_guest_cannot_delete_role(self, security_tester):
        """
        HIGH: Test if guest can delete roles
        Endpoint: DELETE /api/users/roles/{role_id}
        Expected: 403 Forbidden
        Current: NO AUTHENTICATION
        """
        response = security_tester.delete("/api/users/roles/some-role-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted role! Status: {response.status_code}"


# ========================================
# HIGH: Categories Vulnerabilities (3 endpoints)
# ========================================


class TestCategoriesPermissionBypass:
    """Test category endpoints that lack permission checks"""

    def test_guest_cannot_create_category(self, security_tester):
        """
        HIGH: Test if guest can create categories
        Endpoint: POST /api/categories/add_category
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.post(
            "/api/categories/add_category", {"name": "Evil Category", "description": "Created by guest"}
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest created category! Status: {response.status_code}"

    def test_guest_cannot_update_category(self, security_tester):
        """
        HIGH: Test if guest can update categories
        Endpoint: PUT /api/categories/update_category/{category_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.put("/api/categories/update_category/some-id", {"name": "Hacked Category"})

        assert response.status_code == 403, f"VULNERABILITY: Guest updated category! Status: {response.status_code}"

    def test_guest_cannot_delete_category(self, security_tester):
        """
        HIGH: Test if guest can delete categories
        Endpoint: DELETE /api/categories/remove_category
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.delete("/api/categories/remove_category?cat_id=some-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted category! Status: {response.status_code}"


# ========================================
# HIGH: Locations Vulnerabilities (4 endpoints)
# ========================================


class TestLocationsPermissionBypass:
    """Test location endpoints that lack permission checks"""

    def test_guest_cannot_create_location(self, security_tester):
        """
        HIGH: Test if guest can create locations
        Endpoint: POST /api/locations/add_location
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post(
            "/api/locations/add_location", {"name": "Evil Location", "description": "Created by guest"}
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest created location! Status: {response.status_code}"

    def test_guest_cannot_update_location(self, security_tester):
        """
        HIGH: Test if guest can update locations
        Endpoint: PUT /api/locations/update_location/{location_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.put("/api/locations/update_location/some-id", {"name": "Hacked Location"})

        assert response.status_code == 403, f"VULNERABILITY: Guest updated location! Status: {response.status_code}"

    def test_guest_cannot_delete_location(self, security_tester):
        """
        HIGH: Test if guest can delete locations
        Endpoint: DELETE /api/locations/delete_location/{location_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/locations/delete_location/some-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted location! Status: {response.status_code}"

    def test_unauthenticated_cannot_cleanup_locations(self, security_tester):
        """
        CRITICAL: Test completely unauthenticated endpoint
        Endpoint: DELETE /api/locations/cleanup-locations
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION AT ALL!
        """
        # Test without ANY authentication
        response = requests.delete(f"{BASE_URL}/api/locations/cleanup-locations", verify=False)

        assert (
            response.status_code == 401
        ), f"CRITICAL: Unauthenticated cleanup succeeded! Status: {response.status_code}"


# ========================================
# HIGH: Projects Vulnerabilities (5 endpoints)
# ========================================


class TestProjectsPermissionBypass:
    """Test project endpoints that lack permission checks"""

    def test_guest_cannot_create_project(self, security_tester):
        """
        HIGH: Test if guest can create projects
        Endpoint: POST /api/projects/
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.post("/api/projects/", {"name": "Evil Project", "description": "Created by guest"})

        assert response.status_code == 403, f"VULNERABILITY: Guest created project! Status: {response.status_code}"

    def test_guest_cannot_update_project(self, security_tester):
        """
        HIGH: Test if guest can update projects
        Endpoint: PUT /api/projects/{project_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.put("/api/projects/some-id", {"name": "Hacked Project"})

        assert response.status_code == 403, f"VULNERABILITY: Guest updated project! Status: {response.status_code}"

    def test_guest_cannot_delete_project(self, security_tester):
        """
        HIGH: Test if guest can delete projects
        Endpoint: DELETE /api/projects/{project_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.delete("/api/projects/some-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted project! Status: {response.status_code}"

    def test_guest_cannot_add_part_to_project(self, security_tester):
        """
        HIGH: Test if guest can modify project parts
        Endpoint: POST /api/projects/{project_id}/parts/{part_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.post("/api/projects/proj-id/parts/part-id")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest added part to project! Status: {response.status_code}"

    def test_guest_cannot_remove_part_from_project(self, security_tester):
        """
        HIGH: Test if guest can remove parts from projects
        Endpoint: DELETE /api/projects/{project_id}/parts/{part_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user (allows guest)
        """
        response = security_tester.delete("/api/projects/proj-id/parts/part-id")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest removed part from project! Status: {response.status_code}"


# ========================================
# HIGH: Tools Vulnerabilities (8 endpoints)
# ========================================


class TestToolsPermissionBypass:
    """Test tool endpoints that lack permission checks"""

    def test_guest_cannot_create_tool(self, security_tester):
        """
        HIGH: Test if guest can create tools
        Endpoint: POST /api/tools/
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tools/", {"name": "Evil Tool", "tool_type": "power_tool"})

        assert response.status_code == 403, f"VULNERABILITY: Guest created tool! Status: {response.status_code}"

    def test_guest_cannot_update_tool(self, security_tester):
        """
        HIGH: Test if guest can update tools
        Endpoint: PUT /api/tools/{tool_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.put("/api/tools/some-id", {"name": "Hacked Tool"})

        assert response.status_code == 403, f"VULNERABILITY: Guest updated tool! Status: {response.status_code}"

    def test_guest_cannot_delete_tool(self, security_tester):
        """
        HIGH: Test if guest can delete tools
        Endpoint: DELETE /api/tools/{tool_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/tools/some-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted tool! Status: {response.status_code}"

    def test_guest_cannot_checkout_tool(self, security_tester):
        """
        MEDIUM: Test if guest can checkout tools
        Endpoint: POST /api/tools/{tool_id}/checkout
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tools/some-id/checkout", {"checked_out_by": "guest"})

        assert response.status_code == 403, f"VULNERABILITY: Guest checked out tool! Status: {response.status_code}"

    def test_guest_cannot_return_tool(self, security_tester):
        """
        MEDIUM: Test if guest can return tools
        Endpoint: POST /api/tools/{tool_id}/return
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tools/some-id/return", {})

        assert response.status_code == 403, f"VULNERABILITY: Guest returned tool! Status: {response.status_code}"

    def test_guest_cannot_create_maintenance_record(self, security_tester):
        """
        MEDIUM: Test if guest can create maintenance records
        Endpoint: POST /api/tools/{tool_id}/maintenance
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post(
            "/api/tools/some-id/maintenance", {"maintenance_type": "repair", "notes": "Fake maintenance"}
        )

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest created maintenance record! Status: {response.status_code}"

    def test_guest_cannot_update_maintenance_record(self, security_tester):
        """
        MEDIUM: Test if guest can update maintenance records
        Endpoint: PUT /api/tools/{tool_id}/maintenance/{record_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.put("/api/tools/tool-id/maintenance/record-id", {"notes": "Hacked maintenance"})

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest updated maintenance record! Status: {response.status_code}"

    def test_guest_cannot_delete_maintenance_record(self, security_tester):
        """
        MEDIUM: Test if guest can delete maintenance records
        Endpoint: DELETE /api/tools/{tool_id}/maintenance/{record_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/tools/tool-id/maintenance/record-id")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest deleted maintenance record! Status: {response.status_code}"


# ========================================
# HIGH: Tags Vulnerabilities (10 endpoints)
# ========================================


class TestTagsPermissionBypass:
    """Test tag endpoints that lack permission checks"""

    def test_guest_cannot_create_tag(self, security_tester):
        """
        HIGH: Test if guest can create tags
        Endpoint: POST /api/tags
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tags", {"name": "evil-tag", "color": "#FF0000"})

        assert response.status_code == 403, f"VULNERABILITY: Guest created tag! Status: {response.status_code}"

    def test_guest_cannot_update_tag(self, security_tester):
        """
        HIGH: Test if guest can update tags
        Endpoint: PUT /api/tags/{tag_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.put("/api/tags/some-id", {"name": "hacked-tag"})

        assert response.status_code == 403, f"VULNERABILITY: Guest updated tag! Status: {response.status_code}"

    def test_guest_cannot_delete_tag(self, security_tester):
        """
        HIGH: Test if guest can delete tags
        Endpoint: DELETE /api/tags/{tag_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/tags/some-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest deleted tag! Status: {response.status_code}"

    def test_guest_cannot_assign_tag_to_part(self, security_tester):
        """
        MEDIUM: Test if guest can assign tags to parts
        Endpoint: POST /api/tags/{tag_id}/parts/{part_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tags/tag-id/parts/part-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest assigned tag to part! Status: {response.status_code}"

    def test_guest_cannot_remove_tag_from_part(self, security_tester):
        """
        MEDIUM: Test if guest can remove tags from parts
        Endpoint: DELETE /api/tags/{tag_id}/parts/{part_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/tags/tag-id/parts/part-id")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest removed tag from part! Status: {response.status_code}"

    def test_guest_cannot_assign_tag_to_tool(self, security_tester):
        """
        MEDIUM: Test if guest can assign tags to tools
        Endpoint: POST /api/tags/{tag_id}/tools/{tool_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tags/tag-id/tools/tool-id")

        assert response.status_code == 403, f"VULNERABILITY: Guest assigned tag to tool! Status: {response.status_code}"

    def test_guest_cannot_remove_tag_from_tool(self, security_tester):
        """
        MEDIUM: Test if guest can remove tags from tools
        Endpoint: DELETE /api/tags/{tag_id}/tools/{tool_id}
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.delete("/api/tags/tag-id/tools/tool-id")

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest removed tag from tool! Status: {response.status_code}"

    def test_guest_cannot_bulk_tag_operation(self, security_tester):
        """
        HIGH: Test if guest can perform bulk tag operations
        Endpoint: POST /api/tags/bulk
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post(
            "/api/tags/bulk",
            {"operation": "assign", "tag_ids": ["tag1", "tag2"], "item_ids": ["item1", "item2"], "item_type": "part"},
        )

        assert (
            response.status_code == 403
        ), f"VULNERABILITY: Guest performed bulk tag operation! Status: {response.status_code}"

    def test_guest_cannot_merge_tags(self, security_tester):
        """
        HIGH: Test if guest can merge tags
        Endpoint: POST /api/tags/merge
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post(
            "/api/tags/merge", {"source_tag_ids": ["tag1", "tag2"], "target_tag_id": "tag3"}
        )

        assert response.status_code == 403, f"VULNERABILITY: Guest merged tags! Status: {response.status_code}"

    def test_guest_cannot_cleanup_tags(self, security_tester):
        """
        MEDIUM: Test if guest can cleanup unused tags
        Endpoint: POST /api/tags/cleanup
        Expected: 403 Forbidden
        Current: Uses get_current_user_flexible (allows guest)
        """
        response = security_tester.post("/api/tags/cleanup", {"remove_unused": True})

        assert response.status_code == 403, f"VULNERABILITY: Guest cleaned up tags! Status: {response.status_code}"


# ========================================
# Summary Report Generator
# ========================================


def pytest_sessionfinish(session, exitstatus):
    """Generate summary report after all tests complete"""
    print("\n" + "=" * 80)
    print("SECURITY ASSESSMENT SUMMARY")
    print("=" * 80)
    print(f"\nTotal Tests: {session.testscollected}")
    print(f"Failed Tests (Vulnerabilities Found): {session.testsfailed}")
    print(f"Passed Tests (Security Controls Working): {session.testspassed}")
    print("\nNOTE: Failed tests indicate active vulnerabilities!")
    print("After applying permission fixes, all tests should pass.")
    print("=" * 80 + "\n")
