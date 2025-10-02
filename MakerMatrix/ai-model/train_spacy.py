#!/usr/bin/env python3
"""
Train a spaCy NER model for component specification extraction.

This script trains a spaCy Named Entity Recognition model on labeled
component data to extract structured specifications from text descriptions.

Usage:
    python train_spacy.py --training-file data/training/spacy_train_*.py
"""

import argparse
import random
import spacy
from spacy.training import Example
from pathlib import Path
from datetime import datetime
import json


def load_training_data(training_file: Path):
    """Load training data from Python file."""
    print(f"Loading training data from {training_file}...")

    # Import the training data
    import sys
    sys.path.insert(0, str(training_file.parent))
    module_name = training_file.stem

    training_module = __import__(module_name)
    train_data = training_module.TRAIN_DATA

    print(f"✓ Loaded {len(train_data)} training examples")
    return train_data


def create_blank_model():
    """Create a blank spaCy model with NER component."""
    print("\nCreating blank spaCy model...")
    nlp = spacy.blank("en")

    # Add NER component
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")

    print("✓ Created blank model with NER component")
    return nlp


def add_labels(nlp, train_data):
    """Add entity labels to the NER component."""
    print("\nAdding entity labels...")
    ner = nlp.get_pipe("ner")

    labels = set()
    for _, annotations in train_data:
        for ent in annotations.get("entities"):
            labels.add(ent[2])

    for label in labels:
        ner.add_label(label)

    print(f"✓ Added {len(labels)} entity labels")
    return labels


def train_model(nlp, train_data, n_iter=30, drop=0.2):
    """Train the spaCy NER model."""
    print(f"\n{'='*70}")
    print("STARTING TRAINING")
    print(f"{'='*70}\n")
    print(f"Iterations: {n_iter}")
    print(f"Dropout: {drop}")
    print()

    # Get the NER component
    ner = nlp.get_pipe("ner")

    # Disable other pipeline components during training
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]

    # Train the model
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()

        for itn in range(n_iter):
            random.shuffle(train_data)
            losses = {}

            # Batch the examples
            batches = spacy.util.minibatch(train_data, size=8)

            for batch in batches:
                examples = []
                for text, annotations in batch:
                    doc = nlp.make_doc(text)
                    example = Example.from_dict(doc, annotations)
                    examples.append(example)

                nlp.update(examples, drop=drop, losses=losses, sgd=optimizer)

            # Print progress every 5 iterations
            if (itn + 1) % 5 == 0:
                print(f"Iteration {itn + 1}/{n_iter} - Loss: {losses['ner']:.4f}")

    print(f"\n✓ Training complete")
    return nlp


def test_model(nlp, test_examples):
    """Test the trained model on sample examples."""
    print(f"\n{'='*70}")
    print("TESTING MODEL")
    print(f"{'='*70}\n")

    for text, _ in test_examples[:3]:
        doc = nlp(text)
        print(f"Text: {text[:80]}...")
        print(f"Entities found: {len(doc.ents)}")

        if doc.ents:
            for ent in doc.ents:
                print(f"  - {ent.text:20s} → {ent.label_}")
        else:
            print("  (no entities found)")
        print()


def evaluate_model(nlp, test_data):
    """Evaluate model performance."""
    print(f"\n{'='*70}")
    print("EVALUATING MODEL")
    print(f"{'='*70}\n")

    examples = []
    for text, annotations in test_data:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, annotations)
        examples.append(example)

    scores = nlp.evaluate(examples)

    print(f"Precision: {scores['ents_p']:.4f}")
    print(f"Recall:    {scores['ents_r']:.4f}")
    print(f"F-Score:   {scores['ents_f']:.4f}")

    return scores


def save_model(nlp, output_dir: Path, train_data, labels, scores=None):
    """Save the trained model."""
    print(f"\n{'='*70}")
    print("SAVING MODEL")
    print(f"{'='*70}\n")

    output_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(output_dir)

    print(f"✓ Model saved to {output_dir}")

    # Save training info
    info = {
        "trained_at": datetime.now().isoformat(),
        "num_examples": len(train_data),
        "num_labels": len(labels),
        "labels": sorted(list(labels)),
        "scores": scores if scores else {}
    }

    info_path = output_dir / "training_info.json"
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)

    print(f"✓ Training info saved to {info_path}")


def main():
    parser = argparse.ArgumentParser(description='Train spaCy NER model for component extraction')
    parser.add_argument('--training-file', type=str, required=True,
                        help='Path to spaCy training data file (.py)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory for trained model')
    parser.add_argument('--iterations', type=int, default=30,
                        help='Number of training iterations (default: 30)')
    parser.add_argument('--dropout', type=float, default=0.2,
                        help='Dropout rate (default: 0.2)')
    parser.add_argument('--test-split', type=float, default=0.1,
                        help='Fraction of data to use for testing (default: 0.1)')
    parser.add_argument('--no-test', action='store_true',
                        help='Skip testing after training')

    args = parser.parse_args()

    training_file = Path(args.training_file)
    if not training_file.exists():
        print(f"Error: Training file {training_file} not found")
        return 1

    print(f"{'='*70}")
    print("SPACY NER MODEL TRAINING")
    print(f"{'='*70}\n")

    # Load training data
    train_data = load_training_data(training_file)

    # Split into train and test
    if not args.no_test and args.test_split > 0:
        split_idx = int(len(train_data) * (1 - args.test_split))
        random.shuffle(train_data)
        train_examples = train_data[:split_idx]
        test_examples = train_data[split_idx:]

        print(f"\nSplit data: {len(train_examples)} train, {len(test_examples)} test")
    else:
        train_examples = train_data
        test_examples = []

    # Create blank model
    nlp = create_blank_model()

    # Add labels
    labels = add_labels(nlp, train_examples)

    # Train model
    nlp = train_model(nlp, train_examples, n_iter=args.iterations, drop=args.dropout)

    # Test model
    scores = None
    if test_examples and not args.no_test:
        test_model(nlp, test_examples)
        scores = evaluate_model(nlp, test_examples)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = models_dir / f"component-ner-{timestamp}"

    # Save model
    save_model(nlp, output_dir, train_examples, labels, scores)

    print(f"\n{'='*70}")
    print("TRAINING COMPLETE")
    print(f"{'='*70}\n")
    print(f"Model saved to: {output_dir}")
    print(f"\nTo use this model:")
    print(f"  import spacy")
    print(f"  nlp = spacy.load('{output_dir}')")
    print(f"  doc = nlp('100mW 10kΩ ±5% 0603')")
    print(f"  for ent in doc.ents:")
    print(f"      print(ent.text, ent.label_)")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
