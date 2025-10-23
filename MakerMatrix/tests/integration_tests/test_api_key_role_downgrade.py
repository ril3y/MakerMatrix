"""
Test API key security when user roles change
Verifies that API keys respect current user permissions, not permissions at creation time
"""

import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app

client = TestClient(app)

# Admin API key for setup
ADMIN_API_KEY = os.getenv("MAKERMATRIX_API_KEY", "")  # Set in .env


class TestAPIKeyRoleDowngrade:
    """Test API key behavior when user roles change"""

    def test_api_key_inherits_current_user_permissions(self):
        """
        Test that API keys use current user permissions, not stored permissions

        Scenario:
        1. Create admin user
        2. Admin creates API key
        3. Downgrade admin to user role (read-only)
        4. Try to use API key to create another key
        5. Should FAIL - key should use current user permissions
        """

        # Step 1: Get admin role ID
        response = client.get("/api/users/roles", headers={"X-API-Key": ADMIN_API_KEY})
        assert response.status_code == 200
        admin_role = next((r for r in response.json()["data"] if r["name"] == "admin"), None)
        user_role = next((r for r in response.json()["data"] if r["name"] == "user"), None)
        assert admin_role and user_role

        # Step 2: Create test admin user
        import time

        test_username = f"testadmin_{int(time.time())}"

        response = client.post(
            "/api/users/register",
            headers={"X-API-Key": ADMIN_API_KEY},
            json={
                "username": test_username,
                "email": f"{test_username}@test.com",
                "password": "Test123!",
                "roles": ["admin"],
            },
        )

        # May fail if user exists
        if response.status_code not in [200, 201, 422, 409]:
            pytest.fail(f"Failed to create test user: {response.json()}")

        if response.status_code in [200, 201]:
            test_user = response.json()["data"]
            test_user_id = test_user["id"]
            print(f"✅ Created test admin user: {test_username}")
        else:
            # User might exist from previous test, skip this test
            pytest.skip(f"Test user already exists or validation error: {response.json()}")
            return

        # Step 3: Admin user creates API key
        response = client.post(
            "/api/api-keys/",
            headers={"X-API-Key": ADMIN_API_KEY},
            json={
                "name": f"Test Key for {test_username}",
                "description": "Testing downgrade scenario",
                "role_names": ["admin"],
                "expires_in_days": 1,
            },
        )

        # API key creation should fail for the test user via admin
        # We need to create the key as the test user, so let's get a JWT token instead

        # Login as test user to get JWT
        response = client.post("/api/login", data={"username": test_username, "password": "Test123!"})

        if response.status_code != 200:
            pytest.skip(f"Could not login as test user: {response.json()}")
            return

        test_user_token = response.json()["access_token"]

        # Create API key as test user
        response = client.post(
            "/api/api-keys/",
            headers={"Authorization": f"Bearer {test_user_token}"},
            json={
                "name": f"Admin Key for {test_username}",
                "description": "This key will be tested after downgrade",
                "role_names": ["admin"],
                "expires_in_days": 1,
            },
        )

        assert response.status_code in [200, 201], f"Failed to create API key: {response.json()}"
        test_api_key = response.json()["data"]["api_key"]
        print(f"✅ Created API key for test user (has admin permissions)")

        # Step 4: Downgrade user to "user" role (read-only)
        response = client.put(
            f"/api/users/{test_user_id}/roles",
            headers={"X-API-Key": ADMIN_API_KEY},
            json={"role_ids": [user_role["id"]]},
        )

        assert response.status_code == 200, f"Failed to downgrade user: {response.json()}"
        print(f"✅ Downgraded {test_username} to 'user' role")

        # Step 5: Try to use API key to create another key (should FAIL)
        response = client.post(
            "/api/api-keys/",
            headers={"X-API-Key": test_api_key},
            json={
                "name": "Should Not Work",
                "description": "This should fail",
                "role_names": ["admin"],
                "expires_in_days": 1,
            },
        )

        # CRITICAL TEST: This should fail with 403 Forbidden
        # If it succeeds (200/201), we have a privilege escalation vulnerability
        assert (
            response.status_code == 403
        ), f"SECURITY VULN: Downgraded user's API key still has admin permissions! Status: {response.status_code}, Response: {response.json()}"

        print("✅ SECURITY CHECK PASSED: API key correctly uses current user permissions")
        print(f"   User downgraded from admin -> user, API key creation properly denied")

        # Cleanup: Delete test user
        response = client.delete(f"/api/users/{test_user_id}", headers={"X-API-Key": ADMIN_API_KEY})
        print(f"✅ Cleaned up test user")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
