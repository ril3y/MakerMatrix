#!/usr/bin/env python3
"""
Convert labeled JSONL files directly to training format.

Handles files with 'extracted_specs' (from LLM) instead of 'corrected_specs' (from review).
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def convert_to_training(input_file: Path, output_file: Path):
    """Convert labeled data to training format."""

    print(f"Converting {input_file} to training format...")

    training_data = []
    skipped = 0

    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                example = json.loads(line)

                # Get specs - either from extracted_specs or corrected_specs
                specs = example.get('corrected_specs') or example.get('extracted_specs')

                if not specs:
                    skipped += 1
                    continue

                # Build training prompt
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

                # Create training example
                training_example = {
                    "input": prompt,
                    "output": json.dumps(specs, indent=2),
                    "metadata": {
                        "lcsc_number": example.get('lcsc_number'),
                        "category": category,
                        "subcategory": subcategory,
                        "labeled_at": example.get('labeled_at') or example.get('reviewed_at')
                    }
                }

                training_data.append(training_example)

            except json.JSONDecodeError as e:
                print(f"Warning: Skipping line {line_num} - Invalid JSON: {e}")
                skipped += 1
            except Exception as e:
                print(f"Warning: Skipping line {line_num} - Error: {e}")
                skipped += 1

    # Save training data
    with open(output_file, 'w') as f:
        for example in training_data:
            f.write(json.dumps(example) + '\n')

    print(f"\n✓ Converted {len(training_data)} examples")
    if skipped > 0:
        print(f"  Skipped {skipped} examples (missing specs)")
    print(f"✓ Saved to {output_file}")

    # Generate stats
    stats = {
        "total_examples": len(training_data),
        "skipped": skipped,
        "categories": {},
        "avg_specs_per_example": 0,
        "total_specs": 0
    }

    for example in training_data:
        category = example['metadata']['category']
        stats['categories'][category] = stats['categories'].get(category, 0) + 1

        try:
            specs = json.loads(example['output'])
            stats['total_specs'] += len(specs)
        except:
            pass

    if stats['total_examples'] > 0:
        stats['avg_specs_per_example'] = stats['total_specs'] / stats['total_examples']

    # Save stats
    stats_file = output_file.with_suffix('.stats.json')
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"✓ Saved statistics to {stats_file}")

    # Print stats
    print(f"\nStatistics:")
    print(f"  Total examples: {stats['total_examples']}")
    print(f"  Total specs: {stats['total_specs']}")
    print(f"  Avg specs per example: {stats['avg_specs_per_example']:.2f}")
    print(f"\n  Examples by category:")
    for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {category}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Convert labeled JSONL to training format')
    parser.add_argument('input_file', type=str, help='Input labeled JSONL file')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file (default: data/training/training_{timestamp}.jsonl)')

    args = parser.parse_args()

    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"Error: File {input_file} not found")
        return 1

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        training_dir = Path("data/training")
        training_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = training_dir / f"training_{timestamp}.jsonl"

    convert_to_training(input_file, output_file)

    print(f"\n{'='*70}")
    print("READY TO TRAIN")
    print(f"{'='*70}")
    print(f"\nRun training with:")
    print(f"  python train_transformer.py --training-file {output_file} --test")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
