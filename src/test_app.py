import unittest
from pathlib import Path
from unittest import TestCase
from fastapi.testclient import TestClient

from app import app
from configuration import APP_PATH


class TestApp(TestCase):
    def test_info(self):
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(200, response.status_code)

    @unittest.skip("This test requires a running cloud service")
    def test_cloud(self):
        test_file_path = Path(APP_PATH, "test_files", "test.pdf")
        with open(test_file_path, "rb") as stream:
            file_content = stream.read()

        files = {"file": ("test.pdf", file_content, "application/pdf")}
        with TestClient(app) as client:
            response = client.post("/", files=files)

        self.assertEqual(200, response.status_code)
