"""
QR Code generation service.
"""
import qrcode
from PIL import Image
from typing import Tuple


class QRService:
    """Service for generating QR codes."""
    
    def __init__(self):
        pass
    
    def generate_qr_code(self, data: str, size: Tuple[int, int] = (200, 200)) -> Image.Image:
        """
        Generate a QR code image from the given data.
        
        Args:
            data: The data to encode in the QR code
            size: The desired size of the QR code image (width, height)
            
        Returns:
            PIL Image containing the QR code
        """
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to RGB and resize if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to desired size
        if img.size != size:
            img = img.resize(size, Image.Resampling.LANCZOS)
        
        return img
    
    def generate_qr_code_with_text(self, data: str, text: str, 
                                   size: Tuple[int, int] = (300, 250)) -> Image.Image:
        """
        Generate a QR code with text below it.
        
        Args:
            data: The data to encode in the QR code
            text: Text to display below the QR code
            size: The desired size of the combined image
            
        Returns:
            PIL Image containing QR code with text
        """
        from PIL import ImageDraw, ImageFont
        
        # Generate QR code (smaller to leave room for text)
        qr_size = (int(size[0] * 0.8), int(size[0] * 0.8))
        qr_img = self.generate_qr_code(data, qr_size)
        
        # Create combined image
        combined = Image.new('RGB', size, 'white')
        
        # Paste QR code at top center
        qr_x = (size[0] - qr_img.width) // 2
        qr_y = 10
        combined.paste(qr_img, (qr_x, qr_y))
        
        # Add text below QR code
        if text:
            draw = ImageDraw.Draw(combined)
            
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position
            text_y = qr_y + qr_img.height + 10
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (size[0] - text_width) // 2
            
            draw.text((text_x, text_y), text, fill='black', font=font)
        
        return combined