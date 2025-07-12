#!/usr/bin/env python3
"""
Direct LCSC API Test
Test the EasyEDA API directly with the specific part that's failing
"""

import asyncio
import aiohttp
import json

async def test_lcsc_api_direct():
    """Test LCSC API directly"""
    part_number = "C5160761"  # Your specific part
    version = "6.4.19.5"
    url = f"https://easyeda.com/api/products/{part_number}/components?version={version}"
    
    print(f"🔍 Testing LCSC API for part: {part_number}")
    print(f"📍 URL: {url}")
    print("=" * 60)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"📊 Status Code: {response.status}")
                print(f"📊 Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"✅ Response received!")
                        print(f"📄 Data Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                        
                        if isinstance(data, dict):
                            # Check for result data
                            result = data.get("result")
                            if result:
                                print(f"✅ Result found with {len(result)} items")
                                
                                # Look for the specific part
                                found_target = False
                                for i, item in enumerate(result):
                                    if isinstance(item, dict):
                                        lcsc_id = item.get('lcsc_id', '')
                                        if lcsc_id == part_number:  # Match our target part
                                            found_target = True
                                            print(f"\n🎯 TARGET PART FOUND - Item {i+1}:")
                                        else:
                                            print(f"\n📦 Item {i+1}:")
                                        
                                        print(f"   LCSC: {item.get('lcsc_id', 'N/A')}")
                                        print(f"   Title: {item.get('title', 'N/A')}")
                                        print(f"   MPN: {item.get('mpn', 'N/A')}")
                                        print(f"   Manufacturer: {item.get('manufacturer', 'N/A')}")
                                        print(f"   Datasheet: {item.get('datasheet_pdf', 'N/A')}")
                                        print(f"   Image: {item.get('cover_image', 'N/A')}")
                                        print(f"   Price: {item.get('price', 'N/A')}")
                                        print(f"   Stock: {item.get('number_stock', 'N/A')}")
                                        
                                        if found_target:
                                            # Show more details for target part
                                            print(f"   Description: {item.get('description', 'N/A')}")
                                            print(f"   Package: {item.get('package', 'N/A')}")
                                            print(f"   All Keys: {list(item.keys())}")
                                            break
                                
                                if not found_target:
                                    print(f"\n⚠️ Target part {part_number} not found in results")
                                    lcsc_ids = [item.get('lcsc_id') for item in result if isinstance(item, dict)]
                                    print("Available LCSC IDs:", lcsc_ids)
                                    
                                    # Debug: Show structure
                                    print(f"\n🔍 Debug - Result type: {type(result)}")
                                    if isinstance(result, list):
                                        print(f"🔍 Debug - First 3 items structure:")
                                        for i, item in enumerate(result[:3]):
                                            if isinstance(item, dict):
                                                print(f"Item {i+1} keys: {list(item.keys())}")
                                                print(f"Item {i+1} sample: {str(item)[:200]}...")
                                            else:
                                                print(f"Item {i+1} type: {type(item)}, value: {str(item)[:100]}...")
                                    elif isinstance(result, dict):
                                        print(f"🔍 Debug - Dict keys: {list(result.keys())}")
                                        print(f"🔍 Debug - Sample: {str(result)[:300]}...")
                                    else:
                                        print(f"🔍 Debug - Type: {type(result)}, Value: {str(result)[:200]}...")
                            else:
                                print("❌ No 'result' key found in response")
                                print(f"📄 Full response: {json.dumps(data, indent=2)[:500]}...")
                        else:
                            print(f"⚠️ Response is not a dict: {type(data)}")
                            print(f"📄 Response: {str(data)[:200]}...")
                    
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON decode error: {e}")
                        text = await response.text()
                        print(f"📄 Raw response: {text[:200]}...")
                else:
                    print(f"❌ HTTP Error: {response.status}")
                    text = await response.text()
                    print(f"📄 Error response: {text[:200]}...")
                    
    except Exception as e:
        print(f"💥 Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_lcsc_api_direct())