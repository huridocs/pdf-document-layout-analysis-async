from logging import Logger
from pathlib import Path

from ml_cloud_connector.adapters.google_v2.GenericServerless import GenericServerless
from ml_cloud_connector.domain.RestCall import RestCall
from ml_cloud_connector.domain.ServerParameters import ServerParameters
from ml_cloud_connector.domain.ServerType import ServerType
from ml_cloud_connector.use_cases.ExecuteOnServerlessUseCase import ExecuteOnServerlessUseCase

from configuration import DATA_PATH, DOCUMENT_LAYOUT_ANALYSIS_PORT
from domain.ExtractionData import ExtractionData
from domain.PdfFile import PdfFile
from domain.SegmentBox import SegmentBox
from domain.Task import Task


class GoogleDocumentLayoutAnalysisAdapter:
    def __init__(self, service_logger: Logger):
        self.service_logger = service_logger

    def _execute(self, rest_call: RestCall):
        server_parameters = ServerParameters(namespace="google_v2", server_type=ServerType.DOCUMENT_LAYOUT_ANALYSIS)
        cloud_provider = GenericServerless(server_parameters=server_parameters, service_logger=self.service_logger)
        execute_on_cloud_serverless = ExecuteOnServerlessUseCase(
            serverless_provider=cloud_provider, service_logger=self.service_logger
        )
        return execute_on_cloud_serverless.execute(rest_call)

    def extract_segments(self, pdf_file: PdfFile, task: Task, xml_file_name: str = "") -> tuple[bool, ExtractionData | None]:
        with open(pdf_file.get_path(task.params.filename), "rb") as stream:
            file_content = stream.read()

        files = {"file": (task.params.filename, file_content, "application/pdf")}

        rest_call = RestCall(
            port=DOCUMENT_LAYOUT_ANALYSIS_PORT,
            endpoint=["save_xml", xml_file_name] if xml_file_name else "save_xml",
            method="POST",
            files=files,
            data={"fast": "False"},
        )
        response, success, error = self._execute(rest_call)
        if not success:
            return False, None

        if not self._save_xml_file(xml_file_name):
            return False, None

        segments: list[SegmentBox] = [SegmentBox(**segment_box) for segment_box in response.json()]

        return True, ExtractionData(
            tenant=task.tenant,
            file_name=task.params.filename,
            paragraphs=segments,
            page_height=0 if not segments else segments[0].page_height,
            page_width=0 if not segments else segments[0].page_width,
        )

    def _save_xml_file(self, xml_file_name: str) -> bool:
        try:
            rest_call = RestCall(
                port=DOCUMENT_LAYOUT_ANALYSIS_PORT,
                endpoint=["get_xml", xml_file_name],
                method="GET",
            )
            response, success, error = self._execute(rest_call)

            if not success:
                return False

            xml_file_path = Path(DATA_PATH, xml_file_name)
            xml_file_path.write_bytes(response.content)
            return True
        except Exception as e:
            self.service_logger.error(f"Error downloading XML file: {e}")
            return False
