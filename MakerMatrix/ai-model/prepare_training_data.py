#!/usr/bin/env python3
"""
Prepare training data from labeled JSONL files for fine-tuning.

This script:
1. Loads all labeled_*.jsonl or reviewed_*.jsonl files from data/labeled/
2. Converts them to training format (input description -> output specs)
3. Saves in format ready for model fine-tuning

Handles both:
- reviewed_*.jsonl: Has 'corrected_specs' from manual review
- labeled_*.jsonl: Has 'extracted_specs' from LLM

Output formats:
- transformer: For T5/GPT-2 text-to-JSON training
- spacy: For spaCy NER (Named Entity Recognition) training
"""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime


def load_labeled_files(labeled_dir: Path) -> List[Dict]:
    """Load all labeled examples from JSONL files (both reviewed and labeled)."""
    examples = []
    skipped = 0

    # Find both reviewed and labeled files
    reviewed_files = list(labeled_dir.glob("reviewed_*.jsonl"))
    labeled_files = list(labeled_dir.glob("labeled_*.jsonl"))
    all_files = reviewed_files + labeled_files

    print(f"Found {len(reviewed_files)} reviewed files and {len(labeled_files)} labeled files")

    for file_path in all_files:
        print(f"Loading {file_path.name}...")
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    example = json.loads(line)

                    # Get specs from either reviewed or labeled format
                    specs = None
                    if example.get('review_status') == 'correct' and example.get('corrected_specs'):
                        # Reviewed file with manual corrections
                        specs = example.get('corrected_specs')
                    elif example.get('extracted_specs'):
                        # Labeled file with LLM extractions
                        specs = example.get('extracted_specs')

                    if specs:
                        example['_specs'] = specs  # Store for later use
                        examples.append(example)
                    else:
                        skipped += 1

    print(f"✓ Loaded {len(examples)} examples")
    if skipped > 0:
        print(f"  Skipped {skipped} examples (missing specs)")
    return examples


def build_training_prompt(example: Dict) -> str:
    """Build the input prompt for training."""
    description = example.get('description', '')
    category = example.get('main_category', 'Unknown')
    subcategory = example.get('subcategory', 'Unknown')
    package = example.get('package', 'Unknown')

    prompt = f"""Extract specifications from this electronic component.

Component Information:
Category: {category}/{subcategory}
Package: {package}
Description: {description}

Extract the relevant specifications and return them as a JSON object with appropriate fields."""

    return prompt


def find_entity_positions(text: str, value: str) -> Tuple[int, int]:
    """Find the start and end position of a value in text."""
    # Escape special regex characters in the value
    escaped_value = re.escape(str(value))

    # Try to find exact match
    match = re.search(escaped_value, text, re.IGNORECASE)
    if match:
        return match.start(), match.end()

    return None, None


def convert_to_spacy_format(examples: List[Dict]) -> List[Tuple[str, Dict]]:
    """Convert labeled examples to spaCy NER training format."""
    spacy_data = []
    skipped = 0
    overlaps_removed = 0

    for example in examples:
        description = example.get('description', '')
        specs = example.get('_specs', {})

        if not description or not specs:
            skipped += 1
            continue

        # Build entities list: [(start, end, label), ...]
        entities = []

        for field_name, field_value in specs.items():
            if field_value is None or field_value == '':
                continue

            # Convert field name to entity label (uppercase, replace underscores)
            entity_label = field_name.upper().replace('_', '_')

            # Find the value in the description
            start, end = find_entity_positions(description, field_value)

            if start is not None:
                entities.append((start, end, entity_label))

        if entities:
            # Sort entities by start position, then by length (prefer longer entities)
            entities.sort(key=lambda x: (x[0], -(x[1] - x[0])))

            # Remove overlapping entities
            non_overlapping = []
            for ent in entities:
                start, end, label = ent
                # Check if this entity overlaps with any already added
                overlaps = False
                for existing_start, existing_end, _ in non_overlapping:
                    # Check for overlap
                    if not (end <= existing_start or start >= existing_end):
                        overlaps = True
                        overlaps_removed += 1
                        break

                if not overlaps:
                    non_overlapping.append(ent)

            if non_overlapping:
                # Add to spacy training data
                spacy_data.append((description, {"entities": non_overlapping}))
            else:
                skipped += 1
        else:
            skipped += 1

    if skipped > 0:
        print(f"  Skipped {skipped} examples (no entities found in description)")
    if overlaps_removed > 0:
        print(f"  Removed {overlaps_removed} overlapping entities")

    return spacy_data


def convert_to_transformer_format(examples: List[Dict]) -> List[Dict]:
    """Convert labeled examples to transformer training format."""
    training_data = []

    for example in examples:
        # Build input prompt
        prompt = build_training_prompt(example)

        # Get specifications (stored in _specs by load_labeled_files)
        specs = example.get('_specs', {})

        # Create training example
        training_example = {
            "input": prompt,
            "output": json.dumps(specs, indent=2),
            "metadata": {
                "lcsc_number": example.get('lcsc_number'),
                "category": example.get('main_category'),
                "subcategory": example.get('subcategory'),
                "labeled_at": example.get('labeled_at') or example.get('reviewed_at')
            }
        }

        training_data.append(training_example)

    return training_data


def save_transformer_data(training_data: List[Dict], output_path: Path):
    """Save transformer training data to JSONL file."""
    with open(output_path, 'w') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')

    print(f"✓ Saved {len(training_data)} training examples to {output_path}")


def save_spacy_data(spacy_data: List[Tuple[str, Dict]], output_path: Path):
    """Save spaCy training data to Python file."""
    with open(output_path, 'w') as f:
        f.write('"""spaCy NER Training Data\n\n')
        f.write('Generated from labeled component specifications.\n')
        f.write('Use with train_spacy.py to train NER model.\n')
        f.write('"""\n\n')
        f.write('TRAIN_DATA = [\n')

        for text, annotations in spacy_data:
            # Use repr() to properly escape all special characters
            f.write(f'    ({repr(text)}, {annotations}),\n')

        f.write(']\n')

    print(f"✓ Saved {len(spacy_data)} training examples to {output_path}")


def generate_statistics(training_data: List[Dict]) -> Dict:
    """Generate statistics about the training data."""
    stats = {
        "total_examples": len(training_data),
        "categories": {},
        "avg_specs_per_example": 0,
        "total_specs": 0
    }

    for example in training_data:
        # Count by category
        category = example['metadata']['category']
        stats['categories'][category] = stats['categories'].get(category, 0) + 1

        # Count specs
        try:
            specs = json.loads(example['output'])
            stats['total_specs'] += len(specs)
        except:
            pass

    if stats['total_examples'] > 0:
        stats['avg_specs_per_example'] = stats['total_specs'] / stats['total_examples']

    return stats


def main():
    parser = argparse.ArgumentParser(description='Prepare training data from labeled examples')
    parser.add_argument('--labeled-dir', type=str, default='data/labeled',
                        help='Directory containing labeled/reviewed JSONL files')
    parser.add_argument('--output', type=str, default=None,
                        help='Output training data file')
    parser.add_argument('--format', type=str, choices=['transformer', 'spacy'], default='transformer',
                        help='Output format: transformer (T5/GPT) or spacy (NER)')
    args = parser.parse_args()

    print("="*70)
    print("TRAINING DATA PREPARATION")
    print("="*70)
    print(f"Format: {args.format}")
    print()

    labeled_dir = Path(args.labeled_dir)
    if not labeled_dir.exists():
        print(f"Error: Directory {labeled_dir} does not exist")
        return 1

    # Load labeled examples (both reviewed and labeled files)
    examples = load_labeled_files(labeled_dir)

    if len(examples) == 0:
        print("Error: No labeled examples found")
        return 1

    # Convert based on format
    print(f"\nConverting to {args.format} format...")

    if args.format == 'spacy':
        training_data = convert_to_spacy_format(examples)
    else:
        training_data = convert_to_transformer_format(examples)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        training_dir = Path("data/training")
        training_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if args.format == 'spacy':
            output_path = training_dir / f"spacy_train_{timestamp}.py"
        else:
            output_path = training_dir / f"training_{timestamp}.jsonl"

    # Save based on format
    print(f"\nSaving training data...")

    if args.format == 'spacy':
        save_spacy_data(training_data, output_path)

        # Print entity statistics
        print("\nEntity Statistics:")
        entity_counts = {}
        for _, annotations in training_data:
            for start, end, label in annotations['entities']:
                entity_counts[label] = entity_counts.get(label, 0) + 1

        print(f"  Total examples: {len(training_data)}")
        print(f"  Total entities: {sum(entity_counts.values())}")
        print(f"\n  Entities by type:")
        for entity_type, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {entity_type}: {count}")
    else:
        save_transformer_data(training_data, output_path)

        # Generate and save statistics
        stats = generate_statistics(training_data)
        print("\nTraining Data Statistics:")
        print(f"  Total examples: {stats['total_examples']}")
        print(f"  Total specs: {stats['total_specs']}")
        print(f"  Avg specs per example: {stats['avg_specs_per_example']:.2f}")
        print(f"\n  Examples by category:")
        for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {category}: {count}")

        # Save statistics
        stats_path = output_path.with_suffix('.stats.json')
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"✓ Saved statistics to {stats_path}")

    print()
    print("="*70)
    print("READY FOR TRAINING")
    print("="*70)
    print()
    print(f"Training data saved to: {output_path}")

    if args.format == 'spacy':
        print(f"Next steps:")
        print(f"  1. Install spaCy: pip install spacy")
        print(f"  2. Create training script: train_spacy.py")
        print(f"  3. Train model with your data")
    else:
        print(f"You can now use this file to fine-tune a transformer model")

    print()

    return 0


if __name__ == '__main__':
    exit(main())
