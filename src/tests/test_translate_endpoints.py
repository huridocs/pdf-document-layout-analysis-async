from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import configuration
from drivers.rest import app as app_module
from domain.TranslationTask import TranslationTask


class FakeTranslationAdapter:
    def __init__(self, service_logger, api_key=None):
        self.service_logger = service_logger
        self.tasks: list[TranslationTask] = []

    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        self.tasks.append(translation_task)
        return f"[{translation_task.language_to}] {translation_task.text}", True, ""


class FailingTranslationAdapter(FakeTranslationAdapter):
    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        return "", False, "upstream failure"


class TestTranslateEndpoints(TestCase):
    def setUp(self):
        self.patches = [
            patch.object(app_module, "run_migrations", lambda pool: None),
            patch.object(app_module, "connection_pool", _FakePool()),
            patch.object(app_module, "OllamaTranslationAdapter", FakeTranslationAdapter),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _client(self):
        return TestClient(app_module.app, raise_server_exceptions=False)

    def test_body_endpoint_translates_text_sent_in_the_body(self):
        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": "Hello world", "language_from": "en", "language_to": "es"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"translated_text": "[es] Hello world"}, response.json())

    def test_body_endpoint_accepts_text_with_url_unsafe_characters(self):
        text = "a & b = c? d # e % f / g\n\th"

        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": text, "language_from": "en", "language_to": "es"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"translated_text": f"[es] {text}"}, response.json())

    def test_body_endpoint_accepts_text_at_the_maximum_length(self):
        text = "x" * configuration.MAX_TRANSLATE_TEXT_CHARS

        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": text, "language_from": "en", "language_to": "es"},
            )

        self.assertEqual(200, response.status_code)

    def test_body_endpoint_rejects_text_over_the_maximum_length(self):
        text = "x" * (configuration.MAX_TRANSLATE_TEXT_CHARS + 1)

        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": text, "language_from": "en", "language_to": "es"},
            )

        self.assertEqual(400, response.status_code)
        self.assertIn("maximum length", response.json()["detail"])

    def test_body_endpoint_rejects_unsupported_languages(self):
        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": "Hello", "language_from": "en", "language_to": "zh"},
            )

        self.assertEqual(400, response.status_code)
        self.assertIn("not supported", response.json()["detail"])

    def test_body_endpoint_lowercases_language_codes(self):
        with self._client() as client:
            response = client.post(
                "/translate/text",
                json={"text": "Hello", "language_from": "EN", "language_to": "ES"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual({"translated_text": "[es] Hello"}, response.json())

    def test_body_endpoint_rejects_a_missing_field(self):
        with self._client() as client:
            response = client.post("/translate/text", json={"text": "Hello", "language_from": "en"})

        self.assertEqual(422, response.status_code)

    def test_body_endpoint_returns_500_when_the_adapter_fails(self):
        with patch.object(app_module, "OllamaTranslationAdapter", FailingTranslationAdapter):
            with self._client() as client:
                response = client.post(
                    "/translate/text",
                    json={"text": "Hello", "language_from": "en", "language_to": "es"},
                )

        self.assertEqual(500, response.status_code)
        self.assertIn("upstream failure", response.json()["detail"])

    def test_query_endpoint_still_translates_text_from_the_query_string(self):
        with self._client() as client:
            response = client.post("/translate", params={"text": "Hello world", "language_from": "en", "language_to": "es"})

        self.assertEqual(200, response.status_code)
        self.assertEqual({"translated_text": "[es] Hello world"}, response.json())

    def test_query_endpoint_rejects_text_over_the_maximum_length(self):
        text = "x" * (configuration.MAX_TRANSLATE_TEXT_CHARS + 1)

        with self._client() as client:
            response = client.post("/translate", params={"text": text, "language_from": "en", "language_to": "es"})

        self.assertEqual(400, response.status_code)


class _FakePool:
    def check(self):
        pass

    def connection(self):
        raise NotImplementedError

    def close(self):
        pass
