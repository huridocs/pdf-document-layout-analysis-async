import sys
import unittest

sys.path.insert(0, "/home/gabo/ssd/projects/pdf-document-layout-analysis-async/src")

from logging import getLogger

from adapters.translation_test_adapter import TranslationTestAdapter
from configuration import is_language_supported, language_name
from domain.TranslationTask import TranslationTask
from domain.TranslationTaskMessage import TranslationTaskMessage
from use_cases.translate_text_use_case import TranslateTextUseCase


class TestTranslateTextUseCase(unittest.TestCase):
    def setUp(self):
        self.use_case = TranslateTextUseCase(TranslationTestAdapter(getLogger(__name__)))

    def test_supported_uwazi_language_keys_resolve_to_their_name(self):
        expected_names = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "ru": "Russian",
            "ar": "Arabic",
            "nl": "Dutch",
            "de": "German",
            "hi": "Hindi",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "pl": "Polish",
            "pt": "Portuguese",
            "tr": "Turkish",
            "vi": "Vietnamese",
            "zh-Hans": "Simplified Chinese",
            "zh-Hant": "Traditional Chinese",
            "in": "Indonesian",
        }

        for language_code, language_name_expected in expected_names.items():
            self.assertTrue(
                is_language_supported(language_code),
                f"{language_code} should be supported",
            )
            self.assertEqual(language_name_expected, language_name(language_code))

    def test_languages_uwazi_sends_but_the_service_does_not_support(self):
        for language_code in ["zh", "cs", "el", "he", "fa", "ro", "uk"]:
            self.assertFalse(
                is_language_supported(language_code),
                f"{language_code} should not be supported",
            )

    def test_unsupported_target_language_fails_instead_of_translating_as_english(self):
        message = TranslationTaskMessage(key=["key", "1"], text="Hola", language_from="es", languages_to=["uk"])

        translations = self.use_case.execute_message(message)

        self.assertEqual(1, len(translations))
        self.assertFalse(translations[0].success)
        self.assertEqual("uk", translations[0].language)
        self.assertIn("uk", translations[0].error_message)

    def test_unsupported_source_language_fails(self):
        message = TranslationTaskMessage(key=["key", "1"], text="Hola", language_from="cs", languages_to=["en"])

        translations = self.use_case.execute_message(message)

        self.assertFalse(translations[0].success)
        self.assertIn("cs", translations[0].error_message)

    def test_messages_use_the_translation_prompt_with_uwazi_language_codes(self):
        message = TranslationTaskMessage(
            key=["key", "1"],
            text="Hola",
            language_from="es",
            languages_to=["zh-Hans", "in"],
        )

        translations = self.use_case.execute_message(message)

        self.assertEqual(["zh-Hans", "in"], [translation.language for translation in translations])
        self.assertTrue(all(translation.success for translation in translations))

    def test_empty_text_is_not_translated(self):
        message = TranslationTaskMessage(key=["key", "1"], text="   ", language_from="en", languages_to=["es"])

        translations = self.use_case.execute_message(message)

        self.assertTrue(translations[0].success)
        self.assertEqual("", translations[0].text)

    def test_adapter_prompt_names_the_requested_languages(self):
        from adapters.ollama_translation_adapter import OllamaTranslationAdapter

        adapter = OllamaTranslationAdapter(getLogger(__name__), api_key="test-api-key")
        prompt = adapter._get_prompt(TranslationTask(text="Hola", language_from="zh-Hant", language_to="in"))

        self.assertIn("Traditional Chinese", prompt)
        self.assertIn("Indonesian", prompt)


if __name__ == "__main__":
    unittest.main()
