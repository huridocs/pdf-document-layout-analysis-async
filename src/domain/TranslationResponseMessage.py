from domain.Translation import Translation
from domain.TranslationTaskMessage import TranslationTaskMessage


class TranslationResponseMessage(TranslationTaskMessage):
    translations: list[Translation]
