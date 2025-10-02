#!/usr/bin/env python3
"""Test the trained spaCy NER model on order file descriptions."""

import argparse
import csv
import spacy
from pathlib import Path
from collections import Counter

def load_model(model_path: Path):
    """Load the trained spaCy model."""
    print(f"Loading model from {model_path}...")
    nlp = spacy.load(model_path)
    print(f"✓ Model loaded")
    return nlp

def test_on_digikey(nlp, csv_path: Path, limit: int = None):
    """Test model on DigiKey order file."""
    print(f"\n{'='*70}")
    print(f"Testing on DigiKey: {csv_path.name}")
    print(f"{'='*70}\n")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            if limit and i > limit:
                break

            description = row.get('Description', '')
            mpn = row.get('Manufacturer Part Number', '')
            mfr = row.get('Manufacturer', '')

            if not description:
                continue

            print(f"[{i}] {mpn} ({mfr})")
            print(f"Description: {description}")

            doc = nlp(description)

            if doc.ents:
                print(f"Entities found: {len(doc.ents)}")
                specs = {}
                for ent in doc.ents:
                    field_name = ent.label_.lower()
                    specs[field_name] = ent.text
                    print(f"  {ent.label_:20s} = {ent.text}")
                print(f"  → Structured: {specs}")
            else:
                print(f"  No entities found")
            print()

def test_on_lcsc(nlp, csv_path: Path, limit: int = None):
    """Test model on LCSC order file."""
    print(f"\n{'='*70}")
    print(f"Testing on LCSC: {csv_path.name}")
    print(f"{'='*70}\n")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            if limit and i > limit:
                break

            description = row.get('Description', '')
            lcsc_num = row.get('LCSC Part Number', '')
            mpn = row.get('MFR.Part', '')

            if not description:
                continue

            print(f"[{i}] {lcsc_num} - {mpn}")
            print(f"Description: {description}")

            doc = nlp(description)

            if doc.ents:
                print(f"Entities found: {len(doc.ents)}")
                specs = {}
                for ent in doc.ents:
                    field_name = ent.label_.lower()
                    specs[field_name] = ent.text
                    print(f"  {ent.label_:20s} = {ent.text}")
                print(f"  → Structured: {specs}")
            else:
                print(f"  No entities found")
            print()

def analyze_coverage(nlp, orders_dir: Path):
    """Analyze entity extraction coverage across all order files."""
    print(f"\n{'='*70}")
    print("COVERAGE ANALYSIS")
    print(f"{'='*70}\n")

    total_descriptions = 0
    total_with_entities = 0
    entity_counts = Counter()

    # Process DigiKey files
    for csv_file in orders_dir.glob("DK_PRODUCTS_*.csv"):
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                description = row.get('Description', '')
                if description:
                    total_descriptions += 1
                    doc = nlp(description)
                    if doc.ents:
                        total_with_entities += 1
                        for ent in doc.ents:
                            entity_counts[ent.label_] += 1

    # Process LCSC files
    for csv_file in orders_dir.glob("LCSC_Exported_*.csv"):
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                description = row.get('Description', '')
                if description:
                    total_descriptions += 1
                    doc = nlp(description)
                    if doc.ents:
                        total_with_entities += 1
                        for ent in doc.ents:
                            entity_counts[ent.label_] += 1

    print(f"Total descriptions: {total_descriptions}")
    print(f"With entities: {total_with_entities} ({total_with_entities/total_descriptions*100:.1f}%)")
    print(f"Without entities: {total_descriptions - total_with_entities} ({(total_descriptions - total_with_entities)/total_descriptions*100:.1f}%)")
    print(f"\nEntity type distribution:")
    for entity_type, count in entity_counts.most_common():
        print(f"  {entity_type:20s}: {count:4d}")

def main():
    parser = argparse.ArgumentParser(description='Test spaCy model on order files')
    parser.add_argument(
        '--model',
        default='models/component-ner-20250930_180917',
        help='Path to trained spaCy model'
    )
    parser.add_argument(
        '--orders-dir',
        default='orders',
        help='Directory containing order files'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of parts to test per file'
    )
    parser.add_argument(
        '--digikey',
        action='store_true',
        help='Test on DigiKey files'
    )
    parser.add_argument(
        '--lcsc',
        action='store_true',
        help='Test on LCSC files'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Show coverage analysis across all files'
    )

    args = parser.parse_args()

    model_path = Path(args.model)
    orders_dir = Path(args.orders_dir)

    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        return

    if not orders_dir.exists():
        print(f"Error: Orders directory not found at {orders_dir}")
        return

    nlp = load_model(model_path)

    if args.coverage:
        analyze_coverage(nlp, orders_dir)
    elif args.digikey:
        for csv_file in sorted(orders_dir.glob("DK_PRODUCTS_*.csv")):
            test_on_digikey(nlp, csv_file, args.limit)
    elif args.lcsc:
        for csv_file in sorted(orders_dir.glob("LCSC_Exported_*.csv")):
            test_on_lcsc(nlp, csv_file, args.limit)
    else:
        # Default: test on first DigiKey file
        dk_files = list(orders_dir.glob("DK_PRODUCTS_*.csv"))
        if dk_files:
            test_on_digikey(nlp, dk_files[0], args.limit or 10)

        # And first LCSC file
        lcsc_files = list(orders_dir.glob("LCSC_Exported_*.csv"))
        if lcsc_files:
            test_on_lcsc(nlp, lcsc_files[0], args.limit or 10)

if __name__ == '__main__':
    main()
