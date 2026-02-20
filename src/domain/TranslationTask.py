from pydantic import BaseModel


class TranslationTask(BaseModel):
    text: str
    language_from: str
    language_to: str
