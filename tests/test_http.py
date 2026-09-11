from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from orderclerk.core import FixtureExtractor, OrderService, initialize_database
from orderclerk.server import build_server


class HttpSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "http.db"
        initialize_database(db_path)
        self.server = build_server("127.0.0.1", 0, OrderService(db_path, FixtureExtractor()))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def test_page_health_and_processing_endpoint(self) -> None:
        with urlopen(f"{self.base_url}/", timeout=3) as response:
            page = response.read().decode("utf-8")
        self.assertIn("OrderClerk AI", page)
        with urlopen(f"{self.base_url}/api/health", timeout=3) as response:
            health = json.loads(response.read())
        self.assertTrue(health["ok"])
        self.assertTrue(health["provider"]["unverified"])

        payload = json.dumps(
            {
                "external_ref": "HTTP-001",
                "customer": "Demo Customer",
                "message": "1 bag of rice",
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/orders/process",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=3) as response:
            result = json.loads(response.read())
        self.assertEqual(result["outcome"], "reserved")


if __name__ == "__main__":
    unittest.main()
