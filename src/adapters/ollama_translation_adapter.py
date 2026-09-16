from logging import Logger

import requests

from configuration import LANGUAGES_SHORT, LANGUAGES, OLLAMA_API_KEY, OLLAMA_BASE_URL, PROMPTS, TRANSLATION_MODEL
from domain.TranslationTask import TranslationTask
from ports.translation_port import TranslationPort


class OllamaTranslationAdapter(TranslationPort):
    def __init__(self, service_logger: Logger, api_key: str | None = None):
        self.service_logger = service_logger
        self.api_key = api_key or OLLAMA_API_KEY
        if not self.api_key:
            raise RuntimeError("OLLAMA_API_KEY must be set in the environment or .env file")

    def _get_prompt(self, translation_task: TranslationTask) -> str:
        lang_map = dict(zip(LANGUAGES_SHORT, LANGUAGES))
        language_from_name = lang_map.get(translation_task.language_from.lower()[:2], "English")
        language_to_name = lang_map.get(translation_task.language_to.lower()[:2], "English")
        return PROMPTS["Prompt 3"].format(
            language_from_name=language_from_name,
            language_to_name=language_to_name,
            text_to_translate=translation_task.text,
        )

    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        self.service_logger.info(f"Using Ollama cloud model {TRANSLATION_MODEL}")

        try:
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
        except requests.RequestException as error:
            error_message = error.response.text if error.response is not None else str(error)
            self.service_logger.error(f"Ollama cloud translation failed: {error_message}")
            return "", False, error_message
        except (KeyError, IndexError, ValueError) as error:
            error_message = f"Unexpected response from Ollama cloud: {error}"
            self.service_logger.error(error_message)
            return "", False, error_message

        if response_content.startswith("```") and response_content.endswith("```"):
            response_content = response_content[3:-3]

        return response_content, True, ""
