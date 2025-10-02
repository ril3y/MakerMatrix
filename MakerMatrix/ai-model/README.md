# MakerMatrix AI Model - Component Description Extraction

This directory contains tools for training ML models to extract structured data from component descriptions.

## Overview

The goal is to automatically extract structured information (resistance, capacitance, package type, etc.) from free-text component descriptions like:

```
"10K 0805 1% 1/4W Thick Film Resistor"
→ {resistance: "10K", package: "0805", tolerance: "1%", power: "1/4W"}
```

## Pipeline Architecture

### Phase 1: Data Collection
- Download complete LCSC parts database (~500K+ components)
- Extract descriptions and existing categorization
- Filter and sample diverse component types

### Phase 2: LLM Labeling
- Use local Ollama (llama3.2) to label descriptions
- Extract structured fields for each component type
- Generate training dataset with ~10K-50K labeled examples

### Phase 3: Model Training
- Train traditional ML model on LLM-labeled data
- Use sklearn/spaCy for fast inference
- Target: <100ms inference time per description

### Phase 4: Integration
- Add extraction endpoint to MakerMatrix API
- Auto-extract fields during part import
- Populate additional_properties automatically

## Files

### Scripts

- **`download_lcsc_database.py`** - Download complete LCSC database from jlcparts
- **`extract_training_data.py`** - Extract and sample descriptions from database
- **`label_with_llm.py`** - Use Ollama to label descriptions with structured data
- **`train_model.py`** - Train sklearn model on labeled data
- **`inference.py`** - Fast inference API for production use

### Directories

- **`data/lcsc_raw/`** - Downloaded LCSC database (SQLite)
- **`data/training/`** - Sampled descriptions for labeling
- **`data/labeled/`** - LLM-labeled training data
- **`models/`** - Trained sklearn models
- **`notebooks/`** - Jupyter notebooks for exploration

## Quick Start

### 1. Download LCSC Database

```bash
cd MakerMatrix/ai-model
python download_lcsc_database.py
```

This will:
- Download ~500K component descriptions from jlcparts
- Extract SQLite database (~100-500MB)
- Inspect database structure

**Requirements:**
- `wget` - for downloading files
- `7z` (p7zip) - for extraction

**Install dependencies:**
```bash
# Ubuntu/Debian
sudo apt install wget p7zip-full

# macOS
brew install wget p7zip
```

### 2. Extract Training Data

```bash
python extract_training_data.py --sample-size 10000
```

This will:
- Query the LCSC SQLite database
- Sample diverse component types
- Export to JSON for labeling

### 3. Label with LLM

```bash
python label_with_llm.py --model llama3.2
```

This will:
- Use local Ollama to label descriptions
- Extract structured fields automatically
- Save labeled training data

**Requires:** Ollama running locally with llama3.2 model

### 4. Train Model

```bash
python train_model.py
```

This will:
- Train sklearn model on labeled data
- Evaluate accuracy and performance
- Save model for production use

### 5. Use in Production

```python
from MakerMatrix.ai_model.inference import ComponentExtractor

extractor = ComponentExtractor()
result = extractor.extract("10K 0805 1% 1/4W Thick Film Resistor")

# Result:
# {
#   "category": "resistor",
#   "resistance": "10K",
#   "package": "0805",
#   "tolerance": "1%",
#   "power": "1/4W"
# }
```

## Configuration

### Ollama Setup

Make sure Ollama is running locally:

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull llama3.2 model
ollama pull llama3.2

# Verify it's running
ollama list
```

### Component Categories

The system supports extraction for these component types:

- **Resistors**: resistance, package, tolerance, power, type
- **Capacitors**: capacitance, voltage, package, tolerance, type
- **Microcontrollers**: core, flash, ram, speed, package
- **Transistors**: type, package, voltage, current
- **Diodes/LEDs**: type, voltage, current, color, package
- **Inductors**: inductance, current, package, tolerance
- **Connectors**: type, pins, pitch, mounting
- **ICs**: function, package, voltage, pins

More categories can be added as needed.

## Performance Targets

- **Labeling**: ~1-3 seconds per description (LLM)
- **Training**: ~5-30 minutes for 10K samples
- **Inference**: <100ms per description (traditional ML)
- **Accuracy**: >85% field extraction accuracy

## Rate Limits

### LCSC Database (jlcparts)
- ✅ No rate limits - full database download
- ✅ ~500K+ component descriptions available

### Ollama (Local)
- ✅ No rate limits - runs locally
- ⚠️ Speed depends on hardware (1-3 sec/description)
- 💾 Requires ~4-8GB RAM for llama3.2

### Mouser API (Fallback)
- ⚠️ 30 calls/minute, 1,000 calls/day
- Only use if LCSC data insufficient

## Roadmap

- [x] Download LCSC database
- [ ] Extract training samples
- [ ] LLM labeling pipeline
- [ ] Train sklearn model
- [ ] Inference API
- [ ] Integration with import system
- [ ] Web UI for manual corrections
- [ ] Model retraining workflow

## Notes

### Why LCSC Database?

- **Size**: 500K+ components vs 1K from Mouser API
- **Speed**: Instant download vs rate-limited API
- **Cost**: Free vs API quota management
- **Quality**: Pre-categorized and structured

### Why LLM → Traditional ML?

- **Best of both worlds**:
  - LLM provides intelligent labeling (one-time)
  - Traditional ML provides fast inference (production)
- **Cost effective**:
  - LLM labeling is one-time cost (few hours locally)
  - Inference is near-instant and free forever
- **Scalable**:
  - Train once, run millions of times
  - No dependency on LLM availability

## Troubleshooting

### Download fails
- Check internet connection
- Verify wget and 7z are installed
- Try manual download from https://yaqwsx.github.io/jlcparts/data/

### Ollama errors
- Ensure Ollama is running: `ollama list`
- Check model is installed: `ollama pull llama3.2`
- Verify sufficient RAM (8GB+ recommended)

### Database not found
- Check `data/lcsc_raw/cache.sqlite3` exists
- Re-run download script if missing
- Check extraction completed successfully
