"""
Modern printer interface using Python protocols for type safety and modularity.
"""
from abc import ABC, abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid

from PIL import Image


class PrinterStatus(Enum):
    """Printer status enumeration."""
    READY = "ready"
    PRINTING = "printing"
    ERROR = "error"
    OFFLINE = "offline"
    OUT_OF_PAPER = "out_of_paper"
    OUT_OF_INK = "out_of_ink"
    MAINTENANCE_REQUIRED = "maintenance_required"


class PrinterCapability(Enum):
    """Printer capability enumeration."""
    QR_CODES = "qr_codes"
    BARCODES = "barcodes"
    IMAGES = "images"
    COLOR = "color"
    DUPLEX = "duplex"
    CONTINUOUS_LABELS = "continuous_labels"
    DIE_CUT_LABELS = "die_cut_labels"


@dataclass
class LabelSize:
    """Label size specification."""
    name: str
    width_mm: float
    height_mm: Optional[float] = None  # None for continuous labels
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    
    def is_continuous(self) -> bool:
        """Check if this is a continuous label size."""
        return self.height_mm is None


@dataclass
class PrintJobResult:
    """Result of a print job."""
    success: bool
    job_id: str
    message: str = ""
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PreviewResult:
    """Result of label preview generation."""
    image_data: bytes = None
    format: str = "png"  # png, jpg, etc.
    width_px: int = None
    height_px: int = None
    label_size: LabelSize = None
    message: str = ""
    # API compatibility fields
    success: bool = True
    preview_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    error: Optional[str] = None


@dataclass
class PrinterInfo:
    """Information about a printer."""
    id: str
    name: str
    driver: str
    model: str
    status: PrinterStatus
    capabilities: List[PrinterCapability]
    backend: str
    identifier: str
    is_default: bool = False
    last_seen: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class TestResult:
    """Result of printer connectivity test."""
    success: bool
    response_time_ms: Optional[float] = None
    message: str = ""
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PrinterInterface(Protocol):
    """
    Modern printer interface using Python protocols.
    All printer drivers must implement this interface.
    """
    
    async def print_label(self, image: Image.Image, label_size: str, copies: int = 1) -> PrintJobResult:
        """
        Print a label image.
        
        Args:
            image: PIL Image to print
            label_size: Label size identifier (e.g., "12", "29", "62")
            copies: Number of copies to print
            
        Returns:
            PrintJobResult with success status and job ID
        """
        ...
    
    async def preview_label(self, image: Image.Image, label_size: str) -> PreviewResult:
        """
        Generate a preview of what the label will look like when printed.
        
        Args:
            image: PIL Image to preview
            label_size: Label size identifier
            
        Returns:
            PreviewResult with preview image data
        """
        ...
    
    async def get_status(self) -> PrinterStatus:
        """Get current printer status."""
        ...
    
    async def get_capabilities(self) -> List[PrinterCapability]:
        """Get list of printer capabilities."""
        ...
    
    async def test_connection(self) -> TestResult:
        """Test printer connectivity and availability."""
        ...
    
    def get_supported_label_sizes(self) -> List[LabelSize]:
        """Get list of supported label sizes."""
        ...
    
    def get_printer_info(self) -> PrinterInfo:
        """Get printer information."""
        ...
    
    async def cancel_current_job(self) -> bool:
        """Cancel the current print job."""
        ...


class BasePrinter(ABC):
    """
    Abstract base class for all printer implementations.
    Provides common functionality and enforces the interface.
    """
    
    def __init__(self, printer_id: str, name: str, model: str, backend: str, identifier: str):
        self.printer_id = printer_id
        self.name = name
        self.model = model
        self.backend = backend
        self.identifier = identifier
        self._status = PrinterStatus.OFFLINE
        self._last_error: Optional[str] = None
        
    @abstractmethod
    async def print_label(self, image: Image.Image, label_size: str, copies: int = 1) -> PrintJobResult:
        """Print a label image."""
        pass
    
    @abstractmethod
    async def preview_label(self, image: Image.Image, label_size: str) -> PreviewResult:
        """Generate label preview."""
        pass
    
    @abstractmethod
    async def get_status(self) -> PrinterStatus:
        """Get printer status."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[PrinterCapability]:
        """Get printer capabilities."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> TestResult:
        """Test printer connection."""
        pass
    
    @abstractmethod
    def get_supported_label_sizes(self) -> List[LabelSize]:
        """Get supported label sizes."""
        pass
    
    async def cancel_current_job(self) -> bool:
        """Default implementation for job cancellation."""
        return False
    
    def get_printer_info(self) -> PrinterInfo:
        """Get printer information."""
        return PrinterInfo(
            id=self.printer_id,
            name=self.name,
            driver=self.__class__.__name__,
            model=self.model,
            status=self._status,
            capabilities=[],  # Override in subclass
            backend=self.backend,
            identifier=self.identifier,
            error_message=self._last_error
        )
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        return f"job_{uuid.uuid4().hex[:8]}"
    
    def _set_status(self, status: PrinterStatus, error: Optional[str] = None):
        """Update printer status."""
        self._status = status
        self._last_error = error