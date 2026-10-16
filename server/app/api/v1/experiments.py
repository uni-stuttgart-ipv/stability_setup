import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Experiment, ExperimentStatus, ScheduleEvent
from app.scheduler import register_events, unregister_events
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

    events = await _pending_events(db, experiment_id)
    experiment.status = ExperimentStatus.ACTIVE
    # An explicit (re)activation is treated as acknowledgement that an admin has
    # looked into any prior auto-pause, so clear that signal.
    experiment.needs_admin = False
    experiment.failure_reason = None
    await db.commit()
    await db.refresh(experiment)

    register_events(events)
    return experiment


@router.post("/{experiment_id}/pause", response_model=ExperimentOut)
async def pause_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")

    events = await _pending_events(db, experiment_id)
    experiment.status = ExperimentStatus.PAUSED
    await db.commit()
    await db.refresh(experiment)

    unregister_events(events)
    return experiment
