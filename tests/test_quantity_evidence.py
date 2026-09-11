import unittest
from orderclerk.ollama_provider import grounded_quantity

CATALOGUE = [{'id': 1, 'alias': 'rice'}, {'id': 2, 'alias': 'oil'}]

class QuantityEvidenceTests(unittest.TestCase):
    def test_invented_default_quantity_is_rejected(self):
        self.assertIsNone(grounded_quantity({'product': 'rice', 'quantity_text': 'one'}, 'I want rice.', CATALOGUE))
        self.assertIsNone(grounded_quantity({'product': 'rice', 'quantity_text': None}, 'I want rice.', CATALOGUE))

    def test_quantity_belongs_to_its_product(self):
        message = 'Please pack two bags of rice and one bottle of oil.'
        self.assertEqual(2, grounded_quantity({'product': 'rice', 'quantity_text': 'two'}, message, CATALOGUE))
        self.assertEqual(1, grounded_quantity({'product': 'oil', 'quantity_text': 'one'}, message, CATALOGUE))
        self.assertEqual(1, grounded_quantity({'product': 'oil', 'quantity_text': 'two'}, message, CATALOGUE))
        self.assertEqual(1, grounded_quantity({'product': 'oil', 'quantity_text': None}, message, CATALOGUE))
        self.assertIsNone(grounded_quantity({'product': 'rice', 'quantity_text': 'one'}, 'one bottle of oil and rice', CATALOGUE))
