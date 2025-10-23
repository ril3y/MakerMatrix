#!/usr/bin/env python3
"""
Script to find and test Brother QL printer on the network.
"""
import asyncio
import socket
import sys
import os
from PIL import Image, ImageDraw, ImageFont

# Add the MakerMatrix directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "MakerMatrix"))

from MakerMatrix.printers.drivers.brother_ql.driver import BrotherQLModern


def scan_for_printers(ip_base="192.168.1", start_ip=1, end_ip=254):
    """Scan network for Brother QL printers on port 9100."""
    print(f"🔍 Scanning {ip_base}.{start_ip}-{end_ip} for Brother QL printers...")
    found_printers = []

    for i in range(start_ip, min(end_ip + 1, 255)):
        ip = f"{ip_base}.{i}"
        try:
            # Try to connect to port 9100 (standard printer port)
            sock = socket.create_connection((ip, 9100), timeout=1)
            sock.close()
            found_printers.append(ip)
            print(f"✅ Found printer at {ip}")
        except:
            pass  # No printer at this IP

    return found_printers


def create_simple_test_label():
    """Create a simple test label for 12mm printing."""
    image = Image.new("RGB", (200, 80), "white")
    draw = ImageDraw.Draw(image)

    # Add border
    draw.rectangle([0, 0, 199, 79], outline="black", width=2)

    # Add text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font = ImageFont.load_default()

    text = "TEST 12mm"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (200 - text_width) // 2
    y = (80 - text_height) // 2

    draw.text((x, y), text, fill="black", font=font)

    return image


async def test_printer_at_ip(ip_address):
    """Test printing at a specific IP address."""
    print(f"\\n🖨️  Testing printer at {ip_address}")
    print("-" * 40)

    printer = BrotherQLModern(
        printer_id="test_printer",
        name="Test Printer",
        model="QL-800",
        backend="network",
        identifier=f"tcp://{ip_address}:9100",
        dpi=300,
    )

    try:
        # Test connection
        print("1. Testing connection...")
        connection_result = await printer.test_connection()

        if not connection_result.success:
            print(f"❌ Connection failed: {connection_result.error}")
            return False

        print(f"✅ Connected in {connection_result.response_time_ms:.1f}ms")

        # Check status
        print("2. Checking printer status...")
        status = await printer.get_status()
        print(f"📊 Status: {status}")

        if status.name in ["ERROR", "OFFLINE"]:
            print("❌ Printer not ready")
            return False

        print("✅ Printer is ready")

        # Check label sizes
        print("3. Checking supported label sizes...")
        sizes = printer.get_supported_label_sizes()
        size_names = [s.name for s in sizes]

        if "12" not in size_names:
            print("❌ 12mm labels not supported")
            return False

        print("✅ 12mm labels supported")

        # Create test image
        print("4. Creating test label...")
        test_image = create_simple_test_label()
        print("✅ Test label created")

        # Ask user before printing
        print("\\n🚨 READY TO PRINT!")
        print("This will print a small test label with '12mm TEST' text.")
        print("Make sure you have 12mm labels loaded in your printer.")

        try:
            response = input("\\nDo you want to print the test label? (y/N): ").strip().lower()
            if response != "y":
                print("❌ Print cancelled by user")
                return False
        except:
            print("❌ No user input available - skipping print")
            return False

        # Print the label
        print("\\n5. Printing test label...")
        result = await printer.print_label(test_image, "12", copies=1)

        if result.success:
            print(f"🎉 SUCCESS! {result.message}")
            print("\\nCheck your printer - you should see a small label with:")
            print("  - Black border around the edge")
            print("  - Text '12mm TEST' in the center")
            return True
        else:
            print(f"❌ Print failed: {result.error}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main function to find and test printers."""
    print("Brother QL Printer Finder and Tester")
    print("=====================================")

    # Check common IP ranges
    common_ranges = ["192.168.1", "192.168.0", "10.0.0", "172.16.0"]

    all_found_printers = []

    for ip_base in common_ranges:
        found = scan_for_printers(ip_base, 1, 254)
        all_found_printers.extend(found)

        if found:
            break  # Stop scanning if we found printers

    if not all_found_printers:
        print("\\n❌ No Brother QL printers found on the network.")
        print("\\nPlease check:")
        print("  1. Printer is powered on")
        print("  2. Printer is connected to the same network")
        print("  3. Printer has a valid IP address")
        print("\\nYou can also manually test with a specific IP:")
        print("  python find_and_test_printer.py 192.168.1.100")
        return

    print(f"\\n🎯 Found {len(all_found_printers)} printer(s):")
    for i, ip in enumerate(all_found_printers, 1):
        print(f"  {i}. {ip}")

    # Test each printer
    for ip in all_found_printers:
        success = await test_printer_at_ip(ip)
        if success:
            print(f"\\n🏆 Successfully tested printer at {ip}")
            break
        else:
            print(f"\\n❌ Failed to test printer at {ip}")

    print("\\n✅ Testing complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Manual IP provided
        ip = sys.argv[1]
        print(f"Testing printer at manually specified IP: {ip}")
        asyncio.run(test_printer_at_ip(ip))
    else:
        # Scan for printers
        asyncio.run(main())
