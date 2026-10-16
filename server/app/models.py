# models.py

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    String,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.timeutils import utc_now_naive


class ExperimentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    INACTIVE = "INACTIVE"


class Experiment(Base):

    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(
        String,
        primary_key=True
    )

    experiment_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )

    status: Mapped[ExperimentStatus] = mapped_column(
        SAEnum(ExperimentStatus, validate_strings=True, create_constraint=True),
        default=ExperimentStatus.INACTIVE,
        nullable=False
    )

    # Set when the scheduler auto-pauses this experiment after an event exhausts its
    # retries, so the UI can show "wait for admin" instead of a generic paused state.
    # Distinct from status=PAUSED alone, which also covers an ordinary user-initiated pause.
    needs_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive
    )


class ScheduleEvent(Base):

    __tablename__ = "schedule_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("experiments.experiment_id"),
        nullable=False,
        index=True
    )

    device_id: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )

    action: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String,
        default="PENDING",
        nullable=False
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )