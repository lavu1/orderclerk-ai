"""Opt-in real local inference against isolated synthetic databases."""
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orderclerk.core import initialize_database, OrderService
from orderclerk.ollama_provider import OllamaExtractor

report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'synthetic': True,
          'provider': 'ollama', 'model': 'qwen2.5:3b',
          'prior_issue': 'An early model inferred a missing quantity. Quantities now require exact number tokens next to their product in the input; code converts tokens to integers.', 'runs': []}
cases = [('clear', 'Please pack two bags of rice and one bottle of oil.', 'reserved'),
         ('missing', 'I want rice.', 'review'),
         ('unknown', 'I need 2 bags of rice and 3 mangoes.', 'review'),
         ('shortage', 'Please send 5 bottles of oil.', 'review')]
for name, message, expected in cases:
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / 'live.db'
        initialize_database(db)
        service = OrderService(db, OllamaExtractor())
        started = time.monotonic()
        result = service.submit('LIVE-' + name, 'Demo Customer', message)
        passed = result['outcome'] == expected
        if name == 'clear':
            passed = passed and result['order']['total_minor'] == 15500
        if name == 'missing':
            passed = passed and any(x['kind'] == 'missing_quantity' for x in result['review_items'])
        if name == 'unknown':
            passed = passed and any(x['kind'] == 'unsupported_product' for x in result['review_items'])
        if name == 'shortage':
            passed = passed and any(x['kind'] == 'insufficient_stock' for x in result['review_items'])
        report['runs'].append({'case': name, 'passed': passed, 'duration_seconds': round(time.monotonic()-started, 2), 'input': message, 'result': result})
        Path('submission/LIVE_MODEL_EVIDENCE.json').write_text(json.dumps(report, indent=2) + '\n')
        print(name, 'PASS' if passed else 'FAIL', flush=True)
if not all(x['passed'] for x in report['runs']):
    raise SystemExit(1)
