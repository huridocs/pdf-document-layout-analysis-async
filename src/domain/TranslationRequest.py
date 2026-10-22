from pydantic import BaseModel


class TranslationRequest(BaseModel):
    text: str
    language_from: str
    language_to: str
