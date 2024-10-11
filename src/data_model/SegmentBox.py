from pdf_token_type_labels.TokenType import TokenType
from pydantic import BaseModel


class SegmentBox(BaseModel):
    left: float
    top: float
    width: float
    height: float
    page_number: int
    page_width: int
    page_height: int
    text: str = ""
    type: TokenType = TokenType.TEXT


if __name__ == "__main__":
    a = {
        "left": 1,
        "top": 2,
        "width": 3,
        "height": 4,
        "page_width": 5,
        "page_height": 6,
        "page_number": 7,
        "text": "text1",
        "type": "Page header",
    }
    segment_box = SegmentBox(**a)
    print(segment_box)
