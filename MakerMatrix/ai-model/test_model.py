#!/usr/bin/env python3
"""
Test the trained spaCy NER model on component descriptions.

Usage:
    python test_model.py --model models/component-ner-20250930_180917
"""

import argparse
import spacy
from pathlib import Path


def test_model(model_path: Path, test_descriptions: list = None):
    """Test the trained model on sample descriptions."""

    print(f"Loading model from {model_path}...")
    nlp = spacy.load(model_path)
    print("✓ Model loaded\n")

    # Default test descriptions if none provided
    if test_descriptions is None:
        test_descriptions = [
            "100mW 10kΩ ±5% 0603 Chip Resistor",
            "220uF 35V ±20% SMD Electrolytic Capacitor",
            "5V 1A SOT-23-5 Voltage Regulator",
            "47uH 500mA 0805 SMD Inductor",
            "1N4148 100V 200mA DO-35 Diode",
            "2.2nF 50V X7R 0805 Ceramic Capacitor",
            "BC547 NPN 45V 100mA TO-92 Transistor",
        ]

    print("="*70)
    print("INFERENCE TEST")
    print("="*70)
    print()

    for description in test_descriptions:
        doc = nlp(description)

        print(f"Description: {description}")

        if doc.ents:
            print(f"Entities found: {len(doc.ents)}")

            # Group by entity type
            entities_by_type = {}
            for ent in doc.ents:
                if ent.label_ not in entities_by_type:
                    entities_by_type[ent.label_] = []
                entities_by_type[ent.label_].append(ent.text)

            # Display grouped
            for label in sorted(entities_by_type.keys()):
                values = ", ".join(entities_by_type[label])
                print(f"  {label}: {values}")

            # Also show as dict (for programmatic use)
            specs = {label.lower(): values[0] if len(values) == 1 else values
                    for label, values in entities_by_type.items()}
            print(f"  → Structured: {specs}")
        else:
            print("  No entities found")

        print()


def main():
    parser = argparse.ArgumentParser(description='Test trained spaCy NER model')
    parser.add_argument('--model', type=str, required=True,
                       help='Path to trained model directory')
    parser.add_argument('--description', type=str, action='append',
                       help='Test description (can be used multiple times)')

    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        return 1

    test_model(model_path, args.description)
    return 0


if __name__ == '__main__':
    exit(main())
