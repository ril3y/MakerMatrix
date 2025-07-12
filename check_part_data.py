#!/usr/bin/env python3
"""Check the actual part data after enrichment"""

import requests
import json

def check_part_data():
    base_url = 'https://localhost:8443'
    part_id = 'a5ce956d-bc98-483b-8908-1a89e44bd09e'

    # Login
    login_data = {'username': 'admin', 'password': 'Admin123!'}
    response = requests.post(
        f'{base_url}/api/auth/login', 
        data=login_data, 
        headers={'Content-Type': 'application/x-www-form-urlencoded'}, 
        verify=False
    )
    
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} - {response.text}")
        return
    
    data = response.json()
    if 'access_token' not in data:
        print(f"No access token in response: {data}")
        return
        
    token = data['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Get part data
    response = requests.get(f'{base_url}/api/parts/get_part?part_id={part_id}', headers=headers, verify=False)
    if response.status_code != 200:
        print(f"Failed to get part: {response.status_code} - {response.text}")
        return
        
    part_data = response.json()['data']

    print('🔍 Part Data Analysis:')
    print('=' * 50)
    print(f'Part image_url (main field): {part_data.get("image_url")}')
    print(f'Part manufacturer: {part_data.get("manufacturer")}')
    print(f'Part description: {part_data.get("description")}')
    print('')

    additional_props = part_data.get('additional_properties', {})
    print(f'Additional properties: {bool(additional_props)}')
    
    if additional_props:
        print(f'Additional properties keys: {list(additional_props.keys())}')
        print(f'Last enrichment: {additional_props.get("last_enrichment")}')
        
        # Check for image_url in additional_properties
        if 'image_url' in additional_props:
            print(f'Image URL in additional_properties: {additional_props.get("image_url")}')
        
        # Check for supplier data
        supplier_data = additional_props.get('supplier_data', {})
        if supplier_data:
            print(f'Supplier data keys: {list(supplier_data.keys())}')
            lcsc_data = supplier_data.get('lcsc', {})
            if lcsc_data:
                print(f'LCSC data keys: {list(lcsc_data.keys())}')
                print(f'LCSC image URL: {lcsc_data.get("image_url")}')
                print(f'LCSC manufacturer: {lcsc_data.get("manufacturer")}')
                
        # Look for any field containing 'image'
        for key, value in additional_props.items():
            if 'image' in key.lower():
                print(f'Found image field "{key}": {value}')
                
        # Print first few characters of additional_properties for debugging
        props_str = str(additional_props)
        if len(props_str) > 500:
            print(f'Additional properties (truncated): {props_str[:500]}...')
        else:
            print(f'Additional properties (full): {props_str}')

if __name__ == "__main__":
    check_part_data()