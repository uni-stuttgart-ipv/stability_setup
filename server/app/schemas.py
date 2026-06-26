from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

class Registration(BaseModel):
    device_id: str
    ip: str

class SetRequest(BaseModel):
    ch0: int
    ch1: int

class Heartbeat(BaseModel):
    device_id: str
    ip: str

class ESPAlert(BaseModel):
    device_id: str
    alert: str