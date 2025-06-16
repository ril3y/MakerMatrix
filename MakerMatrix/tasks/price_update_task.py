"""
Price Update Task - Updates part prices from supplier APIs using enhanced parsers
"""

import asyncio
from typing import Dict, Any, List
from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import PartModel
from MakerMatrix.parsers.enhanced_parser import get_enhanced_parser
from MakerMatrix.parsers.supplier_capabilities import CapabilityType
from sqlmodel import select
import logging

logger = logging.getLogger(__name__)


class PriceUpdateTask(BaseTask):
    """Task for updating part prices from supplier APIs using enhanced parsers"""
    
    @property
    def task_type(self) -> str:
        return "price_update"
    
    @property
    def name(self) -> str:
        return "Price Update"
    
    @property
    def description(self) -> str:
        return "Update part prices from supplier APIs using enhanced parsers"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute price update task using enhanced parsers"""
        input_data = self.get_input_data(task)
        update_all = input_data.get('update_all', False)
        part_ids = input_data.get('part_ids', [])
        supplier_filter = input_data.get('supplier_filter')
        
        await self.update_progress(task, 10, "Initializing price update")
        
        # Get parts from database
        session = next(get_session())
        try:
            if update_all:
                await self.update_step(task, "Fetching all parts from database")
                query = select(PartModel)
                if supplier_filter:
                    query = query.where(PartModel.supplier == supplier_filter)
                parts = session.exec(query).all()
            else:
                if not part_ids:
                    return {"message": "No parts specified", "updated_count": 0}
                await self.update_step(task, f"Fetching {len(part_ids)} parts from database")
                query = select(PartModel).where(PartModel.id.in_(part_ids))
                parts = session.exec(query).all()
            
            if not parts:
                return {"message": "No parts found to update", "updated_count": 0}
            
            await self.update_progress(task, 20, f"Found {len(parts)} parts to update")
            
            # Group parts by supplier for efficient processing
            parts_by_supplier = {}
            for part in parts:
                supplier = part.supplier or part.part_vendor
                if supplier:
                    if supplier not in parts_by_supplier:
                        parts_by_supplier[supplier] = []
                    parts_by_supplier[supplier].append(part)
            
            updated_parts = []
            failed_updates = []
            total_processed = 0
            
            # Process each supplier's parts
            for supplier, supplier_parts in parts_by_supplier.items():
                await self.update_step(task, f"Processing {len(supplier_parts)} parts for {supplier}")
                
                # Get enhanced parser for this supplier
                parser = get_enhanced_parser(supplier)
                if not parser:
                    self.log_warning(f"No enhanced parser available for supplier: {supplier}", task)
                    # Add all parts from this supplier to failed updates
                    for part in supplier_parts:
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.name,
                            'supplier': supplier,
                            'error': f'No enhanced parser available for supplier {supplier}'
                        })
                        total_processed += 1
                    continue
                
                # Check if supplier supports pricing capability
                if not parser.supports_capability(CapabilityType.FETCH_PRICING):
                    self.log_warning(f"Supplier {supplier} does not support pricing fetch", task)
                    for part in supplier_parts:
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.name,
                            'supplier': supplier,
                            'error': f'Supplier {supplier} does not support pricing fetch'
                        })
                        total_processed += 1
                    continue
                
                # Update prices for parts from this supplier
                for i, part in enumerate(supplier_parts):
                    try:
                        progress = int(20 + (total_processed / len(parts)) * 70)
                        await self.update_progress(
                            task,
                            progress,
                            f"Updating price for {part.name} ({supplier}) - {total_processed + 1}/{len(parts)}"
                        )
                        
                        # Use enhanced parser to fetch pricing
                        pricing_result = await parser.fetch_pricing(part)
                        
                        if pricing_result.success and pricing_result.data:
                            # Extract pricing information
                            old_price = part.price
                            pricing_data = pricing_result.data
                            
                            if 'unit_price' in pricing_data:
                                new_price = float(pricing_data['unit_price'])
                                
                                # Update part price in database
                                part.price = new_price
                                
                                # Store pricing data in additional_properties
                                if not part.additional_properties:
                                    part.additional_properties = {}
                                part.additional_properties['pricing_data'] = pricing_data
                                part.additional_properties['last_price_update'] = task.created_at.isoformat()
                                
                                session.add(part)
                                session.commit()
                                
                                updated_parts.append({
                                    'part_id': part.id,
                                    'part_name': part.name,
                                    'supplier': supplier,
                                    'old_price': old_price,
                                    'new_price': new_price,
                                    'currency': pricing_data.get('currency', 'USD'),
                                    'pricing_data': pricing_data
                                })
                                
                                self.log_info(f"Updated price for {part.name}: {old_price} -> {new_price}", task)
                            else:
                                failed_updates.append({
                                    'part_id': part.id,
                                    'part_name': part.name,
                                    'supplier': supplier,
                                    'error': 'No unit price found in pricing data'
                                })
                        else:
                            failed_updates.append({
                                'part_id': part.id,
                                'part_name': part.name,
                                'supplier': supplier,
                                'error': pricing_result.error or 'Pricing fetch failed'
                            })
                        
                        total_processed += 1
                        
                        # Rate limiting to avoid overwhelming APIs
                        await self.sleep(0.1)
                        
                    except Exception as e:
                        self.log_error(f"Failed to update price for part {part.name}: {str(e)}", task, exc_info=True)
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.name,
                            'supplier': supplier,
                            'error': str(e)
                        })
                        total_processed += 1
            
            await self.update_progress(task, 100, "Price update completed")
            
            result = {
                "total_parts": len(parts),
                "updated_count": len(updated_parts),
                "failed_count": len(failed_updates),
                "suppliers_processed": list(parts_by_supplier.keys()),
                "updated_parts": updated_parts,
                "failed_updates": failed_updates
            }
            
            self.log_info(
                f"Price update complete: {len(updated_parts)} updated, {len(failed_updates)} failed across {len(parts_by_supplier)} suppliers", 
                task
            )
            
            return result
            
        finally:
            session.close()
    
    async def _get_parts_for_update(self, session, update_all: bool, part_ids: List[str], supplier_filter: str = None) -> List[PartModel]:
        """Get parts that need price updates"""
        if update_all:
            query = select(PartModel)
            if supplier_filter:
                query = query.where(PartModel.supplier == supplier_filter)
            return session.exec(query).all()
        else:
            if not part_ids:
                return []
            query = select(PartModel).where(PartModel.id.in_(part_ids))
            return session.exec(query).all()