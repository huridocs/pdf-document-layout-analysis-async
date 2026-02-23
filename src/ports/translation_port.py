from abc import ABC, abstractmethod

from domain.TranslationTask import TranslationTask


class TranslationPort(ABC):
    @abstractmethod
    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        pass
