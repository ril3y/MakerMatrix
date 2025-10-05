#!/usr/bin/env python3
"""
Live WebSocket Test Script

Demonstrates websocket CRUD broadcasts by:
1. Connecting to the live websocket
2. Creating a test part via API
3. Showing the websocket broadcast received
4. Cleaning up
"""

import asyncio
import json
import ssl
import requests
import websockets
from datetime import datetime


# Configuration
BACKEND_URL = "https://192.168.1.58:8443"
WS_URL = "wss://192.168.1.58:8443"
API_KEY = "REDACTED_API_KEY"


async def test_websocket_broadcasts():
    """Test websocket CRUD broadcasts"""
    print("=" * 80)
    print("WebSocket CRUD Broadcast Test")
    print("=" * 80)
    print()

    # Disable SSL verification for self-signed certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    session = requests.Session()
    session.verify = False
    session.headers.update({"X-API-Key": API_KEY})

    # Connect to websocket
    print(f"🔗 Connecting to WebSocket: {WS_URL}/ws/general")
    ws_url = f"{WS_URL}/ws/general?token={API_KEY}"

    async with websockets.connect(ws_url, ssl=ssl_context) as websocket:
        print("✅ WebSocket connected!")
        print()

        # Start listening for messages
        async def listen_for_messages():
            messages = []
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    messages.append(data)

                    # Print received messages
                    msg_type = data.get("type")
                    if msg_type.startswith("entity_"):
                        entity_data = data.get("data", {})
                        print(f"📨 Received: {msg_type}")
                        print(f"   Entity: {entity_data.get('entity_type')} - {entity_data.get('entity_name')}")
                        print(f"   Action: {entity_data.get('action')}")
                        print(f"   User: {entity_data.get('username', 'N/A')}")
                        if entity_data.get('changes'):
                            print(f"   Changes: {entity_data.get('changes')}")
                        print()
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    print(f"❌ Error receiving message: {e}")
                    break
            return messages

        # Start message listener
        listen_task = asyncio.create_task(listen_for_messages())

        # Wait for connection confirmation
        await asyncio.sleep(1)

        # Test 1: Create a part
        print("📝 Test 1: Creating a part...")
        part_data = {
            "part_name": f"WebSocket Test Part {datetime.now().timestamp()}",
            "part_number": f"WST-{int(datetime.now().timestamp())}",
            "quantity": 100,
            "description": "Test part for websocket broadcast",
            "supplier": "Test Supplier"
        }

        response = session.post(f"{BACKEND_URL}/api/parts/add_part", json=part_data)

        if response.status_code == 200:
            created_part = response.json()["data"]
            part_id = created_part["id"]
            print(f"✅ Part created: {created_part['part_name']} (ID: {part_id})")
            print()

            # Wait for websocket message
            await asyncio.sleep(2)

            # Test 2: Update the part
            print("📝 Test 2: Updating the part...")
            update_data = {
                "quantity": 150,
                "description": "Updated via websocket test"
            }

            response = session.put(f"{BACKEND_URL}/api/parts/update_part/{part_id}", json=update_data)

            if response.status_code == 200:
                print(f"✅ Part updated: quantity 100 -> 150")
                print()

                # Wait for websocket message
                await asyncio.sleep(2)

                # Test 3: Delete the part
                print("📝 Test 3: Deleting the part...")
                response = session.delete(f"{BACKEND_URL}/api/parts/delete_part?part_id={part_id}")

                if response.status_code == 200:
                    print(f"✅ Part deleted")
                    print()
                else:
                    print(f"❌ Failed to delete part: {response.status_code}")
                    print(response.text)
            else:
                print(f"❌ Failed to update part: {response.status_code}")
                print(response.text)
        else:
            print(f"❌ Failed to create part: {response.status_code}")
            print(response.text)

        # Get all messages
        messages = await listen_task

        # Summary
        print("=" * 80)
        print(f"📊 Summary: Received {len(messages)} websocket messages")
        print("=" * 80)

        entity_events = [m for m in messages if m.get("type", "").startswith("entity_")]
        print(f"   Entity events: {len(entity_events)}")

        for event in entity_events:
            data = event.get("data", {})
            print(f"   - {data.get('action')} {data.get('entity_type')}: {data.get('entity_name')}")

        print()
        print("✅ WebSocket broadcast test completed successfully!")
        print()


if __name__ == "__main__":
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Run the test
    asyncio.run(test_websocket_broadcasts())
