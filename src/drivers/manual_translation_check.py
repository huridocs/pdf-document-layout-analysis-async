"""Manual check for the Ollama cloud translation path.

Runs a real translation through Ollama cloud using the same prompt and adapter as production,
then prints the prompt and the translated text so the output can be eyeballed.

Usage (from the repo root):

    python src/drivers/manual_translation_check.py

Requires OLLAMA_API_KEY in the environment or in a .env file at the repo root.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from adapters.ollama_translation_adapter import OllamaTranslationAdapter
from configuration import OLLAMA_BASE_URL, TRANSLATION_MODEL, service_logger
from domain.TranslationTask import TranslationTask

TEXT = """ Device keys allow Ollama on macOS, Windows and Linux to access your account's cloud models and allow you to push models to your account.

These keys are automatically added to your account when you sign in to the Ollama app or run ollama signin in the CLI. """

LANGUAGE_FROM = "en"
LANGUAGE_TO = "tr"


def main() -> int:
    translation_task = TranslationTask(text=TEXT, language_from=LANGUAGE_FROM, language_to=LANGUAGE_TO)
    adapter = OllamaTranslationAdapter(service_logger)

    print(f"Model: {TRANSLATION_MODEL}")
    print(f"Endpoint: {OLLAMA_BASE_URL}/chat/completions")
    print(f"Languages: {LANGUAGE_FROM} -> {LANGUAGE_TO}")

    print("\n=== Prompt sent to the model ===\n")
    print(adapter._get_prompt(translation_task))

    print("\n=== Translation ===\n")
    translated_text, success, error = adapter.translate(translation_task)
    if not success:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1

    print(translated_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
