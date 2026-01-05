from pydantic import BaseModel
from typing import Any

class FieldCreate(BaseModel):
    type: str
    geometry: Any

