from pydantic import BaseModel

from src.data_model.Params import Params


class Task(BaseModel):
    tenant: str
    task: str
    params: Params
