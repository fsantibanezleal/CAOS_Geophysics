"""Engine, migration check and private-file reconciliation."""

from __future__ import annotations

from pathlib import Path

import shutil
import time

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import AccountUsage, DeletionReceipt, Project, RawAsset


MIGRATION_HEAD = "0001_api_foundation"


def make_engine(settings: Settings):
    engine = create_async_engine(settings.database_url, connect_args={"timeout": 30})

    @event.listens_for(engine.sync_engine, "connect")
    def sqlite_pragmas(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


async def require_migration_head(engine) -> None:
    async with engine.connect() as conn:
        try:
            revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
        except Exception as exc:
            raise RuntimeError("API schema is absent; run the committed Alembic migration") from exc
    if revision != MIGRATION_HEAD:
        raise RuntimeError(f"API schema revision {revision!r} is not {MIGRATION_HEAD}")


async def reconcile_private_files(settings: Settings, sessions: async_sessionmaker) -> None:
    root = settings.data_dir
    staging = root / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 3600
    for entry in staging.iterdir():
        if entry.is_file() and not entry.is_symlink() and entry.stat().st_mtime < cutoff:
            entry.unlink()
    exports = root / ".exports"
    if exports.exists():
        for entry in exports.iterdir():
            if entry.is_file() and not entry.is_symlink() and entry.stat().st_mtime < cutoff:
                entry.unlink()
    async with sessions() as session:
        await session.execute(text("BEGIN IMMEDIATE"))
        keys = set((await session.execute(select(RawAsset.storage_key))).scalars().all())
        projects = set((await session.execute(select(Project.id))).scalars().all())
        deleted = (await session.execute(select(DeletionReceipt.owner_id, DeletionReceipt.project_id))).all()
        totals = dict((await session.execute(
            select(RawAsset.owner_id, func.sum(RawAsset.byte_count)).group_by(RawAsset.owner_id)
        )).all())
        usage = dict((await session.execute(select(AccountUsage.user_id, AccountUsage.raw_bytes))).all())
        if any(usage.get(owner_id, 0) != count for owner_id, count in totals.items()):
            raise RuntimeError("account raw-byte quota counter differs from stored assets")
        if any(owner_id not in totals and count != 0 for owner_id, count in usage.items()):
            raise RuntimeError("account raw-byte quota counter has no matching assets")
        deleting = root / ".deleting"
        deleting.mkdir(parents=True, exist_ok=True)
        for path in deleting.iterdir():
            if not path.is_dir() or path.is_symlink():
                raise RuntimeError("unexpected deletion recovery entry")
            if "--" not in path.name:
                raise RuntimeError("cannot recover interrupted project deletion")
            owner_id, project_id = path.name.split("--", 1)
            if project_id in projects:
                destination = root / "projects" / owner_id / project_id
                if destination.exists():
                    raise RuntimeError("project deletion recovery collision")
                destination.parent.mkdir(parents=True, exist_ok=True)
                path.rename(destination)
            else:
                shutil.rmtree(path)
        for path in (root / "projects").glob("*/*/*"):
            if path.is_file() and not path.is_symlink():
                key = path.relative_to(root).as_posix()
                if key not in keys:
                    path.unlink()
        for key in keys:
            if not checked_storage_path(settings, key).is_file():
                raise RuntimeError(f"stored raw asset is missing: {key}")
        for owner_id, project_id in deleted:
            backup = root / ".backups" / str(owner_id) / project_id
            if backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup)
        for directory in sorted((root / "projects").glob("*/*"), reverse=True):
            if directory.is_dir() and not directory.is_symlink() and not any(directory.iterdir()):
                directory.rmdir()
        await session.commit()


def checked_storage_path(settings: Settings, storage_key: str) -> Path:
    parts = Path(storage_key).parts
    if len(parts) != 4 or parts[0] != "projects" or any(part in ("", ".", "..") for part in parts):
        raise RuntimeError("invalid private storage key")
    path = settings.data_dir.joinpath(*parts)
    root = settings.data_dir.resolve()
    if not path.resolve(strict=False).is_relative_to(root):
        raise RuntimeError("private storage path leaves the private root")
    for parent in (path, *path.parents):
        if parent == settings.data_dir:
            break
        if parent.is_symlink():
            raise RuntimeError("private storage path is a symlink")
    return path
