"""
Printer System Exceptions

This module now imports from the consolidated MakerMatrix.exceptions module
to eliminate duplication and provide consistent error handling.

This is part of Step 12 cleanup to consolidate error handling patterns.
"""

from MakerMatrix.exceptions import (
    PrinterError,
    PrinterNotFoundError,
    PrinterOfflineError,
    PrinterConnectionError,
    InvalidLabelSizeError,
    PrintJobError,
    PrinterBusyError,
    PrinterConfigurationError,
    # Legacy aliases for backward compatibility
    LabelTooLargeError,
    LabelSizeError,
    UnsupportedOperationError,
    PreviewGenerationError,
    PrinterDriverError,
)

# Re-export for backward compatibility
__all__ = [
    "PrinterError",
    "PrinterNotFoundError",
    "PrinterOfflineError",
    "PrinterConnectionError",
    "InvalidLabelSizeError",
    "PrintJobError",
    "LabelTooLargeError",
    "PrinterBusyError",
    "UnsupportedOperationError",
    "PrinterConfigurationError",
    "PreviewGenerationError",
    "PrinterDriverError",
    "LabelSizeError",  # Legacy
]
