import os
from pathlib import Path

from configuration import (
    DATA_PATH,
    DOCUMENT_LAYOUT_ANALYSIS_URL,
    USE_FAST,
    OCR_OUTPUT,
    USE_LOCAL_SEGMENTATION,
    service_logger,
)
from adapters.google_document_layout_analysis_adapter import GoogleDocumentLayoutAnalysisAdapter
from domain.SegmentBox import SegmentBox
from domain.PdfFile import PdfFile
from domain.ExtractionData import ExtractionData
from domain.Task import Task
import requests

RETRIES = 3

if not USE_LOCAL_SEGMENTATION:
    CLOUD_ADAPTER = GoogleDocumentLayoutAnalysisAdapter(service_logger)


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

    if xml_file_name and not Path(DATA_PATH, xml_file_name).exists():
        service_logger.info(
            f"XML file {xml_file_name} is not available in the service. Downloading it from the local service."
        )
        if not save_local_xml_file(xml_file_name):
            raise RuntimeError(f"Error downloading XML file {xml_file_name} from the local service")

    segments: list[SegmentBox] = [SegmentBox(**segment_box) for segment_box in results.json()]
    return ExtractionData(
        tenant=task.tenant,
        file_name=task.params.filename,
        paragraphs=segments,
        page_height=0 if not segments else segments[0].page_height,
        page_width=0 if not segments else segments[0].page_width,
    )


def extract_segments_cloud(pdf_file: PdfFile, task: Task, xml_file_name: str = "") -> (bool, ExtractionData):
    return CLOUD_ADAPTER.extract_segments(pdf_file, task, xml_file_name)


def save_local_xml_file(xml_file_name: str) -> bool:
    xml_file_path = Path(DATA_PATH, xml_file_name)

    for i in range(RETRIES):
        try:
            results = requests.get(f"{DOCUMENT_LAYOUT_ANALYSIS_URL}/get_xml/{xml_file_name}")
        except Exception as e:
            service_logger.error(f"Error downloading XML file: {e}")
            continue

        if results and results.status_code == 200:
            xml_file_path.write_bytes(results.content)
            return True

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
