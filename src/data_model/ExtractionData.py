from pydantic import BaseModel

from data_model.SegmentBox import SegmentBox


class ExtractionData(BaseModel):
    tenant: str
    file_name: str
    paragraphs: list[SegmentBox]
    page_height: int
    page_width: int
