"""
Test API key auto-revoke on role downgrade
Verifies that API keys are automatically revoked when user permissions are downgraded
"""

import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app

client = TestClient(app)

# Admin API key for setup
ADMIN_API_KEY = os.getenv("MAKERMATRIX_API_KEY", "")  # Set in .env


class TestAPIKeyAutoRevoke:
    """Test automatic API key revocation on role downgrade"""

    def test_api_keys_revoked_on_downgrade(self):
        """
        Test that API keys are automatically revoked when user is downgraded

        Scenario:
        1. Get role IDs
        2. User has admin API key (created via UI/previous test)
        3. Admin downgrades user from admin to user role
        4. All API keys should be automatically revoked
        5. Response should include warning message
        """

        # Get role IDs
        response = client.get("/api/users/roles", headers={"X-API-Key": ADMIN_API_KEY})
        assert response.status_code == 200

        roles = {role["name"]: role["id"] for role in response.json()["data"]}
        admin_role_id = roles.get("admin")
        user_role_id = roles.get("user")

        assert admin_role_id and user_role_id, "Admin and user roles must exist"

        # Find a user with admin role (use the sectest999 we created earlier)
        response = client.get("/api/users/all", headers={"X-API-Key": ADMIN_API_KEY})

        test_user = None
        for user in response.json()["data"]:
            if user["username"] == "sectest999":
                test_user = user
                break

        if not test_user:
            pytest.skip("sectest999 user not found - create it first")
            return

        test_user_id = test_user["id"]
        print(f"\n✅ Found test user: {test_user['username']} (ID: {test_user_id})")

        # Get current API keys count
        response = client.get("/api/api-keys/", headers={"X-API-Key": ADMIN_API_KEY})

        initial_keys = [k for k in response.json()["data"] if k["user_id"] == test_user_id]
        print(f"   User has {len(initial_keys)} API key(s)")

        # Downgrade user from admin to user role
        response = client.put(
            f"/api/users/{test_user_id}/roles", headers={"X-API-Key": ADMIN_API_KEY}, json={"role_ids": [user_role_id]}
        )

        assert response.status_code == 200
        response_data = response.json()

        print(f"\n✅ Downgrade response: {response_data['message']}")

        # Check if warning message is present
        if len(initial_keys) > 0:
            assert (
                "API key(s) were automatically revoked" in response_data["message"]
            ), "Expected warning about API key revocation"
            assert "⚠️" in response_data["message"], "Expected warning emoji in message"

            print(f"✅ WARNING MESSAGE RECEIVED:")
            print(f"   {response_data['message']}")
        else:
            print(f"✅ No API keys to revoke (user had 0 keys)")

        # Verify user roles were updated
        assert "user" in [role["name"] for role in response_data["data"]["roles"]]
        assert "admin" not in [role["name"] for role in response_data["data"]["roles"]]
        print(f"✅ User successfully downgraded to 'user' role")

        # Verify all API keys were revoked
        response = client.get("/api/api-keys/", headers={"X-API-Key": ADMIN_API_KEY})

        remaining_active_keys = [k for k in response.json()["data"] if k["user_id"] == test_user_id and k["is_active"]]

        assert (
            len(remaining_active_keys) == 0
        ), f"Expected all API keys to be revoked, but found {len(remaining_active_keys)} active keys"

        print(f"✅ ALL API KEYS REVOKED: User now has 0 active API keys")
        print(f"\n🔒 SECURITY TEST PASSED: Auto-revoke on downgrade works correctly!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
