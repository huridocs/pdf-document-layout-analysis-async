import os
from pathlib import Path

from ml_cloud_connector.adapters.google_v2.GoogleV2Repository import GoogleV2Repository
from ml_cloud_connector.domain.RestCall import RestCall
from ml_cloud_connector.domain.ServerParameters import ServerParameters
from ml_cloud_connector.domain.ServerType import ServerType
from ml_cloud_connector.ports.CloudProviderRepository import CloudProviderRepository
from ml_cloud_connector.use_cases.ExecuteOnCloudUseCase import ExecuteOnCloudUseCase

from configuration import (
    DOCUMENT_LAYOUT_ANALYSIS_URL,
    USE_FAST,
    OCR_OUTPUT,
    USE_LOCAL_SEGMENTATION,
    service_logger,
    DOCUMENT_LAYOUT_ANALYSIS_PORT,
    DATA_PATH,
)
from domain.SegmentBox import SegmentBox
from domain.PdfFile import PdfFile
from domain.ExtractionData import ExtractionData
from domain.Task import Task
import requests

RETRIES = 3


def get_xml_name(task: Task) -> str:
    xml_file_name = f"{task.tenant}__{task.params.filename.lower().replace('.pdf', '.xml')}"
    xml_file_name = xml_file_name if xml_file_name.endswith(".xml") else f"{xml_file_name}.xml"
    return xml_file_name


def extract_segments(task: Task, xml_file_name: str = "") -> ExtractionData:
    pdf_file = PdfFile(task.tenant)

    if not USE_LOCAL_SEGMENTATION:
        success, result = extract_segments_cloud(pdf_file, task, xml_file_name)
        if success:
            return result
        else:
            service_logger.error(
                f"Error extracting segments on the cloud from PDF file {task.params.filename}. Using local service."
            )

    url = DOCUMENT_LAYOUT_ANALYSIS_URL + (f"/save_xml/{xml_file_name}" if xml_file_name else "")
    data = {"fast": "True" if USE_FAST else "False"}
    results = None
    with open(pdf_file.get_path(task.params.filename), "rb") as stream:
        file_content = stream.read()

    files = {"file": (task.params.filename, file_content, "application/pdf")}

    for i in range(RETRIES):
        results = requests.post(url, files=files, data=data)

        if results and results.status_code == 200:
            break

    if results.status_code != 200:
        raise RuntimeError(f"Error processing PDF document: {results.status_code} - {results.text}")

    segments: list[SegmentBox] = [SegmentBox(**segment_box) for segment_box in results.json()]
    return ExtractionData(
        tenant=task.tenant,
        file_name=task.params.filename,
        paragraphs=segments,
        page_height=0 if not segments else segments[0].page_height,
        page_width=0 if not segments else segments[0].page_width,
    )


def extract_segments_cloud(pdf_file: PdfFile, task: Task, xml_file_name: str = "") -> (bool, ExtractionData):
    server_parameters = ServerParameters(namespace="google_v2", server_type=ServerType.DOCUMENT_LAYOUT_ANALYSIS)
    cloud_provider = GoogleV2Repository(server_parameters=server_parameters, service_logger=service_logger)
    execute_on_cloud_use_case = ExecuteOnCloudUseCase(cloud_provider=cloud_provider, service_logger=service_logger)

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
    results, success, error = execute_on_cloud_use_case.execute(rest_call)
    if not success:
        return False, None

    if not save_cloud_xml_file(cloud_provider, xml_file_name):
        return False, None

    segments: list[SegmentBox] = [SegmentBox(**segment_box) for segment_box in results]

    return True, ExtractionData(
        tenant=task.tenant,
        file_name=task.params.filename,
        paragraphs=segments,
        page_height=0 if not segments else segments[0].page_height,
        page_width=0 if not segments else segments[0].page_width,
    )


def save_cloud_xml_file(cloud_provider: CloudProviderRepository, xml_file_name: str) -> bool:
    try:
        response = requests.get(f"http://{cloud_provider.get_ip()}:{DOCUMENT_LAYOUT_ANALYSIS_PORT}/get_xml/{xml_file_name}")
        xml_file_path = Path(DATA_PATH, xml_file_name)
        xml_file_path.write_bytes(response.content)
        return True
    except Exception as e:
        service_logger.error(f"Error downloading XML file: {e}")
        return False


def ocr_pdf(task: Task) -> bool:
    pdf_file = PdfFile(task.tenant)
    path = pdf_file.get_path(task.params.filename)

    if not path.exists():
        raise FileNotFoundError(f"No PDF to OCR")

    data = {"language": task.params.language}
    for i in range(RETRIES):
        with open(path, "rb") as stream:
            files = {"file": stream}
            results = requests.post(f"{DOCUMENT_LAYOUT_ANALYSIS_URL}/ocr", files=files, data=data)

        if results and results.status_code == 200:
            results_path = Path(OCR_OUTPUT, task.tenant, task.params.filename)
            os.makedirs(results_path.parent, exist_ok=True)
            results_path.write_bytes(results.content)
            path.unlink()
            return True

    raise RuntimeError(f"Error OCR document: {results.status_code} - {results.text}")
