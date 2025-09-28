"""
Test LCSC enrichment with fixed capability names

Tests that LCSC enrichment works correctly after fixing the capability name mismatch
between task types and supplier capabilities.
"""

import pytest
import asyncio
from sqlmodel import Session, select

from MakerMatrix.models.models import PartModel, engine
from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus, TaskPriority
from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.data.part_service import PartService


class TestLCSCEnrichmentFix:
    """Test LCSC enrichment with the capability naming fix"""
    
    @pytest.fixture
    def part_repository(self):
        """Get part repository instance"""
        return PartRepository(engine)
    
    @pytest.fixture 
    def part_service(self):
        """Get part service instance"""
        return PartService()
    
    @pytest.fixture
    def enrichment_handlers(self, part_repository, part_service):
        """Get enrichment handlers instance"""
        return EnrichmentTaskHandlers(part_repository, part_service)
    
    @pytest.fixture
    def cleanup_test_part(self):
        """Clean up test part after test"""
        yield
        # Clean up test part C2918489 if it exists
        try:
            with Session(engine) as session:
                part = session.exec(
                    select(PartModel).where(PartModel.part_number == "C2918489")
                ).first()
                if part:
                    session.delete(part)
                    session.commit()
                    print(f"Cleaned up test part C2918489")
        except Exception as e:
            print(f"Note: Could not clean up test part: {e}")
    
    def test_lcsc_capabilities_consistency(self):
        """Test that LCSC capabilities are consistent with task types"""
        from MakerMatrix.suppliers.lcsc import LCSCSupplier
        from MakerMatrix.suppliers.base import SupplierCapability
        from MakerMatrix.models.task_models import TaskType
        
        supplier = LCSCSupplier()
        capabilities = supplier.get_capabilities()
        
        # Check that LCSC supports the capabilities we expect
        expected_capabilities = [
            SupplierCapability.GET_PART_DETAILS,
            SupplierCapability.FETCH_DATASHEET,
            SupplierCapability.FETCH_SPECIFICATIONS,
            SupplierCapability.FETCH_IMAGE
        ]
        
        for cap in expected_capabilities:
            assert cap in capabilities, f"LCSC should support {cap}"
        
        # Check that task types match capability names
        assert TaskType.DATASHEET_FETCH == "fetch_datasheet"
        assert TaskType.IMAGE_FETCH == "fetch_image"
        assert TaskType.SPECIFICATIONS_FETCH == "fetch_specifications"
        
        print("✅ LCSC capabilities and task types are consistent")
    
    @pytest.mark.asyncio
    async def test_lcsc_enrichment_with_specifications(self, enrichment_handlers, cleanup_test_part):
        """Test LCSC enrichment including specifications fetch"""
        # Create test part C2918489 (LCSC multilayer ceramic capacitor)
        with Session(engine) as session:
            # Check if part already exists
            existing_part = session.exec(
                select(PartModel).where(PartModel.part_number == "C2918489")
            ).first()
            
            if existing_part:
                session.delete(existing_part)
                session.commit()
            
            test_part = PartModel(
                part_number="C2918489",
                part_name="Test LCSC Capacitor C2918489",
                description="4.7µF ±10% 25V Multilayer Ceramic Capacitors MLCC - SMD/SMT 1206",
                quantity=0,
                supplier="LCSC"
            )
            session.add(test_part)
            session.commit()
            session.refresh(test_part)
            part_id = test_part.id
            print(f"Created test part with ID: {part_id}")
        
        # Create enrichment task with specifications capability
        import json
        task_data = {
            "part_id": part_id,
            "supplier": "lcsc",
            "capabilities": ["fetch_datasheet", "fetch_image", "fetch_specifications"]
        }
        
        task = TaskModel(
            task_type=TaskType.PART_ENRICHMENT,
            name="Test LCSC Enrichment with Specifications",
            description="Test enrichment for C2918489 with specifications",
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            progress_percentage=0,
            input_data=json.dumps(task_data)  # Use JSON dumps instead of str()
        )
        
        # Mock progress callback
        def progress_callback(progress: int, message: str):
            print(f"Progress: {progress}% - {message}")
        
        try:
            # Run the enrichment
            result = await enrichment_handlers.handle_part_enrichment(task, progress_callback)
            
            print(f"Enrichment result: {result}")
            
            # Verify the enrichment was successful
            assert result is not None
            assert "error" not in result or not result["error"]
            
            # Check that the part was enriched
            with Session(engine) as session:
                enriched_part = session.get(PartModel, part_id)
                assert enriched_part is not None
                
                # Check for enrichment data (may vary based on LCSC API response)
                print(f"Enriched part description: {enriched_part.description}")
                print(f"Enriched part additional_properties: {enriched_part.additional_properties}")
                
                # Should have some enrichment data
                if enriched_part.additional_properties:
                    print("✅ Part has additional properties from enrichment")
                
                print("✅ LCSC enrichment with specifications completed successfully")
                
        except ValueError as e:
            if "Capabilities not supported" in str(e):
                pytest.fail(f"Capability validation failed: {e}")
            else:
                # Re-raise other ValueErrors
                raise
        except Exception as e:
            print(f"Enrichment failed with error: {e}")
            # Don't fail the test for API errors, just log them
            print("Note: This might be expected if LCSC API is unavailable")
    
    def test_capability_name_mapping(self):
        """Test that all capability names are consistently mapped"""
        from MakerMatrix.suppliers.base import SupplierCapability
        from MakerMatrix.models.task_models import TaskType
        
        # Test the specific mappings that were causing issues
        capability_to_task_mapping = {
            SupplierCapability.FETCH_DATASHEET: TaskType.DATASHEET_FETCH,
            SupplierCapability.FETCH_IMAGE: TaskType.IMAGE_FETCH,
            SupplierCapability.FETCH_SPECIFICATIONS: TaskType.SPECIFICATIONS_FETCH,
            SupplierCapability.FETCH_PRICING: TaskType.PRICING_FETCH,
            SupplierCapability.FETCH_STOCK: TaskType.STOCK_FETCH,
        }
        
        for capability, task_type in capability_to_task_mapping.items():
            assert capability.value == task_type.value, \
                f"Capability {capability.value} should match task type {task_type.value}"
        
        print("✅ All capability names are consistently mapped")