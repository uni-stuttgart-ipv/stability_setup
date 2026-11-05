import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.devices import send_intensity
from app.models import Experiment, ExperimentStatus, ScheduleEvent
from app.scheduler import register_completion, register_events, unregister_completion, unregister_events
from app.scheduling import compile_schedule, save_schedule_events
from app.schemas import ExperimentCreate, ExperimentOut

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentOut, status_code=201)
async def create_experiment(payload: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    experiment = Experiment(
        experiment_id=uuid.uuid4().hex,
        experiment_json=payload.model_dump(mode="json"),
        status=ExperimentStatus.INACTIVE,
    )
    db.add(experiment)

    # Compile the blocks into concrete, timestamped events and persist them, but do
    # NOT hand them to the live scheduler yet — the experiment is still INACTIVE, and
    # only an explicit /activate call should ever cause real hardware commands to fire.
    events_data = compile_schedule(payload.model_dump(), payload.device_id, payload.start_time)
    await save_schedule_events(db, experiment.experiment_id, events_data)

    await db.commit()
    await db.refresh(experiment)
    return experiment


@router.get("", response_model=list[ExperimentOut])
async def list_experiments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Experiment).order_by(Experiment.created_at.desc()))
    return result.scalars().all()


@router.get("/{experiment_id}", response_model=ExperimentOut)
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return experiment


async def _pending_events(db: AsyncSession, experiment_id: str) -> list[ScheduleEvent]:
    result = await db.execute(
        select(ScheduleEvent).where(
            ScheduleEvent.experiment_id == experiment_id,
            ScheduleEvent.status == "PENDING",
        )
    )
    return list(result.scalars().all())


@router.post("/{experiment_id}/activate", response_model=ExperimentOut)
async def activate_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if experiment.status not in (ExperimentStatus.INACTIVE, ExperimentStatus.PAUSED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot activate an experiment with status {experiment.status.value}",
        )

    events = await _pending_events(db, experiment_id)
    experiment.status = ExperimentStatus.ACTIVE
    # An explicit (re)activation is treated as acknowledgement that an admin has
    # looked into any prior auto-pause, so clear that signal.
    experiment.needs_admin = False
    experiment.failure_reason = None
    await db.commit()
    await db.refresh(experiment)

    register_events(events)
    end_time = datetime.fromisoformat(experiment.experiment_json["end_time"])
    register_completion(experiment.experiment_id, end_time)
    return experiment


@router.post("/{experiment_id}/pause", response_model=ExperimentOut)
async def pause_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if experiment.status != ExperimentStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause an experiment with status {experiment.status.value}",
        )

    events = await _pending_events(db, experiment_id)
    experiment.status = ExperimentStatus.PAUSED
    await db.commit()
    await db.refresh(experiment)

    unregister_events(events)
    unregister_completion(experiment_id)
    return experiment


@router.post("/{experiment_id}/stop", response_model=ExperimentOut)
async def stop_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    """Stop a running experiment: block any further scheduled events, turn the
    device off, then either mark the experiment STOPPED (device confirmed off) or
    PAUSED + needs_admin (the shutdown command itself couldn't be confirmed)."""
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    if experiment.status != ExperimentStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot stop an experiment with status {experiment.status.value}",
        )

    # Mark STOPPING first and pull every pending job out of the live scheduler right
    # away, so nothing new can start firing while the shutdown command is in flight.
    # execute_event() also re-checks the experiment's status itself as a backstop for
    # anything that was already about to run in this same instant.
    events = await _pending_events(db, experiment_id)
    experiment.status = ExperimentStatus.STOPPING
    await db.commit()
    unregister_events(events)
    unregister_completion(experiment_id)

    device_id = experiment.experiment_json["device_id"]
    try:
        await send_intensity(device_id, ch0=0, ch1=0)
    except Exception as exc:
        # No confirmation the device actually turned off — don't claim STOPPED.
        # Same "wait for admin" state as an event that exhausted its retries.
        experiment.status = ExperimentStatus.PAUSED
        experiment.needs_admin = True
        experiment.failure_reason = f"Stop command failed to get a confirmation from the device: {exc}"
        await db.commit()
        await db.refresh(experiment)
        return experiment

    # Device confirmed off: the remaining not-yet-fired events never will fire now.
    for event in events:
        event.status = "CANCELLED"
    experiment.status = ExperimentStatus.STOPPED
    await db.commit()
    await db.refresh(experiment)
    return experiment
