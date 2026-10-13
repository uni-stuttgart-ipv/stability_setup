from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional

from app.models import ExperimentStatus


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

class ExperimentAction(BaseModel):
    set_intensity_percent: float
    duration_hours: float

class ExperimentBlock(BaseModel):
    repeat: int = 1
    actions: list[ExperimentAction]

class ExperimentCreate(BaseModel):
    name: str
    device_id: str
    start_time: datetime
    end_time: datetime
    blocks: list[ExperimentBlock]

class ExperimentOut(BaseModel):
    experiment_id: str
    experiment_json: dict[str, Any]
    status: ExperimentStatus
    created_at: datetime

    class Config:
        from_attributes = True