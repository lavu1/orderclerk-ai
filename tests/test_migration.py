import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from orderclerk.core import SCHEMA_PATH, FixtureExtractor, OrderService, connect_database, initialize_database

class MigrationTests(unittest.TestCase):
    def test_provider_upgrade_preserves_saved_order_and_relationships(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'old.db'
            old_schema = Path(tmp) / 'old.sql'
            old_schema.write_text(SCHEMA_PATH.read_text().replace("'openai','ollama','fixture_unverified'", "'openai','fixture_unverified'"))
            with patch('orderclerk.core.SCHEMA_PATH', old_schema):
                initialize_database(db)
            before = OrderService(db, FixtureExtractor()).submit('MIGRATION-1', 'Demo', '2 bags of rice')
            initialize_database(db)
            after = OrderService(db, FixtureExtractor()).submit('MIGRATION-1', 'Demo', '2 bags of rice')
            self.assertTrue(after['replayed'])
            self.assertEqual(before['order'], after['order'])
            with connect_database(db) as connection:
                self.assertEqual([], connection.execute('PRAGMA foreign_key_check').fetchall())
                self.assertEqual('ok', connection.execute('PRAGMA integrity_check').fetchone()[0])
                self.assertIn("'ollama'", connection.execute("SELECT sql FROM sqlite_master WHERE name='incoming_messages'").fetchone()[0])
