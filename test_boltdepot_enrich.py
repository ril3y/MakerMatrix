#!/usr/bin/env python3
"""Test Bolt Depot enrichment endpoint"""

import requests
import json

# Test URL
url = "https://10.2.0.2:8443/api/parts/enrich-from-supplier"

# Test parameters
params = {
    "supplier_name": "boltdepot",
    "part_identifier": "https://boltdepot.com/Product-Details?product=15294"
}

# Headers (use your JWT token or create one)
headers = {
    "X-API-Key": "mm_Z8p_PgbZzc7bqf0Tp4ROc3uppt-3MVFBXZi10kkzJOk",
    "Content-Type": "application/json"
}

print("Testing Bolt Depot enrichment...")
print(f"URL: {url}")
print(f"Params: {params}")
print()

try:
    response = requests.post(url, params=params, headers=headers, verify=False)
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response text: {e.response.text}")
