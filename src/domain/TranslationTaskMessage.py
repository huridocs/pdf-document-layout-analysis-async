from pydantic import BaseModel

from domain.TranslationTask import TranslationTask


class TranslationTaskMessage(BaseModel):
    key: str | list[str]
    text: str
    language_from: str | None
    languages_to: list[str]

    def get_tasks(self):
        for language_to in self.languages_to:
            yield TranslationTask(text=self.text, language_from=self.language_from, language_to=language_to)
