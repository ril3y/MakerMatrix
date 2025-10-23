#!/usr/bin/env python3
"""
Test WebSocket authentication to diagnose and fix the database table issue.
"""
import pytest
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set JWT_SECRET_KEY for testing if not already set
if not os.getenv("JWT_SECRET_KEY"):
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

from MakerMatrix.auth.dependencies import get_current_user_from_token
from MakerMatrix.services.system.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from sqlalchemy import inspect


@pytest.mark.asyncio
async def test_websocket_database_connection():
    """Test that the database connection and usermodel table exist."""

    # Verify the database connection
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Found {len(tables)} tables in database")
        print(f"User-related tables: {[t for t in tables if 'user' in t.lower()]}")

        # Check if usermodel table exists
        assert "usermodel" in tables, "usermodel table should exist in database"

        # Check if userrolelink table exists
        assert "userrolelink" in tables, "userrolelink table should exist in database"

        # Check if rolemodel table exists
        assert "rolemodel" in tables, "rolemodel table should exist in database"

    except Exception as e:
        pytest.fail(f"Database connection error: {e}")


@pytest.mark.asyncio
async def test_websocket_authentication_flow():
    """Test the complete WebSocket authentication flow."""

    try:
        # Initialize services
        auth_service = AuthService()
        user_repo = UserRepository()

        # Try to get admin user
        admin_user = user_repo.get_user_by_username("admin")
        assert admin_user is not None, "Admin user should exist"
        assert admin_user.username == "admin", "Admin user should have correct username"

        # Create a test token
        token_data = {"sub": admin_user.username}
        test_token = auth_service.create_access_token(token_data)
        assert test_token is not None, "Test token should be created"

        # Test the WebSocket authentication function
        authenticated_user = await get_current_user_from_token(test_token)
        assert authenticated_user is not None, "WebSocket authentication should succeed"
        assert authenticated_user.username == "admin", "Authenticated user should be admin"

        print("✅ WebSocket authentication test PASSED")

    except Exception as e:
        pytest.fail(f"WebSocket authentication error: {e}")


@pytest.mark.asyncio
async def test_websocket_authentication_with_invalid_token():
    """Test WebSocket authentication with invalid token."""

    try:
        # Test with invalid token
        with pytest.raises(Exception):
            await get_current_user_from_token("invalid_token")

        # Test with None token
        with pytest.raises(Exception):
            await get_current_user_from_token(None)

        print("✅ Invalid token handling test PASSED")

    except Exception as e:
        pytest.fail(f"Invalid token test error: {e}")


@pytest.mark.asyncio
async def test_database_url_consistency():
    """Test that the database URL is consistent across the application."""

    try:
        # Check the engine URL
        engine_url = str(engine.url)
        print(f"Engine URL: {engine_url}")

        # Should be using makermatrix.db, not makers_matrix.db
        assert "makermatrix.db" in engine_url, f"Engine should use makermatrix.db, got: {engine_url}"
        assert "makers_matrix.db" not in engine_url, f"Engine should NOT use old makers_matrix.db name"

        print("✅ Database URL consistency test PASSED")

    except Exception as e:
        pytest.fail(f"Database URL consistency error: {e}")


@pytest.mark.asyncio
async def test_user_repository_database_connection():
    """Test that UserRepository is using the correct database connection."""

    try:
        user_repo = UserRepository()

        # Check the repository's engine URL
        repo_engine_url = str(user_repo.engine.url)
        print(f"Repository Engine URL: {repo_engine_url}")

        # Should be using makermatrix.db
        assert "makermatrix.db" in repo_engine_url, f"Repository should use makermatrix.db, got: {repo_engine_url}"

        # Test that the repository can query the database
        admin_user = user_repo.get_user_by_username("admin")
        assert admin_user is not None, "Repository should be able to query admin user"

        print("✅ UserRepository database connection test PASSED")

    except Exception as e:
        pytest.fail(f"UserRepository database connection error: {e}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
