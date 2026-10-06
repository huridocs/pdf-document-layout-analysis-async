import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import configuration
from drivers.rest import app as app_module
from domain.ExtractionData import ExtractionData

from fakes import FakePool


def make_paragraphs_row():
    extraction_data = ExtractionData(tenant="t1", file_name="a.pdf", paragraphs=[], page_height=0, page_width=0)
    return extraction_data.model_dump()


class SelectingPool(FakePool):
    def __init__(self, row):
        super().__init__()
        self.row = row

    def check(self):
        pass

    def connection(self):
        connection = FakePool.connection(self)
        connection.execute = lambda sql, params=None: _FakeResult([(self.row,)])
        return connection


class _FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class TestMaterialsNotDeletedOnFetch(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.data_path = Path(self.tmp.name)
        self.patches = [
            patch.object(app_module, "run_migrations", lambda pool: None),
            patch.object(app_module, "MATERIAL_RETENTION_HOURS", 0),
            patch.object(app_module, "connection_pool", FakePool()),
            patch.object(configuration, "DATA_PATH", str(self.data_path)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _client(self):
        return TestClient(app_module.app, raise_server_exceptions=False)

    def test_get_xml_can_be_fetched_twice(self):
        xml_path = self.data_path / "t1__a.pdf.xml"
        xml_path.write_text("<xml>content</xml>")

        with self._client() as client:
            first = client.get("/get_xml/t1__a.pdf.xml")
            second = client.get("/get_xml/t1__a.pdf.xml")

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual("<xml>content</xml>", first.text)
        self.assertEqual(first.text, second.text)
        self.assertTrue(xml_path.exists())

    def test_get_xml_missing_returns_404_and_nothing_is_deleted(self):
        with self._client() as client:
            response = client.get("/get_xml/missing.xml")

        self.assertEqual(404, response.status_code)

    def test_processed_pdf_missing_returns_404_not_500(self):
        ocr_tmp = TemporaryDirectory()
        try:
            with patch.object(app_module, "OCR_OUTPUT", Path(ocr_tmp.name)):
                with self._client() as client:
                    response = client.get("/processed_pdf/t1/missing.pdf")

            self.assertEqual(404, response.status_code)
        finally:
            ocr_tmp.cleanup()

    def test_processed_pdf_can_be_downloaded_twice(self):
        ocr_tmp = TemporaryDirectory()
        try:
            ocr_file = Path(ocr_tmp.name) / "t1"
            ocr_file.mkdir(parents=True)
            (ocr_file / "a.pdf").write_bytes(b"%PDF-fake")

            with patch.object(app_module, "OCR_OUTPUT", Path(ocr_tmp.name)):
                with self._client() as client:
                    first = client.get("/processed_pdf/t1/a.pdf")
                    second = client.get("/processed_pdf/t1/a.pdf")

            self.assertEqual(200, first.status_code)
            self.assertEqual(200, second.status_code)
            self.assertEqual(first.content, second.content)
            self.assertTrue(Path(ocr_tmp.name, "t1", "a.pdf").exists())
        finally:
            ocr_tmp.cleanup()

    def test_get_paragraphs_can_be_fetched_twice(self):
        pool = SelectingPool(row=make_paragraphs_row())
        with patch.object(app_module, "connection_pool", pool):
            with self._client() as client:
                first = client.get("/get_paragraphs/t1/a.pdf")
                second = client.get("/get_paragraphs/t1/a.pdf")

        self.assertEqual(200, first.status_code)
        self.assertEqual(200, second.status_code)
        self.assertEqual(json.loads(first.json())["file_name"], json.loads(second.json())["file_name"])

    def test_get_paragraphs_missing_returns_404(self):
        pool = SelectingPool(row=None)
        with patch.object(app_module, "connection_pool", pool):
            with self._client() as client:
                response = client.get("/get_paragraphs/t1/missing.pdf")

        self.assertEqual(404, response.status_code)
