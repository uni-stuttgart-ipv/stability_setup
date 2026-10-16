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

from datetime import timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.devices import send_intensity
from app.models import Experiment, ExperimentStatus, ScheduleEvent
from app.timeutils import utc_now_naive

# A failed event is retried this many times, 30s apart, before the whole experiment
# is auto-paused and flagged for admin attention.
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30

#  scheduled_at on ScheduleEvent is naive UTC (see app.scheduling._to_naive_utc); pin
#  the scheduler to UTC too, otherwise it interprets naive datetimes using the host's
#  local timezone and every job looks like it was already missed by the UTC offset.
scheduler = AsyncIOScheduler(timezone=timezone.utc)


def _job_id(event_id: int) -> str:
    return f"schedule-event-{event_id}"


def _schedule_retry(event_id: int) -> None:
    run_date = utc_now_naive() + timedelta(seconds=RETRY_DELAY_SECONDS)
    scheduler.add_job(
        execute_event,
        trigger="date",
        run_date=run_date,
        args=[event_id],
        id=_job_id(event_id),
        replace_existing=True,
    )


async def _pause_for_admin(db: AsyncSession, experiment_id: str, reason: str) -> None:
    """Auto-pause an experiment after one of its events exhausts its retries, and
    pull every other still-pending event of that experiment out of the live
    scheduler so nothing else fires until an admin has looked at it."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        return

    result = await db.execute(
        select(ScheduleEvent).where(
            ScheduleEvent.experiment_id == experiment_id,
            ScheduleEvent.status == "PENDING",
        )
    )
    still_pending = list(result.scalars().all())

    experiment.status = ExperimentStatus.PAUSED
    experiment.needs_admin = True
    experiment.failure_reason = reason
    await db.commit()

    unregister_events(still_pending)

#executes a single event from the DB , also updates the status of the event in the DB to EXECUTING , SUCCESS or FAILED depending on the outcome of the execution
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
            event.executed_at = utc_now_naive()
            await db.commit()
            return
        except Exception as exc:
            error_message = str(exc)

        if event.attempt_count < MAX_RETRIES:
            # Leave it PENDING so execute_event's guard above still lets it run
            # again when the retry job fires.
            event.status = "PENDING"
            event.error_message = error_message
            await db.commit()
            _schedule_retry(event_id)
        else:
            event.status = "FAILED"
            event.error_message = error_message
            await db.commit()
            await _pause_for_admin(
                db,
                event.experiment_id,
                f"Event {event.id} ({event.device_id}) failed after {MAX_RETRIES} attempts: {error_message}",
            )

# register all the events belonging to an experiment with the scheduler, so they fire at their scheduled time. Only PENDING events are registered; any already-executed or failed events are ignored , registering happens once an experiment is activated, and unregistering happens when an experiment is paused or deactivated
def register_events(events: list[ScheduleEvent]) -> None:
    """Hand already-persisted PENDING events to the live scheduler so they fire at their time."""
    now = utc_now_naive()
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

#pull events out of live scheduler : on experiment pause or deactivation, we want to stop firing events without deleting their DB rows, so we can re-register them later if the experiment is resumed
def unregister_events(events: list[ScheduleEvent]) -> None:
    """Pull events back out of the live scheduler (e.g. on pause) without touching their DB rows."""
    for event in events:
        try:
            scheduler.remove_job(_job_id(event.id))
        except JobLookupError:
            pass
