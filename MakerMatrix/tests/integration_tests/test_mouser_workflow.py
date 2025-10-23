"""
Integration test for complete Mouser XLS import and enrichment workflow.

This test requires the backend API to be running and tests:
1. Mouser XLS file import via API
2. Part enrichment task queuing
3. Rate limiting system integration
4. Task management workflow
"""

import pytest
import requests
import time
from pathlib import Path


class TestMouserWorkflow:
    """Test complete Mouser import and enrichment workflow"""

    BASE_URL = "http://localhost:8080"

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for API requests"""
        login_response = requests.post(
            f"{self.BASE_URL}/auth/login", data={"username": "admin", "password": "Admin123!"}, timeout=5
        )

        if login_response.status_code != 200:
            pytest.skip("API server not running or authentication failed")

        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_mouser_xls_file_exists(self):
        """Verify the Mouser XLS test file exists"""
        xls_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")
        assert xls_file.exists(), "Mouser XLS test file should exist"
        assert xls_file.stat().st_size > 0, "XLS file should not be empty"

    def test_api_connection(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.BASE_URL}/utility/get_counts", timeout=5)
            assert response.status_code == 200, "API should be accessible"
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")

    def test_mouser_xls_import(self, auth_headers):
        """Test importing Mouser XLS file via API"""
        xls_file = Path("MakerMatrix/tests/mouser_xls_test/271360826.xls")

        if not xls_file.exists():
            pytest.skip("Mouser XLS test file not found")

        with open(xls_file, "rb") as f:
            files = {"file": (xls_file.name, f, "application/vnd.ms-excel")}
            data = {
                "parser_type": "mouser",
                "order_number": "TEST-271360826",
                "notes": "Automated integration test import",
            }

            response = requests.post(
                f"{self.BASE_URL}/csv/import-file", headers=auth_headers, files=files, data=data, timeout=30
            )

            assert response.status_code == 200, f"Import should succeed: {response.text}"

            result = response.json()
            assert result["status"] == "success"
            assert "data" in result

    def test_enrichment_task_queuing(self, auth_headers):
        """Test queueing parts for enrichment with rate limiting protection"""
        # Get some parts to enrich
        parts_response = requests.get(
            f"{self.BASE_URL}/parts/get_all_parts?page=1&page_size=3", headers=auth_headers, timeout=5
        )

        if parts_response.status_code != 200:
            pytest.skip("Could not get parts for enrichment test")

        parts_data = parts_response.json()
        if not parts_data.get("data") or len(parts_data["data"]) == 0:
            pytest.skip("No parts available for enrichment test")

        # Test enrichment queuing for first part
        part = parts_data["data"][0]
        enrich_request = {
            "part_id": part["id"],
            "supplier": "MOUSER",
            "capabilities": ["fetch_datasheet", "fetch_image"],
        }

        enrich_response = requests.post(
            f"{self.BASE_URL}/tasks/quick/part_enrichment", headers=auth_headers, json=enrich_request, timeout=10
        )

        # Should succeed in queuing the task
        assert enrich_response.status_code == 200, f"Enrichment queuing should succeed: {enrich_response.text}"

        task_result = enrich_response.json()
        assert task_result["status"] == "success"
        assert "data" in task_result

    def test_task_system_status(self, auth_headers):
        """Test task system monitoring and status"""
        tasks_response = requests.get(f"{self.BASE_URL}/tasks/?limit=10", headers=auth_headers, timeout=5)

        assert tasks_response.status_code == 200, "Task system should be accessible"

        tasks_data = tasks_response.json()
        assert tasks_data["status"] == "success"

        # Verify task data structure
        if "data" in tasks_data and len(tasks_data["data"]) > 0:
            task = tasks_data["data"][0]
            assert "id" in task
            assert "status" in task
            assert "task_type" in task

    def test_rate_limiting_configuration(self, auth_headers):
        """Test that rate limiting system is properly configured"""
        # This test would check rate limiting endpoints if they exist
        # For now, we'll just verify the system doesn't crash when queuing multiple tasks

        parts_response = requests.get(
            f"{self.BASE_URL}/parts/get_all_parts?page=1&page_size=2", headers=auth_headers, timeout=5
        )

        if parts_response.status_code == 200:
            parts_data = parts_response.json()
            if parts_data.get("data") and len(parts_data["data"]) > 0:
                # Queue multiple enrichment tasks rapidly to test rate limiting
                for part in parts_data["data"][:2]:
                    enrich_request = {"part_id": part["id"], "supplier": "MOUSER", "capabilities": ["fetch_datasheet"]}

                    # Should not crash, rate limiting should handle this gracefully
                    response = requests.post(
                        f"{self.BASE_URL}/tasks/quick/part_enrichment",
                        headers=auth_headers,
                        json=enrich_request,
                        timeout=10,
                    )

                    # Either succeeds or fails gracefully (no 500 errors)
                    assert response.status_code in [
                        200,
                        201,
                        400,
                        429,
                    ], f"Should handle request gracefully: {response.status_code}"


# Standalone test function for manual execution
if __name__ == "__main__":
    print("🧪 Running Mouser Workflow Integration Tests")
    print("=" * 60)
    print("Note: This requires the backend API to be running on localhost:8080")
    print("Run with: venv_test/bin/python -m pytest -v MakerMatrix/tests/integration_tests/test_mouser_workflow.py")
