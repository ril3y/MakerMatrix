#!/usr/bin/env python
"""
Simple test to verify location rename doesn't break allocations.
This test creates a part with an allocation, renames the location, and verifies the allocation remains intact.
"""

import requests
import json
import sys

BASE_URL = "https://localhost:8443/api"
USERNAME = "admin"
PASSWORD = "Admin123!"
HEADERS = {"Content-Type": "application/json"}

# Disable SSL warnings for self-signed cert
import urllib3

urllib3.disable_warnings()


def test_location_rename_preserves_allocations():
    """Test that location rename preserves allocations."""
    print("\n=== Testing Location Rename with Allocations ===\n")

    try:
        # Login first
        print("0. Logging in as admin...")
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/json"},
            verify=False,
        )

        # Check if login was successful
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            return False

        login_result = login_response.json()
        if login_result.get("status") != "success":
            print(f"Login failed: {login_result}")
            return False

        # Get the access token
        access_token = login_result["data"]["access_token"]
        HEADERS["Authorization"] = f"Bearer {access_token}"
        print("   Login successful, got access token")
        # Step 1: Create a test location
        print("1. Creating test location...")
        location_data = {"name": "TEST_Storage_Shelf_Original", "description": "Test storage location"}
        response = requests.post(
            f"{BASE_URL}/locations/add_location", headers=HEADERS, json=location_data, verify=False
        )
        response.raise_for_status()
        location_result = response.json()

        if location_result.get("status") != "success":
            print(f"Failed to create location: {location_result}")
            return False

        location_id = location_result["data"]["id"]
        print(f"   Created location with ID: {location_id}")

        # Step 2: Create a test part with allocation
        print("\n2. Creating test part with allocation...")
        part_data = {
            "part_name": "TEST_Resistor_10K",
            "part_number": "TEST_R10K",
            "description": "Test 10K resistor",
            "quantity": 100,
            "location_id": location_id,
        }
        response = requests.post(f"{BASE_URL}/parts/add_part", headers=HEADERS, json=part_data, verify=False)
        response.raise_for_status()
        part_result = response.json()

        if part_result.get("status") != "success":
            print(f"Failed to create part: {part_result}")
            return False

        part_id = part_result["data"]["id"]
        print(f"   Created part with ID: {part_id}")

        # Step 3: Verify allocation exists
        print("\n3. Verifying allocation exists...")
        response = requests.get(f"{BASE_URL}/parts/{part_id}/allocations", headers=HEADERS, verify=False)
        response.raise_for_status()
        alloc_result = response.json()

        if alloc_result.get("status") != "success":
            print(f"Failed to get allocations: {alloc_result}")
            return False

        alloc_data = alloc_result["data"]
        print(f"   Total quantity: {alloc_data['total_quantity']}")
        print(f"   Location count: {alloc_data['location_count']}")
        print(f"   Location name: {alloc_data['allocations'][0]['location']['name']}")

        if alloc_data["allocations"][0]["location"]["name"] != "TEST_Storage_Shelf_Original":
            print("ERROR: Initial location name doesn't match!")
            return False

        # Step 4: Rename the location
        print("\n4. Renaming location...")
        rename_data = {"name": "TEST_Storage_Shelf_RENAMED"}
        response = requests.put(
            f"{BASE_URL}/locations/update_location/{location_id}", headers=HEADERS, json=rename_data, verify=False
        )
        response.raise_for_status()
        rename_result = response.json()

        if rename_result.get("status") != "success":
            print(f"Failed to rename location: {rename_result}")
            return False

        print(f"   Location renamed to: {rename_result['data']['name']}")

        # Step 5: Verify allocations are still intact with new location name
        print("\n5. Verifying allocations after rename...")
        response = requests.get(f"{BASE_URL}/parts/{part_id}/allocations", headers=HEADERS, verify=False)
        response.raise_for_status()
        alloc_after_result = response.json()

        if alloc_after_result.get("status") != "success":
            print(f"Failed to get allocations after rename: {alloc_after_result}")
            return False

        alloc_after_data = alloc_after_result["data"]
        print(f"   Total quantity: {alloc_after_data['total_quantity']}")
        print(f"   Location count: {alloc_after_data['location_count']}")
        print(f"   Location name: {alloc_after_data['allocations'][0]['location']['name']}")
        print(f"   Location ID: {alloc_after_data['allocations'][0]['location_id']}")

        # Verify the results
        success = True
        if alloc_after_data["total_quantity"] != 100:
            print("ERROR: Total quantity changed after rename!")
            success = False

        if alloc_after_data["location_count"] != 1:
            print("ERROR: Location count changed after rename!")
            success = False

        if alloc_after_data["allocations"][0]["location"]["name"] != "TEST_Storage_Shelf_RENAMED":
            print("ERROR: Location name not updated in allocation!")
            success = False

        if alloc_after_data["allocations"][0]["location_id"] != location_id:
            print("ERROR: Location ID changed after rename!")
            success = False

        if alloc_after_data["allocations"][0]["quantity_at_location"] != 100:
            print("ERROR: Quantity at location changed after rename!")
            success = False

        # Step 6: Clean up - delete the test part and location
        print("\n6. Cleaning up test data...")
        # Delete part first (will cascade delete allocations)
        response = requests.delete(f"{BASE_URL}/parts/delete_part?part_id={part_id}", headers=HEADERS, verify=False)
        response.raise_for_status()
        print(f"   Deleted test part")

        # Delete location
        response = requests.delete(f"{BASE_URL}/locations/delete_location/{location_id}", headers=HEADERS, verify=False)
        response.raise_for_status()
        print(f"   Deleted test location")

        if success:
            print("\n✅ TEST PASSED: Location rename preserves allocations correctly!")
        else:
            print("\n❌ TEST FAILED: Location rename broke allocations!")

        return success

    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_location_rename_preserves_allocations()
    sys.exit(0 if success else 1)
