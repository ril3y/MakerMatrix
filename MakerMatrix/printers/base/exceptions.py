"""
Custom printer exceptions for better error handling and debugging.
"""
from typing import Optional


class PrinterError(Exception):
    """Base exception for all printer-related errors."""
    
    def __init__(self, message: str, printer_id: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.printer_id = printer_id
        self.error_code = error_code
        self.message = message


class PrinterNotFoundError(PrinterError):
    """Raised when a requested printer cannot be found."""
    
    def __init__(self, printer_id: str):
        super().__init__(f"Printer not found: {printer_id}", printer_id=printer_id, error_code="PRINTER_NOT_FOUND")


class PrinterOfflineError(PrinterError):
    """Raised when trying to use an offline printer."""
    
    def __init__(self, printer_id: str, message: str = "Printer is offline"):
        super().__init__(message, printer_id=printer_id, error_code="PRINTER_OFFLINE")


class PrinterConnectionError(PrinterError):
    """Raised when unable to connect to printer."""
    
    def __init__(self, printer_id: str, message: str = "Cannot connect to printer"):
        super().__init__(message, printer_id=printer_id, error_code="CONNECTION_ERROR")


class InvalidLabelSizeError(PrinterError):
    """Raised when an invalid label size is specified."""
    
    def __init__(self, label_size: str, printer_id: Optional[str] = None, supported_sizes: Optional[list] = None):
        message = f"Invalid label size: {label_size}"
        if supported_sizes:
            message += f". Supported sizes: {', '.join(supported_sizes)}"
        super().__init__(message, printer_id=printer_id, error_code="INVALID_LABEL_SIZE")
        self.label_size = label_size
        self.supported_sizes = supported_sizes or []


class PrintJobError(PrinterError):
    """Raised when a print job fails."""
    
    def __init__(self, message: str, printer_id: Optional[str] = None, job_id: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="PRINT_JOB_ERROR")
        self.job_id = job_id


class LabelTooLargeError(PrinterError):
    """Raised when label content exceeds printer capabilities."""
    
    def __init__(self, width: int, height: int, max_width: int, max_height: int, printer_id: Optional[str] = None):
        message = f"Label size ({width}x{height}) exceeds printer limits ({max_width}x{max_height})"
        super().__init__(message, printer_id=printer_id, error_code="LABEL_TOO_LARGE")
        self.width = width
        self.height = height
        self.max_width = max_width
        self.max_height = max_height


class PrinterBusyError(PrinterError):
    """Raised when printer is busy with another job."""
    
    def __init__(self, printer_id: str, current_job_id: Optional[str] = None):
        message = "Printer is currently busy"
        if current_job_id:
            message += f" with job {current_job_id}"
        super().__init__(message, printer_id=printer_id, error_code="PRINTER_BUSY")
        self.current_job_id = current_job_id


class UnsupportedOperationError(PrinterError):
    """Raised when trying to perform an unsupported operation."""
    
    def __init__(self, operation: str, printer_id: Optional[str] = None):
        super().__init__(f"Unsupported operation: {operation}", printer_id=printer_id, error_code="UNSUPPORTED_OPERATION")
        self.operation = operation


class PrinterConfigurationError(PrinterError):
    """Raised when printer configuration is invalid."""
    
    def __init__(self, message: str, printer_id: Optional[str] = None, config_field: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="CONFIGURATION_ERROR")
        self.config_field = config_field


class PreviewGenerationError(PrinterError):
    """Raised when label preview generation fails."""
    
    def __init__(self, message: str, printer_id: Optional[str] = None):
        super().__init__(message, printer_id=printer_id, error_code="PREVIEW_ERROR")


class PrinterDriverError(PrinterError):
    """Raised when there's an error with the printer driver."""
    
    def __init__(self, message: str, driver_name: str, printer_id: Optional[str] = None):
        super().__init__(f"Driver error ({driver_name}): {message}", printer_id=printer_id, error_code="DRIVER_ERROR")
        self.driver_name = driver_name


# Legacy exception for backward compatibility
class LabelSizeError(InvalidLabelSizeError):
    """Legacy exception - use InvalidLabelSizeError instead."""
    
    def __init__(self, width: float, length: float, max_width: float, max_length: float):
        # Convert to pixel-based error for compatibility
        super().__init__(
            label_size=f"{width}x{length}",
            supported_sizes=[f"{max_width}x{max_length}"]
        )
        # Store original values for backward compatibility
        self.width = width
        self.length = length
        self.max_width = max_width
        self.max_length = max_length