# Part Inventory Server

A comprehensive inventory management system designed specifically for makers, hobbyists, and small workshops. This FastAPI-based server helps organize your parts, tools, and materials while providing automated label printing capabilities through Brother QL-800 printer integration.

## Why Use Part Inventory Server?
- **Organize Your Maker Space**: Keep track of all your parts, components, and tools in one central system
- **Quick Part Location**: Generate and print QR code labels to easily locate items in your workshop
- **Smart Categories**: Group items by categories for better organization
- **Location Tracking**: Track where items are stored in your workshop
- **Inventory Management**: Monitor quantities and get insights into your parts collection
- **Network Printing**: Print labels directly from any device on your network

## Key Features
- QR Code Label Generation and Printing
- Network Printer Support
- Part Inventory Management
- Location Management
- Category Organization
- Real-time Inventory Counts
- REST API for Integration

## Requirements
- Python 3.8+
- Brother QL-800 printer (or compatible model)
- Network connectivity to printer

**Installation Guide**

### Prerequisites

*   Python 3.8+
*   Brother QL-800 printer (or compatible model)
*   Network connectivity to printer

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/part_inventory_server.git
cd part_inventory_server
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate the Virtual Environment

```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Step 4: Install Required Packages

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development/testing
```

### Step 5: Configure the Printer

1.  Create a `printer.json` file in the root directory with the following content:

```json
{
    "printer": {
        "model": "QL-800",
        "backend": "network",
        "printer_identifier": "tcp://192.168.1.71",
        "dpi": 300
    }
}
```