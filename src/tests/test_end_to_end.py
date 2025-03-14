import json
import time
from unittest import TestCase

import requests
from rsmq import RedisSMQ

from configuration import APP_PATH
from domain.ResultMessage import ResultMessage
from domain.Params import Params
from domain.Task import Task


class TestEndToEnd(TestCase):
    service_url = "http://localhost:5051"

    def test_error_file(self):
        tenant = "end_to_end_test_error"
        pdf_file_name = "error_pdf.pdf"
        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="segmentation_tasks")

        with open(f"{APP_PATH}/tests/test_files/{pdf_file_name}", "rb") as stream:
            files = {"file": stream}
            requests.post(f"{self.service_url}/async_extraction/{tenant}", files=files)

        task = Task(tenant=tenant, task="segmentation", params=Params(filename=pdf_file_name))

        queue.sendMessage().message(task.model_dump_json()).execute()

        extraction_message = self.get_redis_message()

        self.assertEqual(tenant, extraction_message.tenant)
        self.assertEqual("error_pdf.pdf", extraction_message.params.filename)
        self.assertEqual(False, extraction_message.success)

    def test_async_extraction(self):
        tenant = "end_to_end_test"
        pdf_file_name = "test.pdf"

        with open(f"{APP_PATH}/tests/test_files/{pdf_file_name}", "rb") as stream:
            files = {"file": stream}
            requests.post(f"{self.service_url}/async_extraction/{tenant}", files=files)

        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="segmentation_tasks")

        queue.sendMessage().message('{"message_to_avoid":"to_be_written_in_log_file"}').execute()

        task = Task(tenant=tenant, task="segmentation", params=Params(filename=pdf_file_name))
        queue.sendMessage().message(str(task.model_dump_json())).execute()

        extraction_message = self.get_redis_message()

        response = requests.get(extraction_message.data_url)

        extraction_data_dict = json.loads(response.json())

        self.assertEqual(200, response.status_code)
        self.assertEqual(tenant, extraction_message.tenant)
        self.assertEqual(pdf_file_name, extraction_message.params.filename)
        self.assertEqual(True, extraction_message.success)
        self.assertLess(15, len(extraction_data_dict["paragraphs"]))
        self.assertEqual(612, extraction_data_dict["page_width"])
        self.assertEqual(792, extraction_data_dict["page_height"])
        self.assertTrue(extraction_data_dict["paragraphs"][0]["text"] in ["A /INF/76/1", "United Nations"])
        self.assertEqual({1, 2}, {x["page_number"] for x in extraction_data_dict["paragraphs"]})

        response = requests.get(extraction_message.file_url)
        self.assertEqual(200, response.status_code)
        self.assertTrue('<?xml version="1.0" encoding="UTF-8"?>' in str(response.content))

    def test_blank_pdf(self):
        with open(f"{APP_PATH}/tests/test_files/blank.pdf", "rb") as stream:
            files = {"file": stream}
            response = requests.post(f"{self.service_url}", files=files)

        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json, [])

    def test_one_token_per_page_pdf(self):
        with open(f"{APP_PATH}/tests/test_files/one_token_per_page.pdf", "rb") as stream:
            files = {"file": stream}
            response = requests.post(f"{self.service_url}", files=files)

        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response_json), 2)
        self.assertEqual(response_json[0]["page_number"], 1)
        self.assertEqual(response_json[1]["page_number"], 2)

    def async_ocr(self, pdf_file_name, language) -> list[dict[str, any]]:
        namespace = "async_ocr"

        with open(f"{APP_PATH}/tests/test_files/{pdf_file_name}", "rb") as stream:
            files = {"file": stream}
            requests.post(f"{self.service_url}/upload/{namespace}", files=files)

        task = Task(
            tenant=namespace,
            task="ocr",
            params=Params(filename=pdf_file_name, language=language),
        )

        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="ocr_tasks")
        queue.sendMessage().message(str(task.model_dump_json())).execute()

        extraction_message = self.get_redis_message()
        ocr_response = requests.get(extraction_message.file_url)
        segmentation_response = requests.post(f"{self.service_url}", files={"file": ocr_response.content})
        return segmentation_response.json()

    def test_async_ocr(self):
        paragraphs_per_page = self.async_ocr("ocr-sample-english.pdf", language="en")
        self.assertEqual(1, len(paragraphs_per_page))
        self.assertEqual("Test  text  OCR", paragraphs_per_page[0]["text"])

    def test_async_ocr_specific_language(self):
        paragraphs_per_page = self.async_ocr("ocr-sample-french.pdf", language="fr")
        self.assertEqual(1, len(paragraphs_per_page))
        self.assertEqual("Où  puis-je  m'en  procurer", paragraphs_per_page[0]["text"])

    def test_error_ocr(self):
        tenant = "end_to_end_test_error"
        pdf_file_name = "error_pdf.pdf"
        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="segmentation_tasks")

        with open(f"{APP_PATH}/tests/test_files/{pdf_file_name}", "rb") as stream:
            files = {"file": stream}
            requests.post(f"{self.service_url}/upload/{tenant}", files=files)

        task = Task(tenant=tenant, task="ocr", params=Params(filename=pdf_file_name))

        queue.sendMessage().message(task.model_dump_json()).execute()

        extraction_message = self.get_redis_message()

        self.assertEqual(tenant, extraction_message.tenant)
        self.assertEqual("ocr", extraction_message.task)
        self.assertEqual("error_pdf.pdf", extraction_message.params.filename)
        self.assertEqual(False, extraction_message.success)

    @staticmethod
    def get_redis_message() -> ResultMessage:
        queues_names = ["segmentation", "ocr"]

        for i in range(160):
            for queue_name in queues_names:
                time.sleep(1)
                queue = RedisSMQ(host="127.0.0.1", port="6379", qname=f"{queue_name}_results", quiet=True)
                message = queue.receiveMessage().exceptions(False).execute()
                if message:
                    queue.deleteMessage(id=message["id"]).execute()
                    return ResultMessage(**json.loads(message["message"]))
