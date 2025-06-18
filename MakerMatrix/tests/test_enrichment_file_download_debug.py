#!/usr/bin/env python3
"""
Debug script to test file download configuration during enrichment.
This will help identify why files are not being downloaded.
"""

import asyncio
import json
import logging
from sqlmodel import Session
from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.csv_import_config_model import CSVImportConfigModel
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService
from MakerMatrix.database.db import get_session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_download_config():
    """Test the current download configuration"""
    
    # Check current CSV import configuration
    print("\n=== Checking CSV Import Configuration ===")
    try:
        session = next(get_session())
        try:
            from sqlmodel import select
            config = session.exec(select(CSVImportConfigModel).where(CSVImportConfigModel.id == "default")).first()
            if config:
                print(f"✅ Found CSV import config:")
                print(f"   download_datasheets: {config.download_datasheets}")
                print(f"   download_images: {config.download_images}")
                print(f"   overwrite_existing_files: {config.overwrite_existing_files}")
                print(f"   download_timeout_seconds: {config.download_timeout_seconds}")
            else:
                print("❌ No CSV import config found in database")
                
                # Create default config
                print("Creating default CSV import config...")
                default_config = CSVImportConfigModel(
                    id="default",
                    download_datasheets=True,
                    download_images=True,
                    overwrite_existing_files=False,
                    download_timeout_seconds=30
                )
                session.add(default_config)
                session.commit()
                print("✅ Created default CSV import config")
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Error checking CSV import config: {e}")
    
    # Test enrichment handler configuration
    print("\n=== Testing Enrichment Handler Configuration ===")
    try:
        part_repo = PartRepository(engine)
        part_service = PartService()
        handler = EnrichmentTaskHandlers(part_repo, part_service)
        
        print("✅ Created enrichment handler")
        print(f"   Download config: {handler.download_config}")
        print(f"   download_datasheets: {handler.download_config.get('download_datasheets', 'Not set')}")
        print(f"   download_images: {handler.download_config.get('download_images', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Error creating enrichment handler: {e}")
    
    # Test with a part that has enrichment data
    print("\n=== Testing with Existing Part ===")
    try:
        with Session(engine) as session:
            # Find a part that has enrichment results
            from sqlmodel import select, text
            
            # Query for parts with enrichment data
            query = text("""
                SELECT * FROM partmodel 
                WHERE additional_properties LIKE '%enrichment_results%' 
                LIMIT 1
            """)
            result = session.exec(query).first()
            
            if result:
                print(f"✅ Found part with enrichment data: {result.part_name}")
                
                # Check if files were downloaded
                additional_props = result.additional_properties
                print(f"   additional_properties type: {type(additional_props)}")
                
                if isinstance(additional_props, str):
                    # If it's stored as JSON string, parse it
                    import json
                    try:
                        additional_props = json.loads(additional_props)
                    except:
                        print(f"   Failed to parse additional_properties as JSON: {additional_props[:200]}...")
                        additional_props = {}
                elif additional_props is None:
                    additional_props = {}
                
                datasheet_downloaded = additional_props.get('datasheet_downloaded', False)
                image_downloaded = additional_props.get('image_downloaded', False)
                datasheet_url = additional_props.get('datasheet_url')
                
                print(f"   Datasheet URL: {datasheet_url}")
                print(f"   Datasheet downloaded: {datasheet_downloaded}")
                print(f"   Image downloaded: {image_downloaded}")
                
                if datasheet_url and not datasheet_downloaded:
                    print("❌ Datasheet URL exists but file was not downloaded!")
                    print("   This indicates the download functionality is not working")
                
                # Show enrichment results keys
                enrichment_results = additional_props.get('enrichment_results', {})
                if enrichment_results:
                    print(f"   Enrichment results keys: {list(enrichment_results.keys())}")
                    
                    # Check if enrichment has datasheet info
                    if 'fetch_datasheet' in enrichment_results:
                        datasheet_result = enrichment_results['fetch_datasheet']
                        print(f"   Datasheet enrichment success: {datasheet_result.get('success', False)}")
                        print(f"   Datasheet URL from enrichment: {datasheet_result.get('datasheet_url')}")
                else:
                    print("   No enrichment_results found")
                
            else:
                print("❌ No parts with enrichment data found")
                
    except Exception as e:
        print(f"❌ Error checking existing parts: {e}")

if __name__ == "__main__":
    asyncio.run(test_download_config())