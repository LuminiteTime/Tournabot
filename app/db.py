"""Подключение к PostgreSQL и инициализация схемы через миграции."""

import asyncio
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Накатить миграции до актуальной версии (alembic upgrade head)."""
    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_ini))
    # env.py intentionally requires DATABASE_URL in env for fail-fast.
    os.environ["DATABASE_URL"] = settings.DATABASE_URL

    # Alembic command API is sync; run it off the event loop.
    await asyncio.to_thread(command.upgrade, cfg, "head")
