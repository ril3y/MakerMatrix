"""
Test that part creation and updates preserve emoji field.

This test suite verifies that when a part is created with an emoji,
the emoji is correctly saved and persisted through updates.
"""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient
from sqlmodel import Session, select

# Import test fixtures and utilities
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from MakerMatrix.main import app
from MakerMatrix.models.part_models import PartModel
from MakerMatrix.models.models import engine
from MakerMatrix.database.db import get_session


class TestPartEmojiPersistence:
    """Test suite for part emoji persistence during creation and updates."""

    API_KEY = os.getenv("MAKERMATRIX_API_KEY", "")  # Set in .env

    @pytest.fixture
    def auth_headers(self):
        """Provide authentication headers for API requests."""
        return {"X-API-Key": self.API_KEY}

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clean up test data before and after each test."""
        # Clean up before test
        with Session(engine) as session:
            # Delete all test parts
            test_parts = session.exec(select(PartModel).where(PartModel.part_number.like("TEST_EMOJI_%"))).all()
            for part in test_parts:
                session.delete(part)
            session.commit()

        yield

        # Clean up after test
        with Session(engine) as session:
            # Delete test parts
            test_parts = session.exec(select(PartModel).where(PartModel.part_number.like("TEST_EMOJI_%"))).all()
            for part in test_parts:
                session.delete(part)
            session.commit()

    def test_part_creation_saves_emoji(self, auth_headers):
        """Test that creating a part with an emoji correctly saves the emoji."""
        with TestClient(app) as client:
            # Step 1: Create a test part with an emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_001",
                    "part_name": "Test Resistor with Emoji",
                    "description": "Test part with emoji",
                    "emoji": "⚡",
                    "quantity": 100,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_data = part_response.json()
            part_id = part_data["data"]["id"]
            created_emoji = part_data["data"]["emoji"]

            assert created_emoji == "⚡", f"Emoji was not saved on creation! Expected '⚡', got '{created_emoji}'"

            print(f"✓ Part created with emoji: {created_emoji}")

            # Step 2: Verify emoji persists in database
            with Session(engine) as session:
                part_from_db = session.get(PartModel, part_id)
                assert part_from_db is not None
                assert part_from_db.emoji == "⚡", f"Emoji not in database! Expected '⚡', got '{part_from_db.emoji}'"

            print("✓ Emoji persisted to database")

    def test_part_update_preserves_emoji(self, auth_headers):
        """Test that updating a part preserves the existing emoji."""
        with TestClient(app) as client:
            # Step 1: Create a test part with an emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_002",
                    "part_name": "Test Capacitor",
                    "description": "Test capacitor with emoji",
                    "emoji": "🔋",
                    "quantity": 50,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]
            original_emoji = part_response.json()["data"]["emoji"]

            assert original_emoji == "🔋"
            print(f"Created part with emoji: {original_emoji}")

            # Step 2: Update only the description (not the emoji)
            update_response = client.put(
                f"/api/parts/update_part/{part_id}",
                json={"description": "Updated description without emoji change"},
                headers=auth_headers,
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the emoji is still present
            assert updated_data["data"]["description"] == "Updated description without emoji change"
            assert (
                updated_data["data"]["emoji"] == original_emoji
            ), f"Emoji was lost! Expected '{original_emoji}', got '{updated_data['data'].get('emoji')}'"

            print(f"✓ Emoji preserved after description update: {updated_data['data']['emoji']}")

    def test_part_emoji_can_be_changed(self, auth_headers):
        """Test that a part's emoji can be explicitly changed."""
        with TestClient(app) as client:
            # Step 1: Create a test part with an emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_003",
                    "part_name": "Test LED",
                    "description": "Test LED part",
                    "emoji": "💡",
                    "quantity": 25,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Step 2: Change the emoji
            update_response = client.put(
                f"/api/parts/update_part/{part_id}", json={"emoji": "🌟"}, headers=auth_headers
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the emoji was changed
            assert (
                updated_data["data"]["emoji"] == "🌟"
            ), f"Emoji was not updated! Expected '🌟', got '{updated_data['data'].get('emoji')}'"

            print("✓ Emoji successfully changed from 💡 to 🌟")

    def test_part_emoji_can_be_cleared(self, auth_headers):
        """Test that explicitly setting emoji to None clears it."""
        with TestClient(app) as client:
            # Step 1: Create a test part with an emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_004",
                    "part_name": "Test Diode",
                    "description": "Test diode part",
                    "emoji": "➡️",
                    "quantity": 75,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Step 2: Explicitly clear the emoji by setting it to null
            update_response = client.put(
                f"/api/parts/update_part/{part_id}", json={"emoji": None}, headers=auth_headers
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Step 3: Verify the emoji was cleared
            assert updated_data["data"]["emoji"] is None, "Emoji should be cleared when explicitly set to None"

            print("✓ Emoji successfully cleared when explicitly set to None")

    def test_part_creation_without_emoji(self, auth_headers):
        """Test that creating a part without an emoji works correctly."""
        with TestClient(app) as client:
            # Step 1: Create a test part without an emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_005",
                    "part_name": "Test IC",
                    "description": "Test IC without emoji",
                    "quantity": 30,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_data = part_response.json()

            # Emoji should be None when not provided
            assert (
                part_data["data"]["emoji"] is None
            ), f"Emoji should be None when not provided, got '{part_data['data'].get('emoji')}'"

            print("✓ Part created successfully without emoji (emoji = None)")

    def test_database_level_emoji_persistence(self, auth_headers):
        """Test emoji persistence at the database level."""
        with TestClient(app) as client:
            # Step 1: Create part with emoji
            part_response = client.post(
                "/api/parts/add_part",
                json={
                    "part_number": "TEST_EMOJI_006",
                    "part_name": "Test Transistor",
                    "description": "DB test part",
                    "emoji": "🔌",
                    "quantity": 200,
                },
                headers=auth_headers,
            )
            assert part_response.status_code == 200
            part_id = part_response.json()["data"]["id"]

            # Step 2: Check database state before update
            with Session(engine) as session:
                part_before = session.get(PartModel, part_id)
                assert part_before.emoji == "🔌"
                assert part_before.part_number == "TEST_EMOJI_006"

            # Step 3: Update part name via API
            update_response = client.put(
                f"/api/parts/update_part/{part_id}", json={"part_name": "Updated Transistor Name"}, headers=auth_headers
            )
            assert update_response.status_code == 200

            # Step 4: Check database state after update
            with Session(engine) as session:
                part_after = session.get(PartModel, part_id)
                assert part_after.part_name == "Updated Transistor Name"
                assert part_after.emoji == "🔌", f"Emoji was lost in database! Expected '🔌', got '{part_after.emoji}'"

            print("✓ Database-level verification passed: emoji preserved")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
