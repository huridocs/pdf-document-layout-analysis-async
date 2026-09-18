from logging import Logger
from time import sleep

import requests

from configuration import MAX_TRANSLATE_RETRIES, OLLAMA_API_KEY, OLLAMA_BASE_URL, PROMPTS, TRANSLATION_MODEL, language_name
from domain.TranslationTask import TranslationTask
from ports.translation_port import TranslationPort


class OllamaTranslationAdapter(TranslationPort):
    def __init__(self, service_logger: Logger, api_key: str | None = None):
        self.service_logger = service_logger
        self.api_key = api_key or OLLAMA_API_KEY
        if not self.api_key:
            raise RuntimeError("OLLAMA_API_KEY must be set in the environment or .env file")

    def _get_prompt(self, translation_task: TranslationTask) -> str:
        language_from_name = language_name(translation_task.language_from)
        language_to_name = language_name(translation_task.language_to)
        return PROMPTS["Prompt 3"].format(
            language_from_name=language_from_name,
            language_to_name=language_to_name,
            text_to_translate=translation_task.text,
        )

    @staticmethod
    def _is_retryable(error: requests.RequestException) -> bool:
        response = error.response
        if response is None:
            return True
        return response.status_code == 429 or response.status_code >= 500

    def _request_translation(self, translation_task: TranslationTask) -> str:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": TRANSLATION_MODEL,
                "messages": [{"role": "user", "content": self._get_prompt(translation_task)}],
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        response_content = response.json()["choices"][0]["message"]["content"]

        if response_content.startswith("```") and response_content.endswith("```"):
            response_content = response_content[3:-3]

        return response_content

    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        self.service_logger.info(f"Using Ollama cloud model {TRANSLATION_MODEL}")

        for attempt in range(MAX_TRANSLATE_RETRIES + 1):
            if attempt:
                sleep(min(2 ** (attempt - 1), 10))
                self.service_logger.info(
                    f"Retrying Ollama cloud translation (attempt {attempt + 1}/{MAX_TRANSLATE_RETRIES + 1})"
                )

            try:
                return self._request_translation(translation_task), True, ""
            except requests.RequestException as error:
                error_message = error.response.text if error.response is not None else str(error)
                if not self._is_retryable(error):
                    break
            except (KeyError, IndexError, ValueError) as error:
                error_message = f"Unexpected response from Ollama cloud: {error}"
                break

        self.service_logger.error(f"Ollama cloud translation failed: {error_message}")
        return "", False, error_message
