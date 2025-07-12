#!/usr/bin/env python3
"""
Test the LCSC enrichment fix
"""

import requests
import json
import time

def test_enrichment_fix():
    # Use your existing part
    part_id = "a5ce956d-bc98-483b-8908-1a89e44bd09e"
    
    base_url = "https://localhost:8443"
    
    # Login
    login_data = {"username": "admin", "password": "Admin123!"}
    response = requests.post(
        f"{base_url}/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=False
    )
    
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("✅ Login successful")
    
    # Create enrichment task
    enrichment_data = {
        "part_id": part_id,
        "supplier": "LCSC", 
        "capabilities": ["get_part_details", "fetch_datasheet"]  # Test both capabilities now
    }
    
    response = requests.post(
        f"{base_url}/api/tasks/quick/part_enrichment",
        json=enrichment_data,
        headers=headers,
        verify=False
    )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Task creation failed: {response.status_code}")
        return
    
    task_data = response.json()["data"]
    task_id = task_data["id"]
    print(f"✅ Enrichment task created: {task_id}")
    
    # Monitor task
    for _ in range(30):  # 60 seconds max
        response = requests.get(
            f"{base_url}/api/tasks/{task_id}",
            headers=headers,
            verify=False
        )
        
        if response.status_code == 200:
            task_data = response.json()["data"]
            status = task_data["status"]
            progress = task_data.get("progress_percentage", 0)
            step = task_data.get("current_step", "")
            error = task_data.get("error_message", "")
            
            print(f"📊 Status: {status}, Progress: {progress}%, Step: {step}")
            
            if error:
                print(f"❌ Error: {error}")
                return False
                
            if status == "completed":
                print("🎉 SUCCESS: Task completed!")
                
                # Check the part data now
                part_response = requests.get(
                    f"{base_url}/api/parts/get_part?part_id={part_id}",
                    headers=headers,
                    verify=False
                )
                
                if part_response.status_code == 200:
                    part_data = part_response.json()["data"]
                    print(f"📄 Image URL: {part_data.get('image_url', 'N/A')}")
                    print(f"📄 Manufacturer: {part_data.get('manufacturer', 'N/A')}")
                    print(f"📄 Description: {part_data.get('description', 'N/A')}")
                    
                    # Check additional properties for enrichment data
                    additional = part_data.get('additional_properties', {})
                    print(f"📄 Last enrichment: {additional.get('last_enrichment', 'N/A')}")
                    print(f"📄 Has datasheet: {additional.get('has_datasheet', False)}")
                    print(f"📄 Has image: {additional.get('has_image', False)}")
                
                return True
                
            elif status == "failed":
                print(f"❌ Task failed: {error}")
                return False
        
        time.sleep(2)
    
    print("⏱️ Timeout")
    return False

if __name__ == "__main__":
    success = test_enrichment_fix()
    print("=" * 50)
    if success:
        print("🎉 LCSC Enrichment Fix: SUCCESS!")
    else:
        print("💥 LCSC Enrichment Fix: FAILED")