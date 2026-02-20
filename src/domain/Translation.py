from pydantic import BaseModel


class Translation(BaseModel):
    text: str
    language: str
    success: bool
    error_message: str
