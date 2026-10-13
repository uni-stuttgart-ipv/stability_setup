# scheduling.py
#
# Turns an experiment's declarative JSON (ordered blocks of repeat x actions) into
# a flat, time-ordered list of concrete ScheduleEvent rows, and persists them.
# Does NOT talk to the live scheduler — that only happens once an experiment is
# activated (see app.scheduler.register_events), so a freshly created, still-INACTIVE
# experiment never fires real hardware commands.

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScheduleEvent


def _to_naive_utc(dt: datetime) -> datetime:
    # SQLite has no native timezone-aware datetime type, so everything in this
    # subsystem is stored/compared as naive UTC to avoid aware/naive mismatches.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


def compile_schedule(experiment_json: dict[str, Any], device_id: str, start_time: datetime) -> list[dict[str, Any]]:
    """Expand ordered blocks of (repeat, actions[]) into a flat list of {device_id, scheduled_at, action} dicts."""
    events: list[dict[str, Any]] = []
    cursor = _to_naive_utc(start_time)

    for block in experiment_json["blocks"]:
        repeat = max(1, block.get("repeat", 1))
        for _ in range(repeat):
            for action in block["actions"]:
                events.append({
                    "device_id": device_id,
                    "scheduled_at": cursor,
                    "action": {"set_intensity_percent": action["set_intensity_percent"]},
                })
                cursor += timedelta(hours=action["duration_hours"])

    return events


async def save_schedule_events(
    db: AsyncSession, experiment_id: str, events: list[dict[str, Any]]
) -> list[ScheduleEvent]:
    """Persist compiled events against an experiment. Caller is responsible for committing."""
    rows = [ScheduleEvent(experiment_id=experiment_id, **event) for event in events]
    db.add_all(rows)
    await db.flush()
    return rows
