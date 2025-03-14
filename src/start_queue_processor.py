import json
import pymongo
from pydantic import ValidationError
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
    USE_LOCAL_SEGMENTATION,
)
from data_model.ResultMessage import ResultMessage
from data_model.Task import Task
from extract_segments import get_xml_name, extract_segments, ocr_pdf


def get_failed_results_message(task: Task, message: str) -> ResultMessage:
    return ResultMessage(
        tenant=task.tenant,
        task=task.task,
        params=task.params,
        success=False,
        error_message=message,
    )


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


def process(message):
    try:
        task = Task(**message)
    except ValidationError:
        service_logger.error(f"validation error: {message}", exc_info=True)
        return None

    try:
        service_logger.info(f"Processing Redis message: {message}")

        if task.task == "ocr":
            return ocr_pdf_task(task)

        return process_task(task).model_dump_json()
    except RuntimeError:
        extraction_message = get_failed_results_message(task, "Error processing PDF")
        service_logger.error(extraction_message.model_dump_json(), exc_info=True)
    except FileNotFoundError:
        extraction_message = get_failed_results_message(task, "Error FileNotFoundError")
        service_logger.error(extraction_message.model_dump_json(), exc_info=True)
    except Exception:
        extraction_message = get_failed_results_message(task, "Error")
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
