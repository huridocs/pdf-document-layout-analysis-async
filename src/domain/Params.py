from typing import Any

from pydantic import BaseModel, model_serializer


class Params(BaseModel):
    filename: str
    language: str = "en"
    # Optional opaque passthrough: the service never reads it and returns it unchanged.
    metadata: Any | None = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        dumped = handler(self)
        if self.metadata is None:
            dumped.pop("metadata", None)
        return dumped
