from domain.Translation import Translation
from domain.TranslationTask import TranslationTask
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
