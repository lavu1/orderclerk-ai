from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from orderclerk.core import FixtureExtractor, OrderService, connect_database, initialize_database


class OrderWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "orders.db"
        initialize_database(self.db_path)
        self.service = OrderService(self.db_path, FixtureExtractor())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_clear_message_reserves_stock_and_uses_catalogue_prices(self) -> None:
        result = self.service.submit(
            "CLEAR-001", "Demo Customer", "Please pack 2 bags of rice and 1 bottle of oil."
        )
        self.assertEqual(result["outcome"], "reserved")
        self.assertEqual(result["order"]["total_minor"], 15_500)
        self.assertEqual(len(result["picking_list"]), 2)
        state = self.service.state()
        availability = {item["sku"]: item["available_quantity"] for item in state["catalogue"]}
        self.assertEqual(availability, {"OIL-1L": 2, "RICE-2KG": 8})

    def test_missing_quantity_requires_review_without_reservation(self) -> None:
        result = self.service.submit("MISSING-001", "Demo Customer", "I want rice.")
        self.assertEqual(result["outcome"], "review")
        self.assertEqual(result["review_items"][0]["kind"], "missing_quantity")
        self.assertIsNone(result["order"])
        self.assertEqual(self.service.state()["stats"]["reserved_orders"], 0)

    def test_replay_returns_original_order_without_double_reservation(self) -> None:
        first = self.service.submit("REPLAY-001", "Demo Customer", "2 bags of rice")
        second = self.service.submit("REPLAY-001", "Another Name", "9 bags of rice")
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(first["order"]["id"], second["order"]["id"])
        rice = next(item for item in self.service.state()["catalogue"] if item["sku"] == "RICE-2KG")
        self.assertEqual(rice["available_quantity"], 8)

    def test_stock_shortage_becomes_review_item(self) -> None:
        result = self.service.submit("STOCK-001", "Demo Customer", "5 bottles of oil")
        self.assertEqual(result["outcome"], "review")
        self.assertEqual(result["review_items"][0]["kind"], "insufficient_stock")
        oil = next(item for item in self.service.state()["catalogue"] if item["sku"] == "OIL-1L")
        self.assertEqual(oil["available_quantity"], 3)

    def test_concurrent_requests_cannot_oversell(self) -> None:
        barrier = threading.Barrier(2)

        def reserve(reference: str) -> dict:
            barrier.wait()
            return self.service.submit(reference, "Demo Customer", "2 bottles of oil")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, ["RACE-001", "RACE-002"]))
        self.assertEqual(sorted(result["outcome"] for result in results), ["reserved", "review"])
        oil = next(item for item in self.service.state()["catalogue"] if item["sku"] == "OIL-1L")
        self.assertEqual(oil["available_quantity"], 1)
        with connect_database(self.db_path) as connection:
            reserved = connection.execute(
                """
                SELECT COALESCE(SUM(i.quantity),0)
                FROM order_items i JOIN stock_reservations r ON r.order_item_id=i.id
                WHERE i.product_id=2 AND r.status='active'
                """
            ).fetchone()[0]
        self.assertEqual(reserved, 2)


if __name__ == "__main__":
    unittest.main()
