"""Alembic migration environment for the standalone API schema."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models import Base


config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    raw = os.environ.get("GEOPHYSICS_DB_PATH")
    data_dir = Path(os.environ.get("GEOPHYSICS_DATA_DIR", "data/raw/api")).resolve()
    path = Path(raw).resolve() if raw else data_dir / "api.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite+aiosqlite:///" + path.as_posix()


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = database_url()
    engine = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as connection:
        def apply(sync_connection):
            context.configure(connection=sync_connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()

        await connection.run_sync(apply)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
