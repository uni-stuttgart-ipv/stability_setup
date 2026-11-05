from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Any, Optional

from app.models import ExperimentStatus
from app.timeutils import validate_naive_local


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

    @field_validator("start_time", "end_time")
    @classmethod
    def _reject_invalid_dst_times(cls, value: datetime) -> datetime:
        # Only meaningful for a naive value (a raw local time with no UTC offset) —
        # validate_naive_local() is a no-op for anything already timezone-aware.
        validate_naive_local(value)
        return value

class ExperimentOut(BaseModel):
    experiment_id: str
    experiment_json: dict[str, Any]
    status: ExperimentStatus
    needs_admin: bool
    failure_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True