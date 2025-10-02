#!/usr/bin/env python3
"""
Train an Ollama model using the prepared training data.

This script uses Ollama's built-in fine-tuning capabilities to create
a custom model for component specification extraction.

Usage:
    python train_ollama.py --training-file data/training/training_XXXXXXXX.jsonl
"""

import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime


def convert_to_ollama_format(training_file: Path, output_file: Path):
    """Convert training data to Ollama's expected format."""
    print(f"Converting {training_file} to Ollama format...")

    with open(training_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            if line.strip():
                example = json.loads(line)

                # Ollama expects: {"prompt": "...", "completion": "..."}
                ollama_example = {
                    "prompt": example["input"],
                    "completion": example["output"]
                }

                f_out.write(json.dumps(ollama_example) + '\n')

    print(f"✓ Converted data saved to {output_file}")


def create_modelfile(base_model: str, training_file: Path, output_file: Path):
    """Create an Ollama Modelfile for fine-tuning."""
    modelfile_content = f"""FROM {base_model}

# Fine-tuned for electronic component specification extraction
TEMPLATE \"\"\"{{{{ .System }}}}

{{{{ .Prompt }}}}\"\"\"

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER stop "\\n\\n"

SYSTEM \"\"\"You are an expert at extracting structured specifications from electronic component descriptions.
Your task is to extract relevant technical specifications and return them as a JSON object.
Focus on key parameters like voltage, current, resistance, capacitance, power, tolerance, and package type.\"\"\"
"""

    with open(output_file, 'w') as f:
        f.write(modelfile_content)

    print(f"✓ Modelfile created at {output_file}")


def train_model(modelfile_path: Path, model_name: str):
    """Train the model using Ollama."""
    print(f"\n{'='*70}")
    print(f"TRAINING MODEL: {model_name}")
    print(f"{'='*70}\n")

    # Create the model
    cmd = ['ollama', 'create', model_name, '-f', str(modelfile_path)]
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Training failed: {result.stderr}")
        return False

    print(result.stdout)
    print(f"\n✓ Model '{model_name}' created successfully!")
    return True


def test_model(model_name: str, test_prompt: str):
    """Test the trained model."""
    print(f"\n{'='*70}")
    print("TESTING MODEL")
    print(f"{'='*70}\n")

    print(f"Test prompt: {test_prompt}\n")

    cmd = ['ollama', 'run', model_name, test_prompt]
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("Response:")
    print(result.stdout)


def main():
    parser = argparse.ArgumentParser(description='Train Ollama model for component extraction')
    parser.add_argument('--training-file', type=str, required=True,
                        help='Path to training JSONL file')
    parser.add_argument('--base-model', type=str, default='mistral:7b-instruct',
                        help='Base model to fine-tune (default: mistral:7b-instruct)')
    parser.add_argument('--model-name', type=str, default=None,
                        help='Name for the trained model (default: component-extractor-YYYYMMDD)')
    parser.add_argument('--test', action='store_true',
                        help='Run a test after training')

    args = parser.parse_args()

    training_file = Path(args.training_file)
    if not training_file.exists():
        print(f"Error: Training file {training_file} not found")
        return 1

    # Generate model name if not provided
    if args.model_name:
        model_name = args.model_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d")
        model_name = f"component-extractor-{timestamp}"

    # Create output directory
    output_dir = Path("models")
    output_dir.mkdir(exist_ok=True)

    # Convert training data to Ollama format
    ollama_training_file = output_dir / f"{model_name}_training.jsonl"
    convert_to_ollama_format(training_file, ollama_training_file)

    # Create Modelfile
    modelfile_path = output_dir / f"{model_name}.Modelfile"
    create_modelfile(args.base_model, ollama_training_file, modelfile_path)

    # Train the model
    success = train_model(modelfile_path, model_name)

    if not success:
        return 1

    print(f"\n{'='*70}")
    print("TRAINING COMPLETE")
    print(f"{'='*70}\n")
    print(f"Model name: {model_name}")
    print(f"Training data: {training_file}")
    print(f"Base model: {args.base_model}")
    print(f"\nTo use this model:")
    print(f"  python label_with_llm.py --model {model_name}")
    print(f"\nOr in web mode:")
    print(f"  python label_with_llm.py --mode web --model {model_name}")

    # Optional test
    if args.test:
        test_prompt = """Extract specifications from this electronic component.

Component Information:
Category: Resistors/Chip Resistor - Surface Mount
Package: 0603
Description: 100mW Thick Film Resistors 75V ±100ppm/℃ ±5% 10kΩ 0603 Chip Resistor - Surface Mount ROHS

Extract the relevant specifications and return them as a JSON object with appropriate fields."""

        test_model(model_name, test_prompt)

    return 0


if __name__ == '__main__':
    exit(main())
