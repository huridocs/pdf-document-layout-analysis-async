import unittest
from pathlib import Path
from unittest import TestCase
from fastapi.testclient import TestClient

from drivers.rest.app import app
from configuration import APP_PATH


class TestApp(TestCase):
    @unittest.skip("No need to test")
    def test_info(self):
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(200, response.status_code)

    @unittest.skip("This test requires a running cloud service")
    def test_cloud(self):
        test_file_path = Path(APP_PATH, "tests", "test_files", "test.pdf")
        with open(test_file_path, "rb") as stream:
            file_content = stream.read()

        files = {"file": ("test.pdf", file_content, "application/pdf")}
        with TestClient(app) as client:
            response = client.post("/", files=files)
            self.assertEqual(200, response.status_code)

            response = client.get("/get_xml/default.xml")
            self.assertEqual(200, response.status_code)
