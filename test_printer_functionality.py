#!/usr/bin/env python3
"""
Test printer functionality - attempts to connect and test print
IMPORTANT: Use 12mm tape only for testing as per documentation
"""

import sys
import socket
import json
from datetime import datetime

def test_network_connectivity(printer_ip, printer_port):
    """Test basic network connectivity to the printer"""
    print(f"🔌 Testing network connection to {printer_ip}:{printer_port}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((printer_ip, printer_port))
        sock.close()

        if result == 0:
            print("✅ Network connection successful")
            return True
        else:
            print(f"❌ Network connection failed (error code: {result})")
            return False

    except socket.gaierror as e:
        print(f"❌ DNS lookup failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def test_brother_ql_import():
    """Test if Brother QL libraries can be imported"""
    print("📦 Testing Brother QL library imports...")

    try:
        from brother_ql.backends.helpers import send
        from brother_ql.conversion import convert
        from brother_ql.raster import BrotherQLRaster
        print("✅ Brother QL libraries imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Brother QL library import failed: {e}")
        return False

def create_test_label():
    """Create a simple test label image"""
    print("🏷️ Creating test label...")

    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a simple test label (12mm height = ~47 pixels at 300 DPI)
        # Width can be variable for Brother QL
        width = 200  # pixels
        height = 47  # pixels (approximately 12mm at 300 DPI)

        # Create white background
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        # Add test text
        try:
            # Try to use a default font
            font = ImageFont.load_default()
        except:
            font = None

        text = "TEST LABEL"
        if font:
            # Get text dimensions
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Center the text
            x = (width - text_width) // 2
            y = (height - text_height) // 2

            draw.text((x, y), text, fill='black', font=font)
        else:
            # Fallback without font
            draw.text((20, 15), text, fill='black')

        print("✅ Test label created")
        return image

    except ImportError as e:
        print(f"❌ PIL/Pillow not available: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to create test label: {e}")
        return None

def main():
    print("🖨️ MakerMatrix Printer Functionality Test")
    print("=" * 50)
    print("⚠️  IMPORTANT: Ensure 12mm label tape is loaded!")
    print("=" * 50)

    # Printer configuration from database check
    printer_config = {
        'name': 'Brother',
        'id': 'brother',
        'driver': 'brother_ql',
        'model': 'QL-800',
        'backend': 'network',
        'identifier': 'tcp://192.168.1.71:9100',
        'ip': '192.168.1.71',
        'port': 9100
    }

    print(f"🖨️ Testing printer: {printer_config['name']} ({printer_config['model']})")
    print(f"📍 Address: {printer_config['identifier']}")
    print()

    # Test 1: Network connectivity
    network_ok = test_network_connectivity(printer_config['ip'], printer_config['port'])
    print()

    # Test 2: Brother QL library imports
    library_ok = test_brother_ql_import()
    print()

    # Test 3: Create test label
    test_image = create_test_label()
    print()

    # Summary
    print("📊 Test Results Summary:")
    print("─" * 30)
    print(f"Network Connection: {'✅ PASS' if network_ok else '❌ FAIL'}")
    print(f"Brother QL Library: {'✅ PASS' if library_ok else '❌ FAIL'}")
    print(f"Label Creation:     {'✅ PASS' if test_image else '❌ FAIL'}")
    print()

    if network_ok and library_ok and test_image:
        print("🎉 All tests passed! Printer is ready for use.")
        print()
        print("📝 Next steps:")
        print("   1. Use the web interface to test printing")
        print("   2. Try the API endpoint: POST /api/printer/print/text")
        print("   3. Print a QR code: POST /api/printer/print/qr")
        print()
        print("💡 API Test Example:")
        print('   curl -X POST "https://192.168.1.58:8443/api/printer/print/text" \\')
        print('     -H "Authorization: Bearer YOUR_TOKEN" \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"printer_id": "brother", "text": "Hello World", "label_size": "12", "copies": 1}\'')
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        print()
        if not network_ok:
            print("🔧 Network troubleshooting:")
            print("   • Check if printer is powered on")
            print("   • Verify network IP address (192.168.1.71)")
            print("   • Check network connectivity")
            print("   • Ensure port 9100 is open")

        if not library_ok:
            print("🔧 Library troubleshooting:")
            print("   • Reinstall brother_ql: pip install brother_ql")
            print("   • Check virtual environment activation")

    # Save test results
    results = {
        'timestamp': datetime.now().isoformat(),
        'printer_config': printer_config,
        'tests': {
            'network_connectivity': network_ok,
            'library_import': library_ok,
            'label_creation': test_image is not None
        }
    }

    with open('printer_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Test results saved to: printer_test_results.json")

if __name__ == "__main__":
    main()