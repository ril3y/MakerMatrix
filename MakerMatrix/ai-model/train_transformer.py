#!/usr/bin/env python3
"""
Train a small transformer model for component specification extraction.

Uses T5-small or FLAN-T5-small for text-to-JSON conversion.
Fast training (10-30 minutes on CPU for 1000 samples).

Usage:
    python train_transformer.py --training-file data/training/training_XXXXXXXX.jsonl
"""

import argparse
import json
import torch
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from torch.utils.data import Dataset, DataLoader
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from sklearn.model_selection import train_test_split


class ComponentDataset(Dataset):
    """Dataset for component specification extraction."""

    def __init__(self, examples: List[Dict], tokenizer, max_input_length=512, max_output_length=256):
        self.examples = examples
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_output_length = max_output_length

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        example = self.examples[idx]

        # Tokenize input
        input_encoding = self.tokenizer(
            example['input'],
            max_length=self.max_input_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        # Tokenize output
        output_encoding = self.tokenizer(
            example['output'],
            max_length=self.max_output_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': input_encoding['input_ids'].squeeze(),
            'attention_mask': input_encoding['attention_mask'].squeeze(),
            'labels': output_encoding['input_ids'].squeeze()
        }


def load_training_data(training_file: Path) -> List[Dict]:
    """Load training data from JSONL file."""
    examples = []

    print(f"Loading training data from {training_file}...")
    with open(training_file, 'r') as f:
        for line in f:
            if line.strip():
                example = json.loads(line)
                examples.append(example)

    print(f"✓ Loaded {len(examples)} training examples")
    return examples


def prepare_datasets(examples: List[Dict], tokenizer, test_size=0.1):
    """Split data into train and validation sets."""
    print(f"\nSplitting data: {int((1-test_size)*100)}% train, {int(test_size*100)}% validation")

    train_examples, val_examples = train_test_split(
        examples,
        test_size=test_size,
        random_state=42
    )

    train_dataset = ComponentDataset(train_examples, tokenizer)
    val_dataset = ComponentDataset(val_examples, tokenizer)

    print(f"✓ Train set: {len(train_dataset)} examples")
    print(f"✓ Validation set: {len(val_dataset)} examples")

    return train_dataset, val_dataset


def train_model(
    training_file: Path,
    model_name: str = "google/flan-t5-small",
    output_dir: Path = None,
    num_epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 5e-5
):
    """Train the transformer model."""

    print(f"\n{'='*70}")
    print("TRANSFORMER MODEL TRAINING")
    print(f"{'='*70}\n")

    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Load tokenizer and model
    print(f"\nLoading model: {model_name}")
    tokenizer = T5Tokenizer.from_pretrained(model_name)
    model = T5ForConditionalGeneration.from_pretrained(model_name)

    # Load and prepare data
    examples = load_training_data(training_file)
    train_dataset, val_dataset = prepare_datasets(examples, tokenizer)

    # Setup output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"models/component-extractor-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=str(output_dir / "logs"),
        logging_steps=50,
        eval_strategy="steps",
        eval_steps=200,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        report_to="none",
        warmup_steps=100,
        fp16=device == "cuda",  # Use mixed precision on GPU
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True
    )

    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=data_collator,
    )

    # Train
    print(f"\n{'='*70}")
    print("STARTING TRAINING")
    print(f"{'='*70}\n")
    print(f"Epochs: {num_epochs}")
    print(f"Batch size: {batch_size}")
    print(f"Learning rate: {learning_rate}")
    print(f"Output directory: {output_dir}")
    print()

    trainer.train()

    # Save final model
    print(f"\n{'='*70}")
    print("SAVING MODEL")
    print(f"{'='*70}\n")

    final_model_dir = output_dir / "final"
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(final_model_dir))

    print(f"✓ Model saved to {final_model_dir}")

    # Evaluate
    print(f"\n{'='*70}")
    print("FINAL EVALUATION")
    print(f"{'='*70}\n")

    eval_results = trainer.evaluate()
    print(f"Validation loss: {eval_results['eval_loss']:.4f}")

    # Save training info
    info = {
        "model_name": model_name,
        "training_file": str(training_file),
        "num_examples": len(examples),
        "num_epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "final_eval_loss": eval_results['eval_loss'],
        "trained_at": datetime.now().isoformat()
    }

    with open(output_dir / "training_info.json", 'w') as f:
        json.dump(info, f, indent=2)

    return final_model_dir


def test_model(model_dir: Path, test_description: str = None):
    """Test the trained model."""
    print(f"\n{'='*70}")
    print("TESTING MODEL")
    print(f"{'='*70}\n")

    # Load model and tokenizer
    print(f"Loading model from {model_dir}...")
    tokenizer = T5Tokenizer.from_pretrained(str(model_dir))
    model = T5ForConditionalGeneration.from_pretrained(str(model_dir))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    # Default test case
    if test_description is None:
        test_description = """Extract specifications from this electronic component.

Component Information:
Category: Resistors/Chip Resistor - Surface Mount
Package: 0603
Description: 100mW Thick Film Resistors 75V ±100ppm/℃ ±5% 10kΩ 0603 Chip Resistor - Surface Mount ROHS

Extract the relevant specifications and return them as a JSON object with appropriate fields."""

    print(f"Input:\n{test_description}\n")

    # Tokenize input
    inputs = tokenizer(
        test_description,
        max_length=512,
        truncation=True,
        return_tensors='pt'
    ).to(device)

    # Generate output
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=256,
            num_beams=4,
            early_stopping=True
        )

    # Decode output
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    print(f"Output:\n{result}\n")

    # Try to parse as JSON
    try:
        parsed = json.loads(result)
        print("✓ Valid JSON output")
        print(f"Extracted fields: {', '.join(parsed.keys())}")
    except json.JSONDecodeError:
        print("⚠ Output is not valid JSON")


def main():
    parser = argparse.ArgumentParser(description='Train transformer model for component extraction')
    parser.add_argument('--training-file', type=str, required=True,
                        help='Path to training JSONL file')
    parser.add_argument('--model-name', type=str, default='google/flan-t5-small',
                        help='Base model to fine-tune (default: google/flan-t5-small)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory for trained model')
    parser.add_argument('--epochs', type=int, default=3,
                        help='Number of training epochs (default: 3)')
    parser.add_argument('--batch-size', type=int, default=8,
                        help='Training batch size (default: 8)')
    parser.add_argument('--learning-rate', type=float, default=5e-5,
                        help='Learning rate (default: 5e-5)')
    parser.add_argument('--test', action='store_true',
                        help='Run a test after training')

    args = parser.parse_args()

    training_file = Path(args.training_file)
    if not training_file.exists():
        print(f"Error: Training file {training_file} not found")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else None

    # Train model
    try:
        final_model_dir = train_model(
            training_file=training_file,
            model_name=args.model_name,
            output_dir=output_dir,
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate
        )

        print(f"\n{'='*70}")
        print("TRAINING COMPLETE")
        print(f"{'='*70}\n")
        print(f"Model saved to: {final_model_dir}")
        print(f"\nTo use this model, update label_with_llm.py to load from:")
        print(f"  {final_model_dir}")

        # Optional test
        if args.test:
            test_model(final_model_dir)

        return 0

    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
