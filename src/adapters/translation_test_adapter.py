import os
from logging import Logger

from ml_cloud_connector.adapters.google_v2.GoogleServerless import GoogleServerless
from ml_cloud_connector.domain.RestCall import RestCall
from ml_cloud_connector.domain.ServerParameters import ServerParameters
from ml_cloud_connector.domain.ServerType import ServerType
from ml_cloud_connector.use_cases.ExecuteOnServerlessUseCase import ExecuteOnServerlessUseCase

from configuration import LANGUAGES_SHORT, LANGUAGES, PROMPTS
from domain.TranslationTask import TranslationTask
from ports.translation_port import TranslationPort


class TranslationTestAdapter(TranslationPort):
    def __init__(self, service_logger: Logger):
        self.service_logger = service_logger

    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        self.service_logger.info(f"Using translation test")
        translation_text = f"{translation_task.language_to}: {translation_task.text}"
        return translation_text, True, ""
