#!/usr/bin/env python3
"""
Extract component data from order files (CSV and XLS) for labeling.

This script reads LCSC and DigiKey order files and extracts components
with their descriptions, which can then be labeled by the LLM.

Usage:
    python extract_from_orders.py --output data/training/orders_sample.jsonl
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List
import xlrd


def parse_lcsc_csv(file_path: Path) -> List[Dict]:
    """Parse LCSC CSV order file."""
    components = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            component = {
                'lcsc_number': row.get('LCSC Part Number', ''),
                'mpn': row.get('Manufacture Part Number', ''),
                'manufacturer': row.get('Manufacturer', ''),
                'package': row.get('Package', ''),
                'title': row.get('Manufacture Part Number', ''),
                'description': row.get('Description', ''),
                'source': 'lcsc_order',
                'source_file': file_path.name
            }

            # Parse category from description if available
            desc = component['description']
            if 'Resistor' in desc:
                component['main_category'] = 'Resistors'
                component['subcategory'] = 'Chip Resistor - Surface Mount'
            elif 'Capacitor' in desc:
                component['main_category'] = 'Capacitors'
                component['subcategory'] = 'MLCC - Surface Mount'
            elif 'LED' in desc:
                component['main_category'] = 'Optoelectronics'
                component['subcategory'] = 'LED Indication - Discrete'
            elif 'IC' in desc or 'FLASH' in desc:
                component['main_category'] = 'Integrated Circuits'
                component['subcategory'] = 'Memory ICs'
            else:
                component['main_category'] = 'Unknown'
                component['subcategory'] = 'Unknown'

            if component['mpn'] and component['description']:
                components.append(component)

    return components


def parse_digikey_csv(file_path: Path) -> List[Dict]:
    """Parse DigiKey CSV order file."""
    components = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            component = {
                'mpn': row.get('Manufacturer Part Number', ''),
                'manufacturer': row.get('Manufacturer', ''),
                'title': row.get('Manufacturer Part Number', ''),
                'description': row.get('Description', ''),
                'source': 'digikey_order',
                'source_file': file_path.name
            }

            # Infer category from description
            desc = component['description'].upper()
            if 'RES ' in desc or 'RESISTOR' in desc:
                component['main_category'] = 'Resistors'
                component['subcategory'] = 'Chip Resistor - Surface Mount'
                # Extract package from description (e.g., "0603")
                for token in desc.split():
                    if token in ['0402', '0603', '0805', '1206', '1210']:
                        component['package'] = token
                        break
            elif 'CAP ' in desc or 'CAPACITOR' in desc:
                component['main_category'] = 'Capacitors'
                component['subcategory'] = 'MLCC - Surface Mount'
            elif 'IC ' in desc or 'FLASH' in desc or 'OPAMP' in desc:
                component['main_category'] = 'Integrated Circuits'
                if 'FLASH' in desc:
                    component['subcategory'] = 'Memory ICs'
                elif 'OPAMP' in desc:
                    component['subcategory'] = 'Amplifiers'
                else:
                    component['subcategory'] = 'ICs'
            else:
                component['main_category'] = 'Unknown'
                component['subcategory'] = 'Unknown'

            if component['mpn'] and component['description']:
                components.append(component)

    return components


def parse_mouser_xls(file_path: Path) -> List[Dict]:
    """Parse Mouser XLS order file."""
    components = []

    try:
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)

        # Find header row
        header_row = None
        for i in range(min(10, sheet.nrows)):
            row = [str(cell.value).strip() for cell in sheet.row(i)]
            if 'Manufacturer Part Number' in row or 'Part Number' in row:
                header_row = i
                break

        if header_row is None:
            print(f"⚠ Could not find header row in {file_path.name}")
            return components

        # Get column indices
        headers = [str(cell.value).strip() for cell in sheet.row(header_row)]

        mpn_idx = None
        desc_idx = None
        mfr_idx = None

        for idx, header in enumerate(headers):
            if 'Manufacturer Part Number' in header or header == 'Part Number':
                mpn_idx = idx
            elif 'Description' in header:
                desc_idx = idx
            elif 'Manufacturer' in header and 'Part' not in header:
                mfr_idx = idx

        # Parse data rows
        for row_idx in range(header_row + 1, sheet.nrows):
            try:
                row = sheet.row(row_idx)

                mpn = str(row[mpn_idx].value).strip() if mpn_idx is not None else ''
                desc = str(row[desc_idx].value).strip() if desc_idx is not None else ''
                mfr = str(row[mfr_idx].value).strip() if mfr_idx is not None else ''

                if not mpn or not desc:
                    continue

                component = {
                    'mpn': mpn,
                    'manufacturer': mfr,
                    'title': mpn,
                    'description': desc,
                    'source': 'mouser_order',
                    'source_file': file_path.name
                }

                # Infer category from description
                desc_upper = desc.upper()
                if 'RESISTOR' in desc_upper or 'RES ' in desc_upper:
                    component['main_category'] = 'Resistors'
                    component['subcategory'] = 'Chip Resistor - Surface Mount'
                elif 'CAPACITOR' in desc_upper or 'CAP ' in desc_upper:
                    component['main_category'] = 'Capacitors'
                    component['subcategory'] = 'MLCC - Surface Mount'
                elif 'LED' in desc_upper:
                    component['main_category'] = 'Optoelectronics'
                    component['subcategory'] = 'LEDs'
                else:
                    component['main_category'] = 'Unknown'
                    component['subcategory'] = 'Unknown'

                components.append(component)

            except Exception as e:
                print(f"⚠ Error parsing row {row_idx}: {e}")
                continue

    except Exception as e:
        print(f"✗ Error reading {file_path.name}: {e}")

    return components


def extract_from_orders(orders_dir: Path) -> List[Dict]:
    """Extract all components from order files."""
    all_components = []

    print(f"\nScanning orders directory: {orders_dir}")

    # Process CSV files
    csv_files = list(orders_dir.glob("*.csv"))
    print(f"\nFound {len(csv_files)} CSV files")

    for csv_file in csv_files:
        print(f"  Processing {csv_file.name}...")

        if csv_file.name.startswith('LCSC'):
            components = parse_lcsc_csv(csv_file)
        elif csv_file.name.startswith('DK_'):
            components = parse_digikey_csv(csv_file)
        else:
            # Try both parsers
            try:
                components = parse_lcsc_csv(csv_file)
                if not components:
                    components = parse_digikey_csv(csv_file)
            except:
                components = []

        print(f"    ✓ Extracted {len(components)} components")
        all_components.extend(components)

    # Process XLS files (Mouser)
    xls_files = list(orders_dir.glob("*.xls"))
    print(f"\nFound {len(xls_files)} XLS files")

    for xls_file in xls_files:
        print(f"  Processing {xls_file.name}...")
        components = parse_mouser_xls(xls_file)
        print(f"    ✓ Extracted {len(components)} components")
        all_components.extend(components)

    return all_components


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract component data from order files'
    )
    parser.add_argument(
        '--orders-dir',
        default='orders',
        help='Directory containing order files (default: orders)'
    )
    parser.add_argument(
        '--output',
        default='data/training/orders_sample.jsonl',
        help='Output JSONL file (default: data/training/orders_sample.jsonl)'
    )

    args = parser.parse_args()

    print("="*70)
    print("ORDER FILE EXTRACTION")
    print("="*70)

    orders_dir = Path(args.orders_dir)
    if not orders_dir.exists():
        print(f"✗ Orders directory not found: {orders_dir}")
        sys.exit(1)

    # Extract components
    components = extract_from_orders(orders_dir)

    # Remove duplicates (same MPN)
    seen_mpns = set()
    unique_components = []

    for component in components:
        mpn = component.get('mpn', '')
        if mpn and mpn not in seen_mpns:
            seen_mpns.add(mpn)
            unique_components.append(component)

    print(f"\n" + "="*70)
    print(f"✓ Extracted {len(components)} total components")
    print(f"✓ Unique components: {len(unique_components)}")
    print("="*70)

    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        for component in unique_components:
            f.write(json.dumps(component) + '\n')

    print(f"\n✓ Saved to {output_path}")

    # Show sample
    print(f"\nSample components:")
    for component in unique_components[:3]:
        print(f"\n  {component['title']}")
        print(f"    Category: {component['main_category']}/{component['subcategory']}")
        print(f"    Description: {component['description'][:80]}...")


if __name__ == "__main__":
    main()
