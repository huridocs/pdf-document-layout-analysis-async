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


class GoogleTranslationAdapter(TranslationPort):
    def __init__(self, service_logger: Logger):
        self.service_logger = service_logger

    def _get_prompt(self, translation_task: TranslationTask) -> str:
        lang_map = dict(zip(LANGUAGES_SHORT, LANGUAGES))
        language_to_name = lang_map.get(translation_task.language_to.lower()[:2], "English")
        return PROMPTS["Prompt 3"].format(language_to_name=language_to_name, text_to_translate=translation_task.text)

    def translate(self, translation_task: TranslationTask) -> tuple[str, bool, str]:
        self.service_logger.info(f"Using Google translation serverless")

        server_parameters = ServerParameters(namespace="google_v2", server_type=ServerType.TRANSLATIONS)
        cloud_provider = GoogleServerless(server_parameters=server_parameters, service_logger=self.service_logger)
        execute_on_cloud_serverless = ExecuteOnServerlessUseCase(
            serverless_provider=cloud_provider, service_logger=self.service_logger
        )

        rest_call = RestCall(
            endpoint=[os.getenv("GOOGLE_OLLAMA_URL", ""), "/api/generate"],
            method="POST",
            data={"model": "ali6parmak/hy-mt1.5:latest", "prompt": self._get_prompt(translation_task), "stream": False},
            port=8080,
        )
        response, finished, error = execute_on_cloud_serverless.execute(rest_call)

        if not finished or error:
            return "", False, error

        response_content = response["response"]
        if response_content.startswith("```") and response_content.endswith("```"):
            response_content = response_content[3:-3]

        return response_content, True, ""
