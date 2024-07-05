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
