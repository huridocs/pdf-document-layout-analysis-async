import json
import os
from typing import Union

import pymongo
from ml_cloud_connector.adapters.google_v2.GoogleServerless import GoogleServerless
from ml_cloud_connector.domain.RestCall import RestCall
from ml_cloud_connector.domain.ServerParameters import ServerParameters
from ml_cloud_connector.domain.ServerType import ServerType
from ml_cloud_connector.use_cases.ExecuteOnServerlessUseCase import ExecuteOnServerlessUseCase
from pydantic import ValidationError, TypeAdapter
from queue_processor.QueueProcessor import QueueProcessor

from sentry_sdk.integrations.redis import RedisIntegration
import sentry_sdk

from configuration import (
    MONGO_HOST,
    MONGO_PORT,
    REDIS_HOST,
    REDIS_PORT,
    SERVICE_HOST,
    SERVICE_PORT,
    ENVIRONMENT,
    SENTRY_DSN,
    service_logger,
    QUEUES_NAMES,
    LANGUAGES_SHORT,
    LANGUAGES,
    PROMPTS,
)
from domain.PdfFile import PdfFile
from domain.ResultMessage import ResultMessage
from domain.Task import Task
from domain.Translation import Translation
from domain.TranslationResponseMessage import TranslationResponseMessage
from domain.TranslationTask import TranslationTask
from domain.TranslationTaskMessage import TranslationTaskMessage
from use_cases.extract_segments_use_case import ocr_pdf, get_xml_name, extract_segments

adapter = TypeAdapter(Union[TranslationTaskMessage, Task])


def get_failed_results_message(task: Task, message: str) -> ResultMessage:
    return ResultMessage(
        tenant=task.tenant,
        task=task.task,
        params=task.params,
        success=False,
        error_message=message,
    )


def is_valid_pdf(filepath):
    try:
        with open(filepath, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False
            f.seek(-1024, 2)
            end_bytes = f.read(1024)
            if b"%%EOF" not in end_bytes:
                return False
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def ocr_pdf_task(task):
    ocr_pdf(task)

    processed_pdf_url = f"{SERVICE_HOST}:{SERVICE_PORT}/processed_pdf/{task.tenant}/{task.params.filename}"
    extraction_message = ResultMessage(
        tenant=task.tenant,
        task=task.task,
        params=task.params,
        success=True,
        file_url=processed_pdf_url,
    )

    service_logger.info(f"OCR success: {extraction_message.model_dump_json()}")
    return extraction_message.model_dump_json()


def get_empty_translation(translation_task):
    return Translation(
        text="",
        language=translation_task.language_to,
        success=True,
        error_message="",
    )


def get_error_translation(translation_task: TranslationTask, error_message: str):
    return Translation(
        text=translation_task.text,
        language=translation_task.language_to,
        success=False,
        error_message=error_message,
    )


def get_prompt(translation_task: TranslationTask):
    lang_map = dict(zip(LANGUAGES_SHORT, LANGUAGES))
    language_to_name = lang_map.get(translation_task.language_to.lower()[:2], "English")
    return PROMPTS["Prompt 3"].format(language_to_name=language_to_name, text_to_translate=translation_task.text)


def get_translation_from_task(translation_task: TranslationTask):
    if not translation_task.text.strip():
        return get_empty_translation(translation_task)

    service_logger.info(f"Using translation serverless")

    SERVER_PARAMETERS = ServerParameters(namespace="google_v2", server_type=ServerType.TRANSLATIONS)
    CLOUD_PROVIDER = GoogleServerless(server_parameters=SERVER_PARAMETERS, service_logger=service_logger)
    EXECUTE_ON_CLOUD = ExecuteOnServerlessUseCase(serverless_provider=CLOUD_PROVIDER, service_logger=service_logger)

    rest_call = RestCall(
        endpoint=[os.getenv("GOOGLE_OLLAMA_URL", ""), "/api/generate"],
        method="POST",
        data={"model": "ali6parmak/hy-mt1.5:latest", "prompt": get_prompt(translation_task), "stream": False},
        port=8080,
    )
    response, finished, error = EXECUTE_ON_CLOUD.execute(rest_call)

    if not finished or error:
        return get_error_translation(translation_task, error)

    response_content = response["response"]
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3]

    return Translation(
        text=response_content,
        language=translation_task.language_to,
        success=True,
        error_message="",
    )


def process(message):
    try:
        task = adapter.validate_python(message)
        if isinstance(task, TranslationTaskMessage):
            return TranslationResponseMessage(
                **task.model_dump(),
                translations=[get_translation_from_task(translation_task) for translation_task in task.get_tasks()],
            ).model_dump()
    except ValidationError:
        service_logger.error(f"The message was incorrectly formatted: {message}")
        return None

    try:
        service_logger.info(f"Processing Redis message: {message}")

        if not is_valid_pdf(PdfFile(task.tenant).get_path(task.params.filename)):
            extraction_message = get_failed_results_message(task, f"The file does not appear to be a valid PDF")
            service_logger.info(extraction_message.model_dump_json())
            return extraction_message.model_dump_json()

        if task.task == "ocr":
            return ocr_pdf_task(task)

        return process_task(task).model_dump_json()
    except FileNotFoundError:
        extraction_message = get_failed_results_message(task, "The PDF could not be found")
        service_logger.error(extraction_message.model_dump_json(), exc_info=True)
    except (RuntimeError, Exception):
        extraction_message = get_failed_results_message(task, "An unexpected error occurred")
        service_logger.error(extraction_message.model_dump_json(), exc_info=True)

    return extraction_message.model_dump_json()


def process_task(task):
    xml_file_name = get_xml_name(task)
    extraction_data = extract_segments(task, xml_file_name)
    service_url = f"{SERVICE_HOST}:{SERVICE_PORT}"
    extraction_message = ResultMessage(
        tenant=extraction_data.tenant,
        task=task.task,
        params=task.params,
        success=True,
        data_url=f"{service_url}/get_paragraphs/{task.tenant}/{task.params.filename}",
        file_url=f"{service_url}/get_xml/{xml_file_name}",
    )
    extraction_data_json = extraction_data.model_dump_json()
    client = pymongo.MongoClient(f"{MONGO_HOST}:{MONGO_PORT}")
    pdf_paragraph_db = client["pdf_paragraph"]
    pdf_paragraph_db.paragraphs.insert_one(json.loads(extraction_data_json))
    service_logger.info(f"Results Redis message: {extraction_message}")
    return extraction_message


if __name__ == "__main__":
    try:
        sentry_sdk.init(
            SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=ENVIRONMENT,
            integrations=[RedisIntegration()],
        )
    except Exception:
        pass

    queues_names = QUEUES_NAMES.split(" ")
    queue_processor = QueueProcessor(REDIS_HOST, REDIS_PORT, queues_names, service_logger, 7)
    queue_processor.start(process)
