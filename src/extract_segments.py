from configuration import DOCUMENT_LAYOUT_ANALYSIS_URL
from data_model.SegmentBox import SegmentBox
from PdfFile import PdfFile
from data_model.ExtractionData import ExtractionData
from data_model.Task import Task
import requests


def get_xml_name(task: Task) -> str:
    return f"{task.tenant}__{task.params.filename.lower().replace('.pdf', '.xml')}"


def extract_segments(task: Task, xml_file_name: str = "") -> ExtractionData:
    pdf_file = PdfFile(task.tenant)
    if not pdf_file.get_path(task.params.filename).exists():
        raise FileNotFoundError

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


if __name__ == "__main__":
    a = {
        "left": 1,
        "top": 1,
        "width": 1,
        "height": 1,
        "page_number": 1,
        "page_width": 1,
        "page_height": 1,
        "text": "",
        "type": "Section_Header",
    }
    print(SegmentBox(**a))
