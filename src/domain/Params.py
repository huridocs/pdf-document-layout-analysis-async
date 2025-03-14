from pydantic import BaseModel


class Params(BaseModel):
    filename: str
    language: str = "en"
