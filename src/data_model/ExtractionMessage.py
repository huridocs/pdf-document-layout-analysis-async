from typing import Union

from pydantic import BaseModel

from src.data_model.Params import Params


class ExtractionMessage(BaseModel):
    tenant: str
    task: str
    params: Params
    success: bool
    error_message: Union[str, None] = None
    data_url: Union[str, None] = None
    file_url: Union[str, None] = None
