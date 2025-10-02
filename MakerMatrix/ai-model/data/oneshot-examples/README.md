# One-Shot Examples Directory

This directory contains **high-quality, manually reviewed examples** that are used as few-shot learning examples for the LLM when processing new components.

## Purpose

These examples improve LLM extraction quality by providing context and patterns. When the LLM sees 3-5 good examples, it performs much better on new data.

## Workflow

### 1. Create One-Shot Examples (First Time)

```bash
# Start the labeling UI
python label_with_llm.py --mode web --model mistral:7b-instruct

# In the UI:
# 1. Process 10-20 diverse components (resistors, capacitors, ICs, etc.)
# 2. Carefully review and correct each extraction
# 3. Save to data/oneshot-examples/ (not data/labeled/)
```

### 2. Use Examples for Bulk Processing

When processing thousands of components, the LLM will automatically load examples from this directory and include them in the prompt:

```
Here are some examples of correct extractions:

Example 1:
Description: "100mW 10kΩ ±5% 0603 Chip Resistor"
Extracted: {
  "resistance": "10kΩ",
  "power_rating": "100mW",
  "tolerance": "±5%",
  "package": "0603"
}

Example 2:
Description: "220uF 35V ±20% SMD Electrolytic Capacitor"
Extracted: {
  "capacitance": "220uF",
  "voltage_rating": "35V",
  "tolerance": "±20%"
}

Now extract from this new component:
Description: "47uH 500mA 0805 SMD Inductor"
```

### 3. When to Update Examples

Add new examples when:
- Processing a new component category not in examples
- Finding common extraction errors
- Getting better quality corrections
- Target: 20-50 diverse, high-quality examples

## File Format

Files should be named: `oneshot_YYYYMMDD_HHMMSS.jsonl`

Each line is JSON:
```json
{
  "lcsc_number": "C123456",
  "description": "100mW 10kΩ ±5% 0603 Chip Resistor",
  "main_category": "Resistors",
  "subcategory": "Chip Resistor - Surface Mount",
  "package": "0603",
  "corrected_specs": {
    "resistance": "10kΩ",
    "power_rating": "100mW",
    "tolerance": "±5%",
    "package": "0603"
  },
  "review_status": "correct",
  "reviewed_at": "2025-09-30T18:12:55"
}
```

## Best Practices

### Diversity

Include examples from different categories:
- ✅ Resistors (different values, packages)
- ✅ Capacitors (ceramic, electrolytic, tantalum)
- ✅ Inductors (different sizes)
- ✅ ICs (different types: regulators, op-amps, etc.)
- ✅ Connectors (different pin counts, types)
- ✅ Diodes/LEDs
- ✅ Transistors

### Quality

- ✅ **Accurate**: Double-check all extracted values
- ✅ **Complete**: Extract all visible specs from description
- ✅ **Consistent**: Use same field names for same specs
- ✅ **Clean**: No typos, proper units

### Quantity

- **Minimum**: 10 examples (bare minimum for few-shot)
- **Recommended**: 20-30 examples (good coverage)
- **Maximum**: 50 examples (diminishing returns, slower prompts)

## Integration

The `label_with_llm.py` script will automatically:
1. Load all `oneshot_*.jsonl` files from this directory
2. Select 3-5 relevant examples based on category
3. Include them in the LLM prompt
4. Save new reviewed data back to this directory

## Separate from Training Data

**Important distinction:**

- **`data/oneshot-examples/`** → Few-shot prompts for LLM (10-50 examples)
- **`data/labeled/`** → Training data for ML model (1000s of examples)

The oneshot examples can also be used for ML training, but their primary purpose is improving LLM quality during bulk processing.

---

**Created:** 2025-09-30
**Purpose:** Improve LLM extraction quality through few-shot learning
