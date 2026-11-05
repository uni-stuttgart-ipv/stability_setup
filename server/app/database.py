# database.py

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.orm import DeclarativeBase

# Overridable so tests/tools can point at an isolated, throwaway database instead of
# the real dev DB at ./data/solar.db (the same file the frontend's "Manage Experiments"
# page reads from).
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/solar.db")

# The sqlite driver won't create the parent directory for us.
if DATABASE_URL.startswith("sqlite"):
    _db_path = DATABASE_URL.split("///", 1)[-1]
    if _db_path not in (":memory:", ""):
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

# Create database engine
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "true").lower() == "true"
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Base class for all database models
class Base(DeclarativeBase):
    pass


# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session