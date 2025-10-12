#!/usr/bin/env python3
"""
Script to investigate and test the location rename issue with allocations.

This script tests whether renaming a location breaks part-location allocations.
"""

import requests
import json
from typing import Dict, Any

# Configuration
API_BASE = "https://localhost:8443/api"
API_KEY = "REDACTED_API_KEY"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Disable SSL warnings for localhost
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def make_request(method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict:
    """Make an API request with error handling."""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS, verify=False)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data, verify=False)
        elif method == "PUT":
            response = requests.put(url, headers=HEADERS, json=data, verify=False)
        elif method == "DELETE":
            response = requests.delete(url, headers=HEADERS, verify=False)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        raise


def cleanup_test_data():
    """Clean up any existing test data."""
    print("Cleaning up existing test data...")

    # Get all locations and delete test ones
    locations = make_request("GET", "/locations/get_all_locations")
    for loc in locations.get("data", []):
        if loc["name"].startswith("TEST_RENAME_"):
            try:
                make_request("DELETE", f"/locations/delete_location/{loc['id']}")
                print(f"  Deleted location: {loc['name']}")
            except:
                pass

    # Get all parts and delete test ones
    parts = make_request("GET", "/parts/get_all_parts")
    for part in parts.get("data", []):
        if part["part_name"].startswith("TEST_RENAME_"):
            try:
                make_request("DELETE", f"/parts/delete_part/{part['id']}")
                print(f"  Deleted part: {part['part_name']}")
            except:
                pass


def test_location_rename_preserves_allocations():
    """Main test function."""
    print("\n" + "="*60)
    print("TEST: Location Rename Should Preserve Allocations")
    print("="*60)

    try:
        # Step 1: Create a test location
        print("\n1. Creating test location...")
        location_data = {
            "name": "TEST_RENAME_Storage_A",
            "description": "Test storage location for rename testing",
            "location_type": "storage"
        }
        location_response = make_request("POST", "/locations/add_location", location_data)
        location = location_response["data"]
        location_id = location["id"]
        print(f"   Created location: {location['name']} (ID: {location_id})")

        # Step 2: Create a test part with initial allocation
        print("\n2. Creating test part with allocation to location...")
        part_data = {
            "part_name": "TEST_RENAME_Resistor_10K",
            "part_number": "TEST_R10K",
            "description": "Test 10K resistor for rename testing",
            "manufacturer": "TestCorp",
            "quantity": 100,
            "location_id": location_id
        }
        part_response = make_request("POST", "/parts/add_part", part_data)
        part = part_response["data"]
        part_id = part["id"]
        print(f"   Created part: {part['part_name']} (ID: {part_id})")
        print(f"   Initial quantity: {part['quantity']} at location: {location['name']}")

        # Step 3: Verify the allocation exists
        print("\n3. Verifying allocation exists...")
        allocations_response = make_request("GET", f"/parts/{part_id}/allocations")
        allocations_data = allocations_response["data"]
        print(f"   Total quantity: {allocations_data['total_quantity']}")
        print(f"   Location count: {allocations_data['location_count']}")

        if allocations_data['allocations']:
            alloc = allocations_data['allocations'][0]
            print(f"   Allocation details:")
            print(f"     - Location ID: {alloc['location_id']}")
            print(f"     - Location Name: {alloc['location']['name']}")
            print(f"     - Quantity: {alloc['quantity_at_location']}")
            print(f"     - Is Primary: {alloc['is_primary_storage']}")

            # Store original values for comparison
            original_alloc_id = alloc['id']
            original_location_id = alloc['location_id']
            original_quantity = alloc['quantity_at_location']
        else:
            print("   ERROR: No allocations found!")
            return False

        # Step 4: Rename the location
        print("\n4. Renaming the location...")
        rename_data = {
            "name": "TEST_RENAME_Distribution_Center_B"
        }
        rename_response = make_request("PUT", f"/locations/update_location/{location_id}", rename_data)
        renamed_location = rename_response["data"]
        print(f"   Location renamed from '{location['name']}' to '{renamed_location['name']}'")
        print(f"   Location ID remained: {renamed_location['id']}")

        # Step 5: Verify allocations are preserved
        print("\n5. Checking if allocations are preserved after rename...")
        allocations_after_response = make_request("GET", f"/parts/{part_id}/allocations")
        allocations_after = allocations_after_response["data"]

        print(f"   Total quantity after rename: {allocations_after['total_quantity']}")
        print(f"   Location count after rename: {allocations_after['location_count']}")

        if allocations_after['allocations']:
            alloc_after = allocations_after['allocations'][0]
            print(f"   Allocation details after rename:")
            print(f"     - Allocation ID: {alloc_after['id']}")
            print(f"     - Location ID: {alloc_after['location_id']}")
            print(f"     - Location Name: {alloc_after['location']['name']}")
            print(f"     - Quantity: {alloc_after['quantity_at_location']}")
            print(f"     - Is Primary: {alloc_after['is_primary_storage']}")

            # Verify everything is preserved
            success = True
            print("\n6. Verification Results:")

            if alloc_after['id'] == original_alloc_id:
                print("   ✓ Allocation ID preserved")
            else:
                print(f"   ✗ Allocation ID changed: {original_alloc_id} → {alloc_after['id']}")
                success = False

            if alloc_after['location_id'] == original_location_id:
                print("   ✓ Location ID reference preserved")
            else:
                print(f"   ✗ Location ID changed: {original_location_id} → {alloc_after['location_id']}")
                success = False

            if alloc_after['quantity_at_location'] == original_quantity:
                print("   ✓ Quantity preserved")
            else:
                print(f"   ✗ Quantity changed: {original_quantity} → {alloc_after['quantity_at_location']}")
                success = False

            if alloc_after['location']['name'] == renamed_location['name']:
                print("   ✓ Location name updated correctly in allocation")
            else:
                print(f"   ✗ Location name mismatch: expected '{renamed_location['name']}', got '{alloc_after['location']['name']}'")
                success = False

            # Check part's location reference
            print("\n7. Checking part's location reference...")
            part_after_response = make_request("GET", f"/parts/get_part?part_id={part_id}")
            part_after = part_after_response["data"]

            if part_after.get('location_id') == original_location_id:
                print(f"   ✓ Part's location_id preserved: {part_after['location_id']}")
            else:
                print(f"   ✗ Part's location_id changed or lost: {part_after.get('location_id')}")
                success = False

            if part_after.get('location', {}).get('name') == renamed_location['name']:
                print(f"   ✓ Part shows correct location name: {part_after['location']['name']}")
            else:
                print(f"   ✗ Part shows incorrect location: {part_after.get('location', {}).get('name')}")
                success = False

            return success
        else:
            print("   ERROR: No allocations found after rename!")
            print("   THIS IS THE BUG: Allocations were lost when location was renamed!")
            return False

    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        return False
    finally:
        # Clean up
        print("\n8. Cleaning up test data...")
        cleanup_test_data()


def test_multiple_allocations():
    """Test with multiple allocations to ensure all are preserved."""
    print("\n" + "="*60)
    print("TEST: Multiple Allocations After Location Rename")
    print("="*60)

    try:
        # Create multiple locations
        print("\n1. Creating multiple test locations...")
        locations = []
        for i in range(3):
            loc_data = {
                "name": f"TEST_RENAME_Location_{i}",
                "description": f"Test location {i}",
                "location_type": "storage"
            }
            loc_response = make_request("POST", "/locations/add_location", loc_data)
            locations.append(loc_response["data"])
            print(f"   Created location: {loc_response['data']['name']}")

        # Create a part with initial allocation
        print("\n2. Creating part with initial allocation...")
        part_data = {
            "part_name": "TEST_RENAME_MultiAlloc_Part",
            "part_number": "TEST_MAP",
            "description": "Part with multiple allocations",
            "manufacturer": "TestCorp",
            "quantity": 300,
            "location_id": locations[0]["id"]
        }
        part_response = make_request("POST", "/parts/add_part", part_data)
        part_id = part_response["data"]["id"]
        print(f"   Created part with 300 units at {locations[0]['name']}")

        # Transfer to create multiple allocations
        print("\n3. Creating multiple allocations via transfers...")
        transfer1 = make_request("POST", f"/parts/{part_id}/transfer?from_location_id={locations[0]['id']}&to_location_id={locations[1]['id']}&quantity=100")
        print(f"   Transferred 100 units to {locations[1]['name']}")

        transfer2 = make_request("POST", f"/parts/{part_id}/transfer?from_location_id={locations[0]['id']}&to_location_id={locations[2]['id']}&quantity=50")
        print(f"   Transferred 50 units to {locations[2]['name']}")

        # Verify allocations before rename
        print("\n4. Checking allocations before rename...")
        allocations_before = make_request("GET", f"/parts/{part_id}/allocations")["data"]
        print(f"   Total quantity: {allocations_before['total_quantity']}")
        print(f"   Locations: {allocations_before['location_count']}")
        for alloc in allocations_before['allocations']:
            print(f"     - {alloc['location']['name']}: {alloc['quantity_at_location']} units")

        # Rename all locations
        print("\n5. Renaming all locations...")
        for i, loc in enumerate(locations):
            rename_data = {"name": f"TEST_RENAME_NewName_{i}"}
            make_request("PUT", f"/locations/update_location/{loc['id']}", rename_data)
            print(f"   Renamed {loc['name']} to TEST_RENAME_NewName_{i}")

        # Verify allocations after rename
        print("\n6. Checking allocations after rename...")
        allocations_after = make_request("GET", f"/parts/{part_id}/allocations")["data"]
        print(f"   Total quantity: {allocations_after['total_quantity']}")
        print(f"   Locations: {allocations_after['location_count']}")

        success = True
        expected_quantities = {
            "TEST_RENAME_NewName_0": 150,  # 300 - 100 - 50
            "TEST_RENAME_NewName_1": 100,
            "TEST_RENAME_NewName_2": 50
        }

        for alloc in allocations_after['allocations']:
            loc_name = alloc['location']['name']
            quantity = alloc['quantity_at_location']
            print(f"     - {loc_name}: {quantity} units")

            if loc_name in expected_quantities:
                if quantity == expected_quantities[loc_name]:
                    print(f"       ✓ Correct quantity")
                else:
                    print(f"       ✗ Wrong quantity! Expected {expected_quantities[loc_name]}")
                    success = False
            else:
                print(f"       ✗ Unexpected location name!")
                success = False

        if allocations_after['total_quantity'] == 300:
            print(f"   ✓ Total quantity preserved: 300")
        else:
            print(f"   ✗ Total quantity changed: {allocations_after['total_quantity']}")
            success = False

        if allocations_after['location_count'] == 3:
            print(f"   ✓ All 3 allocations preserved")
        else:
            print(f"   ✗ Location count changed: {allocations_after['location_count']}")
            success = False

        return success

    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        return False
    finally:
        # Clean up
        print("\n7. Cleaning up test data...")
        cleanup_test_data()


if __name__ == "__main__":
    print("="*60)
    print("Location Rename Issue Investigation")
    print("="*60)

    # Run tests
    test1_passed = test_location_rename_preserves_allocations()
    test2_passed = test_multiple_allocations()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    if test1_passed:
        print("✓ Single allocation test: PASSED")
    else:
        print("✗ Single allocation test: FAILED")

    if test2_passed:
        print("✓ Multiple allocations test: PASSED")
    else:
        print("✗ Multiple allocations test: FAILED")

    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED - No bug found with location rename!")
        print("Allocations are correctly preserved when locations are renamed.")
    else:
        print("\n⚠️ BUG CONFIRMED - Location rename breaks allocations!")
        print("This needs to be fixed in the backend code.")