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

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.devices import send_intensity
from app.models import Experiment, ExperimentStatus, ScheduleEvent
from app.timeutils import to_utc_naive, utc_now_naive

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

        # The experiment may have been paused/stopped between this job being
        # registered and it actually firing (e.g. a /stop request landed in the
        # same instant); re-check here rather than trusting registration alone.
        experiment = await db.get(Experiment, event.experiment_id)
        if experiment is None or experiment.status != ExperimentStatus.ACTIVE:
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


def _completion_job_id(experiment_id: str) -> str:
    return f"experiment-completion-{experiment_id}"


def register_completion(experiment_id: str, end_time: datetime) -> None:
    """Schedule the end-of-experiment shutdown sequence to run when the experiment's
    end_time arrives. Safe to call every time an experiment is (re)activated --
    replace_existing=True makes repeated registration at the same end_time a no-op."""
    end_time = to_utc_naive(end_time)
    if end_time <= utc_now_naive():
        return
    scheduler.add_job(
        complete_experiment,
        trigger="date",
        run_date=end_time,
        args=[experiment_id],
        id=_completion_job_id(experiment_id),
        replace_existing=True,
    )


def unregister_completion(experiment_id: str) -> None:
    """Pull the end-of-experiment job for an experiment out of the live scheduler
    (e.g. on manual pause/stop, where that shutdown already happened a different way)."""
    try:
        scheduler.remove_job(_completion_job_id(experiment_id))
    except JobLookupError:
        pass


async def complete_experiment(experiment_id: str) -> None:
    """Runs when an experiment's end_time arrives: block any further events, turn the
    device off, then either mark the experiment COMPLETED (device confirmed off) or
    PAUSED + needs_admin (the shutdown command itself couldn't be confirmed) -- the
    same "wait for admin" pattern used when an event exhausts its retries or a manual
    /stop can't confirm the device turned off."""
    async with AsyncSessionLocal() as db:
        experiment = await db.get(Experiment, experiment_id)
        if experiment is None or experiment.status != ExperimentStatus.ACTIVE:
            return

        result = await db.execute(
            select(ScheduleEvent).where(
                ScheduleEvent.experiment_id == experiment_id,
                ScheduleEvent.status == "PENDING",
            )
        )
        still_pending = list(result.scalars().all())

        experiment.status = ExperimentStatus.COMPLETING
        await db.commit()
        unregister_events(still_pending)

        device_id = experiment.experiment_json["device_id"]
        try:
            await send_intensity(device_id, ch0=0, ch1=0)
        except Exception as exc:
            experiment.status = ExperimentStatus.PAUSED
            experiment.needs_admin = True
            experiment.failure_reason = (
                f"End-of-experiment shutdown failed to get a confirmation from the device: {exc}"
            )
            await db.commit()
            return

        # Device confirmed off. Already-SUCCESS/FAILED events are left untouched;
        # anything that never got a chance to fire (normally none, since end_time
        # lines up with the last action) is marked CANCELLED, not silently dropped.
        for event in still_pending:
            event.status = "CANCELLED"
        experiment.status = ExperimentStatus.COMPLETED
        await db.commit()
