import sys
import unittest
from logging import getLogger

sys.path.insert(0, "/home/gabo/ssd/projects/pdf-document-layout-analysis-async/src")

from adapters.google_translation_adapter import GoogleTranslationAdapter
from domain.TranslationTask import TranslationTask


class TestGoogleTranslationAdapter(unittest.TestCase):
    def setUp(self):
        self.logger = getLogger(__name__)
        self.adapter = GoogleTranslationAdapter(self.logger)

    @unittest.skip("This test requires a running cloud service")
    def test_translate_returns_translated_text(self):
        translation_task = TranslationTask(text="Hello world", language_from="en", language_to="es")
        result, success, error = self.adapter.translate(translation_task)

        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(result, str)
        self.assertEqual(result, "Hola, mundo.")
        self.assertGreater(len(result), 0)
