#!/usr/bin/env python3
"""
Integrated component labeling service with web UI.

This script:
1. Loads LCSC database into memory for fast sampling
2. Uses Ollama LLM to extract structured specs from component descriptions
3. Provides web interface for monitoring progress and reviewing labels
4. Tracks labeling progress in real-time

Usage:
    python label_with_llm.py --mode web  # Start web service
    python label_with_llm.py --mode batch --input samples.jsonl --output labeled.jsonl  # Batch mode
"""

import argparse
import csv
import json
import sys
import time
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, Response
import requests

try:
    import xlrd
except ImportError:
    xlrd = None


class ComponentDatabase:
    """In-memory LCSC component database."""

    def __init__(self, db_path: str):
        """Load database into memory."""
        print(f"Loading database from {db_path}...")

        disk_conn = sqlite3.connect(db_path)
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        disk_conn.backup(self.conn)
        disk_conn.close()

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM components")
        self.total_components = cursor.fetchone()[0]

        print(f"✓ Database loaded: {self.total_components:,} components")

    def parse_component(self, row: tuple) -> Optional[Dict]:
        """Parse component row to dictionary."""
        (lcsc_id, category_id, mfr, package, joints, manufacturer_id,
         basic, description, datasheet, stock, price, last_update,
         extra, flag, last_on_stock, preferred) = row

        try:
            extra_data = json.loads(extra) if extra else {}
            title = extra_data.get('title', mfr)
            category = extra_data.get('category', {})
            manufacturer = extra_data.get('manufacturer', {})

            return {
                'lcsc_number': extra_data.get('number'),
                'title': title,
                'mpn': mfr,
                'package': package,
                'stock': stock,
                'main_category': category.get('name1'),
                'subcategory': category.get('name2'),
                'manufacturer': manufacturer.get('name'),
                'datasheet_url': extra_data.get('datasheet', {}).get('pdf')
                    if isinstance(extra_data.get('datasheet'), dict) else None,
                'description': extra_data.get('description', ''),
                'attributes': extra_data.get('attributes', {}),  # Include all attributes from DB
            }
        except (json.JSONDecodeError, AttributeError):
            return None

    def sample_random(self, count: int = 100, category: Optional[str] = None) -> List[Dict]:
        """Sample random components."""
        cursor = self.conn.cursor()

        # Request more than needed to account for filtering
        oversample_count = int(count * 1.5)

        if category:
            query = """
            SELECT c.*
            FROM components c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE cat.category = ?
            AND c.extra IS NOT NULL
            AND c.stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            cursor.execute(query, (category, oversample_count))
        else:
            query = """
            SELECT * FROM components
            WHERE extra IS NOT NULL
            AND stock > 0
            ORDER BY RANDOM()
            LIMIT ?
            """
            cursor.execute(query, (oversample_count,))

        results = []
        for row in cursor.fetchall():
            component = self.parse_component(row)
            if component and component['main_category']:
                results.append(component)
                # Stop once we have enough valid components
                if len(results) >= count:
                    break

        return results


class OllamaLabeler:
    """Labels component data using Ollama LLM."""

    def __init__(self,
                 model: str = "llama3.2",
                 api_url: str = "http://localhost:11434",
                 examples_path: Optional[str] = None):
        """
        Initialize the labeler.

        Args:
            model: Ollama model name
            api_url: Ollama API URL
            examples_path: Path to JSONL file with reviewed examples for few-shot learning
        """
        self.model = model
        self.api_url = api_url
        self.api_generate = f"{api_url}/api/generate"
        self.few_shot_examples = []

        # Load few-shot examples
        if examples_path and Path(examples_path).exists():
            # Load from specific file
            self.few_shot_examples = self._load_examples(examples_path)
            print(f"✓ Loaded {len(self.few_shot_examples)} few-shot examples from {examples_path}")
        else:
            # Auto-load from oneshot-examples directory
            oneshot_dir = Path("data/oneshot-examples")
            if oneshot_dir.exists():
                self.few_shot_examples = self._load_examples_from_directory(oneshot_dir)
                if self.few_shot_examples:
                    print(f"✓ Loaded {len(self.few_shot_examples)} few-shot examples from {oneshot_dir}")
                else:
                    print(f"ℹ No oneshot examples found in {oneshot_dir}")

        # Check if Ollama is available
        if not self.check_ollama():
            raise ConnectionError(
                f"Cannot connect to Ollama at {api_url}. "
                "Make sure Ollama is running: ollama serve"
            )

    def check_ollama(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]

                if not any(self.model in name for name in model_names):
                    print(f"⚠ Warning: Model '{self.model}' not found")
                    print(f"  Available models: {', '.join(model_names)}")
                    print(f"  Pull it with: ollama pull {self.model}")
                    return False

                return True
        except requests.exceptions.RequestException:
            return False

        return False

    def _load_examples(self, examples_path: str) -> List[Dict]:
        """Load few-shot examples from JSONL file."""
        examples = []
        try:
            with open(examples_path, 'r') as f:
                for line in f:
                    if line.strip():
                        example = json.loads(line)
                        # Only use examples that were reviewed and approved
                        if example.get('review_status') == 'correct' and example.get('corrected_specs'):
                            examples.append({
                                'description': example.get('description', ''),
                                'category': example.get('main_category', ''),
                                'subcategory': example.get('subcategory', ''),
                                'specs': example.get('corrected_specs', {})
                            })
        except Exception as e:
            print(f"Warning: Could not load examples from {examples_path}: {e}")

        return examples

    def _load_examples_from_directory(self, directory: Path) -> List[Dict]:
        """Load few-shot examples from all JSONL files in a directory."""
        all_examples = []

        # Find all JSONL files (oneshot_*.jsonl or reviewed_*.jsonl)
        jsonl_files = sorted(directory.glob("*.jsonl"))

        if not jsonl_files:
            return all_examples

        print(f"Loading oneshot examples from {len(jsonl_files)} files...")

        for jsonl_file in jsonl_files:
            examples = self._load_examples(str(jsonl_file))
            all_examples.extend(examples)
            if examples:
                print(f"  ✓ {jsonl_file.name}: {len(examples)} examples")

        return all_examples

    def build_prompt(self, component: Dict) -> str:
        """
        Build extraction prompt for a component.

        Args:
            component: Component data dictionary

        Returns:
            Formatted prompt string
        """
        description = component.get('description', 'N/A')

        # Load prompt template from external file
        prompt_file = Path(__file__).parent / 'extraction_prompt.txt'
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                base_prompt = f.read()
        else:
            # Fallback minimal prompt if file missing
            base_prompt = "Extract component specifications from the description. Return only JSON."

        # Add the actual description to extract
        prompt = f"""{base_prompt}

COMPONENT TO EXTRACT:
Description: {description}

Extract specifications and return ONLY valid JSON:"""

        return prompt

    def extract_with_ollama(self, prompt: str, max_retries: int = 3) -> Optional[Dict]:
        """
        Extract structured data using Ollama.

        Args:
            prompt: Extraction prompt
            max_retries: Number of retry attempts

        Returns:
            Extracted structured data or None on failure
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_generate,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistency
                            "num_predict": 500,   # Limit response length
                        }
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '').strip()

                    # Try to parse JSON from response
                    # Sometimes LLM adds extra text, so find JSON block
                    json_start = response_text.find('{')

                    if json_start >= 0:
                        # Use JSONDecoder to parse only the first valid JSON object
                        try:
                            decoder = json.JSONDecoder()
                            extracted, end_idx = decoder.raw_decode(response_text, json_start)
                            return extracted
                        except json.JSONDecodeError as e:
                            # Log the actual response for debugging
                            if attempt < max_retries - 1:
                                print(f"    ⚠ JSON parse error: {e}")
                                print(f"    Response preview: {response_text[:200]}...")
                                print(f"    Retry {attempt + 1}/{max_retries}")
                                time.sleep(1)
                                continue
                            return None

                    # Try parsing whole response as fallback
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        if attempt < max_retries - 1:
                            print(f"    ⚠ Invalid JSON, retry {attempt + 1}/{max_retries}")
                            time.sleep(1)
                            continue
                        return None

            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    print(f"    ⚠ Error: {e}, retry {attempt + 1}/{max_retries}")
                    time.sleep(1)
                    continue
                return None

        return None

    def flatten_specs(self, specs: Dict) -> Dict:
        """
        Flatten nested spec objects to string values.

        Args:
            specs: Extracted specifications that may contain nested objects

        Returns:
            Flattened specifications with only string/null values
        """
        flattened = {}
        for key, value in specs.items():
            if value is None:
                flattened[key] = None
            elif isinstance(value, dict):
                # Flatten nested dict by converting to string or extracting single value
                if len(value) == 1:
                    # If single key, use its value
                    flattened[key] = str(list(value.values())[0])
                else:
                    # Multiple keys, convert to readable string
                    flattened[key] = ', '.join(f"{k}: {v}" for k, v in value.items())
            elif isinstance(value, (list, tuple)):
                # Convert list/tuple to comma-separated string
                flattened[key] = ', '.join(str(v) for v in value)
            else:
                flattened[key] = str(value)

        return flattened

    def label_component(self, component: Dict) -> Optional[Dict]:
        """
        Label a single component with extracted specifications.

        Args:
            component: Component data

        Returns:
            Labeled component data or None on failure
        """
        prompt = self.build_prompt(component)
        extracted_specs = self.extract_with_ollama(prompt)

        if not extracted_specs:
            return None

        # Flatten any nested structures
        extracted_specs = self.flatten_specs(extracted_specs)

        # Debug log for troubleshooting
        print(f"  Extracted: {extracted_specs}")

        # Combine original data with extracted specs
        labeled = {
            **component,  # Original fields
            'extracted_specs': extracted_specs,  # LLM-extracted specifications
            'labeled_by': f'{self.model}',
            'labeled_at': time.time()
        }

        return labeled

    def label_batch(self,
                   components: List[Dict],
                   show_progress: bool = True) -> List[Dict]:
        """
        Label a batch of components.

        Args:
            components: List of component data
            show_progress: Whether to show progress

        Returns:
            List of labeled components
        """
        labeled = []
        failed = 0
        start_time = time.time()

        print(f"\nLabeling {len(components)} components with {self.model}...")
        print("(This may take a while - ~2-3 seconds per component)")
        print()

        for i, component in enumerate(components, 1):
            # Progress bar
            if show_progress:
                percent = (i / len(components)) * 100
                bar_length = 40
                filled = int(bar_length * i / len(components))
                bar = '█' * filled + '░' * (bar_length - filled)

                # Time estimates
                elapsed = time.time() - start_time
                avg_time = elapsed / i if i > 0 else 0
                remaining_items = len(components) - i
                eta = remaining_items * avg_time

                # Format time
                eta_str = f"{int(eta//60)}m {int(eta%60)}s" if eta > 60 else f"{int(eta)}s"
                elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s" if elapsed > 60 else f"{int(elapsed)}s"

                # Component info
                title = component.get('title', 'Unknown')[:40]
                category = component.get('main_category', '?')[:15]

                print(f"\r[{bar}] {i}/{len(components)} ({percent:.1f}%) | "
                      f"✓ {len(labeled)} ✗ {failed} | "
                      f"ETA: {eta_str} | "
                      f"Current: {category}", end='', flush=True)

            result = self.label_component(component)

            if result:
                labeled.append(result)
            else:
                failed += 1
                if show_progress:
                    print()  # New line for error
                    title = component.get('title', 'Unknown')[:50]
                    print(f"    ✗ Failed: {title}")

        # Final newline
        if show_progress:
            print()

        return labeled


def load_samples(input_path: str) -> List[Dict]:
    """Load component samples from JSONL file."""
    samples = []
    with open(input_path, 'r') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def save_labeled(labeled: List[Dict], output_path: str):
    """Save labeled data to JSONL file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for item in labeled:
            f.write(json.dumps(item) + '\n')

    print(f"\n✓ Saved {len(labeled)} labeled components to {output_file}")


def print_sample_labels(labeled: List[Dict], count: int = 5):
    """Print sample labeled data."""
    print("\n" + "="*70)
    print("SAMPLE LABELED DATA")
    print("="*70)

    for i, item in enumerate(labeled[:count], 1):
        print(f"\n{i}. {item['title']}")
        print(f"   Category: {item['main_category']}/{item['subcategory']}")
        print(f"   Package: {item['package']}")
        print(f"   Extracted specs:")

        specs = item.get('extracted_specs', {})
        for key, value in specs.items():
            if value is not None:
                print(f"     - {key}: {value}")


# ============================================================================
# ORDER FILE LOADING
# ============================================================================

def load_order_files(supplier: str, count: int = 100) -> List[Dict]:
    """Load components from order files."""
    orders_dir = Path('orders')
    components = []

    if supplier == 'digikey':
        files = sorted(orders_dir.glob("DK_PRODUCTS_*.csv"))
        for csv_file in files:
            components.extend(parse_digikey_csv(csv_file))
    elif supplier == 'mouser':
        files = sorted(orders_dir.glob("*.xls"))
        for xls_file in files:
            components.extend(parse_mouser_xls(xls_file))

    # Limit to requested count
    return components[:count]


def parse_digikey_csv(csv_path: Path) -> List[Dict]:
    """Parse DigiKey order CSV file."""
    components = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            description = row.get('Description', '').strip()
            mpn = row.get('Manufacturer Part Number', '').strip()
            manufacturer = row.get('Manufacturer', '').strip()

            if description:
                components.append({
                    'description': description,
                    'mpn': mpn,
                    'manufacturer': manufacturer,
                    'supplier': 'DigiKey',
                    'main_category': 'Unknown',
                    'subcategory': 'Unknown',
                    'package': 'Unknown'
                })
    return components


def parse_mouser_xls(xls_path: Path) -> List[Dict]:
    """Parse Mouser order XLS file."""
    if xlrd is None:
        return []

    components = []
    try:
        workbook = xlrd.open_workbook(xls_path)
        sheet = workbook.sheet_by_index(0)

        headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]
        desc_col = next((i for i, h in enumerate(headers) if 'Desc' in h), None)
        mpn_col = next((i for i, h in enumerate(headers) if 'Mfr. #' in h or 'Part' in h), None)

        if desc_col is not None:
            for row_idx in range(1, sheet.nrows):
                description = str(sheet.cell_value(row_idx, desc_col)).strip()
                mpn = str(sheet.cell_value(row_idx, mpn_col)).strip() if mpn_col is not None else ''

                if description:
                    components.append({
                        'description': description,
                        'mpn': mpn,
                        'manufacturer': '',
                        'supplier': 'Mouser',
                        'main_category': 'Unknown',
                        'subcategory': 'Unknown',
                        'package': 'Unknown'
                    })
    except Exception:
        pass

    return components


# ============================================================================
# WEB SERVICE MODE
# ============================================================================

# Global state for web mode
app = Flask(__name__, static_folder='.')
db_conn = None
labeler = None
labeling_state = {
    'active': False,
    'progress': [],
    'current': None,
    'stats': {'total': 0, 'completed': 0, 'failed': 0, 'success_rate': 0},
    'labeled_components': [],
    'cancel_requested': False
}
labeling_lock = threading.Lock()


@app.route('/')
def index():
    """Serve the review interface."""
    return send_from_directory('.', 'review_labels.html')


@app.route('/api/status')
def get_status():
    """Get current labeling status."""
    with labeling_lock:
        return jsonify({
            'active': labeling_state['active'],
            'stats': labeling_state['stats'],
            'current': labeling_state['current'],
            'database': {
                'loaded': db_conn is not None,
                'total_components': db_conn.total_components if db_conn else 0
            },
            'ollama': {
                'connected': labeler is not None,
                'model': labeler.model if labeler else None
            }
        })


@app.route('/api/sample')
def sample_components():
    """Get random component samples."""
    if not db_conn:
        return jsonify({'error': 'Database not loaded'}), 503

    count = int(request.args.get('count', 10))
    category = request.args.get('category')
    count = max(1, min(count, 1000))

    try:
        samples = db_conn.sample_random(count, category)
        return jsonify({
            'count': len(samples),
            'components': samples
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/label/start', methods=['POST'])
def start_labeling():
    """Start a labeling job."""
    if labeling_state['active']:
        return jsonify({'error': 'Labeling already in progress'}), 409

    data = request.get_json() or {}
    count = data.get('count', 10)
    category = data.get('category')
    data_source = data.get('data_source', 'lcsc')

    # Load components from selected source
    if data_source == 'lcsc':
        if not db_conn:
            return jsonify({'error': 'LCSC database not loaded'}), 503
        samples = db_conn.sample_random(count, category)
    elif data_source in ['digikey', 'mouser']:
        samples = load_order_files(data_source, count)
        if not samples:
            return jsonify({'error': f'No {data_source} order files found'}), 404
    else:
        return jsonify({'error': f'Unknown data source: {data_source}'}), 400

    # Start labeling in background
    thread = threading.Thread(
        target=run_labeling_job,
        args=(samples,)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': 'Labeling job started',
        'data_source': data_source,
        'count': len(samples)
    })


@app.route('/api/label/progress')
def labeling_progress():
    """Server-sent events for real-time progress."""
    def generate():
        last_completed = 0
        while True:
            with labeling_lock:
                if labeling_state['stats']['completed'] > last_completed:
                    last_completed = labeling_state['stats']['completed']
                    data = json.dumps({
                        'stats': labeling_state['stats'],
                        'current': labeling_state['current']
                    })
                    yield f"data: {data}\n\n"

                if not labeling_state['active'] and last_completed > 0:
                    yield f"data: {json.dumps({'complete': True})}\n\n"
                    break

            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/label/results')
def get_labeled_results():
    """Get all labeled components."""
    with labeling_lock:
        return jsonify({
            'count': len(labeling_state['labeled_components']),
            'components': labeling_state['labeled_components']
        })


@app.route('/api/label/save', methods=['POST'])
def save_corrections():
    """Save corrected labels."""
    data = request.get_json()
    reviewed = data.get('reviewed_components', [])

    if not reviewed:
        return jsonify({'error': 'No reviewed components provided'}), 400

    # Save to file
    output_path = Path('data/oneshot-examples') / f"reviewed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        for item in reviewed:
            f.write(json.dumps(item) + '\n')

    return jsonify({
        'message': 'Corrections saved',
        'file': str(output_path),
        'count': len(reviewed)
    })


@app.route('/api/label/cancel', methods=['POST'])
def cancel_labeling():
    """Cancel active labeling job (keeps progress)."""
    with labeling_lock:
        if not labeling_state['active']:
            return jsonify({'error': 'No active labeling job'}), 400

        labeling_state['cancel_requested'] = True

    return jsonify({
        'message': 'Cancellation requested - will stop after current component',
        'note': 'Progress will be saved'
    })


@app.route('/api/label/discard', methods=['POST'])
def discard_labeling():
    """Cancel and discard all progress from current labeling job."""
    with labeling_lock:
        if not labeling_state['active']:
            return jsonify({'error': 'No active labeling job'}), 400

        labeling_state['cancel_requested'] = True
        # Clear all labeled components
        labeling_state['labeled_components'] = []

    return jsonify({
        'message': 'Cancellation requested - all progress will be discarded',
        'discarded': True
    })


@app.route('/api/training/prepare', methods=['POST'])
def prepare_training_data():
    """Prepare training data from reviewed JSONL files."""
    try:
        import subprocess

        # Run the prepare_training_data.py script
        result = subprocess.run(
            ['python', 'prepare_training_data.py'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return jsonify({
                'error': 'Training data preparation failed',
                'details': result.stderr
            }), 500

        # Parse the output to extract statistics
        output_lines = result.stdout.strip().split('\n')
        stats = {}
        training_file = None

        for line in output_lines:
            if 'Total examples:' in line:
                stats['total_examples'] = int(line.split(':')[1].strip())
            elif 'Total specs:' in line:
                stats['total_specs'] = int(line.split(':')[1].strip())
            elif 'Avg specs per example:' in line:
                stats['avg_specs'] = float(line.split(':')[1].strip())
            elif 'Training data saved to:' in line:
                training_file = line.split('Training data saved to:')[1].strip()

        return jsonify({
            'success': True,
            'message': 'Training data prepared successfully',
            'stats': stats,
            'training_file': training_file,
            'output': result.stdout
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'error': 'Training data preparation timed out'
        }), 500
    except Exception as e:
        return jsonify({
            'error': f'Failed to prepare training data: {str(e)}'
        }), 500


def run_labeling_job(samples: List[Dict]):
    """Run labeling job in background thread."""
    global labeling_state

    with labeling_lock:
        labeling_state['active'] = True
        labeling_state['cancel_requested'] = False
        labeling_state['stats'] = {
            'total': len(samples),
            'completed': 0,
            'failed': 0,
            'success_rate': 0
        }
        labeling_state['labeled_components'] = []

    for i, component in enumerate(samples, 1):
        # Check for cancellation
        with labeling_lock:
            if labeling_state['cancel_requested']:
                labeling_state['active'] = False
                labeling_state['current'] = None
                labeling_state['cancel_requested'] = False
                return

            labeling_state['current'] = {
                'index': i,
                'title': component.get('title', 'Unknown'),
                'category': component.get('main_category', 'Unknown'),
                'description': component.get('description', 'No description available')
            }

        result = labeler.label_component(component)

        with labeling_lock:
            if result:
                labeling_state['labeled_components'].append(result)
                labeling_state['stats']['completed'] += 1
            else:
                labeling_state['stats']['failed'] += 1

            completed = labeling_state['stats']['completed']
            total = labeling_state['stats']['total']
            labeling_state['stats']['success_rate'] = (
                (completed / total * 100) if total > 0 else 0
            )

    with labeling_lock:
        labeling_state['active'] = False
        labeling_state['current'] = None
        labeling_state['cancel_requested'] = False


def run_web_service(db_path: str, model: str, api_url: str, port: int = 8766):
    """Run the integrated web service."""
    global db_conn, labeler

    print("="*70)
    print("COMPONENT LABELING WEB SERVICE")
    print("="*70)
    print()

    # Load database
    db_conn = ComponentDatabase(db_path)

    # Find most recent reviewed examples file for few-shot learning
    # Initialize labeler with automatic oneshot loading
    # (Pass None for examples_path to trigger auto-load from data/oneshot-examples/)
    print(f"\nInitializing Ollama labeler (model: {model})...")
    labeler = OllamaLabeler(model=model, api_url=api_url, examples_path=None)
    print("✓ Ollama connection successful")

    print()
    print("="*70)
    print(f"Web service ready at http://localhost:{port}")
    print("="*70)
    print()
    print("Available endpoints:")
    print(f"  GET  /                     - Review interface")
    print(f"  GET  /api/status           - Service status")
    print(f"  GET  /api/sample           - Sample components")
    print(f"  POST /api/label/start      - Start labeling job")
    print(f"  GET  /api/label/progress   - Real-time progress (SSE)")
    print(f"  GET  /api/label/results    - Get labeled results")
    print(f"  POST /api/label/save       - Save corrections")
    print()

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


# ============================================================================
# BATCH MODE (original functionality)
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Component labeling with LLM - Web service or batch mode'
    )
    parser.add_argument(
        '--mode',
        choices=['web', 'batch'],
        default='batch',
        help='Operating mode: web service or batch processing'
    )

    # Web mode arguments
    parser.add_argument(
        '--db-path',
        default='data/lcsc_raw/cache.sqlite3',
        help='Path to LCSC database (web mode)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8766,
        help='Web service port (default: 8766)'
    )

    # Batch mode arguments
    parser.add_argument(
        '--input',
        help='Input JSONL file with component samples (batch mode)'
    )
    parser.add_argument(
        '--output',
        default='data/labeled/labeled.jsonl',
        help='Output JSONL file for labeled data (batch mode)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of components to label (batch mode)'
    )

    # Common arguments
    parser.add_argument(
        '--model',
        default='mistral:7b-instruct',
        help='Ollama model name (default: mistral:7b-instruct)'
    )
    parser.add_argument(
        '--api-url',
        default='http://localhost:11434',
        help='Ollama API URL (default: http://localhost:11434)'
    )

    args = parser.parse_args()

    if args.mode == 'web':
        # Web service mode
        db_path = Path(args.db_path)
        if not db_path.exists():
            print(f"❌ Database not found at {db_path}")
            print("   Run: python download_lcsc_database.py")
            sys.exit(1)

        run_web_service(str(db_path), args.model, args.api_url, args.port)

    else:
        # Batch mode (original functionality)
        if not args.input:
            parser.error("--input is required for batch mode")

        print("="*70)
        print("LLM-BASED COMPONENT LABELING (BATCH MODE)")
        print("="*70)

        try:
            # Load samples
            print(f"\nLoading samples from {args.input}...")
            samples = load_samples(args.input)
            print(f"✓ Loaded {len(samples)} components")

            # Limit if requested
            if args.limit and args.limit < len(samples):
                samples = samples[:args.limit]
                print(f"  Limiting to first {args.limit} components")

            # Initialize labeler
            print(f"\nInitializing Ollama labeler (model: {args.model})...")
            labeler = OllamaLabeler(model=args.model, api_url=args.api_url)
            print("✓ Ollama connection successful")

            # Label components
            start_time = time.time()
            labeled = labeler.label_batch(samples, show_progress=True)
            elapsed = time.time() - start_time

            # Print statistics
            print(f"\n" + "="*70)
            print(f"✓ Labeled {len(labeled)}/{len(samples)} components")
            print(f"  Success rate: {len(labeled)/len(samples)*100:.1f}%")
            print(f"  Total time: {elapsed:.1f}s")
            print(f"  Average: {elapsed/len(samples):.2f}s per component")
            print("="*70)

            # Show samples
            print_sample_labels(labeled)

            # Save results
            save_labeled(labeled, args.output)

            print(f"\n✅ Labeling complete!")

        except Exception as e:
            print(f"\n✗ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
