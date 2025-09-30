#!/usr/bin/env python3
"""
Simple test script to check printer configuration and test basic functionality.
This script directly accesses the database to check printer settings.
"""

import sqlite3
import json
from pathlib import Path

def main():
    # Database path
    db_path = Path(__file__).parent / "makermatrix.db"

    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return

    print("🖨️ MakerMatrix Printer Configuration Check")
    print("=" * 50)

    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()

        # Check if printers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='printermodel'")
        if not cursor.fetchone():
            print("❌ Printers table not found in database")
            return

        # Get all printers
        cursor.execute("""
            SELECT printer_id, name, driver_type, model, backend, identifier,
                   dpi, scaling_factor, is_active, last_seen, config
            FROM printermodel
            ORDER BY printer_id
        """)

        printers = cursor.fetchall()

        if not printers:
            print("⚠️ No printers configured in database")
            print("\nTo configure a printer, you would typically:")
            print("1. Register a printer via the API: POST /api/printer/register")
            print("2. Set up the connection (USB, network, etc.)")
            print("3. Test the printer with: POST /api/printer/test-setup")
            return

        print(f"📋 Found {len(printers)} configured printer(s):")
        print()

        for printer in printers:
            print(f"🖨️ Printer: {printer['name']} (ID: {printer['printer_id']})")
            print(f"   ├─ Driver: {printer['driver_type']}")
            print(f"   ├─ Model: {printer['model']}")
            print(f"   ├─ Backend: {printer['backend']}")
            print(f"   ├─ Identifier: {printer['identifier']}")
            print(f"   ├─ DPI: {printer['dpi']}")
            print(f"   ├─ Scaling: {printer['scaling_factor']}x")
            print(f"   ├─ Active: {'✅' if printer['is_active'] else '❌'}")
            print(f"   ├─ Last Seen: {printer['last_seen'] or 'Never'}")

            # Parse config JSON if available
            config_data = printer['config']
            if config_data:
                try:
                    if isinstance(config_data, str):
                        config = json.loads(config_data)
                    else:
                        config = config_data
                    if config:
                        print(f"   └─ Config: {json.dumps(config, indent=11)}")
                    else:
                        print(f"   └─ Config: (empty)")
                except (json.JSONDecodeError, TypeError):
                    print(f"   └─ Config: (invalid JSON)")
            else:
                print(f"   └─ Config: (none)")
            print()

        # Check if Brother QL library is available
        try:
            import brother_ql
            print(f"✅ Brother QL library available (version: {brother_ql.__version__})")
        except ImportError:
            print("❌ Brother QL library not available")

        # Provide next steps
        print("\n📝 Printer Configuration Summary:")
        print("─" * 40)

        for printer in printers:
            if printer['driver_type'] == 'brother_ql':
                print(f"🏷️ Brother QL printer '{printer['name']}' configured")
                print(f"   • Use 12mm label tape for testing (as per documentation)")
                print(f"   • API endpoint: POST /api/printer/print/text")
                print(f"   • Test endpoint: POST /api/printer/test-setup")

                if printer['backend'] == 'network':
                    print(f"   • Network printer: {printer['identifier']}")
                elif printer['backend'] == 'usb':
                    print(f"   • USB printer: {printer['identifier']}")
                else:
                    print(f"   • {printer['backend']} printer: {printer['identifier']}")
            else:
                print(f"🖨️ Generic printer '{printer['name']}' configured")

        print(f"\n💡 Next steps:")
        print(f"   1. Ensure printer is connected and powered on")
        print(f"   2. Load 12mm label tape in the printer")
        print(f"   3. Test printing via API or web interface")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()