#!/usr/bin/env python3
from __future__ import annotations

import json
import platform
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(PROJECT_DIR / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "fixture_mode": "fixture_unverified",
        "live_model_tested": False,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "successful": result.wasSuccessful(),
        "scope": [
            "clear message to reserved order and picking list",
            "missing quantity review",
            "idempotent replay",
            "insufficient stock review",
            "concurrent oversell protection",
            "HTTP page, health, and processing smoke flow",
        ],
        "live_evidence": "Separate opt-in Ollama checks: scripts/verify_live.py and submission/LIVE_MODEL_EVIDENCE.json",
    }
    output_path = PROJECT_DIR / "submission" / "TEST_EVIDENCE.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
