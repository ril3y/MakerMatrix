"""
Base printer interfaces and classes.
"""
from .printer_interface import (
    PrinterInterface,
    BasePrinter,
    PrinterStatus,
    PrinterCapability,
    LabelSize,
    PrintJobResult,
    PreviewResult,
    PrinterInfo,
    TestResult
)
from .exceptions import (
    PrinterError,
    PrinterNotFoundError,
    PrinterOfflineError,
    PrinterConnectionError,
    InvalidLabelSizeError,
    PrintJobError,
    LabelTooLargeError,
    PrinterBusyError,
    UnsupportedOperationError,
    PrinterConfigurationError,
    PreviewGenerationError,
    PrinterDriverError,
    LabelSizeError  # Legacy
)

__all__ = [
    "PrinterInterface",
    "BasePrinter", 
    "PrinterStatus",
    "PrinterCapability",
    "LabelSize",
    "PrintJobResult",
    "PreviewResult",
    "PrinterInfo",
    "TestResult",
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
    "LabelSizeError"
]