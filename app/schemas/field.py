from pydantic import BaseModel
from typing import List

class Geometry(BaseModel):
    type: str
    coordinates: List

class FieldCreate(BaseModel):
    type: str
    geometry: Geometry
