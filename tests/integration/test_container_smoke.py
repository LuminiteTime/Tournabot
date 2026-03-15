"""Integration smoke tests for containerized dependencies."""

from __future__ import annotations

import asyncio
import importlib
import sys
import time
from pathlib import Path

import asyncpg
from sqlalchemy import text
from testcontainers.core.container import DockerContainer

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


POSTGRES_USER = "tournabot"
POSTGRES_PASSWORD = "test_password"
POSTGRES_DB = "tournabot"


async def _wait_for_postgres(host: str, port: int, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
            )
            await conn.fetchval("SELECT 1")
            await conn.close()
            return
        except Exception as exc:  # pragma: no cover - retry path
            last_error = exc
            await asyncio.sleep(1)

    raise AssertionError(f"Postgres is not ready in time: {last_error}")


def test_postgres_and_bot_startup_smoke(monkeypatch) -> None:
    """Verify DB migrations and bot startup path against ephemeral Postgres."""
    with (
        DockerContainer("postgres:16-alpine")
        .with_env("POSTGRES_USER", POSTGRES_USER)
        .with_env("POSTGRES_PASSWORD", POSTGRES_PASSWORD)
        .with_env("POSTGRES_DB", POSTGRES_DB)
        .with_exposed_ports(5432)
    ) as pg:
        wrapped = pg.get_wrapped_container()
        wrapped.reload()
        state = wrapped.attrs.get("State", {})
        assert state.get("Status") == "running"

        host = pg.get_container_host_ip()
        port = int(pg.get_exposed_port(5432))
        asyncio.run(_wait_for_postgres(host, port))

        async_url = (
            f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{host}:{port}/{POSTGRES_DB}"
        )

        # Токен должен проходить форматную валидацию aiogram.Bot.
        monkeypatch.setenv("BOT_TOKEN", "123456:TESTTOKEN_TESTTOKEN_TESTTOKEN_TESTTOK")
        monkeypatch.setenv("ADMIN_USER_ID", "1")
        monkeypatch.setenv("POSTGRES_USER", POSTGRES_USER)
        monkeypatch.setenv("POSTGRES_PASSWORD", POSTGRES_PASSWORD)
        monkeypatch.setenv("POSTGRES_DB", POSTGRES_DB)
        monkeypatch.setenv("DATABASE_URL", async_url)

        import app.config as config_module
        import app.db as db_module

        importlib.reload(config_module)
        importlib.reload(db_module)

        asyncio.run(db_module.init_db())

        async def _probe() -> None:
            async with db_module.async_session() as session:
                value = await session.scalar(text("SELECT 1"))
                assert value == 1

        asyncio.run(_probe())

        import app.__main__ as main_module

        importlib.reload(main_module)

        started = {"value": False}

        async def _fake_start_polling(self, *bots, **kwargs):
            started["value"] = True
            for bot in bots:
                await bot.session.close()

        monkeypatch.setattr("aiogram.Dispatcher.start_polling", _fake_start_polling)

        asyncio.run(main_module.main())
        assert started["value"] is True

        asyncio.run(db_module.engine.dispose())
