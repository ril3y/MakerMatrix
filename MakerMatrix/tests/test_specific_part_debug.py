#!/usr/bin/env python3
"""
Debug script to check the specific part CL21A475KAQNNNE mentioned by the user.
"""

import asyncio
import json
from sqlmodel import Session, select
from MakerMatrix.models.models import PartModel, engine

async def check_specific_part():
    """Check the specific part mentioned by the user"""
    
    print("=== Checking Specific Part: CL21A475KAQNNNE ===")
    
    with Session(engine) as session:
        # Look for the specific part
        part = session.exec(
            select(PartModel).where(PartModel.part_number == "CL21A475KAQNNNE")
        ).first()
        
        if not part:
            print("❌ Part CL21A475KAQNNNE not found")
            
            # Try searching by part name
            part = session.exec(
                select(PartModel).where(PartModel.part_name == "CL21A475KAQNNNE")
            ).first()
            
            if part:
                print("✅ Found part by part_name")
            else:
                print("❌ Part not found by part_name either")
                return
        else:
            print("✅ Found part by part_number")
        
        print(f"Part ID: {part.id}")
        print(f"Part Name: {part.part_name}")
        print(f"Part Number: {part.part_number}")
        print(f"Supplier: {part.supplier}")
        
        # Parse additional properties
        additional_props = part.additional_properties
        if isinstance(additional_props, str):
            additional_props = json.loads(additional_props)
        elif additional_props is None:
            additional_props = {}
        
        print(f"\n=== Download Status ===")
        print(f"Datasheet downloaded: {additional_props.get('datasheet_downloaded', 'Not set')}")
        print(f"Image downloaded: {additional_props.get('image_downloaded', 'Not set')}")
        print(f"Datasheet URL: {additional_props.get('datasheet_url', 'Not set')}")
        print(f"Image URL: {part.image_url}")
        
        # Check enrichment results
        enrichment_results = additional_props.get('enrichment_results', {})
        if enrichment_results:
            print(f"\n=== Enrichment Results ===")
            for capability, result in enrichment_results.items():
                if isinstance(result, dict):
                    print(f"{capability}:")
                    print(f"  Success: {result.get('success', False)}")
                    if capability == 'fetch_datasheet':
                        print(f"  Datasheet URL: {result.get('datasheet_url')}")
                        print(f"  Download verified: {result.get('download_verified', 'Not set')}")
                        print(f"  Datasheet filename: {result.get('datasheet_filename', 'Not set')}")
                    elif capability == 'fetch_image':
                        print(f"  Primary image URL: {result.get('primary_image_url')}")
                        images = result.get('images', [])
                        if images:
                            print(f"  Number of images: {len(images)}")
        else:
            print("❌ No enrichment results found")
        
        # Check if local files exist
        print(f"\n=== Local File Status ===")
        datasheet_filename = additional_props.get('datasheet_filename')
        image_filename = additional_props.get('image_filename')
        
        if datasheet_filename:
            import os
            datasheet_path = f"static/datasheets/{datasheet_filename}"
            if os.path.exists(datasheet_path):
                print(f"✅ Datasheet file exists: {datasheet_path}")
            else:
                print(f"❌ Datasheet file missing: {datasheet_path}")
        else:
            print("❌ No datasheet filename recorded")
        
        if image_filename:
            image_path = f"static/images/{image_filename}"
            if os.path.exists(image_path):
                print(f"✅ Image file exists: {image_path}")
            else:
                print(f"❌ Image file missing: {image_path}")
        else:
            print("❌ No image filename recorded")

if __name__ == "__main__":
    asyncio.run(check_specific_part())