"""
Enrichment Queue Manager

Manages intelligent queuing and processing of part enrichment tasks with 
supplier-aware rate limiting and real-time progress updates.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from MakerMatrix.suppliers.registry import get_supplier, get_available_suppliers
from MakerMatrix.services.rate_limit_service import RateLimitService, RateLimitExceeded
from MakerMatrix.schemas.websocket_schemas import (
    create_enrichment_progress_message,
    create_notification_message,
    create_toast_message,
    create_rate_limit_update_message,
    WebSocketEventType
)

logger = logging.getLogger(__name__)


class EnrichmentPriority(str, Enum):
    """Priority levels for enrichment tasks"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EnrichmentStatus(str, Enum):
    """Status of enrichment tasks"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


@dataclass
class EnrichmentTask:
    """Individual enrichment task"""
    id: str
    part_id: str
    part_name: str
    supplier_name: str
    capabilities: List[str]
    priority: EnrichmentPriority = EnrichmentPriority.NORMAL
    status: EnrichmentStatus = EnrichmentStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completed_capabilities: List[str] = field(default_factory=list)
    failed_capabilities: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def progress_percentage(self) -> int:
        """Calculate completion percentage"""
        if not self.capabilities:
            return 100
        completed = len(self.completed_capabilities)
        total = len(self.capabilities)
        return int((completed / total) * 100)
    
    @property
    def remaining_capabilities(self) -> List[str]:
        """Get capabilities that still need to be processed"""
        return [cap for cap in self.capabilities if cap not in self.completed_capabilities]


class SupplierQueue:
    """Queue for a specific supplier with rate limiting"""
    
    def __init__(self, supplier_name: str, rate_limit_service: RateLimitService):
        self.supplier_name = supplier_name
        self.rate_limit_service = rate_limit_service
        self.pending_tasks: List[EnrichmentTask] = []
        self.running_tasks: Set[str] = set()
        self.completed_tasks: List[EnrichmentTask] = []
        self.failed_tasks: List[EnrichmentTask] = []
        self.is_processing = False
        self.last_request_time: Optional[datetime] = None
        
        # Get supplier instance for rate limit info
        try:
            self.supplier = get_supplier(supplier_name.lower())
            self.rate_limit_delay = self.supplier.get_rate_limit_delay()
        except Exception as e:
            logger.warning(f"Could not get supplier {supplier_name}: {e}")
            self.supplier = None
            self.rate_limit_delay = 1.0  # Default 1 second delay
    
    def add_task(self, task: EnrichmentTask):
        """Add a task to the queue"""
        # Insert based on priority
        if task.priority == EnrichmentPriority.URGENT:
            self.pending_tasks.insert(0, task)
        elif task.priority == EnrichmentPriority.HIGH:
            # Insert after any urgent tasks
            urgent_count = sum(1 for t in self.pending_tasks if t.priority == EnrichmentPriority.URGENT)
            self.pending_tasks.insert(urgent_count, task)
        else:
            # Normal and low priority go to the end
            self.pending_tasks.append(task)
        
        logger.info(f"Added {task.priority} priority task for {task.part_name} to {self.supplier_name} queue")
    
    def get_next_task(self) -> Optional[EnrichmentTask]:
        """Get the next task to process"""
        if not self.pending_tasks:
            return None
        return self.pending_tasks.pop(0)
    
    def mark_task_running(self, task: EnrichmentTask):
        """Mark a task as currently running"""
        task.status = EnrichmentStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self.running_tasks.add(task.id)
    
    def mark_task_completed(self, task: EnrichmentTask):
        """Mark a task as completed"""
        task.status = EnrichmentStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        self.running_tasks.discard(task.id)
        self.completed_tasks.append(task)
    
    def mark_task_failed(self, task: EnrichmentTask, error_message: str):
        """Mark a task as failed"""
        task.status = EnrichmentStatus.FAILED
        task.error_message = error_message
        task.completed_at = datetime.now(timezone.utc)
        self.running_tasks.discard(task.id)
        
        # Retry logic
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = EnrichmentStatus.PENDING
            task.started_at = None
            task.completed_at = None
            self.add_task(task)  # Re-queue for retry
            logger.info(f"Re-queued task {task.id} for retry ({task.retry_count}/{task.max_retries})")
        else:
            self.failed_tasks.append(task)
            logger.error(f"Task {task.id} failed permanently after {task.max_retries} retries")
    
    @property
    def queue_size(self) -> int:
        """Get current queue size"""
        return len(self.pending_tasks)
    
    @property
    def running_count(self) -> int:
        """Get number of running tasks"""
        return len(self.running_tasks)
    
    def estimate_completion_time(self) -> Optional[datetime]:
        """Estimate when queue will be completed"""
        if not self.pending_tasks:
            return None
        
        # Estimate based on rate limit delay and queue size
        total_capabilities = sum(len(task.remaining_capabilities) for task in self.pending_tasks)
        estimated_seconds = total_capabilities * self.rate_limit_delay
        
        return datetime.now(timezone.utc) + timedelta(seconds=estimated_seconds)


class EnrichmentQueueManager:
    """Manages enrichment queues for all suppliers"""
    
    def __init__(self, engine, rate_limit_service: RateLimitService, websocket_manager=None):
        self.engine = engine
        self.rate_limit_service = rate_limit_service
        self.websocket_manager = websocket_manager
        self.supplier_queues: Dict[str, SupplierQueue] = {}
        self.task_registry: Dict[str, EnrichmentTask] = {}
        self.is_running = False
        self.processing_tasks: Set[str] = set()
        
        # Initialize queues for available suppliers
        self._initialize_supplier_queues()
    
    def _initialize_supplier_queues(self):
        """Initialize queues for all available suppliers"""
        try:
            available_suppliers = get_available_suppliers()
            for supplier_name in available_suppliers:
                self.supplier_queues[supplier_name.upper()] = SupplierQueue(
                    supplier_name.upper(),
                    self.rate_limit_service
                )
            logger.info(f"Initialized enrichment queues for {len(available_suppliers)} suppliers")
        except Exception as e:
            logger.error(f"Failed to initialize supplier queues: {e}")
    
    async def queue_part_enrichment(
        self,
        part_id: str,
        part_name: str,
        supplier_name: str,
        capabilities: List[str],
        priority: EnrichmentPriority = EnrichmentPriority.NORMAL,
        task_id: Optional[str] = None
    ) -> str:
        """Queue a part for enrichment"""
        import uuid
        
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        supplier_name = supplier_name.upper()
        
        # Validate supplier
        if supplier_name not in self.supplier_queues:
            raise ValueError(f"Supplier {supplier_name} not available")
        
        # Create enrichment task
        task = EnrichmentTask(
            id=task_id,
            part_id=part_id,
            part_name=part_name,
            supplier_name=supplier_name,
            capabilities=capabilities,
            priority=priority
        )
        
        # Add to registry and queue
        self.task_registry[task_id] = task
        self.supplier_queues[supplier_name].add_task(task)
        
        logger.info(f"Queued enrichment task {task_id} for part {part_name} with {supplier_name}")
        
        # Broadcast queue update
        if self.websocket_manager:
            try:
                await self._broadcast_queue_status(supplier_name)
            except Exception as e:
                logger.warning(f"Failed to broadcast queue update: {e}")
        
        # Start processing if not already running
        if not self.is_running:
            asyncio.create_task(self.start_processing())
        
        return task_id
    
    async def start_processing(self):
        """Start processing all supplier queues"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting enrichment queue processing")
        
        try:
            # Start processing tasks for each supplier
            tasks = []
            for supplier_name, queue in self.supplier_queues.items():
                if queue.queue_size > 0:
                    tasks.append(self._process_supplier_queue(supplier_name))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self.is_running = False
            logger.info("Enrichment queue processing stopped")
    
    async def _process_supplier_queue(self, supplier_name: str):
        """Process enrichment queue for a specific supplier"""
        queue = self.supplier_queues[supplier_name]
        
        if queue.is_processing:
            return
        
        queue.is_processing = True
        logger.info(f"Starting processing queue for {supplier_name}")
        
        try:
            while queue.queue_size > 0:
                task = queue.get_next_task()
                if not task:
                    break
                
                try:
                    await self._process_enrichment_task(task, queue)
                except RateLimitExceeded as e:
                    # Re-queue task and wait
                    task.status = EnrichmentStatus.RATE_LIMITED
                    queue.add_task(task)
                    logger.warning(f"Rate limit exceeded for {supplier_name}, waiting {e.retry_after} seconds")
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    logger.error(f"Error processing task {task.id}: {e}")
                    queue.mark_task_failed(task, str(e))
        finally:
            queue.is_processing = False
            logger.info(f"Finished processing queue for {supplier_name}")
    
    async def _process_enrichment_task(self, task: EnrichmentTask, queue: SupplierQueue):
        """Process a single enrichment task"""
        queue.mark_task_running(task)
        
        try:
            # Import enrichment handler
            from MakerMatrix.services.enrichment_task_handlers import EnrichmentTaskHandlers
            from MakerMatrix.repositories.parts_repositories import PartRepository
            from MakerMatrix.services.part_service import PartService
            
            # Create services
            part_repository = PartRepository(self.engine)
            part_service = PartService(self.engine)
            enrichment_handler = EnrichmentTaskHandlers(part_repository, part_service)
            
            # Get the part
            part = await part_repository.get_by_id(task.part_id)
            if not part:
                raise ValueError(f"Part {task.part_id} not found")
            
            # Process each capability with rate limiting
            for capability in task.remaining_capabilities:
                if task.id in self.processing_tasks:
                    # Task was cancelled
                    task.status = EnrichmentStatus.CANCELLED
                    return
                
                # Check rate limit
                rate_status = await self.rate_limit_service.check_rate_limit(
                    task.supplier_name, capability
                )
                
                if not rate_status.get("allowed", False):
                    raise RateLimitExceeded(
                        task.supplier_name,
                        "rate_limit",
                        rate_status.get("retry_after_seconds", 60)
                    )
                
                # Apply rate limit delay
                if queue.last_request_time:
                    elapsed = (datetime.now(timezone.utc) - queue.last_request_time).total_seconds()
                    if elapsed < queue.rate_limit_delay:
                        sleep_time = queue.rate_limit_delay - elapsed
                        await asyncio.sleep(sleep_time)
                
                # Perform enrichment
                start_time = datetime.now(timezone.utc)
                try:
                    # Use the new enrichment handler
                    result = await enrichment_handler.handle_part_enrichment(
                        task_id=task.id,
                        part_id=task.part_id,
                        supplier=task.supplier_name,
                        requested_capabilities=[capability]
                    )
                    
                    # Record successful request
                    response_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    await self.rate_limit_service.record_request(
                        task.supplier_name,
                        capability,
                        True,
                        response_time
                    )
                    
                    # Mark capability as completed
                    task.completed_capabilities.append(capability)
                    queue.last_request_time = datetime.now(timezone.utc)
                    
                    # Broadcast progress update
                    if self.websocket_manager:
                        try:
                            message = create_enrichment_progress_message(
                                supplier_name=task.supplier_name,
                                part_id=task.part_id,
                                part_name=task.part_name,
                                capabilities_completed=task.completed_capabilities,
                                capabilities_total=task.capabilities,
                                current_capability=capability,
                                task_id=task.id
                            )
                            await self.websocket_manager.broadcast_to_all(message.model_dump())
                        except Exception as e:
                            logger.warning(f"Failed to broadcast enrichment progress: {e}")
                    
                except Exception as e:
                    # Record failed request
                    response_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    await self.rate_limit_service.record_request(
                        task.supplier_name,
                        capability,
                        False,
                        response_time,
                        str(e)
                    )
                    
                    task.failed_capabilities.append(capability)
                    logger.warning(f"Failed to enrich {capability} for part {task.part_name}: {e}")
            
            # Mark task as completed
            queue.mark_task_completed(task)
            
            # Send completion notification
            if self.websocket_manager:
                try:
                    success_count = len(task.completed_capabilities)
                    total_count = len(task.capabilities)
                    
                    if success_count == total_count:
                        message = create_toast_message(
                            "success",
                            f"✅ Enrichment completed for {task.part_name}",
                            duration=3000
                        )
                    elif success_count > 0:
                        message = create_toast_message(
                            "warning",
                            f"⚠️ Partial enrichment completed for {task.part_name} ({success_count}/{total_count})",
                            duration=5000
                        )
                    else:
                        message = create_toast_message(
                            "error",
                            f"❌ Enrichment failed for {task.part_name}",
                            duration=5000
                        )
                    
                    await self.websocket_manager.broadcast_to_all(message.model_dump())
                except Exception as e:
                    logger.warning(f"Failed to broadcast completion notification: {e}")
            
        except Exception as e:
            queue.mark_task_failed(task, str(e))
            raise
    
    async def _broadcast_queue_status(self, supplier_name: str):
        """Broadcast queue status update"""
        if not self.websocket_manager:
            return
        
        queue = self.supplier_queues.get(supplier_name)
        if not queue:
            return
        
        try:
            # Get rate limit status
            rate_status = await self.rate_limit_service.check_rate_limit(supplier_name)
            
            message = create_rate_limit_update_message(
                supplier_name=supplier_name,
                current_usage=rate_status.get("current_usage", {}),
                limits=rate_status.get("limits", {}),
                next_reset=rate_status.get("next_reset", {}),
                queue_size=queue.queue_size
            )
            
            await self.websocket_manager.broadcast_to_all(message.model_dump())
        except Exception as e:
            logger.warning(f"Failed to broadcast queue status: {e}")
    
    def get_queue_status(self, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of enrichment queues"""
        if supplier_name:
            supplier_name = supplier_name.upper()
            if supplier_name not in self.supplier_queues:
                return {}
            
            queue = self.supplier_queues[supplier_name]
            return {
                "supplier_name": supplier_name,
                "queue_size": queue.queue_size,
                "running_count": queue.running_count,
                "completed_count": len(queue.completed_tasks),
                "failed_count": len(queue.failed_tasks),
                "estimated_completion": queue.estimate_completion_time(),
                "is_processing": queue.is_processing
            }
        else:
            # Return status for all queues
            status = {}
            for name, queue in self.supplier_queues.items():
                status[name] = {
                    "queue_size": queue.queue_size,
                    "running_count": queue.running_count,
                    "completed_count": len(queue.completed_tasks),
                    "failed_count": len(queue.failed_tasks),
                    "estimated_completion": queue.estimate_completion_time(),
                    "is_processing": queue.is_processing
                }
            return status
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.task_registry.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "part_id": task.part_id,
            "part_name": task.part_name,
            "supplier_name": task.supplier_name,
            "status": task.status,
            "progress_percentage": task.progress_percentage,
            "capabilities": task.capabilities,
            "completed_capabilities": task.completed_capabilities,
            "failed_capabilities": task.failed_capabilities,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "retry_count": task.retry_count
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        task = self.task_registry.get(task_id)
        if not task:
            return False
        
        if task.status in [EnrichmentStatus.COMPLETED, EnrichmentStatus.FAILED, EnrichmentStatus.CANCELLED]:
            return False
        
        task.status = EnrichmentStatus.CANCELLED
        self.processing_tasks.discard(task_id)
        
        # Remove from supplier queue if still pending
        if task.supplier_name in self.supplier_queues:
            queue = self.supplier_queues[task.supplier_name]
            queue.pending_tasks = [t for t in queue.pending_tasks if t.id != task_id]
            queue.running_tasks.discard(task_id)
        
        logger.info(f"Cancelled enrichment task {task_id}")
        return True
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics"""
        total_pending = sum(queue.queue_size for queue in self.supplier_queues.values())
        total_running = sum(queue.running_count for queue in self.supplier_queues.values())
        total_completed = sum(len(queue.completed_tasks) for queue in self.supplier_queues.values())
        total_failed = sum(len(queue.failed_tasks) for queue in self.supplier_queues.values())
        
        return {
            "total_pending": total_pending,
            "total_running": total_running,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "total_queues": len(self.supplier_queues),
            "active_queues": len([q for q in self.supplier_queues.values() if q.is_processing]),
            "queue_details": self.get_queue_status()
        }