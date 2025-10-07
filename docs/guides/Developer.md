# Developer Technical Insights

This document contains verified technical nuggets about how the MakerMatrix system works internally. All details are verified against the actual codebase.

## Task System Architecture

### Task Registration Process
**Auto-Discovery Pattern:** Tasks are automatically discovered and registered at startup through file-based scanning.

**Verified Implementation:**
- File pattern: Any `*_task.py` file in `/MakerMatrix/tasks/` directory
- Discovery happens in `MakerMatrix/tasks/__init__.py:61` when module is imported
- Each task class must inherit from `BaseTask` and define a `task_type` property
- Registration creates a global `TASK_REGISTRY` dictionary mapping task types to classes
- TaskService then instantiates handlers in `_register_modular_handlers()`

**Code Pattern:**
```python
class MyNewTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "my_new_task"  # This becomes the registry key
```

**Startup Log Pattern:**
```
Registered task: part_enrichment -> PartEnrichmentTask      # From __init__.py discovery
Registered task handler: part_enrichment -> PartEnrichmentTask  # From TaskService registration
```

**To Add New Task:** Simply create `my_new_task.py` in tasks directory - it will auto-register on restart.

## WebSocket Service Architecture

### Dynamic Host Resolution
**Environment-Aware Connection:** WebSocket service intelligently determines connection host based on environment and configuration.

**Verified Implementation in `websocket.service.ts:46-74`:**
1. **VITE_API_URL Override:** If `VITE_API_URL` environment variable is set, parse and use that host/protocol
2. **Development Port Detection:** If on ports 5173, 5174, or 3000, fallback to backend on port 8080 with WS protocol
3. **Protocol Mapping:** HTTPS → WSS, HTTP → WS

**Connection Resolution Order:**
```typescript
if (envApiUrl) {
  // Use parsed VITE_API_URL
} else if (developmentPort) {
  // Force ws://localhost:8080 for dev
} else {
  // Use current page host/protocol
}
```

## Authentication Architecture

### JWT Token Flow
**Stateless Authentication:** System uses JWT tokens with refresh token pattern stored in HTTP-only cookies.

**Verified Endpoints:**
- `POST /api/auth/login` - Form-based login (web UI)
- `POST /api/auth/mobile-login` - JSON login (APIs/mobile)
- `POST /api/auth/refresh` - Refresh expired tokens using cookie
- `GET /api/users/me` - Get current user info with JWT

**Token Storage Pattern:**
- **Access Token:** Stored in localStorage as 'auth_token'
- **Refresh Token:** HTTP-only cookie for security
- **WebSocket Auth:** Token passed as query parameter `?token={jwt}`

## Database Session Management

### Repository Pattern Enforcement
**Critical Architecture Rule:** ONLY repositories interact with database sessions - never services or routes directly.

**Verified Pattern in codebase:**
```python
# CORRECT: Repository handles session
with Session(engine) as session:
    repository = PartRepository(engine)
    return repository.get_by_id(session, part_id)

# VIOLATION: Service/route direct DB access
session.add(model)  # Never do this outside repositories
```

**Session Lifecycle:**
- Repositories receive `Session` object as parameter
- Services use `with Session(engine)` pattern
- Tasks create their own sessions for background work
- Routes delegate all DB operations to services

## Development Environment

### dev_manager.py TUI
**Primary Development Tool:** Rich TUI interface manages both backend and frontend servers with integrated monitoring.

**Verified Features:**
- **Auto-restart:** File watching with 5-second debounce
- **Process Management:** Port conflict resolution and health checks
- **Log Aggregation:** Real-time logs from both servers
- **HTTPS/HTTP Toggle:** Dynamic protocol switching

**Usage Pattern:**
```bash
python dev_manager.py  # Start TUI
# Use keyboard shortcuts in TUI to control services
```

**Log File:** `/home/ril3y/MakerMatrix/dev_manager.log` contains startup and service logs

### Virtual Environment
**Standard Environment:** All Python operations use `venv_test` virtual environment.

**Verified Setup:**
```bash
source venv_test/bin/activate  # Required for all Python commands
python -m MakerMatrix.main     # Backend server
```

## API Response Architecture

### Standardized Response Schema
**Consistent API Responses:** All endpoints return standardized ResponseSchema format.

**Verified Schema in `schemas/response.py`:**
```json
{
  "status": "success|error|warning",
  "message": "Human readable message",
  "data": "Response data (any type)",
  "page": "Page number (pagination)",
  "page_size": "Items per page (pagination)",
  "total_parts": "Total count (pagination)"
}
```

**BaseRouter Pattern:** Routes use `BaseRouter.build_success_response()` and `BaseRouter.build_error_response()` for consistency.

## File Upload System

### Image Upload Workflow
**Two-Step Process:** Images uploaded separately then referenced by URL.

**Verified Workflow:**
1. `POST /utility/upload_image` → Returns `{image_id: "uuid"}`
2. Use URL format: `/utility/get_image/{image_id}.{extension}`
3. Reference in part/location: `"image_url": "/utility/get_image/uuid.png"`

**Security:** JWT authentication required for both upload and retrieval.

## Adding Printer Support

### Printer Driver Architecture
**Modular Design:** Printer support is implemented through a driver abstraction layer allowing easy addition of new printer types.

**Verified Architecture:**
- **Location:** `/MakerMatrix/services/printer/` directory
- **Base Class:** `BasePrinter` interface defines required methods
- **Current Implementation:** `BrotherQLPrinter` for Brother QL-series printers
- **Service Layer:** `PrinterManagerService` coordinates printer operations

### Required Implementation Components

#### 1. Printer Driver Class
**File Pattern:** Create `my_printer_driver.py` in `/MakerMatrix/services/printer/`

**Required Methods:**
```python
from typing import Optional, List
from PIL import Image
from dataclasses import dataclass

@dataclass
class LabelSize:
    """Label size information"""
    name: str           # Display name (e.g., "12mm", "29x90mm")
    width_mm: float     # Width in millimeters
    height_mm: float    # Height in millimeters (optional for continuous)
    dots_printable: tuple  # (width_dots, height_dots) or (width_dots, 0)

class MyPrinterDriver:
    """Driver for My Printer Model"""

    def __init__(self, printer_identifier: str, model: str):
        """
        Initialize printer driver

        Args:
            printer_identifier: USB ID, IP address, or serial port
            model: Specific printer model (e.g., "Model-X100")
        """
        self.printer_identifier = printer_identifier
        self.model = model

    async def connect(self) -> bool:
        """
        Establish connection to printer

        Returns:
            True if connection successful, False otherwise
        """
        # Implement connection logic (USB, network, serial)
        pass

    def get_supported_label_sizes(self) -> List[LabelSize]:
        """
        Get list of supported label sizes for this printer

        Returns:
            List of LabelSize objects with dimensions and capabilities
        """
        return [
            LabelSize(
                name="12mm",
                width_mm=12.0,
                height_mm=0,  # 0 for continuous tape
                dots_printable=(106, 0)
            ),
            # Add more label sizes...
        ]

    async def print_label(self, image: Image.Image, label_size: str,
                         copies: int = 1) -> dict:
        """
        Print label image to printer

        Args:
            image: PIL Image object to print
            label_size: Label size identifier (e.g., "12mm", "29x90")
            copies: Number of copies to print

        Returns:
            dict with:
                success: bool
                message: str (error message if failed)
                job_id: Optional[str] (if printer provides job tracking)
        """
        # 1. Validate label size
        # 2. Convert image to printer format (dithering, resolution)
        # 3. Send print command to printer
        # 4. Handle response/errors
        pass

    def get_printer_status(self) -> dict:
        """
        Query printer status

        Returns:
            dict with:
                online: bool
                ready: bool
                error: Optional[str]
                media_type: Optional[str]
                media_width: Optional[float]
        """
        pass
```

#### 2. Image Preparation Requirements

**Critical Considerations:**
- **Resolution Conversion:** Convert image to printer's native DPI
- **Rotation:** Some printers require 90° rotation (e.g., Brother QL 12mm labels)
- **Dithering:** Convert color/grayscale images to monochrome with dithering
- **Size Validation:** Ensure image dimensions match label size

**Verified Pattern from BrotherQLPrinter:**
```python
# Example: Brother QL requires 90° rotation for 12mm labels
if label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0:
    label_image = label_image.rotate(90, expand=True)

# Dithering for monochrome printers
if image.mode != '1':  # Not already monochrome
    image = image.convert('1', dither=Image.FLOYDSTEINBERG)
```

#### 3. Printer Registration in Database

**Schema:** Printers stored in `PrinterModel` table with configuration JSON.

**Registration Pattern:**
```python
from MakerMatrix.models.models import PrinterModel
from sqlmodel import Session, create_engine

def register_printer(session: Session):
    """Register printer in database"""
    printer = PrinterModel(
        name="My Office Printer",
        printer_type="my_printer_model",  # Driver identifier
        connection_type="network",  # "usb", "network", "serial"
        identifier="192.168.1.100",  # Connection string
        model="Model-X100",
        configuration={
            "dpi": 300,
            "scaling_factor": 1.0,
            "rotation_required": False,
            "supports_color": False,
            # Add printer-specific settings
        },
        is_active=True
    )
    session.add(printer)
    session.commit()
```

#### 4. Integration with PrinterManagerService

**Update Service:** Modify `printer_manager_service.py` to support new driver.

**Pattern:**
```python
def _get_printer_driver(self, printer: PrinterModel):
    """Factory method to create appropriate driver instance"""

    if printer.printer_type == "brother_ql":
        return BrotherQLPrinter(
            printer_identifier=printer.identifier,
            model=printer.model
        )
    elif printer.printer_type == "my_printer_model":
        from .my_printer_driver import MyPrinterDriver
        return MyPrinterDriver(
            printer_identifier=printer.identifier,
            model=printer.model
        )
    else:
        raise ValueError(f"Unsupported printer type: {printer.printer_type}")
```

#### 5. API Endpoints (Already Implemented)

**Existing Endpoints Work with New Drivers:**
- `POST /api/printer/print_label` - Print using template
- `POST /api/printer/config` - Configure printer settings
- `GET /api/printer/current_printer` - Get active printer
- `POST /api/preview/template` - Preview label (printer-independent)

**No Changes Needed** - New drivers automatically work with existing API.

### Testing Checklist

#### Connection Testing
- [ ] USB connection successful (if applicable)
- [ ] Network connection successful (if applicable)
- [ ] Serial connection successful (if applicable)
- [ ] Printer status query returns valid data
- [ ] Error handling for offline/disconnected printer

#### Print Testing
- [ ] Basic text-only label prints correctly
- [ ] QR code labels print with correct size/position
- [ ] Multi-line text wraps properly
- [ ] Images print with correct resolution
- [ ] Label size validation works
- [ ] Multiple copies print correctly
- [ ] Print quality is acceptable (no artifacts, correct density)

#### Integration Testing
- [ ] Printer appears in frontend printer selection
- [ ] Configuration saves correctly
- [ ] Template preview matches actual print output
- [ ] All label sizes work correctly
- [ ] Rotation applied correctly (if needed)
- [ ] Error messages display properly in UI

### Common Implementation Patterns

#### USB Communication
```python
import usb.core
import usb.util

def find_usb_printer(vendor_id: int, product_id: int):
    """Find USB printer by vendor/product ID"""
    device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
    if device is None:
        raise ValueError("Printer not found")
    return device
```

#### Network Communication
```python
import socket

def send_to_network_printer(ip: str, port: int, data: bytes):
    """Send data to network printer"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((ip, port))
        sock.sendall(data)
        response = sock.recv(1024)
    return response
```

#### Serial Communication
```python
import serial

def send_to_serial_printer(port: str, baudrate: int, data: bytes):
    """Send data to serial printer"""
    with serial.Serial(port, baudrate, timeout=1) as ser:
        ser.write(data)
        response = ser.read(1024)
    return response
```

### Troubleshooting Guide

**Common Issues:**

1. **Image Appears Rotated**
   - Check if printer requires 90° rotation for certain label sizes
   - Verify image dimensions match expected label size

2. **Print Quality Poor**
   - Adjust dithering algorithm (Floyd-Steinberg, Ordered, Threshold)
   - Check printer DPI settings
   - Verify scaling factor is correct

3. **Label Size Mismatch**
   - Ensure `LabelSize` definitions match printer capabilities
   - Check that label size validation accounts for printer margins
   - Verify dots_printable calculations

4. **Connection Failures**
   - Check permissions for USB/serial access
   - Verify network printer IP and port
   - Test connection outside of application first

5. **Template Rendering Issues**
   - Template processing is printer-independent
   - Issues are likely in image preparation, not template parsing
   - Check `_create_advanced_label_image()` method in PrinterManagerService

### Reference Implementation

**Study Existing Driver:** `/MakerMatrix/services/printer/brother_ql_printer.py`

**Key Features to Review:**
- Label size definitions for Brother QL-800/700/570
- USB device discovery and connection
- Image rotation logic for 12mm labels
- Print command generation
- Status checking

**Complete Example:** Brother QL driver implements all required methods and serves as template for new drivers.

---

## Issues Identified

### Printer/Preview Functionality Problems
**Frontend-Backend API Mismatch:** Frontend calls `/api/printer/preview/*` but preview endpoints moved to `/api/preview/*`.

**Critical Pydantic Schema Error:** Backend crashes with OpenAPI generation:
```
PydanticInvalidForJsonSchema: Cannot generate a JsonSchema for core_schema.CallableSchema
```

**Verified Issues:**
- `settings.service.ts:40` calls `/api/printer/preview/text` (moved to `/api/preview/text`)
- `settings.service.ts:88` calls `/api/printer/preview/advanced` (moved to `/api/preview/advanced`)
- Backend returns 500 errors on OpenAPI endpoint causing timeouts
- Printer endpoints hanging due to schema generation errors

**Solution Status:** ✅ Fixed - Frontend endpoints updated and missing `/api/preview/advanced` endpoint added

### Add Part Modal Missing Description Field
**Issue:** Description field was missing from the Add Part form despite being supported by the API.

**Verified Problem:**
- `CreatePartRequest` interface includes `description?: string` field
- AddPartModal form state missing `description` property
- No description input field in the UI

**✅ Fixed:**
- Added `description: ''` to form state initialization
- Added description field to form reset function
- Added textarea input field for description after Part Number field
- Used full-width layout with proper styling and placeholder text

---

*This document is maintained as a living reference. All entries are verified against actual codebase implementation.*