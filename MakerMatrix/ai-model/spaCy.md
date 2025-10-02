# spaCy NER Model Training Guide

Complete guide for training and testing the spaCy Named Entity Recognition model for component specification extraction.

## Quick Reference

```bash
# 1. Generate training data from labeled examples
python prepare_training_data.py --labeled-dir data/labeled --format spacy

# 2. Train the model
python train_spacy.py --training-file data/training/spacy_train_*.py --iterations 30

# 3. Test the model
python test_model.py --model models/component-ner-YYYYMMDD_HHMMSS
```

## Complete Workflow

### Step 1: Generate Labeled Data

First, you need labeled examples. Use the web UI to label and review component data:

```bash
# Start the labeling UI
python label_with_llm.py --mode web --model mistral:7b-instruct
```

**In the web UI:**
1. Load unlabeled components from LCSC database or order files
2. Let the LLM extract specifications
3. Review and correct the extractions
4. Mark as "correct" or "incorrect"
5. Save corrections
6. Export as `reviewed_YYYYMMDD_HHMMSS.jsonl` to `data/labeled/`

**Target:** 1000+ reviewed examples for good model performance

### Step 2: Convert to spaCy Format

Convert the reviewed JSONL files to spaCy training format:

```bash
python prepare_training_data.py \
  --labeled-dir data/labeled \
  --format spacy \
  --output data/training/spacy_train_$(date +%Y%m%d_%H%M%S).py
```

**What this does:**
- Loads all `reviewed_*.jsonl` files from `data/labeled/`
- Extracts text descriptions and specification entities
- Finds entity positions in the text
- Removes overlapping entities (spaCy requirement)
- Outputs Python file with training data
- Generates statistics about entities

**Example output:**
```
Found 6 reviewed files and 0 labeled files
✓ Loaded 1023 examples
  Skipped 2 examples (missing specs)

Converting to spacy format...
  Skipped 19 examples (no entities found in description)
  Removed 135 overlapping entities

✓ Saved 1004 training examples to data/training/spacy_train_20250930_180756.py

Entity Statistics:
  Total examples: 1004
  Total entities: 3158

  Entities by type:
    PACKAGE: 591
    RESISTANCE: 248
    POWER_RATING: 238
    ...
```

### Step 3: Train the Model

Train the spaCy NER model using the converted training data:

```bash
python train_spacy.py \
  --training-file data/training/spacy_train_20250930_180756.py \
  --iterations 30 \
  --dropout 0.2 \
  --test-split 0.1
```

**Command-line options:**
- `--training-file`: Path to spaCy training data file (required)
- `--output-dir`: Output directory for trained model (default: `models/component-ner-{timestamp}`)
- `--iterations`: Number of training iterations (default: 30)
- `--dropout`: Dropout rate for regularization (default: 0.2)
- `--test-split`: Fraction of data for testing (default: 0.1)
- `--no-test`: Skip testing after training

**Training process:**
```
Loading training data...
✓ Loaded 1004 training examples

Split data: 903 train, 101 test

Creating blank spaCy model...
✓ Created blank model with NER component

Adding entity labels...
✓ Added 138 entity labels

STARTING TRAINING
Iterations: 30
Dropout: 0.2

Iteration 5/30 - Loss: 1804.1522
Iteration 10/30 - Loss: 1230.9045
Iteration 15/30 - Loss: 963.0245
Iteration 20/30 - Loss: 798.2396
Iteration 25/30 - Loss: 698.9547
Iteration 30/30 - Loss: 610.5791

✓ Training complete

TESTING MODEL
Text: 2 ±0.1% 100mW ±25ppm/℃ SOT-23  Resistor Networks & Arrays ROHS...
Entities found: 2
  - 100mW                → POWER_RATING
  - ±25ppm/℃             → TEMP_COEFFICIENT

EVALUATING MODEL
Precision: 0.7033
Recall:    0.5581
F-Score:   0.6223

SAVING MODEL
✓ Model saved to models/component-ner-20250930_180917
✓ Training info saved to models/component-ner-20250930_180917/training_info.json
```

**Model output:**
- `models/component-ner-YYYYMMDD_HHMMSS/` - Trained model directory
  - `ner/` - Model weights
  - `training_info.json` - Training metadata and scores
  - `meta.json` - spaCy metadata

### Step 4: Test the Model

Test the trained model on sample descriptions:

```bash
python test_model.py --model models/component-ner-20250930_180917
```

**Example output:**
```
Loading model from models/component-ner-20250930_180917...
✓ Model loaded

INFERENCE TEST

Description: 100mW 10kΩ ±5% 0603 Chip Resistor
Entities found: 2
  PACKAGE: 0603
  POWER_RATING: 100mW
  → Structured: {'power_rating': '100mW', 'package': '0603'}

Description: 220uF 35V ±20% SMD Electrolytic Capacitor
Entities found: 3
  CAPACITANCE: 220uF
  TOLERANCE: ±20%
  VOLTAGE_RATING: 35V
  → Structured: {'capacitance': '220uF', 'voltage_rating': '35V', 'tolerance': '±20%'}
```

**Test custom descriptions:**
```bash
python test_model.py \
  --model models/component-ner-20250930_180917 \
  --description "47uH 500mA 0805 SMD Inductor" \
  --description "1N4148 100V 200mA DO-35 Diode"
```

## Using the Model in Python

### Basic Usage

```python
import spacy

# Load the trained model
nlp = spacy.load('models/component-ner-20250930_180917')

# Process a component description
description = "100mW 10kΩ ±5% 0603 Chip Resistor"
doc = nlp(description)

# Extract entities
for ent in doc.ents:
    print(f"{ent.label_}: {ent.text}")
```

**Output:**
```
POWER_RATING: 100mW
RESISTANCE: 10kΩ
TOLERANCE: ±5%
PACKAGE: 0603
```

### Extract as Dictionary

```python
import spacy

nlp = spacy.load('models/component-ner-20250930_180917')
description = "220uF 35V ±20% SMD Electrolytic Capacitor"
doc = nlp(description)

# Convert to dict
specs = {}
for ent in doc.ents:
    field_name = ent.label_.lower()
    specs[field_name] = ent.text

print(specs)
```

**Output:**
```python
{
    'capacitance': '220uF',
    'voltage_rating': '35V',
    'tolerance': '±20%'
}
```

### Batch Processing

```python
import spacy

nlp = spacy.load('models/component-ner-20250930_180917')

descriptions = [
    "100mW 10kΩ ±5% 0603",
    "220uF 35V ±20% SMD",
    "47uH 500mA 0805"
]

# Process multiple documents efficiently
for doc in nlp.pipe(descriptions):
    specs = {ent.label_.lower(): ent.text for ent in doc.ents}
    print(f"Description: {doc.text}")
    print(f"Specs: {specs}\n")
```

## Model Performance

### Understanding Metrics

**Precision** (70.33%)
- Of all entities extracted, how many were correct?
- Higher = fewer false positives

**Recall** (55.81%)
- Of all entities that should be found, how many did we find?
- Higher = fewer missing extractions

**F-Score** (62.23%)
- Harmonic mean of precision and recall
- Balance between finding entities and being accurate

### Improving Performance

#### 1. Add More Training Data

More labeled examples = better performance:
- **Current**: 1004 examples
- **Target**: 3000-5000 examples
- **Focus on**: Categories with low performance

```bash
# Generate more labeled data
python label_with_llm.py --mode web --model mistral:7b-instruct

# After labeling, retrain
python prepare_training_data.py --labeled-dir data/labeled --format spacy
python train_spacy.py --training-file data/training/spacy_train_*.py --iterations 50
```

#### 2. Increase Training Iterations

More iterations can improve learning:

```bash
# Default: 30 iterations
python train_spacy.py --training-file data/training/spacy_train_*.py --iterations 50

# Monitor loss - should decrease steadily
# If loss plateaus, more iterations won't help
```

#### 3. Adjust Dropout

Dropout prevents overfitting:

```bash
# Lower dropout = faster learning, more overfitting risk
python train_spacy.py --training-file data/training/spacy_train_*.py --dropout 0.1

# Higher dropout = slower learning, less overfitting
python train_spacy.py --training-file data/training/spacy_train_*.py --dropout 0.3
```

#### 4. Review and Fix Training Data

Bad training data = bad model:

```bash
# Check for:
# - Incorrect labels
# - Missing entities
# - Inconsistent naming
# - Overlapping entities (automatically removed)

# Fix in the web UI, then retrain
```

## Troubleshooting

### Issue: Low Recall (Missing Entities)

**Symptoms:** Model doesn't find many entities

**Solutions:**
1. Add more training examples with those entity types
2. Check if entity values are actually in the description text
3. Increase training iterations
4. Review training data for consistency

### Issue: Low Precision (Wrong Entities)

**Symptoms:** Model extracts incorrect entities

**Solutions:**
1. Review training data for errors
2. Increase dropout to reduce overfitting
3. Add more diverse examples
4. Check for ambiguous text patterns

### Issue: Overlapping Entities Warning

**Symptoms:** `Removed 135 overlapping entities` during data preparation

**Explanation:** spaCy doesn't support overlapping entities. The script keeps the longer entity and removes shorter overlapping ones.

**Example:**
```
Text: "SMD,P=0.5mm"
Entities:
  "SMD" (MOUNTING) at positions 0-3
  "SMD,P=0.5mm" (PACKAGE) at positions 0-11
→ Keeps PACKAGE (longer), removes MOUNTING
```

**Solution:** This is automatic and expected. Review output to ensure important entities aren't lost.

### Issue: Training Loss Not Decreasing

**Symptoms:** Loss stays high or increases

**Solutions:**
1. Check training data quality
2. Reduce learning rate (not exposed in current script)
3. Ensure training data has correct format
4. Try lower dropout (0.1)

### Issue: Model Too Large / Slow

**Symptoms:** Model file > 500KB, inference > 10ms

**Solutions:**
1. Current model is ~100KB and <1ms - this shouldn't happen
2. If it does, you may have added extra components to the pipeline
3. Rebuild with only NER component

## Advanced Topics

### Cross-Validation

For better performance estimates:

```python
# Split data manually into 5 folds
# Train on 4 folds, test on 1
# Repeat 5 times and average scores
```

### Entity Confidence Scores

```python
import spacy

nlp = spacy.load('models/component-ner-20250930_180917')
doc = nlp("100mW 10kΩ ±5% 0603")

# spaCy doesn't expose confidence scores by default
# But you can use the raw scores:
for ent in doc.ents:
    # Get the score from the entity
    # (requires modifying the training script to save scores)
    print(f"{ent.text} ({ent.label_})")
```

### Custom Entity Types

To add new entity types:

1. Add them to your labeled data
2. Retrain the model
3. The model will automatically learn the new entity types

### Model Versioning

Keep track of models:

```bash
# Models are automatically timestamped
ls models/
# component-ner-20250930_180917/
# component-ner-20251001_093045/
# component-ner-20251001_143022/

# Training info is saved
cat models/component-ner-20250930_180917/training_info.json
```

## Best Practices

### Training Data Quality

✅ **DO:**
- Review LLM extractions carefully
- Fix errors before marking as correct
- Ensure entity values exist in description text
- Use consistent entity type names
- Include diverse component categories

❌ **DON'T:**
- Trust LLM extractions without review
- Include entities not visible in description
- Use different names for same entity type
- Skip difficult examples
- Over-represent one component category

### Model Training

✅ **DO:**
- Start with 30 iterations
- Use 10% test split for evaluation
- Monitor training loss (should decrease)
- Test on real examples after training
- Keep old models for comparison

❌ **DON'T:**
- Train on less than 500 examples
- Use 100+ iterations (overfitting risk)
- Skip testing
- Train on unreviewed data
- Delete old models immediately

### Model Usage

✅ **DO:**
- Load model once and reuse
- Use `nlp.pipe()` for batch processing
- Convert to dict for structured data
- Handle missing entities gracefully
- Monitor extraction quality

❌ **DON'T:**
- Reload model for each prediction
- Process one at a time if batching possible
- Assume all entities will be found
- Trust extractions blindly
- Ignore low-confidence predictions

## File Structure

```
ai-model/
├── prepare_training_data.py      # Convert JSONL → spaCy format
├── train_spacy.py                # Train spaCy NER model
├── test_model.py                 # Test trained model
├── spaCy.md                      # This guide
└── data/
    ├── labeled/                  # Reviewed JSONL files
    │   └── reviewed_*.jsonl
    ├── training/                 # spaCy training data
    │   └── spacy_train_*.py
    └── models/                   # Trained models
        └── component-ner-*/
            ├── ner/              # Model weights
            ├── training_info.json
            └── meta.json
```

## Quick Commands Cheat Sheet

```bash
# Full workflow from scratch
python label_with_llm.py --mode web --model mistral:7b-instruct
# (label data in web UI)
python prepare_training_data.py --labeled-dir data/labeled --format spacy
python train_spacy.py --training-file data/training/spacy_train_*.py --iterations 30
python test_model.py --model models/component-ner-*

# Retrain with more data
python prepare_training_data.py --labeled-dir data/labeled --format spacy
python train_spacy.py --training-file data/training/spacy_train_*.py --iterations 50

# Test specific descriptions
python test_model.py --model models/component-ner-20250930_180917 \
  --description "Your description here"

# Use in Python
python -c "
import spacy
nlp = spacy.load('models/component-ner-20250930_180917')
doc = nlp('100mW 10kΩ ±5% 0603')
print({ent.label_.lower(): ent.text for ent in doc.ents})
"
```

---

**Created:** 2025-09-30
**Model Version:** v1.0
**Performance:** 70.33% precision, 55.81% recall, 62.23% F-score
