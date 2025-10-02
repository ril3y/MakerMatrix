# Component Specification Extraction - Training Guide

This guide explains how to train a custom model for extracting structured specifications from component descriptions.

## Overview

The training pipeline consists of three stages:

1. **Label & Review** - Use the web UI to label components and create training examples
2. **Prepare Training Data** - Convert reviewed examples to training format
3. **Train Model** - Fine-tune a transformer model on your data

## Prerequisites

```bash
# Install training dependencies
source venv/bin/activate
pip install torch transformers scikit-learn accelerate
```

## Stage 1: Label & Review Components

Start the labeling web service:

```bash
python label_with_llm.py --mode web --model mistral:7b-instruct
```

Then open http://localhost:8766 and:

1. Enter sample count (start with 10-20 for quick iteration)
2. Click "▶️ Start Labeling"
3. Review each component:
   - Check extracted specifications
   - Add missing fields using database attributes (+ buttons)
   - Add custom fields if needed
   - Mark as "Correct" or "Needs Review"
4. Click "💾 Save Reviewed Data"

Your reviewed data is saved to `data/labeled/reviewed_YYYYMMDD_HHMMSS.jsonl`

**Tips:**
- Review 20-50 examples manually to get high-quality few-shot examples
- The system automatically uses these as examples for future extractions
- Focus on getting diverse categories (resistors, capacitors, ICs, etc.)

## Stage 2: Generate Large Dataset

Once you have 20-50 reviewed examples:

1. Click "▶️ Start Labeling" with a larger count (1000+)
2. Let it run - the model will use your reviewed examples
3. Click "💾 Download Results" (these don't need manual review)
4. Click "🎓 Prepare Training Data"

This converts all reviewed files to training format at `data/training/training_YYYYMMDD_HHMMSS.jsonl`

## Stage 3: Train the Model

### Quick Training (Recommended)

Train with default settings (3 epochs, batch size 8):

```bash
python train_transformer.py \
    --training-file data/training/training_XXXXXX.jsonl \
    --test
```

### Custom Training

```bash
python train_transformer.py \
    --training-file data/training/training_XXXXXX.jsonl \
    --model-name google/flan-t5-small \
    --epochs 5 \
    --batch-size 16 \
    --learning-rate 3e-5 \
    --output-dir models/my-custom-model \
    --test
```

**Training Parameters:**

- `--model-name`: Base model (default: `google/flan-t5-small`)
  - Options: `google/flan-t5-small` (77M params, fast)
  - `google/flan-t5-base` (250M params, better)
  - `google/flan-t5-large` (780M params, best, slow)

- `--epochs`: Training epochs (default: 3)
  - More epochs = better fit, but risk overfitting
  - Start with 3, increase to 5-10 if needed

- `--batch-size`: Training batch size (default: 8)
  - Larger = faster but needs more memory
  - Reduce to 4 if you get OOM errors

- `--learning-rate`: Learning rate (default: 5e-5)
  - Higher = faster learning, but less stable
  - Lower = more stable, but slower

### Training Time Estimates

For 1000 examples:

- **CPU only**: 30-60 minutes
- **GPU (RTX 3060)**: 10-15 minutes
- **GPU (RTX 4090)**: 5-10 minutes

The script will:
- Download the base model (first time only)
- Split data 90% train / 10% validation
- Train and save checkpoints
- Evaluate on validation set
- Save final model to `models/component-extractor-YYYYMMDD_HHMMSS/final/`

## Stage 4: Use the Trained Model

### Option A: Create an Inference Script

Create `inference.py`:

```python
from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

# Load model
model_dir = "models/component-extractor-XXXXXX/final"
tokenizer = T5Tokenizer.from_pretrained(model_dir)
model = T5ForConditionalGeneration.from_pretrained(model_dir)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
model.eval()

def extract_specs(description, category, package):
    """Extract specifications from component description."""

    # Build input prompt
    prompt = f"""Extract specifications from this electronic component.

Component Information:
Category: {category}
Package: {package}
Description: {description}

Extract the relevant specifications and return them as a JSON object with appropriate fields."""

    # Tokenize
    inputs = tokenizer(
        prompt,
        max_length=512,
        truncation=True,
        return_tensors='pt'
    ).to(device)

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_length=256,
            num_beams=4,
            early_stopping=True
        )

    # Decode
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Parse JSON
    import json
    return json.loads(result)

# Example usage
specs = extract_specs(
    description="100mW Thick Film Resistors 75V ±100ppm/℃ ±5% 10kΩ 0603 Chip Resistor - Surface Mount ROHS",
    category="Resistors/Chip Resistor - Surface Mount",
    package="0603"
)

print(specs)
# Output: {"resistance": "10kΩ", "tolerance": "±5%", "power_rating": "100mW", ...}
```

### Option B: Integrate with label_with_llm.py

Add a new labeler class to `label_with_llm.py`:

```python
class TransformerLabeler:
    def __init__(self, model_path: str):
        self.tokenizer = T5Tokenizer.from_pretrained(model_path)
        self.model = T5ForConditionalGeneration.from_pretrained(model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    def label_component(self, component: Dict) -> Dict:
        # Similar to inference.py above
        pass
```

Then use it:

```bash
python label_with_llm.py --mode web --model-type transformer --model-path models/component-extractor-XXXXXX/final
```

## Performance Tips

### Improve Accuracy

1. **More training data**: Aim for 1000-2000 examples
2. **Better examples**: Review more examples manually (50-100)
3. **Diverse categories**: Cover all component types
4. **Longer training**: Increase epochs to 5-10
5. **Larger model**: Use flan-t5-base instead of small

### Reduce Training Time

1. **Use GPU**: 5-10x faster than CPU
2. **Smaller model**: Use flan-t5-small (fastest)
3. **Larger batch size**: 16 or 32 if you have enough memory
4. **Fewer epochs**: Start with 3

### Reduce Model Size

1. **Use smaller base model**: flan-t5-small is 300MB
2. **Quantization**: Convert to 8-bit after training
3. **Pruning**: Remove unused weights (advanced)

## Troubleshooting

### Out of Memory Errors

```bash
# Reduce batch size
python train_transformer.py --training-file ... --batch-size 4

# Or use CPU only (slower)
export CUDA_VISIBLE_DEVICES=""
python train_transformer.py --training-file ...
```

### Poor Quality Outputs

- Review more examples manually (aim for 50-100)
- Train for more epochs (5-10)
- Use a larger model (flan-t5-base)
- Check that training data is diverse

### Model Not Improving

- Check training loss is decreasing
- Verify data quality (look at training_XXXXXX.jsonl)
- Try different learning rate (3e-5 or 1e-4)
- Make sure you have enough examples (500+)

## Next Steps

1. **Evaluate**: Test on held-out examples
2. **Iterate**: Add more training data for poorly performing categories
3. **Deploy**: Integrate into your application
4. **Monitor**: Track accuracy on real-world data
5. **Retrain**: Periodically add new examples and retrain

## File Structure

```
MakerMatrix/ai-model/
├── label_with_llm.py          # Main labeling service
├── review_labels.html          # Web UI
├── prepare_training_data.py    # Convert reviews to training format
├── train_transformer.py        # Train the model
├── data/
│   ├── labeled/               # Reviewed examples (few-shot)
│   │   └── reviewed_*.jsonl
│   └── training/              # Training data
│       └── training_*.jsonl
└── models/                     # Trained models
    └── component-extractor-*/
        └── final/
            ├── pytorch_model.bin
            ├── config.json
            └── tokenizer files
```

## Advanced: Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| flan-t5-small | 300MB | Fast | Good | Development, testing |
| flan-t5-base | 900MB | Medium | Better | Production |
| flan-t5-large | 3GB | Slow | Best | High accuracy needed |

## Resources

- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [T5 Model Card](https://huggingface.co/google/flan-t5-small)
- [Training Tips](https://huggingface.co/docs/transformers/training)
