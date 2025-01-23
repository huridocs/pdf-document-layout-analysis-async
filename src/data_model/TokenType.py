from enum import Enum


class TokenType(Enum):
    FORMULA = "Formula"
    FOOTNOTE = "Footnote"
    LIST_ITEM = "List item"
    TABLE = "Table"
    PICTURE = "Picture"
    TITLE = "Title"
    TEXT = "Text"
    PAGE_HEADER = "Page header"
    SECTION_HEADER = "Section header"
    CAPTION = "Caption"
    PAGE_FOOTER = "Page footer"
