"""API v1 package."""

from fastapi import APIRouter

from app.api.v1.routes import router as influx_router
from app.api.v1.experiments import router as experiments_router

router = APIRouter()
router.include_router(influx_router)
router.include_router(experiments_router)
