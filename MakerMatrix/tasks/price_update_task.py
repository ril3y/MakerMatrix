"""
Price Update Task - Updates part prices from supplier APIs using the modular supplier system
"""

import asyncio
from typing import Dict, Any, List
from .base_task import BaseTask
from MakerMatrix.models.task_models import TaskModel
from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import PartModel
from MakerMatrix.suppliers import SupplierRegistry
from MakerMatrix.suppliers.base import SupplierCapability
from MakerMatrix.services.supplier_config_service import SupplierConfigService
from sqlmodel import select
import logging

logger = logging.getLogger(__name__)


class PriceUpdateTask(BaseTask):
    """Task for updating part prices from supplier APIs using the modular supplier system"""
    
    @property
    def task_type(self) -> str:
        return "price_update"
    
    @property
    def name(self) -> str:
        return "Price Update"
    
    @property
    def description(self) -> str:
        return "Update part prices from supplier APIs"
    
    async def execute(self, task: TaskModel) -> Dict[str, Any]:
        """Execute price update task using the modular supplier system"""
        input_data = self.get_input_data(task)
        update_all = input_data.get('update_all', False)
        part_ids = input_data.get('part_ids', [])
        supplier_filter = input_data.get('supplier_filter')
        
        await self.update_progress(task, 10, "Initializing price update")
        
        # Get parts from database
        session = next(get_session())
        config_service = SupplierConfigService(session)
        
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
            for supplier_name, supplier_parts in parts_by_supplier.items():
                await self.update_step(task, f"Processing {len(supplier_parts)} parts for {supplier_name}")
                
                # Check if supplier is available in the registry
                if not SupplierRegistry.is_supplier_available(supplier_name):
                    self.log_warning(f"Supplier not available in registry: {supplier_name}", task)
                    # Add all parts from this supplier to failed updates
                    for part in supplier_parts:
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.part_name,
                            'supplier': supplier_name,
                            'error': f'Supplier {supplier_name} not available in system'
                        })
                        total_processed += 1
                    continue
                
                # Get supplier instance
                try:
                    supplier = SupplierRegistry.get_supplier(supplier_name)
                    
                    # Check if supplier is configured
                    config = await config_service.get_supplier_config(supplier_name)
                    if not config or not config.is_configured:
                        self.log_warning(f"Supplier {supplier_name} is not configured", task)
                        for part in supplier_parts:
                            failed_updates.append({
                                'part_id': part.id,
                                'part_name': part.part_name,
                                'supplier': supplier_name,
                                'error': f'Supplier {supplier_name} is not configured'
                            })
                            total_processed += 1
                        continue
                    
                    # Configure the supplier with credentials
                    supplier.configure(config.credentials, config.config)
                    
                    # Check if supplier supports pricing capability
                    if SupplierCapability.FETCH_PRICING not in supplier.get_capabilities():
                        self.log_warning(f"Supplier {supplier_name} does not support pricing fetch", task)
                        for part in supplier_parts:
                            failed_updates.append({
                                'part_id': part.id,
                                'part_name': part.part_name,
                                'supplier': supplier_name,
                                'error': f'Supplier {supplier_name} does not support pricing fetch'
                            })
                            total_processed += 1
                        continue
                    
                except Exception as e:
                    self.log_error(f"Failed to initialize supplier {supplier_name}: {str(e)}", task)
                    for part in supplier_parts:
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.part_name,
                            'supplier': supplier_name,
                            'error': f'Failed to initialize supplier: {str(e)}'
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
                            f"Updating price for {part.part_name} ({supplier_name}) - {total_processed + 1}/{len(parts)}"
                        )
                        
                        # Use supplier to fetch pricing
                        pricing_data = await supplier.fetch_pricing(part.part_number)
                        
                        if pricing_data:
                            # Extract pricing information
                            old_price = part.price
                            
                            # Pricing data is a list of price breaks
                            # Find the price for quantity 1 or the lowest quantity
                            unit_price = None
                            if isinstance(pricing_data, list) and len(pricing_data) > 0:
                                # Sort by quantity to find the lowest quantity price
                                sorted_prices = sorted(pricing_data, key=lambda x: x.get('quantity', 1))
                                unit_price = sorted_prices[0].get('price')
                            
                            if unit_price is not None:
                                new_price = float(unit_price)
                                
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
                                    'part_name': part.part_name,
                                    'supplier': supplier_name,
                                    'old_price': old_price,
                                    'new_price': new_price,
                                    'currency': sorted_prices[0].get('currency', 'USD'),
                                    'pricing_data': pricing_data
                                })
                                
                                self.log_info(f"Updated price for {part.part_name}: {old_price} -> {new_price}", task)
                            else:
                                failed_updates.append({
                                    'part_id': part.id,
                                    'part_name': part.part_name,
                                    'supplier': supplier_name,
                                    'error': 'No unit price found in pricing data'
                                })
                        else:
                            failed_updates.append({
                                'part_id': part.id,
                                'part_name': part.part_name,
                                'supplier': supplier_name,
                                'error': 'No pricing data returned from supplier'
                            })
                        
                        total_processed += 1
                        
                        # Rate limiting to avoid overwhelming APIs
                        # Use supplier-specific rate limit delay
                        delay = supplier.get_rate_limit_delay()
                        await self.sleep(delay)
                        
                    except Exception as e:
                        self.log_error(f"Failed to update price for part {part.part_name}: {str(e)}", task, exc_info=True)
                        failed_updates.append({
                            'part_id': part.id,
                            'part_name': part.part_name,
                            'supplier': supplier_name,
                            'error': str(e)
                        })
                        total_processed += 1
                
                # Clean up supplier resources
                try:
                    await supplier.close()
                except:
                    pass
            
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