from configuration import DOCUMENT_LAYOUT_ANALYSIS_URL, service_logger
from data_model.SegmentBox import SegmentBox
from PdfFile import PdfFile
from data_model.ExtractionData import ExtractionData
from data_model.Task import Task
import requests

RETRIES = 3


def get_xml_name(task: Task) -> str:
    return f"{task.tenant}__{task.params.filename.lower().replace('.pdf', '.xml')}"


def extract_segments(task: Task, xml_file_name: str = "") -> ExtractionData:
    pdf_file = PdfFile(task.tenant)
    data = {"fast": "True"}
    url = DOCUMENT_LAYOUT_ANALYSIS_URL + (f"/save_xml/{xml_file_name}" if xml_file_name else "")

    results = None
    for i in range(RETRIES):
        with open(pdf_file.get_path(task.params.filename), "rb") as stream:
            files = {"file": stream}
            results = requests.post(url, files=files, data=data)

        if results and results.status_code == 200:
            break

    if not results:
        raise SystemError(f"The PDF document layout analysis container did not respond with \n {task}")

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
