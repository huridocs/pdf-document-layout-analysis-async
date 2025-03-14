from pydantic import BaseModel

from domain.Params import Params


class Task(BaseModel):
    tenant: str
    task: str
    params: Params
