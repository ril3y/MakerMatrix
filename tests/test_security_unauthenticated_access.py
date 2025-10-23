"""
Security Test Suite: Unauthenticated Access Vulnerabilities

This test suite attempts to access endpoints without ANY authentication token.
All write operations and sensitive data access should require authentication.

Expected Behavior:
- All tests should return 401 Unauthorized for requests without auth token
- Critical endpoints like user management should be completely locked down

CVSS Score: 9.1 (CRITICAL)
- Attack Vector: Network
- Attack Complexity: Low
- Privileges Required: None
- User Interaction: None
- Scope: Unchanged
- Confidentiality: High
- Integrity: High
- Availability: High

Author: Security Assessment
Date: 2025-10-22
"""

import pytest
import requests
from typing import Dict, Optional

# Test Configuration
BASE_URL = "https://10.2.0.2:8443"

# Disable SSL verification warnings for self-signed cert
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UnauthenticatedTester:
    """Helper class for testing unauthenticated requests"""

    def __init__(self):
        self.base_url = BASE_URL
        self.headers = {"Content-Type": "application/json"}

    def post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make unauthenticated POST request"""
        url = f"{self.base_url}{endpoint}"
        return requests.post(url, headers=self.headers, json=data or {}, verify=False)

    def put(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make unauthenticated PUT request"""
        url = f"{self.base_url}{endpoint}"
        return requests.put(url, headers=self.headers, json=data or {}, verify=False)

    def delete(self, endpoint: str) -> requests.Response:
        """Make unauthenticated DELETE request"""
        url = f"{self.base_url}{endpoint}"
        return requests.delete(url, headers=self.headers, verify=False)

    def get(self, endpoint: str) -> requests.Response:
        """Make unauthenticated GET request"""
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, verify=False)


@pytest.fixture(scope="session")
def unauth_tester():
    """Fixture to provide unauthenticated tester instance"""
    return UnauthenticatedTester()


# ========================================
# CRITICAL: Completely Unprotected Endpoints
# ========================================


class TestCriticalUnauthenticatedAccess:
    """Test endpoints with NO authentication at all"""

    def test_register_requires_auth(self, unauth_tester):
        """
        CRITICAL: User registration endpoint has NO authentication
        Endpoint: POST /api/users/register
        Expected: 401 Unauthorized
        Current: COMPLETELY UNPROTECTED - anyone can create admin users!
        """
        response = unauth_tester.post(
            "/api/users/register",
            {
                "username": "anonymous_hacker",
                "email": "hacker@evil.com",
                "password": "EvilPassword123!",
                "roles": ["admin"],
            },
        )

        assert response.status_code == 401, (
            f"CRITICAL: Unauthenticated user registration! Status: {response.status_code}, "
            f"Response: {response.text[:200]}"
        )

    def test_cleanup_locations_requires_auth(self, unauth_tester):
        """
        CRITICAL: Location cleanup has NO authentication
        Endpoint: DELETE /api/locations/cleanup-locations
        Expected: 401 Unauthorized
        Current: COMPLETELY UNPROTECTED - can delete locations!
        """
        response = unauth_tester.delete("/api/locations/cleanup-locations")

        assert response.status_code == 401, (
            f"CRITICAL: Unauthenticated location cleanup! Status: {response.status_code}, "
            f"Response: {response.text[:200]}"
        )

    def test_get_user_by_id_requires_auth(self, unauth_tester):
        """
        CRITICAL: Get user endpoint has NO authentication
        Endpoint: GET /api/users/{user_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - information disclosure!
        """
        response = unauth_tester.get("/api/users/admin")

        assert response.status_code == 401, f"CRITICAL: Unauthenticated user access! Status: {response.status_code}"

    def test_get_user_by_username_requires_auth(self, unauth_tester):
        """
        CRITICAL: Get user by username has NO authentication
        Endpoint: GET /api/users/by-username/{username}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can enumerate users!
        """
        response = unauth_tester.get("/api/users/by-username/admin")

        assert response.status_code == 401, f"CRITICAL: Unauthenticated username lookup! Status: {response.status_code}"

    def test_update_user_requires_auth(self, unauth_tester):
        """
        CRITICAL: Update user has NO authentication
        Endpoint: PUT /api/users/{user_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - account takeover possible!
        """
        response = unauth_tester.put("/api/users/admin", {"email": "pwned@hacker.com", "roles": ["admin"]})

        assert (
            response.status_code == 401
        ), f"CRITICAL: Unauthenticated user modification! Status: {response.status_code}"

    def test_delete_user_requires_auth(self, unauth_tester):
        """
        CRITICAL: Delete user has NO authentication
        Endpoint: DELETE /api/users/{user_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can delete any user!
        """
        response = unauth_tester.delete("/api/users/some-user-id")

        assert response.status_code == 401, f"CRITICAL: Unauthenticated user deletion! Status: {response.status_code}"

    def test_update_user_roles_requires_auth(self, unauth_tester):
        """
        CRITICAL: Update user roles has NO authentication
        Endpoint: PUT /api/users/{user_id}/roles
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - privilege escalation!
        """
        response = unauth_tester.put("/api/users/admin/roles", {"role_ids": ["admin-role-id"]})

        assert (
            response.status_code == 401
        ), f"CRITICAL: Unauthenticated role modification! Status: {response.status_code}"

    def test_update_user_status_requires_auth(self, unauth_tester):
        """
        CRITICAL: Update user status has NO authentication
        Endpoint: PUT /api/users/{user_id}/status
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can disable admin!
        """
        response = unauth_tester.put("/api/users/admin/status", {"is_active": False})

        assert response.status_code == 401, f"CRITICAL: Unauthenticated status change! Status: {response.status_code}"

    def test_create_role_requires_auth(self, unauth_tester):
        """
        CRITICAL: Create role has NO authentication
        Endpoint: POST /api/users/roles/add_role
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can create superuser role!
        """
        response = unauth_tester.post("/api/users/roles/add_role", {"name": "superadmin", "permissions": ["*:*"]})

        assert response.status_code == 401, f"CRITICAL: Unauthenticated role creation! Status: {response.status_code}"

    def test_update_role_requires_auth(self, unauth_tester):
        """
        CRITICAL: Update role has NO authentication
        Endpoint: PUT /api/users/roles/{role_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can modify role permissions!
        """
        response = unauth_tester.put("/api/users/roles/some-role-id", {"permissions": ["*:*"]})

        assert response.status_code == 401, f"CRITICAL: Unauthenticated role update! Status: {response.status_code}"

    def test_delete_role_requires_auth(self, unauth_tester):
        """
        CRITICAL: Delete role has NO authentication
        Endpoint: DELETE /api/users/roles/{role_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION
        """
        response = unauth_tester.delete("/api/users/roles/some-role-id")

        assert response.status_code == 401, f"CRITICAL: Unauthenticated role deletion! Status: {response.status_code}"

    def test_get_role_requires_auth(self, unauth_tester):
        """
        HIGH: Get role details has NO authentication
        Endpoint: GET /api/users/roles/{role_id}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - information disclosure
        """
        response = unauth_tester.get("/api/users/roles/some-role-id")

        assert response.status_code == 401, f"HIGH: Unauthenticated role access! Status: {response.status_code}"

    def test_get_role_by_name_requires_auth(self, unauth_tester):
        """
        HIGH: Get role by name has NO authentication
        Endpoint: GET /api/users/roles/by-name/{name}
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - can enumerate roles and permissions
        """
        response = unauth_tester.get("/api/users/roles/by-name/admin")

        assert response.status_code == 401, f"HIGH: Unauthenticated role lookup! Status: {response.status_code}"

    def test_get_all_roles_requires_auth(self, unauth_tester):
        """
        HIGH: Get all roles has NO authentication
        Endpoint: GET /api/users/roles
        Expected: 401 Unauthorized
        Current: NO AUTHENTICATION - complete role enumeration
        """
        response = unauth_tester.get("/api/users/roles")

        assert response.status_code == 401, f"HIGH: Unauthenticated roles listing! Status: {response.status_code}"


# ========================================
# HIGH: Data Modification Without Auth
# ========================================


class TestWriteOperationsRequireAuth:
    """Test that all write operations require authentication"""

    def test_create_category_requires_auth(self, unauth_tester):
        """
        HIGH: Category creation without auth
        Endpoint: POST /api/categories/add_category
        Expected: 401 Unauthorized
        """
        response = unauth_tester.post("/api/categories/add_category", {"name": "Unauthorized Category"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated category creation! Status: {response.status_code}"

    def test_update_category_requires_auth(self, unauth_tester):
        """
        HIGH: Category update without auth
        Endpoint: PUT /api/categories/update_category/{category_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.put("/api/categories/update_category/some-id", {"name": "Hacked"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated category update! Status: {response.status_code}"

    def test_delete_category_requires_auth(self, unauth_tester):
        """
        HIGH: Category deletion without auth
        Endpoint: DELETE /api/categories/remove_category
        Expected: 401 Unauthorized
        """
        response = unauth_tester.delete("/api/categories/remove_category?cat_id=some-id")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated category deletion! Status: {response.status_code}"

    def test_create_location_requires_auth(self, unauth_tester):
        """
        HIGH: Location creation without auth
        Endpoint: POST /api/locations/add_location
        Expected: 401 Unauthorized
        """
        response = unauth_tester.post("/api/locations/add_location", {"name": "Unauthorized Location"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated location creation! Status: {response.status_code}"

    def test_update_location_requires_auth(self, unauth_tester):
        """
        HIGH: Location update without auth
        Endpoint: PUT /api/locations/update_location/{location_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.put("/api/locations/update_location/some-id", {"name": "Hacked"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated location update! Status: {response.status_code}"

    def test_delete_location_requires_auth(self, unauth_tester):
        """
        HIGH: Location deletion without auth
        Endpoint: DELETE /api/locations/delete_location/{location_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.delete("/api/locations/delete_location/some-id")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated location deletion! Status: {response.status_code}"

    def test_create_project_requires_auth(self, unauth_tester):
        """
        HIGH: Project creation without auth
        Endpoint: POST /api/projects/
        Expected: 401 Unauthorized
        """
        response = unauth_tester.post("/api/projects/", {"name": "Unauthorized Project"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated project creation! Status: {response.status_code}"

    def test_update_project_requires_auth(self, unauth_tester):
        """
        HIGH: Project update without auth
        Endpoint: PUT /api/projects/{project_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.put("/api/projects/some-id", {"name": "Hacked"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated project update! Status: {response.status_code}"

    def test_delete_project_requires_auth(self, unauth_tester):
        """
        HIGH: Project deletion without auth
        Endpoint: DELETE /api/projects/{project_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.delete("/api/projects/some-id")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated project deletion! Status: {response.status_code}"

    def test_create_tag_requires_auth(self, unauth_tester):
        """
        HIGH: Tag creation without auth
        Endpoint: POST /api/tags
        Expected: 401 Unauthorized
        """
        response = unauth_tester.post("/api/tags", {"name": "unauthorized-tag"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated tag creation! Status: {response.status_code}"

    def test_update_tag_requires_auth(self, unauth_tester):
        """
        HIGH: Tag update without auth
        Endpoint: PUT /api/tags/{tag_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.put("/api/tags/some-id", {"name": "hacked"})

        assert response.status_code == 401, f"VULNERABILITY: Unauthenticated tag update! Status: {response.status_code}"

    def test_delete_tag_requires_auth(self, unauth_tester):
        """
        HIGH: Tag deletion without auth
        Endpoint: DELETE /api/tags/{tag_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.delete("/api/tags/some-id")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated tag deletion! Status: {response.status_code}"

    def test_create_tool_requires_auth(self, unauth_tester):
        """
        HIGH: Tool creation without auth
        Endpoint: POST /api/tools/
        Expected: 401 Unauthorized
        """
        response = unauth_tester.post("/api/tools/", {"name": "Unauthorized Tool"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated tool creation! Status: {response.status_code}"

    def test_update_tool_requires_auth(self, unauth_tester):
        """
        HIGH: Tool update without auth
        Endpoint: PUT /api/tools/{tool_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.put("/api/tools/some-id", {"name": "Hacked"})

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated tool update! Status: {response.status_code}"

    def test_delete_tool_requires_auth(self, unauth_tester):
        """
        HIGH: Tool deletion without auth
        Endpoint: DELETE /api/tools/{tool_id}
        Expected: 401 Unauthorized
        """
        response = unauth_tester.delete("/api/tools/some-id")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated tool deletion! Status: {response.status_code}"


# ========================================
# MEDIUM: Information Disclosure
# ========================================


class TestReadOperationsRequireAuth:
    """Test that sensitive read operations require authentication"""

    def test_get_all_users_requires_auth(self, unauth_tester):
        """
        HIGH: Get all users without auth
        Endpoint: GET /api/users/all
        Expected: 401 Unauthorized
        Current: Information disclosure of all user accounts
        """
        response = unauth_tester.get("/api/users/all")

        assert (
            response.status_code == 401
        ), f"VULNERABILITY: Unauthenticated user enumeration! Status: {response.status_code}"

    def test_get_categories_public_or_requires_auth(self, unauth_tester):
        """
        INFO: Check if category listing is intentionally public
        Endpoint: GET /api/categories/get_all_categories
        Note: May be intentionally public for product catalog
        """
        response = unauth_tester.get("/api/categories/get_all_categories")

        # Document the behavior - may be intentional
        if response.status_code == 200:
            print(f"\nINFO: Categories endpoint is public (may be intentional): {response.status_code}")
        else:
            print(f"\nSECURE: Categories require auth: {response.status_code}")

    def test_get_locations_public_or_requires_auth(self, unauth_tester):
        """
        INFO: Check if location listing is intentionally public
        Endpoint: GET /api/locations/get_all_locations
        Note: May be intentionally public for warehouse navigation
        """
        response = unauth_tester.get("/api/locations/get_all_locations")

        # Document the behavior - may be intentional
        if response.status_code == 200:
            print(f"\nINFO: Locations endpoint is public (may be intentional): {response.status_code}")
        else:
            print(f"\nSECURE: Locations require auth: {response.status_code}")


def pytest_sessionfinish(session, exitstatus):
    """Generate summary report after all tests complete"""
    print("\n" + "=" * 80)
    print("UNAUTHENTICATED ACCESS VULNERABILITY SUMMARY")
    print("=" * 80)
    print(f"\nTotal Tests: {session.testscollected}")
    print(f"Failed Tests (Endpoints Accessible Without Auth): {session.testsfailed}")
    print(f"Passed Tests (Auth Required): {session.testspassed}")
    print("\nCRITICAL: Any failed test represents an endpoint that can be accessed")
    print("without authentication, which is a severe security vulnerability!")
    print("=" * 80 + "\n")
