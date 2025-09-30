"""
Printer manager service for managing multiple printers and routing print jobs.
"""
import uuid
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from MakerMatrix.printers.base import (
    PrinterInterface,
    PrintJobResult,
    PreviewResult,
    PrinterStatus,
    PrinterCapability,
    LabelSize,
    PrinterInfo,
    TestResult,
    PrinterError,
    PrinterOfflineError
)
from MakerMatrix.printers.drivers.mock.driver import MockPrinter
from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern
from MakerMatrix.services.printer.label_service import LabelService
from MakerMatrix.services.printer.template_processor import TemplateProcessor
from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.models.label_template_models import LabelTemplateModel
from MakerMatrix.repositories.label_template_repository import LabelTemplateRepository


@dataclass
class PrintJob:
    """Represents a print job with routing information."""
    job_id: str
    printer_id: str
    job_type: str  # "qr_code", "text", "part_name", "combined"
    status: str  # "pending", "printing", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[PrintJobResult] = None
    error: Optional[str] = None


class PrinterManagerService:
    """Service for managing multiple printers and routing print jobs."""
    
    SUPPORTED_DRIVERS = {
        "MockPrinter": MockPrinter,
        "BrotherQLModern": BrotherQLModern
    }
    
    def __init__(self):
        self.printers: Dict[str, PrinterInterface] = {}
        self.print_jobs: Dict[str, PrintJob] = {}
        self.default_printer_id: Optional[str] = None
        self._job_lock = asyncio.Lock()
        self.template_processor = TemplateProcessor()
        self.template_repository = LabelTemplateRepository()
    
    async def register_printer(self, printer: PrinterInterface) -> bool:
        """
        Register a printer with the manager.
        
        Args:
            printer: Printer instance implementing PrinterInterface
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Get printer info
            info = printer.get_printer_info()
            print(f"Registering printer: {info.id} - {info.name}")
            
            # Store printer
            self.printers[info.id] = printer
            print(f"Stored printer {info.id}. Total printers: {len(self.printers)}")
            
            # Set as default if this is the first printer
            if not self.default_printer_id:
                self.default_printer_id = info.id
                print(f"Set default printer to: {info.id}")
            
            return True
            
        except Exception as e:
            print(f"Failed to register printer: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def unregister_printer(self, printer_id: str) -> bool:
        """Remove a printer from the manager."""
        if printer_id in self.printers:
            del self.printers[printer_id]
            
            # Update default if needed
            if self.default_printer_id == printer_id:
                self.default_printer_id = next(iter(self.printers.keys()), None)
            
            return True
        return False
    
    async def get_printer(self, printer_id: Optional[str] = None) -> Optional[PrinterInterface]:
        """Get a printer by ID or the default printer."""
        if printer_id and printer_id in self.printers:
            return self.printers[printer_id]
        elif self.default_printer_id:
            return self.printers[self.default_printer_id]
        return None
    
    def get_default_printer(self) -> Optional[PrinterInterface]:
        """Get the default printer."""
        return self.get_printer()
    
    def set_default_printer(self, printer_id: str) -> bool:
        """Set the default printer."""
        if printer_id in self.printers:
            self.default_printer_id = printer_id
            return True
        return False
    
    async def list_printers(self, enabled_only: bool = True) -> List[PrinterInterface]:
        """List all registered printers."""
        printers = list(self.printers.values())
        print(f"list_printers called: {len(printers)} printers found")
        for printer in printers:
            info = printer.get_printer_info()
            print(f"  - {info.id}: {info.name} ({info.model})")
        return printers
    
    async def get_printer_status(self, printer_id: Optional[str] = None) -> Optional[PrinterStatus]:
        """Get status of a specific printer or default printer."""
        printer = await self.get_printer(printer_id)
        if printer:
            return await printer.get_status()
        return None
    
    async def get_all_printer_statuses(self) -> Dict[str, PrinterStatus]:
        """Get status of all printers."""
        statuses = {}
        
        for printer_id, printer in self.printers.items():
            try:
                statuses[printer_id] = await printer.get_status()
            except Exception as e:
                print(f"Failed to get status for printer {printer_id}: {e}")
                statuses[printer_id] = PrinterStatus.ERROR
        
        return statuses
    
    async def test_printer_connection(self, printer_id: Optional[str] = None) -> Optional[TestResult]:
        """Test connection to a specific printer."""
        printer = await self.get_printer(printer_id)
        if printer:
            return await printer.test_connection()
        return None
    
    async def test_all_printers(self) -> Dict[str, TestResult]:
        """Test connections to all enabled printers."""
        results = {}
        
        for printer_id, printer in self.printers.items():
            try:
                results[printer_id] = await printer.test_connection()
            except Exception as e:
                results[printer_id] = TestResult(
                    success=False,
                    error=f"Test failed: {str(e)}"
                )
        
        return results
    
    async def route_print_job(self, job_type: str, printer_id: Optional[str] = None, 
                              **job_params) -> PrintJob:
        """Route a print job to the appropriate printer."""
        async with self._job_lock:
            # Create job record
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            job = PrintJob(
                job_id=job_id,
                printer_id=printer_id or self.default_printer_id or "unknown",
                job_type=job_type,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            self.print_jobs[job_id] = job
            
            try:
                # Get printer
                printer = await self.get_printer(printer_id)
                if not printer:
                    raise PrinterError("No printer available for job")
                
                job.status = "printing"
                
                # Route to appropriate print method based on job type
                if job_type == "text":
                    result = await printer.print_label(
                        job_params["image"], 
                        job_params["label_size"], 
                        job_params.get("copies", 1)
                    )
                elif job_type == "qr_code":
                    result = await printer.print_label(
                        job_params["image"], 
                        job_params["label_size"], 
                        job_params.get("copies", 1)
                    )
                elif job_type == "part_name":
                    result = await printer.print_label(
                        job_params["image"], 
                        job_params["label_size"], 
                        job_params.get("copies", 1)
                    )
                elif job_type == "combined":
                    result = await printer.print_label(
                        job_params["image"], 
                        job_params["label_size"], 
                        job_params.get("copies", 1)
                    )
                else:
                    raise ValueError(f"Unknown job type: {job_type}")
                
                # Update job with result
                job.status = "completed" if result.success else "failed"
                job.result = result
                job.completed_at = datetime.utcnow()
                
                if not result.success:
                    job.error = result.error
                
                return job
                
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.utcnow()
                return job
    
    def get_print_job(self, job_id: str) -> Optional[PrintJob]:
        """Get a print job by ID."""
        return self.print_jobs.get(job_id)
    
    def list_print_jobs(self, limit: int = 100, printer_id: Optional[str] = None) -> List[PrintJob]:
        """List recent print jobs."""
        jobs = list(self.print_jobs.values())
        
        # Filter by printer if specified
        if printer_id:
            jobs = [job for job in jobs if job.printer_id == printer_id]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return jobs[:limit]
    
    async def cancel_print_job(self, job_id: str) -> bool:
        """Cancel a print job."""
        job = self.get_print_job(job_id)
        if not job or job.status not in ["pending", "printing"]:
            return False
        
        # Try to cancel on the printer
        printer = await self.get_printer(job.printer_id)
        if printer:
            try:
                cancelled = await printer.cancel_current_job()
                if cancelled:
                    job.status = "cancelled"
                    job.completed_at = datetime.utcnow()
                    return True
            except Exception as e:
                print(f"Failed to cancel job on printer: {e}")
        
        return False
    
    async def get_supported_label_sizes(self, printer_id: Optional[str] = None) -> List[LabelSize]:
        """Get supported label sizes for a printer."""
        printer = await self.get_printer(printer_id)
        if printer:
            return printer.get_supported_label_sizes()
        return []
    
    async def get_printer_capabilities(self, printer_id: Optional[str] = None) -> List[PrinterCapability]:
        """Get capabilities of a printer."""
        printer = await self.get_printer(printer_id)
        if printer:
            return await printer.get_capabilities()
        return []
    
    
    def clear_completed_jobs(self, older_than_hours: int = 24) -> int:
        """Clear completed jobs older than specified hours."""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        jobs_to_remove = []
        
        for job_id, job in self.print_jobs.items():
            if (job.status in ["completed", "failed", "cancelled"] and 
                job.completed_at and job.completed_at < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.print_jobs[job_id]
        
        return len(jobs_to_remove)
    
    async def print_template_label(self, printer_id: str, template_id: str, data: dict,
                                   label_size: str, copies: int = 1) -> PrintJobResult:
        """Print a label using a saved template."""
        printer = await self.get_printer(printer_id)
        if not printer:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Printer {printer_id} not found"
            )

        try:
            # Get the template from database
            from sqlmodel import Session
            from MakerMatrix.models.models import engine

            with Session(engine) as session:
                template = self.template_repository.get_by_id(session, template_id)
                if not template:
                    return PrintJobResult(
                        success=False,
                        job_id="",
                        message="",
                        error=f"Template {template_id} not found"
                    )

                # Create print settings
                print_settings = PrintSettings(
                    label_size=template.label_height_mm,  # Brother QL uses height as the "size"
                    dpi=300,
                    qr_scale=template.qr_scale,
                    qr_min_size_mm=template.qr_min_size_mm
                )

                # Process template to create label image
                label_image = self.template_processor.process_template(
                    template, data, print_settings
                )

                # Update template usage
                template.update_usage()
                session.add(template)
                session.commit()

                # Print the label
                return await printer.print_label(label_image, label_size, copies)

        except Exception as e:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Failed to print template label: {str(e)}"
            )

    async def preview_template_label(self, template_id: str, data: dict) -> PreviewResult:
        """Preview a label using a saved template."""
        try:
            from sqlmodel import Session
            from MakerMatrix.models.models import engine

            with Session(engine) as session:
                template = self.template_repository.get_by_id(session, template_id)
                if not template:
                    return PreviewResult(
                        success=False,
                        error=f"Template {template_id} not found"
                    )

                # Create print settings for preview
                print_settings = PrintSettings(
                    label_size=template.label_height_mm,
                    dpi=300,
                    qr_scale=template.qr_scale,
                    qr_min_size_mm=template.qr_min_size_mm
                )

                # Process template to create preview image
                preview_image = self.template_processor.process_template(
                    template, data, print_settings
                )

                # Convert image to base64 for preview
                import io
                import base64

                buffer = io.BytesIO()
                preview_image.save(buffer, format='PNG')
                image_data = base64.b64encode(buffer.getvalue()).decode()

                return PreviewResult(
                    success=True,
                    preview_url=f"data:image/png;base64,{image_data}",
                    width=preview_image.width,
                    height=preview_image.height
                )

        except Exception as e:
            return PreviewResult(
                success=False,
                error=f"Failed to preview template label: {str(e)}"
            )

    async def _create_advanced_label_image(self, template: str, data: dict, label_size: str,
                                          label_length: int = None, options: dict = None):
        """Create an advanced label image with template processing and QR codes (legacy method)."""
        from PIL import Image, ImageDraw, ImageFont
        import qrcode
        import re
        
        options = options or {}
        
        # Get label size info
        # We need to get a printer to get supported sizes - use any available printer
        printer = await self.get_printer()
        if not printer:
            raise Exception("No printer available for label creation")
            
        supported_sizes = printer.get_supported_label_sizes()
        label_info = None
        for size in supported_sizes:
            if size.name == label_size:
                label_info = size
                break
        
        if not label_info:
            raise Exception(f"Label size {label_size} not supported")
        
        # Determine dimensions
        if label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0:
            # Create appropriate length x 12mm image that will be rotated 90°
            if label_length and label_length > 20:
                # Use custom length, but adjust for scaling factor to achieve desired output
                # Target output length / 0.905 scaling ratio = input length needed
                target_length = label_length / 0.905  # Compensate for printer scaling
                width = int(target_length * 300 / 25.4)
                print(f"Using custom label length: {label_length}mm -> {target_length:.1f}mm input -> {width}px width")
            else:
                width = int(43.1 * 300 / 25.4)  # ~508 pixels for 43.1mm (39mm output)
                print(f"Using default label length: 43.1mm input -> {width}px width (label_length was: {label_length})")
            height = int(12 * 300 / 25.4)  # 141 pixels for 12mm
        elif label_info.height_mm:  # Other die-cut labels
            width = int(label_info.width_px or 400)
            height = int(label_info.height_px or 200)
        else:  # Continuous label - use width and calculate height based on content
            width = int(label_info.width_px or 400)
            if label_length:
                height = int(label_length * 300 / 25.4)
            else:
                height = max(100, 200)  # Default height
        
        # Parse template for QR codes and text
        # Check for both {qr} and {qr=field} syntax
        has_simple_qr = '{qr}' in template
        qr_field_matches = re.findall(r'\{qr=([^}]+)\}', template)
        has_qr = has_simple_qr or len(qr_field_matches) > 0 or options.get('include_qr', False)

        # Replace text placeholders using template processor's method
        processed_text = self.template_processor._process_template_text(template, data)
        
        # Create base image
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        if has_qr:
            # Create optimized layout with QR code and text using improved sizing logic

            # Create print settings for optimal QR sizing
            label_height_mm = label_info.width_mm if label_info else 12.0  # Label width becomes height in output
            print_settings = PrintSettings(
                label_size=label_height_mm,
                dpi=300,  # Standard Brother QL DPI
                qr_scale=0.95,  # Use 95% of available height for better scanning
                qr_min_size_mm=8.0,  # Minimum 8mm for phone scanning
                qr_max_margin_mm=1.0  # 1mm max margin
            )

            # Generate optimized QR code using LabelService
            # Determine QR data based on template syntax
            if qr_field_matches:
                # User specified {qr=field_name}
                qr_field = qr_field_matches[0]
                qr_data = str(data.get(qr_field, 'UNKNOWN'))
                print(f"[DEBUG] Using QR field '{qr_field}': {qr_data}")
                part_dict = {'id': qr_data}
            else:
                # Default to MM:id format
                part_id = data.get('id') or data.get('part_id') or 'UNKNOWN'
                qr_data = f"MM:{part_id}"
                print(f"[DEBUG] Using default QR data: {qr_data}")
                part_dict = {'id': qr_data}

            qr_image = LabelService.generate_optimized_qr(part_dict, print_settings)
            qr_size = qr_image.width  # Get actual optimized size

            # Calculate layout - absolute minimal margins to maximize text size
            if label_info and (label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0):
                # For 12mm labels, use absolute minimal margins
                left_padding = 2  # ~0.17mm
                qr_text_spacing = 4  # ~0.34mm between QR and text
                right_padding = 2  # ~0.17mm

                # Calculate available text area
                text_x = left_padding + qr_size + qr_text_spacing
                text_width = width - text_x - right_padding
                text_height = height - 4  # 2px top/bottom margins (~0.17mm each)

                print(f"[DEBUG] 12mm QR+text layout: QR={qr_size}px, text_area={text_width}x{text_height}px")
            else:
                # For other label sizes, use absolute minimal margins
                min_qr_size = max(qr_size, height // 4)
                qr_size = max(min_qr_size, min(height - 6, width // 3))

                if qr_image.width != qr_size:
                    qr_image = qr_image.resize((qr_size, qr_size), Image.Resampling.LANCZOS)

                left_padding = 2
                qr_text_spacing = 4
                right_padding = 2

                text_x = left_padding + qr_size + qr_text_spacing
                text_width = width - text_x - right_padding
                text_height = height - 4  # 2px top/bottom margins

                print(f"[DEBUG] Other label QR+text layout: QR={qr_size}px, text_area={text_width}x{text_height}px")

            # Paste QR code (left side)
            qr_y = (height - qr_size) // 2
            image.paste(qr_image, (left_padding if 'left_padding' in locals() else 10, qr_y))

            # Optimized text sizing for the available space
            max_text_width = text_width

            # Maximize text size for available space
            clean_text = processed_text.strip()
            is_single_line = '\n' not in clean_text

            # Use nearly all available height for maximum text size
            if is_single_line:
                # Single line - use 98% of available height
                max_font_height = int(text_height * 0.98)
                print(f"[DEBUG] Single line, max height: {max_font_height}px from {text_height}px available")

                font_size = max_font_height
                font = None

                while font_size > 8:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                        break

                    test_bbox = draw.textbbox((0, 0), clean_text, font=font)
                    test_width = test_bbox[2] - test_bbox[0]

                    if test_width <= max_text_width:
                        print(f"[DEBUG] Single line fits at font_size={font_size}px")
                        break

                    font_size = int(font_size * 0.95)
            else:
                # Multi-line - calculate per-line sizing
                text_lines = clean_text.split('\n')
                num_lines = len(text_lines)

                # Use 95% of available height, divided by number of lines
                target_height = int(text_height * 0.95)
                max_line_height = target_height // num_lines
                font_size = max(max_line_height - 4, 12)  # Account for line spacing

                print(f"[DEBUG] Multi-line ({num_lines} lines), max line height: {max_line_height}px, starting font: {font_size}px")

                font = None
                while font_size > 8:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                        break

                    # Check if all lines fit within width
                    all_fit = True
                    for line in text_lines:
                        if line.strip():
                            test_bbox = draw.textbbox((0, 0), line, font=font)
                            test_width = test_bbox[2] - test_bbox[0]
                            if test_width > max_text_width:
                                all_fit = False
                                break

                    if all_fit:
                        print(f"[DEBUG] All lines fit at font_size={font_size}px")
                        break

                    font_size = int(font_size * 0.95)

            if font is None:
                font = ImageFont.load_default()
            
            # Split text into lines and fit in available space
            lines = processed_text.strip().split('\n')
            line_height = font_size + 2
            start_y = (height - len(lines) * line_height) // 2
            
            for i, line in enumerate(lines):
                if line.strip():
                    y = start_y + i * line_height
                    # Simple text fitting - truncate if too long
                    while font.getbbox(line)[2] > text_width and len(line) > 1:
                        line = line[:-1]
                    draw.text((text_x, y), line, fill='black', font=font)
        else:
            # Text-only layout - maximize text size
            target_height = int(height * 0.98)  # Use 98% of label height
            max_width = int(width * 0.96)       # Use 96% of label width

            text_lines = processed_text.strip().split('\n')
            num_lines = len(text_lines) if '\n' in processed_text else 1

            # For multi-line, divide height by number of lines
            if num_lines > 1:
                max_line_height = target_height // num_lines
                font_size = max(max_line_height - 4, 12)
                print(f"[DEBUG] Text-only multi-line ({num_lines} lines): starting font={font_size}px")
            else:
                font_size = target_height
                print(f"[DEBUG] Text-only single line: starting font={font_size}px")

            font = None
            while font_size > 8:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                    break

                # Check if all lines fit within width
                all_fit = True
                for line in text_lines:
                    if line.strip():
                        bbox = draw.textbbox((0, 0), line, font=font)
                        line_width = bbox[2] - bbox[0]
                        if line_width > max_width:
                            all_fit = False
                            break

                if all_fit:
                    print(f"[DEBUG] Text-only fits at font_size={font_size}px")
                    break

                font_size = int(font_size * 0.95)

            if font is None:
                font = ImageFont.load_default()

            # Center text
            line_height = font_size + 2
            total_height = len(text_lines) * line_height
            start_y = (height - total_height) // 2

            for i, line in enumerate(text_lines):
                if line.strip():
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    x = (width - line_width) // 2
                    y = start_y + i * line_height
                    draw.text((x, y), line, fill='black', font=font)
        
        return image
    
    async def _create_advanced_label_image_for_preview(self, template: str, data: dict, label_size: str, 
                                                      label_length: int = None, options: dict = None):
        """Create an advanced label image for preview (with proper rotation for display)."""
        # Get the base image without rotation
        image = await self._create_advanced_label_image(template, data, label_size, label_length, options)
        
        # Get label info to determine if we need rotation
        printer = await self.get_printer()
        if not printer:
            return image
            
        supported_sizes = printer.get_supported_label_sizes()
        label_info = None
        for size in supported_sizes:
            if size.name == label_size:
                label_info = size
                break
        
        # Rotate for 12mm labels to show how it will look when printed (horizontal preview)
        if label_info and (label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0):
            image = image.rotate(-90, expand=True)  # Rotate -90° to show horizontally
        
        return image
    
    async def print_advanced_label(self, printer_id: str, template: str, data: dict, label_size: str, 
                                   label_length: int = None, options: dict = None, copies: int = 1) -> PrintJobResult:
        """Print an advanced label with template processing and QR codes."""
        printer = await self.get_printer(printer_id)
        if not printer:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Printer {printer_id} not found"
            )
        
        try:
            # Process template and create label image
            label_image = await self._create_advanced_label_image(template, data, label_size, label_length, options)
            
            # Apply rotation for 12mm labels for printing
            supported_sizes = printer.get_supported_label_sizes()
            label_info = None
            for size in supported_sizes:
                if size.name == label_size:
                    label_info = size
                    break
            
            if label_info and (label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0):
                label_image = label_image.rotate(90, expand=True)
            
            # Print the label
            return await printer.print_label(label_image, label_size, copies)
            
        except Exception as e:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Failed to create advanced label: {str(e)}"
            )

    async def print_text_label(self, printer_id: str, text: str, label_size: str, copies: int = 1) -> PrintJobResult:
        """Print a text label using the specified printer."""
        printer = await self.get_printer(printer_id)
        if not printer:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Printer {printer_id} not found"
            )
        
        # Create text label image directly
        from PIL import Image, ImageDraw, ImageFont
        
        # Get label size info
        supported_sizes = printer.get_supported_label_sizes()
        label_info = None
        for size in supported_sizes:
            if size.name == label_size:
                label_info = size
                break
        
        if not label_info:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Label size {label_size} not supported by printer {printer_id}"
            )
        
        # Create image with appropriate dimensions
        # For 12mm labels (both "12" die-cut and "12mm" continuous), we need to create a wide image and rotate it 90°
        if label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0:
            # Create 43.1mm x 12mm image that will be rotated 90° (based on precise testing)
            # This accounts for the scaling factor to get exactly 39mm output
            width = int(43.1 * 300 / 25.4)  # ~508 pixels for 43.1mm
            height = int(12 * 300 / 25.4)  # 141 pixels for 12mm
        elif label_info.height_mm:  # Other die-cut labels
            width = int(label_info.width_px or 400)
            height = int(label_info.height_px or 200)
        else:  # Continuous label - use width and calculate height based on text
            width = int(label_info.width_px or 400)
            height = max(100, len(text) * 20 + 40)  # Dynamic height based on text
        
        # Create white background image
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Dynamic font sizing to fit label dimensions (same as preview service)
        target_height = int(height * 0.8)  # Use 80% of label height
        max_width = int(width * 0.9)       # Use 90% of label width

        # Start with a large font size and scale down to fit
        font_size = max(target_height, 12)  # Start with target height or minimum 12
        font = None

        # Try to find the best font size that fits
        while font_size > 8:
            try:
                # Try to use a proper font
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # Fall back to default font - note: default font size cannot be changed
                font = ImageFont.load_default()
                break

            # Check if text fits within bounds
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # If text fits both width and height constraints, we're done
            if text_width <= max_width and text_height <= target_height:
                break

            # Otherwise, reduce font size and try again
            font_size = int(font_size * 0.9)

        # If we couldn't load a TrueType font, use default
        if font is None:
            font = ImageFont.load_default()
        
        # Calculate text position (centered)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(text) * 10
            text_height = 20
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text in black
        draw.text((x, y), text, fill='black', font=font)
        
        # For 12mm labels, rotate 90° like the old implementation
        if label_info.name in ["12", "12mm"] or label_info.width_mm == 12.0:
            image = image.rotate(90, expand=True)
        
        # Print the label
        return await printer.print_label(image, label_size, copies)
    
    async def print_qr_code(self, printer_id: str, data: str, label_size: str, copies: int = 1) -> PrintJobResult:
        """Print a QR code label using the specified printer."""
        printer = await self.get_printer(printer_id)
        if not printer:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Printer {printer_id} not found"
            )
        
        # Create QR code image directly
        from PIL import Image
        import qrcode
        
        # Get label size info
        supported_sizes = printer.get_supported_label_sizes()
        label_info = None
        for size in supported_sizes:
            if size.name == label_size:
                label_info = size
                break
        
        if not label_info:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Label size {label_size} not supported by printer {printer_id}"
            )
        
        # Create label image with appropriate dimensions
        if label_info.height_mm:  # Die-cut label
            width = int(label_info.width_px or 400)
            height = int(label_info.height_px or 200)
        else:  # Continuous label
            width = int(label_info.width_px or 400)
            height = max(200, width)  # Square-ish for QR codes

        # Create print settings for optimal QR sizing
        label_height_mm = label_info.width_mm if label_info else 12.0  # Label width becomes height in output
        print_settings = PrintSettings(
            label_size=label_height_mm,
            dpi=300,  # Standard Brother QL DPI
            qr_scale=0.98,  # Use 98% of available space for QR-only labels
            qr_min_size_mm=8.0,  # Minimum 8mm for phone scanning
            qr_max_margin_mm=0.5  # Minimal margin for QR-only labels
        )

        # Generate optimized QR code using template processor
        qr_image = self.template_processor.generate_qr_code(str(data), print_settings)
        qr_size = qr_image.width  # Get actual optimized size

        # Create white background and center the QR code
        image = Image.new('RGB', (width, height), 'white')
        
        # Center the QR code
        x = (width - qr_size) // 2
        y = (height - qr_size) // 2
        image.paste(qr_image, (x, y))
        
        # Print the label
        return await printer.print_label(image, label_size, copies)
    
    async def print_image(self, printer_id: str, image_data: bytes, label_size: str, copies: int = 1) -> PrintJobResult:
        """Print an image label using the specified printer."""
        printer = await self.get_printer(printer_id)
        if not printer:
            return PrintJobResult(
                success=False,
                job_id="",
                message="",
                error=f"Printer {printer_id} not found"
            )
        
        # Convert image data to PIL Image
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_data))
        
        # Print the label
        return await printer.print_label(image, label_size, copies)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get printer manager statistics."""
        total_printers = len(self.printers)
        total_jobs = len(self.print_jobs)
        
        job_statuses = {}
        for job in self.print_jobs.values():
            job_statuses[job.status] = job_statuses.get(job.status, 0) + 1
        
        return {
            "total_printers": total_printers,
            "enabled_printers": total_printers,  # All registered printers are enabled
            "default_printer": self.default_printer_id,
            "total_jobs": total_jobs,
            "job_statuses": job_statuses,
            "supported_drivers": list(self.SUPPORTED_DRIVERS.keys())
        }


# Global printer manager instance
printer_manager = PrinterManagerService()


def get_printer_manager() -> PrinterManagerService:
    """Get the global printer manager instance."""
    return printer_manager


async def initialize_default_printers():
    """Initialize default printers for testing and development."""
    manager = get_printer_manager()
    
    # Note: Mock printers are only added during testing
    # Production users should add their real Brother QL printers via the UI
    
    print(f"Initialized printer manager with {len(manager.printers)} printers")