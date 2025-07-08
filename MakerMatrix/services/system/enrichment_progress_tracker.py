"""
Enrichment Progress Tracker Service.
Handles progress tracking and reporting for enrichment operations using observer pattern.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ProgressEventType(Enum):
    """Types of progress events"""
    STARTED = "started"
    PROGRESS = "progress"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    CANCELLED = "cancelled"


class EnrichmentProgressTracker:
    """Progress tracking and reporting for enrichment operations"""
    
    def __init__(self, task_id: Optional[str] = None):
        """
        Initialize progress tracker.
        
        Args:
            task_id: Optional task ID for tracking
        """
        self.task_id = task_id
        self.callbacks: List[Callable] = []
        self.current_step = 0
        self.total_steps = 0
        self.current_progress = 0.0
        self.status = "initialized"
        self.start_time = None
        self.end_time = None
        self.current_message = ""
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.cancelled = False
        
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a progress callback function.
        
        Args:
            callback: Function to call with progress updates
        """
        if callback and callable(callback):
            self.callbacks.append(callback)
            logger.debug(f"Registered progress callback for task {self.task_id}")
    
    def start_tracking(self, total_steps: int, message: str = "Starting enrichment") -> None:
        """
        Start progress tracking.
        
        Args:
            total_steps: Total number of steps to track
            message: Initial message
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.current_progress = 0.0
        self.start_time = datetime.utcnow()
        self.status = "running"
        self.current_message = message
        
        self._emit_event(ProgressEventType.STARTED, {
            'message': message,
            'total_steps': total_steps,
            'start_time': self.start_time.isoformat()
        })
        
        logger.info(f"Started progress tracking for task {self.task_id}: {message}")
    
    def update_progress(self, current_step: int, message: str = "", additional_data: Dict[str, Any] = None) -> None:
        """
        Update progress with current step.
        
        Args:
            current_step: Current step number
            message: Progress message
            additional_data: Additional data to include in event
        """
        if self.cancelled:
            return
            
        self.current_step = current_step
        self.current_message = message
        
        # Calculate progress percentage
        if self.total_steps > 0:
            self.current_progress = (current_step / self.total_steps) * 100
        else:
            self.current_progress = 0.0
        
        event_data = {
            'current_step': current_step,
            'total_steps': self.total_steps,
            'progress_percentage': self.current_progress,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if additional_data:
            event_data.update(additional_data)
        
        self._emit_event(ProgressEventType.PROGRESS, event_data)
        
        logger.debug(f"Progress update for task {self.task_id}: {current_step}/{self.total_steps} - {message}")
    
    def increment_progress(self, message: str = "", additional_data: Dict[str, Any] = None) -> None:
        """
        Increment progress by one step.
        
        Args:
            message: Progress message
            additional_data: Additional data to include in event
        """
        self.update_progress(self.current_step + 1, message, additional_data)
    
    def report_success(self, message: str = "Operation completed successfully", 
                      result_data: Dict[str, Any] = None) -> None:
        """
        Report successful completion.
        
        Args:
            message: Success message
            result_data: Result data to include
        """
        self.status = "completed"
        self.end_time = datetime.utcnow()
        self.current_message = message
        self.current_progress = 100.0
        
        event_data = {
            'message': message,
            'end_time': self.end_time.isoformat(),
            'duration': self._calculate_duration(),
            'progress_percentage': 100.0
        }
        
        if result_data:
            event_data['result_data'] = result_data
        
        self._emit_event(ProgressEventType.SUCCESS, event_data)
        
        logger.info(f"Success reported for task {self.task_id}: {message}")
    
    def report_error(self, error: Exception, message: str = "", 
                    context: Dict[str, Any] = None) -> None:
        """
        Report an error.
        
        Args:
            error: Exception that occurred
            message: Error message
            context: Additional context information
        """
        self.status = "failed"
        self.end_time = datetime.utcnow()
        
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'message': message or str(error),
            'timestamp': datetime.utcnow().isoformat(),
            'duration': self._calculate_duration()
        }
        
        if context:
            error_data['context'] = context
        
        self.errors.append(error_data)
        
        self._emit_event(ProgressEventType.ERROR, error_data)
        
        logger.error(f"Error reported for task {self.task_id}: {message} - {error}")
    
    def report_warning(self, warning: str, context: Dict[str, Any] = None) -> None:
        """
        Report a warning.
        
        Args:
            warning: Warning message
            context: Additional context information
        """
        warning_data = {
            'message': warning,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if context:
            warning_data['context'] = context
        
        self.warnings.append(warning_data)
        
        self._emit_event(ProgressEventType.WARNING, warning_data)
        
        logger.warning(f"Warning reported for task {self.task_id}: {warning}")
    
    def cancel(self, message: str = "Operation cancelled") -> None:
        """
        Cancel the operation.
        
        Args:
            message: Cancellation message
        """
        self.cancelled = True
        self.status = "cancelled"
        self.end_time = datetime.utcnow()
        self.current_message = message
        
        event_data = {
            'message': message,
            'end_time': self.end_time.isoformat(),
            'duration': self._calculate_duration()
        }
        
        self._emit_event(ProgressEventType.CANCELLED, event_data)
        
        logger.info(f"Cancellation reported for task {self.task_id}: {message}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Get current progress status.
        
        Returns:
            Dict with current status information
        """
        return {
            'task_id': self.task_id,
            'status': self.status,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percentage': self.current_progress,
            'current_message': self.current_message,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self._calculate_duration(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'cancelled': self.cancelled
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed progress status including events and errors.
        
        Returns:
            Dict with detailed status information
        """
        status = self.get_current_status()
        status.update({
            'events': self.events,
            'errors': self.errors,
            'warnings': self.warnings
        })
        return status
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get operation summary.
        
        Returns:
            Dict with operation summary
        """
        return {
            'task_id': self.task_id,
            'status': self.status,
            'completed_steps': self.current_step,
            'total_steps': self.total_steps,
            'success_rate': (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0,
            'duration': self._calculate_duration(),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'cancelled': self.cancelled
        }
    
    def is_completed(self) -> bool:
        """Check if operation is completed"""
        return self.status in ["completed", "failed", "cancelled"]
    
    def is_running(self) -> bool:
        """Check if operation is still running"""
        return self.status == "running"
    
    def has_errors(self) -> bool:
        """Check if operation has errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if operation has warnings"""
        return len(self.warnings) > 0
    
    def _emit_event(self, event_type: ProgressEventType, event_data: Dict[str, Any]) -> None:
        """
        Emit progress event to all registered callbacks.
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        event = {
            'event_type': event_type.value,
            'task_id': self.task_id,
            'timestamp': datetime.utcnow().isoformat(),
            **event_data
        }
        
        self.events.append(event)
        
        # Call all registered callbacks
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _calculate_duration(self) -> Optional[float]:
        """
        Calculate operation duration in seconds.
        
        Returns:
            Duration in seconds or None if not started
        """
        if not self.start_time:
            return None
        
        end_time = self.end_time or datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        return round(duration, 2)


class MultiStepProgressTracker:
    """Progress tracker for multi-step operations with sub-steps"""
    
    def __init__(self, task_id: Optional[str] = None):
        """
        Initialize multi-step progress tracker.
        
        Args:
            task_id: Optional task ID for tracking
        """
        self.task_id = task_id
        self.main_tracker = EnrichmentProgressTracker(task_id)
        self.step_trackers: Dict[str, EnrichmentProgressTracker] = {}
        self.current_step_key = None
        
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for main tracker"""
        self.main_tracker.register_callback(callback)
    
    def start_tracking(self, total_steps: int, message: str = "Starting multi-step operation") -> None:
        """Start main progress tracking"""
        self.main_tracker.start_tracking(total_steps, message)
    
    def start_step(self, step_key: str, step_name: str, sub_steps: int = 1) -> EnrichmentProgressTracker:
        """
        Start a new step with its own progress tracker.
        
        Args:
            step_key: Unique key for the step
            step_name: Human-readable step name
            sub_steps: Number of sub-steps in this step
            
        Returns:
            Progress tracker for this step
        """
        step_tracker = EnrichmentProgressTracker(f"{self.task_id}_{step_key}")
        step_tracker.start_tracking(sub_steps, f"Starting {step_name}")
        
        self.step_trackers[step_key] = step_tracker
        self.current_step_key = step_key
        
        # Update main tracker
        self.main_tracker.update_progress(
            self.main_tracker.current_step + 1,
            f"Starting {step_name}",
            {'current_step_key': step_key}
        )
        
        return step_tracker
    
    def complete_step(self, step_key: str, message: str = "Step completed") -> None:
        """
        Complete a step.
        
        Args:
            step_key: Key of the step to complete
            message: Completion message
        """
        if step_key in self.step_trackers:
            step_tracker = self.step_trackers[step_key]
            step_tracker.report_success(message)
            
            # Update main tracker
            self.main_tracker.update_progress(
                self.main_tracker.current_step,
                f"Completed {message}",
                {'completed_step_key': step_key}
            )
    
    def get_step_tracker(self, step_key: str) -> Optional[EnrichmentProgressTracker]:
        """Get progress tracker for a specific step"""
        return self.step_trackers.get(step_key)
    
    def get_current_step_tracker(self) -> Optional[EnrichmentProgressTracker]:
        """Get progress tracker for current step"""
        if self.current_step_key:
            return self.step_trackers.get(self.current_step_key)
        return None
    
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall status including all steps"""
        status = self.main_tracker.get_current_status()
        status['steps'] = {
            key: tracker.get_current_status() 
            for key, tracker in self.step_trackers.items()
        }
        return status