import sys
import unittest
from logging import getLogger
from pathlib import Path

sys.path.insert(0, "/home/gabo/ssd/projects/pdf-document-layout-analysis-async/src")

from adapters.google_document_layout_analysis_adapter import GoogleDocumentLayoutAnalysisAdapter
from configuration import APP_PATH
from domain.Params import Params
from domain.PdfFile import PdfFile
from domain.Task import Task


class TestGoogleDocumentLayoutAnalysisAdapter(unittest.TestCase):
    def setUp(self):
        self.logger = getLogger(__name__)
        self.adapter = GoogleDocumentLayoutAnalysisAdapter(self.logger)

    @unittest.skip("This test requires a running cloud service")
    def test_extract_segments_returns_segments(self):
        tenant = "cloud_adapter_test"
        pdf_file_name = "test.pdf"
        xml_file_name = f"{tenant}__{pdf_file_name.lower().replace('.pdf', '.xml')}"
        pdf_file = PdfFile(tenant)
        pdf_file.save(pdf_file_name, Path(APP_PATH, "tests", "test_files", pdf_file_name).read_bytes())

        task = Task(tenant=tenant, task="segmentation", params=Params(filename=pdf_file_name))

        success, extraction_data = self.adapter.extract_segments(pdf_file, task, xml_file_name=xml_file_name)

        self.assertTrue(success)
        self.assertIsNotNone(extraction_data)
        self.assertEqual(tenant, extraction_data.tenant)
        self.assertEqual(pdf_file_name, extraction_data.file_name)
        self.assertGreater(len(extraction_data.paragraphs), 0)
        self.assertEqual(612, extraction_data.page_width)
        self.assertEqual(792, extraction_data.page_height)
        self.assertTrue(extraction_data.paragraphs[0].text in ["A /INF/76/1", "United Nations"])

    @unittest.skip("This test requires a running cloud service")
    def test_extract_segments_saves_xml_file(self):
        tenant = "cloud_adapter_test"
        pdf_file_name = "test.pdf"
        xml_file_name = f"{tenant}__{pdf_file_name.lower().replace('.pdf', '.xml')}"
        pdf_file = PdfFile(tenant)
        pdf_file.save(pdf_file_name, Path(APP_PATH, "tests", "test_files", pdf_file_name).read_bytes())

        task = Task(tenant=tenant, task="segmentation", params=Params(filename=pdf_file_name))

        success, extraction_data = self.adapter.extract_segments(pdf_file, task, xml_file_name=xml_file_name)

        self.assertTrue(success)
        self.assertIsNotNone(extraction_data)
        self.assertGreater(len(extraction_data.paragraphs), 0)

        xml_file_path = Path(APP_PATH, "..", "data", xml_file_name)
        self.assertTrue(xml_file_path.exists())
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', xml_file_path.read_text())
