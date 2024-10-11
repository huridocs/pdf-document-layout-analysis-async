import json

import mongomock
import pymongo
from fastapi.testclient import TestClient
from unittest import TestCase
from app import app
from pdf_token_type_labels.TokenType import TokenType
from data_model.ExtractionData import ExtractionData


class TestApp(TestCase):

    def test_info(self):
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(200, response.status_code)

    @mongomock.patch(servers=["mongodb://localhost:25017"])
    def test_post_extraction_data(self):
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

        with TestClient(app) as client:
            response = client.post(f"/set_paragraphs", json=json_data)

        mongo_client = pymongo.MongoClient("mongodb://localhost:25017")
        extraction_data = mongo_client.pdf_paragraph.paragraphs.find_one()

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

    @mongomock.patch(servers=["mongodb://localhost:25017"])
    def test_get_extraction_data(self):
        tenant = "endpoint_test"
        file_name = "file_name"
        mongo_client = pymongo.MongoClient("mongodb://localhost:25017")

        json_data = {
            "tenant": tenant,
            "file_name": file_name,
            "page_width": 600,
            "page_height": 600,
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
            ],
        }

        mongo_client.pdf_paragraph.paragraphs.insert_one(json_data)

        with TestClient(app) as client:
            response = client.get(f"/get_paragraphs/{tenant}/{file_name}")

        extraction_data = ExtractionData(**json.loads(response.json()))

        self.assertEqual(200, response.status_code)
        self.assertEqual(tenant, extraction_data.tenant)
        self.assertEqual(file_name, extraction_data.file_name)

        self.assertEqual(1, len(extraction_data.paragraphs))
        self.assertEqual(1, extraction_data.paragraphs[0].left)
        self.assertEqual(2, extraction_data.paragraphs[0].top)
        self.assertEqual(3, extraction_data.paragraphs[0].width)
        self.assertEqual(4, extraction_data.paragraphs[0].height)
        self.assertEqual(5, extraction_data.paragraphs[0].page_width)
        self.assertEqual(6, extraction_data.paragraphs[0].page_height)
        self.assertEqual(7, extraction_data.paragraphs[0].page_number)
        self.assertEqual("text1", extraction_data.paragraphs[0].text)
        self.assertEqual(TokenType.PAGE_HEADER, extraction_data.paragraphs[0].type)
