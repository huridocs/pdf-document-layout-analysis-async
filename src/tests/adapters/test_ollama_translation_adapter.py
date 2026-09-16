import sys
import unittest
from logging import getLogger

sys.path.insert(0, "/home/gabo/ssd/projects/pdf-document-layout-analysis-async/src")

from adapters.ollama_translation_adapter import OllamaTranslationAdapter
from domain.TranslationTask import TranslationTask


class TestOllamaTranslationAdapter(unittest.TestCase):
    def setUp(self):
        self.logger = getLogger(__name__)
        self.adapter = OllamaTranslationAdapter(self.logger, api_key="test-api-key")

    @unittest.skip("This test requires a valid Ollama cloud API key")
    def test_translate_returns_translated_text(self):
        translation_task = TranslationTask(text="Hello world", language_from="en", language_to="es")
        result, success, error = self.adapter.translate(translation_task)

        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    @unittest.skip("This test requires a valid Ollama cloud API key")
    def test_translate_returns_translated_text_other_languages(self):
        translation_task = TranslationTask(text="Hola mundo.", language_from="es", language_to="ar")
        result, success, error = self.adapter.translate(translation_task)

        self.assertTrue(success)
        self.assertEqual(error, "")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
