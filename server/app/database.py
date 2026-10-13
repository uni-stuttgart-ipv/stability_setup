# database.py

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./data/solar.db"

# The sqlite driver won't create the parent directory for us.
Path("data").mkdir(exist_ok=True)

# Create database engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True
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