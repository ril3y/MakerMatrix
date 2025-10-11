#!/usr/bin/env python
"""
Manual integration test for datasheet download task functionality.
Run this after starting the dev manager to test the full flow.
"""

import asyncio
import aiohttp
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API configuration
API_BASE_URL = "http://localhost:3000/api"
API_KEY = "mm_Z8p_PgbZzc7bqf0Tp4ROc3uppt-3MVFBXZi10kkzJOk"  # Development API key


async def test_datasheet_download_task():
    """Test creating a datasheet download task."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Test data for datasheet download
    task_data = {
        "part_id": "test-part-001",
        "datasheet_url": "https://datasheet.lcsc.com/lcsc/1810231112_UNI-ROYAL-Uniroyal-Elec-0805W8F1001T5E_C17414.pdf",
        "supplier": "LCSC",
        "part_number": "C17414"
    }

    async with aiohttp.ClientSession() as session:
        # Create datasheet download task
        print("\n1. Creating datasheet download task...")
        async with session.post(
            f"{API_BASE_URL}/tasks/quick/datasheet_download",
            json=task_data,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                task_id = result['data']['id']
                print(f"✅ Task created successfully: {task_id}")
                print(f"   Task name: {result['data']['name']}")
                print(f"   Status: {result['data']['status']}")
                return task_id
            else:
                error_text = await response.text()
                print(f"❌ Failed to create task: {response.status}")
                print(f"   Error: {error_text}")
                return None


async def check_task_status(task_id):
    """Check the status of a task."""
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    async with aiohttp.ClientSession() as session:
        print(f"\n2. Checking task status for {task_id}...")

        # Poll task status for up to 30 seconds
        for i in range(30):
            async with session.get(
                f"{API_BASE_URL}/tasks/{task_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    task_data = result['data']

                    print(f"   Status: {task_data['status']}")
                    print(f"   Progress: {task_data['progress_percentage']}%")
                    if task_data.get('current_step'):
                        print(f"   Current step: {task_data['current_step']}")

                    if task_data['status'] in ['completed', 'failed']:
                        print(f"\n✅ Task finished with status: {task_data['status']}")
                        if task_data.get('result_data'):
                            print("   Result data:", json.dumps(task_data['result_data'], indent=2))
                        if task_data.get('error_message'):
                            print("   Error:", task_data['error_message'])
                        return task_data['status']

                    await asyncio.sleep(1)  # Wait 1 second before next check
                else:
                    print(f"❌ Failed to get task status: {response.status}")
                    return None

        print("⏱️ Task did not complete within 30 seconds")
        return None


async def test_enrichment_with_datasheet():
    """Test part enrichment which should trigger datasheet download."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Create enrichment task for a part (this will trigger datasheet download)
    enrichment_data = {
        "part_id": "test-part-002",
        "supplier": "LCSC",
        "capabilities": ["fetch_datasheet", "get_part_details"]
    }

    async with aiohttp.ClientSession() as session:
        print("\n3. Creating part enrichment task (should trigger datasheet download)...")
        async with session.post(
            f"{API_BASE_URL}/tasks/quick/part_enrichment",
            json=enrichment_data,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                task_id = result['data']['id']
                print(f"✅ Enrichment task created: {task_id}")

                # Wait and check for any child tasks
                await asyncio.sleep(2)

                # Get all tasks to see if datasheet download was created
                async with session.get(
                    f"{API_BASE_URL}/tasks/?task_type=datasheet_download&limit=5",
                    headers=headers
                ) as tasks_response:
                    if tasks_response.status == 200:
                        tasks_result = await tasks_response.json()
                        if tasks_result['data']:
                            print("\n   Datasheet download tasks found:")
                            for task in tasks_result['data'][:3]:
                                print(f"   - {task['name']} (Status: {task['status']})")

                return task_id
            else:
                error_text = await response.text()
                print(f"❌ Failed to create enrichment task: {response.status}")
                print(f"   Error: {error_text}")
                return None


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Datasheet Download Task Integration Test")
    print("=" * 60)

    # Test 1: Direct datasheet download task
    print("\n### Test 1: Direct Datasheet Download Task ###")
    task_id = await test_datasheet_download_task()
    if task_id:
        await check_task_status(task_id)

    # Test 2: Enrichment with datasheet (should create child task)
    print("\n### Test 2: Enrichment with Datasheet Download ###")
    enrichment_task_id = await test_enrichment_with_datasheet()
    if enrichment_task_id:
        await check_task_status(enrichment_task_id)

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())