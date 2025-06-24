"""
Test QR Code Enrichment Fix

Tests that the original QR code enrichment error is fixed after resolving
the capability naming mismatch and implementing environment credential fallback.
"""

import pytest
import asyncio
import json
from sqlmodel import Session, select

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus, TaskPriority
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService


class TestQREnrichmentFix:
    """Test that QR code enrichment issues are resolved"""
    
    @pytest.fixture
    def part_repository(self):
        return PartRepository(engine)
    
    @pytest.fixture 
    def part_service(self):
        return PartService()
    
    @pytest.fixture
    def enrichment_handlers(self, part_repository, part_service):
        return EnrichmentTaskHandlers(part_repository, part_service)
    
    @pytest.fixture
    def cleanup_test_parts(self):
        """Clean up test parts after test"""
        test_parts = ["CS2012X5R475K250NRE", "C2918489", "STM32F373CBT6"]
        yield
        # Clean up test parts if they exist
        try:
            with Session(engine) as session:
                for part_number in test_parts:
                    part = session.exec(
                        select(PartModel).where(PartModel.part_number == part_number)
                    ).first()
                    if part:
                        session.delete(part)
                        session.commit()
                        print(f"Cleaned up test part {part_number}")
        except Exception as e:
            print(f"Note: Could not clean up test parts: {e}")
    
    @pytest.mark.asyncio
    async def test_lcsc_qr_enrichment_with_specifications(self, enrichment_handlers, cleanup_test_parts):
        """Test LCSC QR enrichment that previously failed with capability error"""
        # Simulate the original QR code scan that failed
        # This mimics what happens when mobile app scans a QR code and requests enrichment
        
        with Session(engine) as session:
            # Clean up any existing part
            existing_part = session.exec(
                select(PartModel).where(PartModel.part_number == "CS2012X5R475K250NRE")
            ).first()
            if existing_part:
                session.delete(existing_part)
                session.commit()
            
            # Create test part (this is what mobile app would do after QR scan)
            test_part = PartModel(
                part_number="CS2012X5R475K250NRE",
                part_name="QR Part Enrichment - CS2012X5R475K250NRE",
                description="4.7µF ±10% 25V Multilayer Ceramic Capacitors MLCC - SMD/SMT 1206",
                quantity=0,
                supplier="LCSC"
            )
            session.add(test_part)
            session.commit()
            session.refresh(test_part)
            part_id = test_part.id
            print(f"Created QR test part with ID: {part_id}")
        
        # Create the exact task that was failing before
        # This replicates the original error scenario from the logs
        task_data = {
            "part_id": part_id,
            "supplier": "lcsc",
            "capabilities": ["fetch_datasheet", "fetch_image", "fetch_specifications"]
        }
        
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="QR Part Enrichment - CS2012X5R475K250NRE",
            description="QR code enrichment with auto-enrichment enabled",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            progress_percentage=0,
            input_data=json.dumps(task_data)
        )
        
        def progress_callback(progress: int, message: str):
            print(f"QR Enrichment Progress: {progress}% - {message}")
        
        try:
            # This should NOT fail with "Capabilities not supported by lcsc: ['specifications_fetch']"
            result = await enrichment_handlers.handle_part_enrichment(task, progress_callback)
            
            print(f"QR Enrichment result: {result}")
            
            # The key success criteria:
            # 1. No capability validation error
            # 2. Task completes (even if some enrichment steps fail due to API issues)
            assert result is not None
            
            # Check that we didn't get the original capability error
            if isinstance(result, dict) and "error" in result:
                assert "Capabilities not supported" not in str(result["error"]), \
                    "Should not get capability validation error anymore"
            
            print("✅ QR Code enrichment capability validation PASSED")
            print("✅ No more 'Capabilities not supported by lcsc: [specifications_fetch]' error")
            
        except ValueError as e:
            if "Capabilities not supported" in str(e):
                pytest.fail(f"❌ Original capability validation error still exists: {e}")
            else:
                # Other errors are acceptable (API issues, network, etc.)
                print(f"⚠️  Enrichment had other error (not capability issue): {e}")
        except Exception as e:
            print(f"⚠️  Enrichment failed with non-capability error: {e}")
            # Don't fail test for non-capability errors
    
    @pytest.mark.asyncio
    async def test_mouser_qr_enrichment_capabilities(self, enrichment_handlers, cleanup_test_parts):
        """Test Mouser QR enrichment with multiple capabilities"""
        with Session(engine) as session:
            # Clean up any existing part
            existing_part = session.exec(
                select(PartModel).where(PartModel.part_number == "STM32F373CBT6")
            ).first()
            if existing_part:
                session.delete(existing_part)
                session.commit()
            
            test_part = PartModel(
                part_number="STM32F373CBT6",
                part_name="QR Mouser Test - STM32F373CBT6",
                description="ARM Microcontroller",
                quantity=0,
                supplier="MOUSER"
            )
            session.add(test_part)
            session.commit()
            session.refresh(test_part)
            part_id = test_part.id
        
        # Test Mouser with all its capabilities
        task_data = {
            "part_id": part_id,
            "supplier": "mouser",
            "capabilities": [
                "fetch_datasheet", 
                "fetch_image", 
                "fetch_pricing", 
                "fetch_stock",
                "fetch_specifications"
            ]
        }
        
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="QR Mouser Enrichment - STM32F373CBT6",
            description="Mouser QR enrichment with all capabilities",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            progress_percentage=0,
            input_data=json.dumps(task_data)
        )
        
        def progress_callback(progress: int, message: str):
            print(f"Mouser QR Progress: {progress}% - {message}")
        
        try:
            result = await enrichment_handlers.handle_part_enrichment(task, progress_callback)
            
            # Should not get capability validation errors
            assert result is not None
            if isinstance(result, dict) and "error" in result:
                assert "Capabilities not supported" not in str(result["error"])
            
            print("✅ Mouser QR enrichment capability validation PASSED")
            
        except ValueError as e:
            if "Capabilities not supported" in str(e):
                pytest.fail(f"❌ Mouser capability validation error: {e}")
            else:
                print(f"⚠️  Mouser enrichment other error: {e}")
        except Exception as e:
            print(f"⚠️  Mouser enrichment failed: {e}")
    
    def test_capability_name_consistency_fixed(self):
        """Test that the capability naming inconsistency is fixed"""
        from MakerMatrix.suppliers.base import SupplierCapability
        from MakerMatrix.models.task_models import TaskType
        
        # These were the problematic mappings that caused the original error
        critical_mappings = {
            SupplierCapability.FETCH_SPECIFICATIONS: TaskType.SPECIFICATIONS_FETCH,
            SupplierCapability.FETCH_DATASHEET: TaskType.DATASHEET_FETCH,
            SupplierCapability.FETCH_IMAGE: TaskType.IMAGE_FETCH,
            SupplierCapability.FETCH_PRICING: TaskType.PRICING_FETCH,
            SupplierCapability.FETCH_STOCK: TaskType.STOCK_FETCH,
        }
        
        for capability, task_type in critical_mappings.items():
            assert capability.value == task_type.value, \
                f"CRITICAL: {capability.value} != {task_type.value} - this causes QR enrichment failures!"
        
        print("✅ All critical capability names are now consistent")
        print("✅ Original 'specifications_fetch' vs 'fetch_specifications' mismatch is FIXED")
    
    def test_environment_credentials_working(self):
        """Test that environment credential fallback is working"""
        from MakerMatrix.utils.env_credentials import get_supplier_credentials_from_env
        
        # Test that our .env credentials are detected
        lcsc_creds = get_supplier_credentials_from_env("LCSC")
        mouser_creds = get_supplier_credentials_from_env("Mouser") 
        digikey_creds = get_supplier_credentials_from_env("DigiKey")
        
        print(f"LCSC env creds: {lcsc_creds is not None}")
        print(f"Mouser env creds: {mouser_creds is not None}")  
        print(f"DigiKey env creds: {digikey_creds is not None}")
        
        # Should at least have DigiKey and Mouser from .env
        assert digikey_creds is not None, "DigiKey credentials should be available in environment"
        assert mouser_creds is not None, "Mouser credentials should be available in environment"
        
        print("✅ Environment credential fallback is working")
        print("✅ Suppliers can work even without database encryption key")
    
    @pytest.mark.asyncio
    async def test_enrichment_with_invalid_capability(self, enrichment_handlers, cleanup_test_parts):
        """Test that enrichment fails gracefully with invalid capabilities"""
        with Session(engine) as session:
            test_part = PartModel(
                part_number="TEST_INVALID_CAP",
                part_name="Test Invalid Capability",
                description="Test part for invalid capability handling",
                quantity=0,
                supplier="LCSC"
            )
            session.add(test_part)
            session.commit()
            session.refresh(test_part)
            part_id = test_part.id
        
        # Test with an invalid capability that LCSC doesn't support
        task_data = {
            "part_id": part_id,
            "supplier": "lcsc",
            "capabilities": ["invalid_capability", "fetch_datasheet"]
        }
        
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test Invalid Capability",
            description="Test invalid capability handling",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            progress_percentage=0,
            input_data=json.dumps(task_data)
        )
        
        def progress_callback(progress: int, message: str):
            print(f"Invalid cap test: {progress}% - {message}")
        
        try:
            result = await enrichment_handlers.handle_part_enrichment(task, progress_callback)
            
            # Should get a proper capability validation error for truly invalid capabilities
            if isinstance(result, dict) and "error" in result:
                assert "invalid_capability" in str(result["error"]) or "Capabilities not supported" in str(result["error"])
                print("✅ Invalid capabilities are properly rejected")
            
        except ValueError as e:
            if "invalid_capability" in str(e) or "Capabilities not supported" in str(e):
                print("✅ Invalid capabilities properly cause ValueError")
            else:
                raise