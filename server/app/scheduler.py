# scheduler.py
#
# Thin wrapper around APScheduler that fires persisted ScheduleEvent rows at their
# scheduled_at time. Only installed APScheduler 3.x is available (there is no
# released 4.x on PyPI yet), so this uses AsyncIOScheduler / add_job, not the
# asyncio-native v4 AsyncScheduler API.
#
# Events are only ever handed here by app.api.v1.experiments when an experiment is
# activated — compiling/saving events (app.scheduling) does not register them, so a
# freshly created INACTIVE experiment never fires real hardware commands.

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from app.database import AsyncSessionLocal
from app.devices import send_intensity
from app.models import ScheduleEvent

#  scheduled_at on ScheduleEvent is naive UTC (see app.scheduling._to_naive_utc); pin
#  the scheduler to UTC too, otherwise it interprets naive datetimes using the host's
#  local timezone and every job looks like it was already missed by the UTC offset.
scheduler = AsyncIOScheduler(timezone=timezone.utc)


def _job_id(event_id: int) -> str:
    return f"schedule-event-{event_id}"


async def execute_event(event_id: int) -> None:
    async with AsyncSessionLocal() as db:
        event = await db.get(ScheduleEvent, event_id)
        if event is None or event.status != "PENDING":
            return

        event.status = "EXECUTING"
        event.attempt_count += 1
        await db.commit()

        try:
            intensity = event.action["set_intensity_percent"]
            await send_intensity(event.device_id, ch0=intensity, ch1=intensity)
            event.status = "SUCCESS"
            event.executed_at = datetime.now(timezone.utc)
        except Exception as exc:
            event.status = "FAILED"
            event.error_message = str(exc)

        await db.commit()


def register_events(events: list[ScheduleEvent]) -> None:
    """Hand already-persisted PENDING events to the live scheduler so they fire at their time."""
    now = datetime.utcnow()
    for event in events:
        if event.scheduled_at <= now:
            continue
        scheduler.add_job(
            execute_event,
            trigger="date",
            run_date=event.scheduled_at,
            args=[event.id],
            id=_job_id(event.id),
            replace_existing=True,
        )


def unregister_events(events: list[ScheduleEvent]) -> None:
    """Pull events back out of the live scheduler (e.g. on pause) without touching their DB rows."""
    for event in events:
        try:
            scheduler.remove_job(_job_id(event.id))
        except JobLookupError:
            pass
