from time import sleep

from configuration import DOCUMENT_LAYOUT_ANALYSIS_URL, service_logger
from data_model.SegmentBox import SegmentBox
from PdfFile import PdfFile
from data_model.ExtractionData import ExtractionData
from data_model.Task import Task
import requests


def get_xml_name(task: Task) -> str:
    return f"{task.tenant}__{task.params.filename.lower().replace('.pdf', '.xml')}"


def exists_file(tenant: str, file_name: str) -> bool:
    for i in range(5):
        pdf_file = PdfFile(tenant)
        if pdf_file.get_path(file_name).exists():
            return True

        service_logger.info(f"File {pdf_file.get_path(file_name)} exists")
        sleep(1)

    return False


def extract_segments(task: Task, xml_file_name: str = "") -> ExtractionData:
    if not exists_file(task.tenant, task.params.filename):
        raise FileNotFoundError

    pdf_file = PdfFile(task.tenant)

    with open(pdf_file.get_path(task.params.filename), "rb") as stream:
        files = {"file": stream}

        if xml_file_name:
            results = requests.post(f"{DOCUMENT_LAYOUT_ANALYSIS_URL}/save_xml/{xml_file_name}", files=files)
        else:
            results = requests.post(DOCUMENT_LAYOUT_ANALYSIS_URL, files=files)

    if results.status_code != 200:
        raise Exception("Error extracting the paragraphs")

    segments: list[SegmentBox] = [SegmentBox(**segment_box) for segment_box in results.json()]
    return ExtractionData(
        tenant=task.tenant,
        file_name=task.params.filename,
        paragraphs=segments,
        page_height=0 if not segments else segments[0].page_height,
        page_width=0 if not segments else segments[0].page_width,
    )
