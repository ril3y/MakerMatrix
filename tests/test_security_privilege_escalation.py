"""
Security Test Suite: Privilege Escalation Vulnerabilities

This test suite attempts various privilege escalation attacks to gain
administrative access from a low-privilege guest account.

Attack Vectors Tested:
1. Direct role modification (assign self admin role)
2. Create new superuser account
3. Modify existing role permissions
4. Create custom role with all permissions
5. Exploit missing RBAC checks

CVSS Score: 9.9 (CRITICAL)
- Attack Vector: Network
- Attack Complexity: Low
- Privileges Required: Low (guest access)
- User Interaction: None
- Scope: Changed
- Confidentiality: High
- Integrity: High
- Availability: High

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

# Disable SSL verification warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PrivilegeEscalationTester:
    """Helper class for privilege escalation testing"""

    def __init__(self):
        self.base_url = BASE_URL
        self.guest_data = self._load_guest_token()
        self.guest_token = self.guest_data['access_token']
        self.guest_user_id = self.guest_data['user']['id']
        self.guest_username = self.guest_data['user']['username']
        self.headers = {
            "Authorization": f"Bearer {self.guest_token}",
            "Content-Type": "application/json"
        }

    def _load_guest_token(self) -> Dict:
        """Load guest token and user data"""
        try:
            with open(GUEST_TOKEN_PATH, 'r') as f:
                return json.load(f)
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

    def get(self, endpoint: str) -> requests.Response:
        """Make authenticated GET request"""
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, verify=False)


@pytest.fixture(scope="session")
def escalation_tester():
    """Fixture to provide privilege escalation tester"""
    return PrivilegeEscalationTester()


# ========================================
# CRITICAL: Direct Privilege Escalation
# ========================================

class TestDirectPrivilegeEscalation:
    """Test direct privilege escalation through role manipulation"""

    def test_cannot_self_assign_admin_role(self, escalation_tester):
        """
        CRITICAL: Attempt to assign admin role to own account
        Endpoint: PUT /api/users/{user_id}/roles
        Attack: Guest user modifies own roles to include admin
        Expected: 403 Forbidden
        """
        # First, try to get list of roles to find admin role ID
        roles_response = escalation_tester.get("/api/users/roles")

        if roles_response.status_code == 200:
            roles_data = roles_response.json()
            admin_role_id = None

            # Find admin role ID
            for role in roles_data.get('data', []):
                if role.get('name') == 'admin':
                    admin_role_id = role.get('id')
                    break

            print(f"\n[RECON] Found admin role ID: {admin_role_id}")

        # Attempt to escalate privileges
        response = escalation_tester.put(
            f"/api/users/{escalation_tester.guest_user_id}/roles",
            {"role_ids": [admin_role_id] if admin_role_id else ["fake-admin-id"]}
        )

        assert response.status_code == 403, \
            f"CRITICAL PRIVILEGE ESCALATION: Guest assigned admin role to self! " \
            f"Status: {response.status_code}, Response: {response.text[:500]}"

    def test_cannot_modify_own_user_record(self, escalation_tester):
        """
        CRITICAL: Attempt to modify own user record
        Endpoint: PUT /api/users/{user_id}
        Attack: Guest user updates email/roles in user record
        Expected: 403 Forbidden (guests should not modify users)
        """
        response = escalation_tester.put(
            f"/api/users/{escalation_tester.guest_user_id}",
            {
                "email": "admin@pwned.com",
                "roles": ["admin"],
                "is_active": True
            }
        )

        assert response.status_code == 403, \
            f"CRITICAL: Guest modified own user record! Status: {response.status_code}"

    def test_cannot_create_admin_user(self, escalation_tester):
        """
        CRITICAL: Attempt to create new admin user
        Endpoint: POST /api/users/register
        Attack: Create a new user with admin privileges
        Expected: 403 Forbidden (only admins should create users)
        """
        response = escalation_tester.post("/api/users/register", {
            "username": f"backdoor_admin_{escalation_tester.guest_username}",
            "email": "backdoor@evil.com",
            "password": "BackdoorPass123!",
            "roles": ["admin"]  # Attempting to create admin!
        })

        assert response.status_code == 403, \
            f"CRITICAL BACKDOOR: Guest created admin user! " \
            f"Status: {response.status_code}, Response: {response.text[:500]}"

    def test_cannot_create_custom_superuser_role(self, escalation_tester):
        """
        CRITICAL: Attempt to create role with all permissions
        Endpoint: POST /api/users/roles/add_role
        Attack: Create "superadmin" role with wildcard permissions
        Expected: 403 Forbidden
        """
        response = escalation_tester.post("/api/users/roles/add_role", {
            "name": "superadmin",
            "description": "Escalated privileges",
            "permissions": [
                "*:*",  # Wildcard all permissions
                "admin",
                "user:create",
                "user:update",
                "user:delete",
                "role:create",
                "role:update",
                "role:delete"
            ]
        })

        assert response.status_code == 403, \
            f"CRITICAL: Guest created superuser role! " \
            f"Status: {response.status_code}, Response: {response.text[:500]}"

    def test_cannot_modify_viewer_role_permissions(self, escalation_tester):
        """
        CRITICAL: Attempt to modify viewer role to have admin permissions
        Endpoint: PUT /api/users/roles/{role_id}
        Attack: Escalate viewer role permissions to admin level
        Expected: 403 Forbidden
        """
        # Get viewer role ID
        roles_response = escalation_tester.get("/api/users/roles")

        if roles_response.status_code == 200:
            roles_data = roles_response.json()
            viewer_role_id = None

            for role in roles_data.get('data', []):
                if role.get('name') == 'viewer':
                    viewer_role_id = role.get('id')
                    break

            print(f"\n[RECON] Found viewer role ID: {viewer_role_id}")

            if viewer_role_id:
                # Attempt to escalate viewer role permissions
                response = escalation_tester.put(
                    f"/api/users/roles/{viewer_role_id}",
                    {
                        "permissions": [
                            "*:*",  # All permissions
                            "admin",
                            "user:create",
                            "user:update",
                            "user:delete"
                        ]
                    }
                )

                assert response.status_code == 403, \
                    f"CRITICAL: Guest escalated viewer role! " \
                    f"Status: {response.status_code}, Response: {response.text[:500]}"


# ========================================
# HIGH: Indirect Privilege Escalation
# ========================================

class TestIndirectPrivilegeEscalation:
    """Test indirect privilege escalation through data manipulation"""

    def test_cannot_delete_admin_user(self, escalation_tester):
        """
        HIGH: Attempt to delete admin user (DoS attack)
        Endpoint: DELETE /api/users/{user_id}
        Attack: Delete admin to prevent legitimate access
        Expected: 403 Forbidden
        """
        response = escalation_tester.get("/api/users/all")

        if response.status_code == 200:
            users_data = response.json()
            admin_user_id = None

            for user in users_data.get('data', {}).get('users', []):
                if 'admin' in [r.get('name') for r in user.get('roles', [])]:
                    admin_user_id = user.get('id')
                    break

            print(f"\n[RECON] Found admin user ID: {admin_user_id}")

            if admin_user_id:
                delete_response = escalation_tester.delete(f"/api/users/{admin_user_id}")

                # Should be 403, but might succeed if no permission check!
                assert delete_response.status_code == 403, \
                    f"CRITICAL: Guest deleted admin user! Status: {delete_response.status_code}"

    def test_cannot_deactivate_admin_account(self, escalation_tester):
        """
        HIGH: Attempt to deactivate admin account
        Endpoint: PUT /api/users/{user_id}/status
        Attack: Disable admin account to prevent access
        Expected: 403 Forbidden
        """
        response = escalation_tester.get("/api/users/all")

        if response.status_code == 200:
            users_data = response.json()

            for user in users_data.get('data', {}).get('users', []):
                if 'admin' in [r.get('name') for r in user.get('roles', [])]:
                    admin_user_id = user.get('id')

                    # Attempt to deactivate admin
                    deactivate_response = escalation_tester.put(
                        f"/api/users/{admin_user_id}/status",
                        {"is_active": False}
                    )

                    assert deactivate_response.status_code == 403, \
                        f"CRITICAL: Guest deactivated admin! Status: {deactivate_response.status_code}"
                    break

    def test_cannot_delete_admin_role(self, escalation_tester):
        """
        HIGH: Attempt to delete admin role (DoS attack)
        Endpoint: DELETE /api/users/roles/{role_id}
        Attack: Delete admin role to break authorization
        Expected: 403 Forbidden
        """
        response = escalation_tester.get("/api/users/roles")

        if response.status_code == 200:
            roles_data = response.json()

            for role in roles_data.get('data', []):
                if role.get('name') == 'admin':
                    admin_role_id = role.get('id')

                    delete_response = escalation_tester.delete(
                        f"/api/users/roles/{admin_role_id}"
                    )

                    assert delete_response.status_code == 403, \
                        f"CRITICAL: Guest deleted admin role! Status: {delete_response.status_code}"
                    break


# ========================================
# MEDIUM: Information Gathering for Escalation
# ========================================

class TestInformationDisclosure:
    """Test information disclosure that aids privilege escalation"""

    def test_enumerate_all_users(self, escalation_tester):
        """
        HIGH: Enumerate all users and their roles
        Endpoint: GET /api/users/all
        Attack: Gather intelligence for targeted attacks
        Expected: 403 Forbidden (guests shouldn't see user list)
        """
        response = escalation_tester.get("/api/users/all")

        # This should require admin permission
        assert response.status_code == 403, \
            f"INFO LEAK: Guest enumerated all users! Status: {response.status_code}"

        if response.status_code == 200:
            users_data = response.json()
            print(f"\n[CRITICAL INFO DISCLOSURE] Guest accessed {len(users_data.get('data', {}).get('users', []))} users")

    def test_enumerate_all_roles(self, escalation_tester):
        """
        MEDIUM: Enumerate all roles and permissions
        Endpoint: GET /api/users/roles
        Attack: Map out permission structure
        Expected: May be allowed for guests (need to verify intent)
        """
        response = escalation_tester.get("/api/users/roles")

        if response.status_code == 200:
            roles_data = response.json()
            roles = roles_data.get('data', [])
            print(f"\n[INFO] Guest can view {len(roles)} roles")

            for role in roles:
                print(f"  - {role.get('name')}: {len(role.get('permissions', []))} permissions")

        # Document whether this is intentional
        # Guest users may need to see available roles for UI purposes
        # but should not be able to modify them

    def test_view_specific_user_details(self, escalation_tester):
        """
        HIGH: View specific user details
        Endpoint: GET /api/users/{user_id}
        Attack: Profile users for social engineering
        Expected: 403 Forbidden (guests shouldn't see other user details)
        """
        # Try to view admin user
        response = escalation_tester.get("/api/users/admin")

        assert response.status_code == 403, \
            f"INFO LEAK: Guest viewed user details! Status: {response.status_code}"

    def test_lookup_user_by_username(self, escalation_tester):
        """
        HIGH: Lookup users by username
        Endpoint: GET /api/users/by-username/{username}
        Attack: Enumerate valid usernames
        Expected: 403 Forbidden
        """
        # Try common usernames
        usernames = ['admin', 'root', 'administrator', 'user']

        for username in usernames:
            response = escalation_tester.get(f"/api/users/by-username/{username}")

            assert response.status_code == 403, \
                f"INFO LEAK: Guest looked up username '{username}'! Status: {response.status_code}"


# ========================================
# CRITICAL: Chain Attack Scenarios
# ========================================

class TestChainedEscalation:
    """Test multi-step escalation attacks"""

    def test_full_escalation_chain(self, escalation_tester):
        """
        CRITICAL: Attempt complete privilege escalation chain
        Steps:
        1. Create new role with admin permissions
        2. Assign new role to self
        3. Verify admin access

        Expected: All steps should fail with 403
        """
        print("\n[ATTACK CHAIN] Starting privilege escalation sequence...")

        # Step 1: Try to create admin role
        step1 = escalation_tester.post("/api/users/roles/add_role", {
            "name": "backdoor_admin",
            "permissions": ["*:*", "admin"]
        })
        print(f"  Step 1 (Create Role): {step1.status_code}")

        # Step 2: If step 1 succeeded, try to assign it
        if step1.status_code == 200:
            role_id = step1.json().get('data', {}).get('id')
            step2 = escalation_tester.put(
                f"/api/users/{escalation_tester.guest_user_id}/roles",
                {"role_ids": [role_id]}
            )
            print(f"  Step 2 (Assign Role): {step2.status_code}")

            # Step 3: If step 2 succeeded, verify we have admin
            if step2.status_code == 200:
                step3 = escalation_tester.get("/api/users/all")
                print(f"  Step 3 (Verify Admin): {step3.status_code}")

                pytest.fail(
                    f"CRITICAL: Complete privilege escalation succeeded!\n"
                    f"Created role: {step1.status_code}\n"
                    f"Assigned role: {step2.status_code}\n"
                    f"Admin access: {step3.status_code}"
                )

        # At least one step should have failed
        assert step1.status_code == 403, \
            f"First step of escalation chain succeeded! Status: {step1.status_code}"


def pytest_sessionfinish(session, exitstatus):
    """Generate summary report"""
    print("\n" + "="*80)
    print("PRIVILEGE ESCALATION VULNERABILITY SUMMARY")
    print("="*80)
    print(f"\nTotal Tests: {session.testscollected}")
    print(f"Failed Tests (Escalation Possible): {session.testsfailed}")
    print(f"Passed Tests (Escalation Blocked): {session.testspassed}")
    print("\nCRITICAL: Any failed test indicates a privilege escalation vulnerability!")
    print("Attackers can use these to gain administrative access from guest accounts.")
    print("="*80 + "\n")
