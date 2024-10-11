import json
import time
from unittest import TestCase

import requests
from rsmq import RedisSMQ

import configuration
from data_model.ResultMessage import ResultMessage
from data_model.Params import Params
from data_model.Task import Task


class TestEndToEnd(TestCase):
    service_url = "http://localhost:5051"

    def test_error_file(self):
        tenant = "end_to_end_test_error"
        pdf_file_name = "error_pdf.pdf"
        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="segmentation_tasks")

        with open(f"{configuration.APP_PATH}/test_files/{pdf_file_name}", "rb") as stream:
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

        with open(f"{configuration.APP_PATH}/test_files/{pdf_file_name}", "rb") as stream:
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
        with open(f"{configuration.APP_PATH}/test_files/blank.pdf", "rb") as stream:
            files = {"file": stream}
            response = requests.post(f"{self.service_url}", files=files)

        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json, [])

    def test_one_token_per_page_pdf(self):
        with open(f"{configuration.APP_PATH}/test_files/one_token_per_page.pdf", "rb") as stream:
            files = {"file": stream}
            response = requests.post(f"{self.service_url}", files=files)

        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response_json), 2)
        self.assertEqual(response_json[0]["page_number"], 1)
        self.assertEqual(response_json[1]["page_number"], 2)

    def test_filter_segments(self):
        tenant = "endpoint_test"
        file_name = "file_name"

        json_data = {
            "tenant": tenant,
            "file_name": file_name,
            "page_width": 600,
            "page_height": 700,
            "paragraphs": [
                {
                    "left": 1,
                    "top": 2,
                    "width": 3,
                    "height": 4,
                    "page_width": 5,
                    "page_height": 6,
                    "page_number": 7,
                    "text": "text1",
                    "type": "Page header",
                },
                {
                    "left": 1,
                    "top": 2,
                    "width": 3,
                    "height": 4,
                    "page_width": 5,
                    "page_height": 6,
                    "page_number": 7,
                    "text": "text2",
                    "type": "Page footer",
                },
            ],
        }

        requests.post(f"{self.service_url}/set_paragraphs", json=json_data)

        queue = RedisSMQ(host="127.0.0.1", port="6379", qname="extraction_tasks")
        task = Task(tenant=tenant, task="extraction", params=Params(filename=file_name))
        queue.sendMessage().message(str(task.model_dump_json())).execute()

        extraction_message = self.get_redis_message()

        response = requests.get(extraction_message.data_url)

        extraction_data = json.loads(response.json())

        self.assertEqual(200, response.status_code)
        self.assertEqual(tenant, extraction_data["tenant"])
        self.assertEqual(file_name, extraction_data["file_name"])
        self.assertEqual(600, extraction_data["page_width"])
        self.assertEqual(700, extraction_data["page_height"])
        self.assertEqual(1, len(extraction_data["paragraphs"]))

        self.assertEqual(1, extraction_data["paragraphs"][0]["left"])
        self.assertEqual(2, extraction_data["paragraphs"][0]["top"])
        self.assertEqual(3, extraction_data["paragraphs"][0]["width"])
        self.assertEqual(4, extraction_data["paragraphs"][0]["height"])
        self.assertEqual(5, extraction_data["paragraphs"][0]["page_width"])
        self.assertEqual(6, extraction_data["paragraphs"][0]["page_height"])
        self.assertEqual(7, extraction_data["paragraphs"][0]["page_number"])
        self.assertEqual("text1", extraction_data["paragraphs"][0]["text"])
        self.assertEqual("Page header", extraction_data["paragraphs"][0]["type"])

    @staticmethod
    def get_redis_message() -> ResultMessage:
        for i in range(80):
            queue_name = "segmentation_results" if i % 2 else "extraction_results"
            queue = RedisSMQ(host="127.0.0.1", port="6379", qname=queue_name, quiet=True)

            time.sleep(3)
            message = queue.receiveMessage().exceptions(False).execute()
            if message:
                queue.deleteMessage(id=message["id"]).execute()
                return ResultMessage(**json.loads(message["message"]))
