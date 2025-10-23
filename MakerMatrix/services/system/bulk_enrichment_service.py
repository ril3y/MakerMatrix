"""
BulkEnrichmentService - Handles bulk enrichment operations for multiple parts.
Extracted from monolithic enrichment_task_handlers.py as part of Step 12.7.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

from MakerMatrix.models.task_models import TaskModel, TaskType, TaskStatus
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.system.part_enrichment_service import PartEnrichmentService
from MakerMatrix.services.base_service import BaseService

logger = logging.getLogger(__name__)


class BulkEnrichmentService(BaseService):
    """
    Service for handling bulk enrichment operations for multiple parts.
    Supports both specific part lists and paginated all-parts enrichment.
    """

    def __init__(self):
        super().__init__()
        self.part_enrichment_service = PartEnrichmentService()

    async def handle_bulk_enrichment(
        self, task: TaskModel, progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle bulk enrichment for multiple parts.

        Input data can contain:
        - part_ids: List of specific part IDs to enrich (legacy mode)
        - enrich_all: Boolean to enrich all parts in system with pagination (new mode)
        - supplier_filter: Optional supplier filter
        - capabilities: List of capabilities to use
        - batch_size: Number of parts to process in parallel (default: 5)
        - page_size: Number of parts to fetch per page when enrich_all=true (default: 10)

        Args:
            task: The task model containing bulk enrichment parameters
            progress_callback: Optional callback for progress updates

        Returns:
            Dict containing bulk enrichment results and statistics
        """
        try:
            input_data = task.get_input_data()
            part_ids = input_data.get("part_ids", [])
            enrich_all = input_data.get("enrich_all", False)
            supplier_filter = input_data.get("supplier_filter")
            requested_capabilities = input_data.get("capabilities", [])
            batch_size = input_data.get("batch_size", 5)
            page_size = input_data.get("page_size", 10)

            logger.info(f"🚀 [BULK ENRICHMENT] Starting bulk enrichment task")
            logger.info(f"🔧 [BULK ENRICHMENT] Requested capabilities: {requested_capabilities}")
            logger.info(f"🏭 [BULK ENRICHMENT] Supplier filter: {supplier_filter}")
            logger.info(f"📦 [BULK ENRICHMENT] Batch size: {batch_size}")

            if enrich_all:
                logger.info(f"🌍 [BULK ENRICHMENT] Mode: Enrich ALL parts with pagination (page size: {page_size})")
                return await self._handle_bulk_enrichment_paginated(
                    supplier_filter, requested_capabilities, batch_size, page_size, progress_callback
                )
            else:
                logger.info(f"📋 [BULK ENRICHMENT] Mode: Enrich specific parts ({len(part_ids)} parts)")
                if not part_ids:
                    raise ValueError("part_ids list is required when enrich_all=false")
                return await self._handle_bulk_enrichment_specific(
                    part_ids, supplier_filter, requested_capabilities, batch_size, progress_callback
                )

        except Exception as e:
            logger.error(f"💥 [BULK ENRICHMENT] Task failed with error: {e}", exc_info=True)
            raise

    async def _handle_bulk_enrichment_specific(
        self,
        part_ids: List[str],
        supplier_filter: Optional[str],
        requested_capabilities: List[str],
        batch_size: int,
        progress_callback: Optional[Callable],
    ) -> Dict[str, Any]:
        """Handle bulk enrichment for specific part IDs (legacy mode)."""
        try:
            logger.info(f"📊 [BULK ENRICHMENT] Total parts to process: {len(part_ids)}")

            total_parts = len(part_ids)
            processed_parts = 0
            successful_enrichments = []
            failed_enrichments = []

            # Process parts in batches
            logger.info(f"🔄 [BULK ENRICHMENT] Processing {total_parts} parts in batches of {batch_size}")
            for i in range(0, total_parts, batch_size):
                batch = part_ids[i : i + batch_size]
                batch_number = (i // batch_size) + 1
                total_batches = (total_parts + batch_size - 1) // batch_size

                logger.info(
                    f"📦 [BULK ENRICHMENT] Starting batch {batch_number}/{total_batches} with {len(batch)} parts"
                )
                batch_tasks = []

                for j, part_id in enumerate(batch):
                    logger.info(f"   📋 [BULK ENRICHMENT] Batch {batch_number}, Part {j+1}/{len(batch)}: {part_id}")

                    # Create enrichment task for each part
                    enrichment_data = {"part_id": part_id, "capabilities": requested_capabilities}
                    if supplier_filter:
                        enrichment_data["supplier"] = supplier_filter
                        logger.info(f"   🏭 [BULK ENRICHMENT] Using supplier filter: {supplier_filter}")

                    logger.info(f"   🔧 [BULK ENRICHMENT] Part {part_id} capabilities: {requested_capabilities}")

                    # Create a mock task for the part enrichment
                    part_task = TaskModel(
                        task_type=TaskType.PART_ENRICHMENT,
                        name=f"Part Enrichment - {part_id}",
                        status=TaskStatus.RUNNING,
                    )
                    part_task.set_input_data(enrichment_data)

                    batch_tasks.append(self.part_enrichment_service.handle_part_enrichment(part_task))

                # Execute batch in parallel
                logger.info(
                    f"⚡ [BULK ENRICHMENT] Executing batch {batch_number} with {len(batch_tasks)} tasks in parallel"
                )
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Process batch results
                batch_successful = 0
                batch_failed = 0

                for j, result in enumerate(batch_results):
                    part_id = batch[j]
                    if isinstance(result, Exception):
                        logger.error(f"❌ [BULK ENRICHMENT] Part {part_id} failed: {result}")
                        failed_enrichments.append({"part_id": part_id, "error": str(result)})
                        batch_failed += 1
                    else:
                        logger.info(f"✅ [BULK ENRICHMENT] Part {part_id} succeeded")
                        successful_enrichments.append(
                            {
                                "part_id": part_id,
                                "supplier": result.get("supplier"),
                                "completed_capabilities": result.get("completed_capabilities", 0),
                            }
                        )
                        batch_successful += 1

                processed_parts += len(batch)
                logger.info(
                    f"📊 [BULK ENRICHMENT] Batch {batch_number} completed: {batch_successful} successful, {batch_failed} failed"
                )

                # Update progress
                if progress_callback:
                    progress_pct = int((processed_parts / total_parts) * 100)
                    await progress_callback(
                        progress_pct,
                        f"Processed {processed_parts}/{total_parts} parts ({batch_successful} successful, {batch_failed} failed)",
                    )

            logger.info(f"🎉 [BULK ENRICHMENT] Specific parts enrichment completed!")
            logger.info(
                f"📊 [BULK ENRICHMENT] Final results: {len(successful_enrichments)} successful, {len(failed_enrichments)} failed"
            )

            return {
                "mode": "specific_parts",
                "total_parts": total_parts,
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments,
                "success_rate": len(successful_enrichments) / total_parts if total_parts > 0 else 0,
            }

        except Exception as e:
            logger.error(f"💥 [BULK ENRICHMENT] Specific parts enrichment failed: {e}", exc_info=True)
            raise

    async def _handle_bulk_enrichment_paginated(
        self,
        supplier_filter: Optional[str],
        requested_capabilities: List[str],
        batch_size: int,
        page_size: int,
        progress_callback: Optional[Callable],
    ) -> Dict[str, Any]:
        """Handle bulk enrichment with pagination (enrich all parts)."""
        try:
            logger.info(f"🌍 [BULK ENRICHMENT] Starting paginated enrichment (ALL parts)")

            # Get total count of parts to process
            with self.get_session() as session:
                if supplier_filter:
                    total_parts = PartRepository.get_parts_count_by_supplier(session, supplier_filter)
                    logger.info(
                        f"📊 [BULK ENRICHMENT] Total parts with supplier filter '{supplier_filter}': {total_parts}"
                    )
                else:
                    total_parts = PartRepository.get_all_parts_count(session)
                    logger.info(f"📊 [BULK ENRICHMENT] Total parts in system: {total_parts}")

            if total_parts == 0:
                logger.warning(f"⚠️ [BULK ENRICHMENT] No parts found to enrich")
                return {
                    "mode": "paginated_all",
                    "total_parts": 0,
                    "successful_enrichments": [],
                    "failed_enrichments": [],
                    "success_rate": 0,
                }

            processed_parts = 0
            successful_enrichments = []
            failed_enrichments = []

            # Process parts in pages
            total_pages = (total_parts + page_size - 1) // page_size
            logger.info(
                f"📄 [BULK ENRICHMENT] Processing {total_parts} parts across {total_pages} pages (page size: {page_size})"
            )

            for page_num in range(total_pages):
                offset = page_num * page_size

                logger.info(f"📄 [BULK ENRICHMENT] Processing page {page_num + 1}/{total_pages} (offset: {offset})")

                # Get parts for this page
                with self.get_session() as session:
                    parts = PartRepository.get_parts_paginated(session, offset, page_size, supplier_filter)

                if not parts:
                    logger.warning(f"⚠️ [BULK ENRICHMENT] No parts found for page {page_num + 1}")
                    continue

                logger.info(f"📦 [BULK ENRICHMENT] Got {len(parts)} parts for page {page_num + 1}")

                # Process this page's parts in batches
                page_successful = []
                page_failed = []

                for batch_start in range(0, len(parts), batch_size):
                    batch_parts = parts[batch_start : batch_start + batch_size]
                    batch_number = (batch_start // batch_size) + 1
                    page_batches = (len(parts) + batch_size - 1) // batch_size

                    logger.info(
                        f"🔄 [BULK ENRICHMENT] Page {page_num + 1}, Batch {batch_number}/{page_batches}: {len(batch_parts)} parts"
                    )

                    # Create enrichment tasks for this batch
                    batch_tasks = []
                    for part in batch_parts:
                        enrichment_data = {"part_id": part.id, "capabilities": requested_capabilities}
                        if supplier_filter:
                            enrichment_data["supplier"] = supplier_filter

                        # Create a mock task for the part enrichment
                        part_task = TaskModel(
                            task_type=TaskType.PART_ENRICHMENT,
                            name=f"Part Enrichment - {part.id}",
                            status=TaskStatus.RUNNING,
                        )
                        part_task.set_input_data(enrichment_data)

                        batch_tasks.append(self.part_enrichment_service.handle_part_enrichment(part_task))

                    # Execute batch in parallel
                    logger.info(
                        f"⚡ [BULK ENRICHMENT] Executing page {page_num + 1}, batch {batch_number} with {len(batch_tasks)} tasks"
                    )
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                    # Process batch results
                    for j, result in enumerate(batch_results):
                        part = batch_parts[j]
                        if isinstance(result, Exception):
                            logger.error(f"❌ [BULK ENRICHMENT] Part {part.id} ({part.part_name}) failed: {result}")
                            page_failed.append({"part_id": part.id, "part_name": part.part_name, "error": str(result)})
                        else:
                            logger.info(f"✅ [BULK ENRICHMENT] Part {part.id} ({part.part_name}) succeeded")
                            page_successful.append(
                                {
                                    "part_id": part.id,
                                    "part_name": part.part_name,
                                    "supplier": result.get("supplier"),
                                    "completed_capabilities": result.get("completed_capabilities", 0),
                                }
                            )

                # Update totals
                successful_enrichments.extend(page_successful)
                failed_enrichments.extend(page_failed)
                processed_parts += len(parts)

                logger.info(
                    f"📊 [BULK ENRICHMENT] Page {page_num + 1} completed: {len(page_successful)} successful, {len(page_failed)} failed"
                )

                # Update progress
                if progress_callback:
                    progress_pct = int((processed_parts / total_parts) * 100)
                    await progress_callback(
                        progress_pct,
                        f"Processed {processed_parts}/{total_parts} parts ({len(successful_enrichments)} successful, {len(failed_enrichments)} failed)",
                    )

            logger.info(f"🎉 [BULK ENRICHMENT] Paginated enrichment completed!")
            logger.info(
                f"📊 [BULK ENRICHMENT] Final results: {len(successful_enrichments)} successful, {len(failed_enrichments)} failed"
            )

            return {
                "mode": "paginated_all",
                "total_parts": total_parts,
                "successful_enrichments": successful_enrichments,
                "failed_enrichments": failed_enrichments,
                "success_rate": len(successful_enrichments) / total_parts if total_parts > 0 else 0,
            }

        except Exception as e:
            logger.error(f"💥 [BULK ENRICHMENT] Paginated enrichment failed: {e}", exc_info=True)
            raise
