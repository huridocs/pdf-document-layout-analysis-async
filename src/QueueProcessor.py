import json
import logging
from time import sleep
import configuration
import pymongo
import redis
from pydantic import ValidationError
from rsmq.consumer import RedisSMQConsumer
from rsmq import RedisSMQ, cmd
from sentry_sdk.integrations.redis import RedisIntegration
import sentry_sdk

from data_model.ExtractionMessage import ExtractionMessage
from data_model.Task import Task
from src.data_model.ExtractionData import ExtractionData

SERVICE_NAME = "segmentation"
TASK_QUEUE_NAME = SERVICE_NAME + "_tasks"
RESULTS_QUEUE_NAME = SERVICE_NAME + "_results"


class QueueProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        client = pymongo.MongoClient(f"{configuration.MONGO_HOST}:{configuration.MONGO_PORT}")
        self.pdf_paragraph_db = client["pdf_paragraph"]

        self.results_queue = RedisSMQ(
            host=configuration.REDIS_HOST,
            port=configuration.REDIS_PORT,
            qname=RESULTS_QUEUE_NAME,
        )
        self.extractions_tasks_queue = RedisSMQ(
            host=configuration.REDIS_HOST,
            port=configuration.REDIS_PORT,
            qname=TASK_QUEUE_NAME,
        )

    def process(self, id, message, rc, ts):
        try:
            task = Task(**message)
        except ValidationError:
            self.logger.error(f"Not a valid Redis message: {message}")
            return True

        self.logger.info(f"Processing Redis message: {message}")

        try:
            # Get data from pdf-document-layout-analysis
            extraction_data = ExtractionData(
                tenant=task.tenant,
                file_name=task.params.filename,
                paragraphs=[],
                page_height=1,
                page_width=1
            )

            if not extraction_data:
                raise FileNotFoundError

            service_url = f"{configuration.SERVICE_HOST}:{configuration.SERVICE_PORT}"
            results_url = f"{service_url}/get_paragraphs/{task.tenant}/{task.params.filename}"
            file_results_url = f"{service_url}/get_xml/{task.tenant}/{task.params.filename}"
            extraction_message = ExtractionMessage(
                tenant=extraction_data.tenant,
                task=task.task,
                params=task.params,
                success=True,
                data_url=results_url,
                file_url=file_results_url,
            )

            extraction_data_json = extraction_data.model_dump_json()
            self.pdf_paragraph_db.paragraphs.insert_one(json.loads(extraction_data_json))
            self.logger.info(f"Results Redis message: {extraction_message}")
            self.results_queue.sendMessage(delay=5).message(extraction_message.model_dump_json()).execute()

        except FileNotFoundError:
            extraction_message = ExtractionMessage(
                tenant=task.tenant,
                task=task.task,
                params=task.params,
                success=False,
                error_message="Error getting the xml from the pdf",
            )

            self.results_queue.sendMessage().message(extraction_message.model_dump_json()).execute()
            self.logger.error(extraction_message.model_dump_json())

        except Exception:
            self.logger.error("error extracting the paragraphs", exc_info=1)

        return True

    def subscribe_to_extractions_tasks_queue(self):
        while True:
            try:
                self.extractions_tasks_queue.getQueueAttributes().exec_command()
                self.results_queue.getQueueAttributes().exec_command()

                self.logger.info(f"Connecting to redis: {configuration.REDIS_HOST}:{configuration.REDIS_PORT}")

                redis_smq_consumer = RedisSMQConsumer(
                    qname=TASK_QUEUE_NAME,
                    processor=self.process,
                    host=configuration.REDIS_HOST,
                    port=configuration.REDIS_PORT,
                )
                redis_smq_consumer.run()
            except redis.exceptions.ConnectionError:
                self.logger.error(f"Error connecting to redis: {configuration.REDIS_HOST}:{configuration.REDIS_PORT}")
                sleep(20)
            except cmd.exceptions.QueueDoesNotExist:
                self.logger.info("Creating queues")
                self.extractions_tasks_queue.createQueue().vt(120).exceptions(False).execute()
                self.results_queue.createQueue().exceptions(False).execute()
                self.logger.info("Queues have been created")


if __name__ == "__main__":
    try:
        sentry_sdk.init(
            configuration.SENTRY_DSN,
            traces_sample_rate=0.1,
            environment=configuration.ENVIRONMENT,
            integrations=[RedisIntegration()],
        )
    except Exception:
        pass

    redis_tasks_processor = QueueProcessor()
    redis_tasks_processor.subscribe_to_extractions_tasks_queue()
