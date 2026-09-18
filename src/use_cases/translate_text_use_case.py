from configuration import is_language_supported
from domain.Translation import Translation
from domain.TranslationTask import TranslationTask
from domain.TranslationTaskMessage import TranslationTaskMessage
from ports.translation_port import TranslationPort


class TranslateTextUseCase:

    def __init__(self, translation_adapter: TranslationPort):
        self.translation_adapter = translation_adapter

    @staticmethod
    def _get_empty_translation(translation_task: TranslationTask) -> Translation:
        return Translation(
            text="",
            language=translation_task.language_to,
            success=True,
            error_message="",
        )

    @staticmethod
    def _get_error_translation(translation_task: TranslationTask, error_message: str) -> Translation:
        return Translation(
            text=translation_task.text,
            language=translation_task.language_to,
            success=False,
            error_message=error_message,
        )

    @staticmethod
    def _get_unsupported_languages(language_from: str | None, languages_to: list[str]) -> list[str]:
        return [
            str(language_code)
            for language_code in (language_from, *languages_to)
            if not is_language_supported(language_code)
        ]

    def execute_message(self, message: TranslationTaskMessage) -> list[Translation]:
        unsupported_languages = self._get_unsupported_languages(message.language_from, message.languages_to)
        if unsupported_languages:
            error_message = f"Unsupported language(s): {', '.join(unsupported_languages)}"
            return [
                Translation(text=message.text, language=language_to, success=False, error_message=error_message)
                for language_to in message.languages_to
            ]

        return [self.execute(translation_task) for translation_task in message.get_tasks()]

    def execute(self, translation_task: TranslationTask) -> Translation:
        if not translation_task.text.strip():
            return self._get_empty_translation(translation_task)

        translated_text, success, error_message = self.translation_adapter.translate(translation_task)

        if not success:
            return self._get_error_translation(translation_task, error_message)

        return Translation(
            text=translated_text,
            language=translation_task.language_to,
            success=True,
            error_message="",
        )
