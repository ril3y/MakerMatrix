# AI Model Development Status

## Overview

AI model pipeline for extracting structured specifications from component descriptions using hybrid LLM + traditional ML approach.

## Current Status: Phase 3.5 - Oneshot Training Data Generation ✅

### Completed

- [x] **Download LCSC Database** (7 million components)
- [x] **Extraction Script** (intelligent sampling by category)
- [x] **LLM Labeling Script** (Ollama-based extraction)
- [x] **Test Run** (100 samples extracted successfully)
- [x] **Generate Training Data** (1023 labeled examples)
- [x] **Train spaCy NER Model** (70.33% precision, 62.23% F-score)
- [x] **Model Testing** (inference < 1ms per component)
- [x] **External Prompt Management** (extraction_prompt.txt for easy editing)
- [x] **Order File Support** (DigiKey CSV + Mouser XLS parsing)
- [x] **Web UI Data Source Selection** (LCSC/DigiKey/Mouser)
- [x] **Prompt Quality Fix** (eliminated LLM copying from examples)

### Database Statistics

- **Total Components**: 6,997,290
- **Categories**: 1,648 unique category/subcategory combinations
- **Major Categories**: Resistors (938K), Connectors (570K), Capacitors (532K), etc.
- **Database Size**: 6.7 GB
- **Data Quality**: High - includes titles, categories, packages, manufacturers, datasheets

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Data Collection (COMPLETE)                            │
├─────────────────────────────────────────────────────────────────┤
│ download_lcsc_database.py → 7M components from jlcparts        │
│ extract_training_data.py  → Smart sampling by category         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: LLM Labeling (READY)                                  │
├─────────────────────────────────────────────────────────────────┤
│ label_with_llm.py          → Ollama extracts specifications    │
│ Model: llama3.2 (local)                                         │
│ Speed: ~2-3 seconds/component                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Model Training (COMPLETE)                             │
├─────────────────────────────────────────────────────────────────┤
│ train_spacy.py             → Train spaCy NER model             │
│ Achievement: <1ms inference time, 70.33% precision             │
│ Model: models/component-ner-20250930_180917                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Integration (TODO)                                    │
├─────────────────────────────────────────────────────────────────┤
│ inference.py               → Production API                     │
│ Integration with import system                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Recent Improvements (2025-09-30)

### External Prompt System
**Problem:** LLM was copying specifications from few-shot examples instead of extracting from actual descriptions.

**Example of Issue:**
- Description: "100uF 25V ±20% Aluminum Electrolytic Capacitor"
- Extracted (WRONG): `{"type": "Wire To Board Connector", "pins": "6", "pitch": "1.5mm"}`

**Solution:**
1. Moved prompt to external file (`extraction_prompt.txt`)
2. Simplified from 200+ line complex prompt to focused extraction rules
3. Removed overwhelming examples that were confusing the LLM
4. Emphasized "Extract ONLY what is in THIS description"

**Result:**
- Same capacitor now correctly extracts: `{"capacitance": "100uF", "voltage_rating": "25V", "tolerance": "±20%", "type": "Capacitor"}`
- Accuracy improved from ~20% to ~80% on test samples
- Users can now easily edit `extraction_prompt.txt` without touching code

### Multi-Supplier Support
**Added:** DigiKey CSV and Mouser XLS order file parsing
- `convert_orders_to_training_data.py` - Process order files into training data
- Web UI dropdown to select data source (LCSC/DigiKey/Mouser)
- Automatic deduplication across multiple order files
- Support for both CSV (DigiKey) and XLS (Mouser) formats

**Workflow:**
1. Place order files in `orders/` directory
2. Select data source in web UI
3. LLM extracts specifications
4. Manually review and correct in web UI
5. Save as oneshot training examples

## Trained Model Performance

### Model: component-ner-20250930_180917

**Metrics:**
- **Precision**: 70.33% (how many extracted entities are correct)
- **Recall**: 55.81% (how many entities we found vs total)
- **F-Score**: 62.23% (harmonic mean of precision/recall)

**Training Details:**
- Training examples: 903
- Test examples: 101
- Entity types: 138 unique labels
- Training iterations: 30
- Training time: ~30 seconds
- Model size: ~100KB

**Inference Performance:**
- Speed: <1ms per component (CPU-only)
- Memory: ~50MB loaded
- No GPU required
- Deterministic results

**Example Extraction:**
```
Input: "100mW 10kΩ ±5% 0603 Chip Resistor"
Output: {
  'power_rating': '100mW',
  'resistance': '10kΩ',
  'tolerance': '±5%',
  'package': '0603'
}
```

## Next Steps

### Immediate (Phase 4 - Integration)

1. **Backend API Integration**
   - Add model loading to FastAPI service
   - Create `/api/ai/extract_specs` endpoint
   - Return structured JSON from descriptions

2. **Web UI Integration**
   - Add "Extract Specs" button to part forms
   - Auto-populate fields from description
   - Show confidence scores per field

3. **Batch Processing**
   - Process all existing parts without specs
   - CSV import auto-extraction
   - Background task integration

### Short-term (Model Improvement)

1. **Create `inference.py`**: Fast prediction API
2. **Integration**: Add to import workflow
3. **Web UI**: Manual correction interface
4. **Retraining**: Pipeline for model updates

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Labeling Speed** | 2-3 sec/component | Ollama llama3.2 local |
| **Training Time** | 5-30 min | For 10K samples |
| **Inference Speed** | <100ms | sklearn production model |
| **Extraction Accuracy** | >85% | Field-level accuracy |
| **Coverage** | >80% | % of parts with extracted data |

## Component Categories Supported

### High Priority (Well-structured specs)
- **Resistors**: resistance, tolerance, power, temp coefficient
- **Capacitors**: capacitance, voltage, tolerance, dielectric
- **Microcontrollers**: core, flash, ram, speed
- **Transistors**: type, voltage, current, power
- **Diodes/LEDs**: type, voltage, current, color
- **Inductors**: inductance, current, tolerance, DCR

### Medium Priority (Variable specs)
- **Connectors**: type, pins, pitch, mounting
- **ICs**: function, voltage, pins, interface
- **Optoelectronics**: wavelength, current, viewing angle
- **Power Management**: output voltage, current, efficiency

### Future Categories
- **Sensors**: type, range, accuracy, interface
- **RF Devices**: frequency, power, gain
- **Crystals**: frequency, load capacitance, tolerance
- **Transformers**: ratio, power, isolation

## File Structure

```
ai-model/
├── README.md                      # Full documentation
├── STATUS.md                      # This file
├── download_lcsc_database.py      # Phase 1: Download LCSC DB
├── extract_training_data.py       # Phase 1: Sample extraction
├── extract_from_orders.py         # Extract from order history
├── label_with_llm.py             # Phase 2: LLM labeling (web UI) ✅
├── extraction_prompt.txt          # External LLM prompt (editable) ✅ NEW
├── review_labels.html             # Web UI for manual review ✅
├── convert_orders_to_training_data.py  # Process order files ✅ NEW
├── prepare_training_data.py       # Phase 2: Convert to training format
├── train_spacy.py                # Phase 3: Train spaCy NER model ✅
├── test_model.py                 # Phase 3: Test trained model ✅
├── train_transformer.py          # Alternative: Transformer training (not used)
├── convert_labeled_to_training.py # Helper script
├── requirements.txt              # Python dependencies
├── orders/                        # Order files directory ✅ NEW
│   ├── DK_PRODUCTS_*.csv          # DigiKey order files
│   └── *.xls                      # Mouser order files
└── data/
    ├── lcsc_raw/
    │   └── cache.sqlite3         # 7M components (6.7 GB)
    ├── training/
    │   ├── test_samples.jsonl    # 100 test samples
    │   ├── spacy_train_*.py      # spaCy training data ✅
    │   └── training_*.jsonl      # Transformer training data
    ├── oneshot-examples/          # Few-shot learning examples ✅ NEW
    │   ├── reviewed_*.jsonl       # Human-corrected examples
    │   └── orders_extracted_*.jsonl  # LLM-extracted from orders
    ├── labeled/
    │   └── reviewed_*.jsonl      # 1023 reviewed labeled examples ✅
    └── models/
        └── component-ner-20250930_180917/  # Trained spaCy model ✅
            ├── ner/              # Model weights
            ├── training_info.json
            └── meta.json
```

## Technical Details

### LLM Labeling Prompt Strategy

The labeling prompt is category-aware:
- Extracts different fields based on component category
- Uses low temperature (0.1) for consistency
- Returns structured JSON only
- Retries up to 3 times on failure

### Extraction Sampling Strategy

Smart sampling ensures diversity:
- Samples from 15+ major component categories
- Minimum 50 parts per category
- Filters for parts with stock > 0
- Random sampling within each category

### Why This Approach Works

**LLM Advantages:**
- Understands context and variations
- No training data needed
- Handles inconsistent formats
- Can extract complex specs

**Traditional ML Advantages:**
- Fast inference (<100ms vs 2-3s)
- Deterministic results
- No API dependencies
- Scales to millions of parts

**Hybrid Benefits:**
- LLM labels data once (one-time cost)
- ML model runs in production (fast + free)
- Best of both worlds

## Testing

### Test Run Results

```
✓ Downloaded 7M components successfully
✓ Extracted 100 diverse samples (46 resistors, 46 connectors, 8 capacitors)
✓ Sample data quality: Excellent
  - All have titles, categories, packages
  - 100% have datasheet URLs
  - Manufacturer info present
```

### Ready for Phase 2

All prerequisites met:
- [x] Database downloaded and verified
- [x] Extraction script tested and working
- [x] Labeling script ready (needs Ollama running)
- [x] Documentation complete

## Requirements

### System Requirements
- **Python 3.8+**
- **Disk Space**: 10 GB (database + models)
- **RAM**: 8 GB minimum (for Ollama)

### Dependencies
- `sqlite3` (built-in)
- `requests` (HTTP calls to Ollama)
- `scikit-learn` (Phase 3)

### External Services
- **Ollama** with llama3.2 model (local, free)
  ```bash
  curl https://ollama.ai/install.sh | sh
  ollama pull llama3.2
  ollama serve
  ```

## Future Enhancements

1. **Active Learning**: Users correct extractions, retrain model
2. **Confidence Scores**: Flag uncertain extractions for manual review
3. **Multi-language**: Support Chinese/other language descriptions
4. **Attribute Prediction**: Predict missing specs based on similar parts
5. **Category Classification**: Auto-categorize parts from description only
6. **Entity Linking**: Link extracted values to standardized vocabularies
7. **Comparison Engine**: "Find parts similar to X with Y specs"

## Notes

- Database downloaded from https://yaqwsx.github.io/jlcparts/
- jlcparts maintained by Jan Mrázek (yaqwsx)
- LCSC database updated regularly (last update tracked in DB)
- Alternative: Could use Mouser/DigiKey APIs but rate-limited

## License & Attribution

- **jlcparts**: MIT License (Jan Mrázek)
- **LCSC Data**: For personal/development use
- **MakerMatrix AI Model**: Part of MakerMatrix project

---

**Last Updated:** 2025-09-30
**Status:** Phase 3.5 - Oneshot Training Data Generation ✅
**Current Work:** Processing DigiKey/Mouser orders with improved LLM extraction
**Next:** Phase 4 - Backend Integration
